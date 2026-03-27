from __future__ import annotations

import asyncio
import json
import logging
import re

from openai import OpenAI

from app.locale import AppLocale
from app.models import Book, EnrichedBook, ReaderProfile, Recommendation
from app.services.recommendation_scoring import match_scores_for_recommendation_dicts
from app.services.settings_db import (
    SETTING_LLM_API_KEY,
    SETTING_LLM_BASE_URL,
    SETTING_LLM_MODEL_ENRICH,
    SETTING_LLM_MODEL_PROFILE,
    SETTING_LLM_MODEL_RECOMMEND,
    get_setting,
)
from config import config

logger = logging.getLogger(__name__)


def _resolve_online_llm_model() -> str:
    """LLM used for enrichment, recommendations, and tag localization.

    Prefer the recommendations setting; fall back to the legacy enrichment key
    and env defaults so older DB rows keep working.
    """
    return (
        get_setting(SETTING_LLM_MODEL_RECOMMEND)
        or get_setting(SETTING_LLM_MODEL_ENRICH)
        or config.LLM_MODEL_RECOMMEND
        or config.LLM_MODEL_ENRICH
    )


# Latin letters in genre/theme labels → needs Russian normalization for the RU UI.
_TAG_LATIN_RE = re.compile(r"[A-Za-z]")
# Cyrillic in labels → needs English normalization for the EN UI.
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")

# Shared across LLMClient instances: dedupes identical English labels across books
# and profile batch localization (see ProfileBuilder._enriched_books_ru_reader_labels).
_tag_ru_cache: dict[str, str] = {}
_tag_en_cache: dict[str, str] = {}
_tag_loc_lock: asyncio.Lock | None = None


def _norm_tag_key(s: str) -> str:
    return s.strip().lower()


def _tag_localization_lock() -> asyncio.Lock:
    global _tag_loc_lock
    if _tag_loc_lock is None:
        _tag_loc_lock = asyncio.Lock()
    return _tag_loc_lock


def _tags_contain_latin(tags: list[str]) -> bool:
    return any(_TAG_LATIN_RE.search(t) for t in tags if isinstance(t, str))


def _tags_contain_cyrillic(tags: list[str]) -> bool:
    return any(_CYRILLIC_RE.search(t) for t in tags if isinstance(t, str))


def _extract_json(text: str) -> dict | list:
    """Strip optional markdown fences and parse JSON."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    return json.loads(cleaned)


class LLMClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
    ) -> None:
        self._api_key = api_key or get_setting(SETTING_LLM_API_KEY) or ""
        self._base_url = (
            base_url
            or get_setting(SETTING_LLM_BASE_URL)
            or config.LLM_BASE_URL
        )
        self._client: OpenAI | None = None

    def _ensure_client(self) -> OpenAI:
        """Lazily create the OpenAI client, raising if no key is configured."""
        if not self._api_key:
            raise ValueError(
                "LLM API key not configured. Go to Settings to add your key."
            )
        if self._client is None:
            self._client = OpenAI(
                api_key=self._api_key, base_url=self._base_url,
            )
        return self._client

    def _chat(
        self,
        prompt: str,
        model: str,
        *,
        temperature: float = 0.4,
    ) -> str:
        client = self._ensure_client()
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
        )
        return response.choices[0].message.content or ""

    # ------------------------------------------------------------------
    # Public async API
    # ------------------------------------------------------------------

    async def enrich_book(
        self,
        book: Book,
        *,
        locale: AppLocale = "ru",
        model: str | None = None,
    ) -> EnrichedBook:
        model = model or _resolve_online_llm_model()
        prompt = self._build_enrichment_prompt(book, locale)
        raw = await asyncio.to_thread(self._chat, prompt, model)

        try:
            data = _extract_json(raw)
        except (json.JSONDecodeError, ValueError):
            logger.error(
                "Failed to parse enrichment JSON for '%s': %s",
                book.title,
                raw[:300],
            )
            return EnrichedBook(book=book)

        if not isinstance(data, dict):
            return EnrichedBook(book=book)

        genres = [str(x).strip() for x in data.get("genres", []) if x is not None]
        themes = [str(x).strip() for x in data.get("themes", []) if x is not None]
        mood = str(data.get("mood", "") or "").strip()
        moods_in = [mood] if mood else []
        if locale == "ru":
            if (
                _tags_contain_latin(genres)
                or _tags_contain_latin(themes)
                or _tags_contain_latin(moods_in)
            ):
                genres, themes, moods_out = await self.localize_tag_vocab_ru(
                    genres, themes, moods_in,
                )
                mood = moods_out[0] if moods_out else mood
        else:
            if (
                _tags_contain_cyrillic(genres)
                or _tags_contain_cyrillic(themes)
                or _tags_contain_cyrillic(moods_in)
            ):
                genres, themes, moods_out = await self.localize_tag_vocab_en(
                    genres, themes, moods_in,
                )
                mood = moods_out[0] if moods_out else mood

        return EnrichedBook(
            book=book,
            genres=genres,
            themes=themes,
            mood=mood,
            complexity=data.get("complexity", ""),
            similar_authors=data.get("similar_authors", []),
        )

    async def summarize_profile(
        self,
        profile: ReaderProfile,
        *,
        locale: AppLocale = "ru",
        model: str | None = None,
    ) -> str:
        model = (
            model
            or get_setting(SETTING_LLM_MODEL_PROFILE)
            or config.LLM_MODEL_PROFILE
        )
        prompt = self._build_profile_summary_prompt(profile, locale)
        return await asyncio.to_thread(self._chat, prompt, model)

    async def get_recommendations(
        self,
        profile: ReaderProfile,
        read_books: list[Book],
        num: int = 5,
        *,
        locale: AppLocale = "ru",
        model: str | None = None,
    ) -> list[Recommendation]:
        model = model or _resolve_online_llm_model()
        prompt = self._build_recommendation_prompt(
            profile, read_books, num, locale,
        )
        raw = await asyncio.to_thread(
            self._chat, prompt, model, temperature=0.6,
        )

        try:
            data = _extract_json(raw)
        except (json.JSONDecodeError, ValueError):
            logger.error("Failed to parse recommendations JSON: %s", raw[:500])
            return []

        items = data if isinstance(data, list) else data.get("recommendations", [])
        raw_items = [item for item in items[:num] if isinstance(item, dict)]
        filled = match_scores_for_recommendation_dicts(profile, raw_items)

        recommendations: list[Recommendation] = []
        for item, match_score in zip(raw_items, filled, strict=True):
            genres = (
                item.get("genres", [])
                if isinstance(item.get("genres"), list)
                else []
            )
            themes = (
                item.get("themes", [])
                if isinstance(item.get("themes"), list)
                else []
            )
            recommendations.append(
                Recommendation(
                    title=str(item.get("title", "")),
                    author=str(item.get("author", "")),
                    genres=[str(x) for x in genres if x is not None],
                    themes=[str(x) for x in themes if x is not None],
                    reasoning=str(item.get("reasoning", "")),
                    match_score=match_score,
                )
            )
        return recommendations

    async def _localize_latin_tag_strings(
        self,
        tags_in: list[str],
        model: str,
    ) -> list[str]:
        """Translate a list of Latin-containing labels to Russian; same length/order."""
        if not tags_in:
            return []
        g_in = list(tags_in)
        last_ok: list[str] | None = None

        for attempt in range(2):
            payload = {"tags": g_in}
            retry_note = ""
            if attempt == 1:
                retry_note = (
                    "The previous output still contained Latin letters. "
                    "Translate EVERY remaining Latin character to Russian. "
                    "Keep the same array length and order.\n\n"
                )
            prompt = (
                retry_note
                + "You normalize literary metadata for a Russian reading app UI.\n\n"
                "Rules:\n"
                '- Return ONLY valid JSON (no markdown, no commentary).\n'
                '- Output: {"tags": [...]}.\n'
                "- Output length and order MUST match the input tags.\n"
                "- Each tag: short Russian literary label (lowercase, 1–4 words). "
                "Translate every Latin letter: e.g. coming-of-age → взросление; "
                "fiction → художественная проза (or an appropriate short Russian genre label).\n"
                "- Pure Cyrillic labels: keep unchanged.\n"
                "- Never leave English in the output.\n\n"
                f"Input:\n{json.dumps(payload, ensure_ascii=False)}\n"
            )
            raw = await asyncio.to_thread(
                self._chat, prompt, model, temperature=0.1,
            )
            try:
                data = _extract_json(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(
                    "Tag localization: JSON parse failed; %s",
                    (raw or "")[:200],
                )
                return list(tags_in) if attempt == 0 else list(g_in)
            if not isinstance(data, dict):
                return list(tags_in) if attempt == 0 else list(g_in)
            out = data.get("tags")
            if not isinstance(out, list) or len(out) != len(g_in):
                logger.warning(
                    "Tag localization: tags length mismatch; keeping inputs.",
                )
                return list(tags_in) if attempt == 0 else list(g_in)
            fixed = [
                str(x).strip() if str(x).strip() else g_in[i]
                for i, x in enumerate(out)
            ]
            last_ok = fixed
            if not _tags_contain_latin(fixed):
                return fixed
            g_in = fixed

        return last_ok if last_ok is not None else list(tags_in)

    async def localize_tag_vocab_ru(
        self,
        genres: list[str],
        themes: list[str],
        moods: list[str] | None = None,
        model: str | None = None,
    ) -> tuple[list[str], list[str], list[str]]:
        """Map genre, theme, and mood strings to Russian (fixes model/cache English)."""
        genres = [str(g).strip() for g in genres if str(g).strip()]
        themes = [str(t).strip() for t in themes if str(t).strip()]
        moods = [str(m).strip() for m in (moods or []) if str(m).strip()]
        if not genres and not themes and not moods:
            return [], [], []
        if (
            not _tags_contain_latin(genres)
            and not _tags_contain_latin(themes)
            and not _tags_contain_latin(moods)
        ):
            return genres, themes, moods

        model = model or _resolve_online_llm_model()

        def map_label(s: str) -> str:
            if not _TAG_LATIN_RE.search(s):
                return s
            k = _norm_tag_key(s)
            return _tag_ru_cache.get(k, s)

        lock = _tag_localization_lock()
        async with lock:
            seen_norm: set[str] = set()
            to_fetch: list[str] = []
            for lst in (genres, themes, moods):
                for s in lst:
                    if not _TAG_LATIN_RE.search(s):
                        continue
                    k = _norm_tag_key(s)
                    if k in seen_norm:
                        continue
                    seen_norm.add(k)
                    if k not in _tag_ru_cache:
                        to_fetch.append(s)

        if to_fetch:
            ru_list = await self._localize_latin_tag_strings(to_fetch, model)
            if len(ru_list) != len(to_fetch):
                logger.warning(
                    "Tag localization: batch length mismatch; skipping cache merge.",
                )
                ru_list = list(to_fetch)
            async with lock:
                for src, ru in zip(to_fetch, ru_list):
                    if not _TAG_LATIN_RE.search(ru):
                        _tag_ru_cache[_norm_tag_key(src)] = ru

        out_g = [map_label(s) for s in genres]
        out_t = [map_label(s) for s in themes]
        out_m = [map_label(s) for s in moods]

        if (
            _tags_contain_latin(out_g)
            or _tags_contain_latin(out_t)
            or _tags_contain_latin(out_m)
        ):
            return await self._localize_tag_vocab_ru_legacy(
                out_g, out_t, out_m, model=model,
            )

        return out_g, out_t, out_m

    async def _localize_tag_vocab_ru_legacy(
        self,
        genres: list[str],
        themes: list[str],
        moods: list[str],
        model: str,
    ) -> tuple[list[str], list[str], list[str]]:
        """Fallback: structured three-array prompt when flat-tag batch left Latin."""
        g_in, t_in, m_in = genres, themes, moods
        last_ok: tuple[list[str], list[str], list[str]] | None = None

        for attempt in range(2):
            payload = {"genres": g_in, "themes": t_in, "moods": m_in}
            retry_note = ""
            if attempt == 1:
                retry_note = (
                    "The previous output still contained Latin letters. "
                    "Translate EVERY remaining Latin character to Russian. "
                    "Keep the same three array lengths and order.\n\n"
                )
            prompt = (
                retry_note
                + "You normalize literary metadata for a Russian reading app UI.\n\n"
                "Rules:\n"
                '- Return ONLY valid JSON (no markdown, no commentary).\n'
                '- Output: {"genres": [...], "themes": [...], "moods": [...]}.\n'
                "- Each output array MUST match its input length and order.\n"
                "- genres/themes: short Russian literary labels (lowercase, 1–4 words). "
                "Translate every Latin letter: e.g. coming-of-age → взросление; "
                "motherhood → материнство.\n"
                "- moods: one short Russian phrase for overall reading tone "
                "(e.g. приподнятое, мрачное, философское). No English words.\n"
                "- Pure Cyrillic labels: keep unchanged.\n"
                "- Never leave English in the output.\n\n"
                f"Input:\n{json.dumps(payload, ensure_ascii=False)}\n"
            )
            raw = await asyncio.to_thread(
                self._chat, prompt, model, temperature=0.1,
            )
            try:
                data = _extract_json(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(
                    "Tag localization: JSON parse failed; %s",
                    (raw or "")[:200],
                )
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            if not isinstance(data, dict):
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            out_g = data.get("genres")
            out_t = data.get("themes")
            out_m = data.get("moods")
            if not isinstance(out_g, list) or not isinstance(out_t, list):
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            if not isinstance(out_m, list):
                out_m = []
            if len(out_m) != len(m_in):
                logger.warning(
                    "Tag localization: moods length mismatch; keeping mood inputs.",
                )
                out_m = list(m_in)
            if len(out_g) != len(g_in) or len(out_t) != len(t_in):
                logger.warning(
                    "Tag localization: length mismatch; keeping originals.",
                )
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            fixed_g = [
                str(x).strip() if str(x).strip() else g_in[i]
                for i, x in enumerate(out_g)
            ]
            fixed_t = [
                str(x).strip() if str(x).strip() else t_in[i]
                for i, x in enumerate(out_t)
            ]
            fixed_m = [
                str(x).strip() if str(x).strip() else m_in[i]
                for i, x in enumerate(out_m)
            ]
            last_ok = (fixed_g, fixed_t, fixed_m)
            still_latin = (
                _tags_contain_latin(fixed_g)
                or _tags_contain_latin(fixed_t)
                or _tags_contain_latin(fixed_m)
            )
            if not still_latin:
                async with _tag_localization_lock():
                    for lst_src, lst_out in (
                        (genres, fixed_g),
                        (themes, fixed_t),
                        (moods, fixed_m),
                    ):
                        for a, b in zip(lst_src, lst_out, strict=True):
                            if _TAG_LATIN_RE.search(a):
                                _tag_ru_cache[_norm_tag_key(a)] = b
                return fixed_g, fixed_t, fixed_m
            g_in, t_in, m_in = fixed_g, fixed_t, fixed_m

        result = last_ok if last_ok else (genres, themes, moods)
        return result

    async def _localize_cyrillic_tag_strings(
        self,
        tags_in: list[str],
        model: str,
    ) -> list[str]:
        """Translate Cyrillic-containing labels to English; same length/order."""
        if not tags_in:
            return []
        g_in = list(tags_in)
        last_ok: list[str] | None = None

        for attempt in range(2):
            payload = {"tags": g_in}
            retry_note = ""
            if attempt == 1:
                retry_note = (
                    "The previous output still contained Cyrillic characters. "
                    "Rewrite EVERY tag using Latin letters only (English). "
                    "Keep the same array length and order.\n\n"
                )
            prompt = (
                retry_note
                + "You normalize literary metadata for an English reading app UI.\n\n"
                "Rules:\n"
                '- Return ONLY valid JSON (no markdown, no commentary).\n'
                '- Output: {"tags": [...]}.\n'
                "- Output length and order MUST match the input tags.\n"
                "- Each tag: short English literary label (lowercase, 1–4 words). "
                "Replace Cyrillic with clear English equivalents.\n"
                "- Pure ASCII English labels: keep unchanged.\n"
                "- Do not leave Cyrillic in the output.\n\n"
                f"Input:\n{json.dumps(payload, ensure_ascii=False)}\n"
            )
            raw = await asyncio.to_thread(
                self._chat, prompt, model, temperature=0.1,
            )
            try:
                data = _extract_json(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(
                    "EN tag localization: JSON parse failed; %s",
                    (raw or "")[:200],
                )
                return list(tags_in) if attempt == 0 else list(g_in)
            if not isinstance(data, dict):
                return list(tags_in) if attempt == 0 else list(g_in)
            out = data.get("tags")
            if not isinstance(out, list) or len(out) != len(g_in):
                logger.warning(
                    "EN tag localization: tags length mismatch; keeping inputs.",
                )
                return list(tags_in) if attempt == 0 else list(g_in)
            fixed = [
                str(x).strip() if str(x).strip() else g_in[i]
                for i, x in enumerate(out)
            ]
            last_ok = fixed
            if not _tags_contain_cyrillic(fixed):
                return fixed
            g_in = fixed

        return last_ok if last_ok is not None else list(tags_in)

    async def localize_tag_vocab_en(
        self,
        genres: list[str],
        themes: list[str],
        moods: list[str] | None = None,
        model: str | None = None,
    ) -> tuple[list[str], list[str], list[str]]:
        """Map genre, theme, and mood strings to English (fixes Cyrillic output)."""
        genres = [str(g).strip() for g in genres if str(g).strip()]
        themes = [str(t).strip() for t in themes if str(t).strip()]
        moods = [str(m).strip() for m in (moods or []) if str(m).strip()]
        if not genres and not themes and not moods:
            return [], [], []
        if (
            not _tags_contain_cyrillic(genres)
            and not _tags_contain_cyrillic(themes)
            and not _tags_contain_cyrillic(moods)
        ):
            return genres, themes, moods

        model = model or _resolve_online_llm_model()

        def map_label(s: str) -> str:
            if not _CYRILLIC_RE.search(s):
                return s
            k = _norm_tag_key(s)
            return _tag_en_cache.get(k, s)

        lock = _tag_localization_lock()
        async with lock:
            seen_norm: set[str] = set()
            to_fetch: list[str] = []
            for lst in (genres, themes, moods):
                for s in lst:
                    if not _CYRILLIC_RE.search(s):
                        continue
                    k = _norm_tag_key(s)
                    if k in seen_norm:
                        continue
                    seen_norm.add(k)
                    if k not in _tag_en_cache:
                        to_fetch.append(s)

        if to_fetch:
            en_list = await self._localize_cyrillic_tag_strings(to_fetch, model)
            if len(en_list) != len(to_fetch):
                logger.warning(
                    "EN tag localization: batch length mismatch; skipping cache merge.",
                )
                en_list = list(to_fetch)
            async with lock:
                for src, en in zip(to_fetch, en_list):
                    if not _CYRILLIC_RE.search(en):
                        _tag_en_cache[_norm_tag_key(src)] = en

        out_g = [map_label(s) for s in genres]
        out_t = [map_label(s) for s in themes]
        out_m = [map_label(s) for s in moods]

        if (
            _tags_contain_cyrillic(out_g)
            or _tags_contain_cyrillic(out_t)
            or _tags_contain_cyrillic(out_m)
        ):
            return await self._localize_tag_vocab_en_legacy(
                out_g, out_t, out_m, model=model,
            )

        return out_g, out_t, out_m

    async def _localize_tag_vocab_en_legacy(
        self,
        genres: list[str],
        themes: list[str],
        moods: list[str],
        model: str,
    ) -> tuple[list[str], list[str], list[str]]:
        """Fallback: structured three-array prompt when flat-tag batch left Cyrillic."""
        g_in, t_in, m_in = genres, themes, moods
        last_ok: tuple[list[str], list[str], list[str]] | None = None

        for attempt in range(2):
            payload = {"genres": g_in, "themes": t_in, "moods": m_in}
            retry_note = ""
            if attempt == 1:
                retry_note = (
                    "The previous output still contained Cyrillic characters. "
                    "Rewrite EVERY tag using Latin letters only (English). "
                    "Keep the same three array lengths and order.\n\n"
                )
            prompt = (
                retry_note
                + "You normalize literary metadata for an English reading app UI.\n\n"
                "Rules:\n"
                '- Return ONLY valid JSON (no markdown, no commentary).\n'
                '- Output: {"genres": [...], "themes": [...], "moods": [...]}.\n'
                "- Each output array MUST match its input length and order.\n"
                "- genres/themes: short English literary labels (lowercase, 1–4 words).\n"
                "- moods: one short English phrase for overall reading tone.\n"
                "- Pure ASCII English labels: keep unchanged.\n"
                "- Do not leave Cyrillic in the output.\n\n"
                f"Input:\n{json.dumps(payload, ensure_ascii=False)}\n"
            )
            raw = await asyncio.to_thread(
                self._chat, prompt, model, temperature=0.1,
            )
            try:
                data = _extract_json(raw)
            except (json.JSONDecodeError, ValueError, TypeError):
                logger.warning(
                    "EN tag localization: JSON parse failed; %s",
                    (raw or "")[:200],
                )
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            if not isinstance(data, dict):
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            out_g = data.get("genres")
            out_t = data.get("themes")
            out_m = data.get("moods")
            if not isinstance(out_g, list) or not isinstance(out_t, list):
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            if not isinstance(out_m, list):
                out_m = []
            if len(out_m) != len(m_in):
                logger.warning(
                    "EN tag localization: moods length mismatch; keeping mood inputs.",
                )
                out_m = list(m_in)
            if len(out_g) != len(g_in) or len(out_t) != len(t_in):
                logger.warning(
                    "EN tag localization: length mismatch; keeping originals.",
                )
                return (genres, themes, moods) if attempt == 0 else (g_in, t_in, m_in)
            fixed_g = [
                str(x).strip() if str(x).strip() else g_in[i]
                for i, x in enumerate(out_g)
            ]
            fixed_t = [
                str(x).strip() if str(x).strip() else t_in[i]
                for i, x in enumerate(out_t)
            ]
            fixed_m = [
                str(x).strip() if str(x).strip() else m_in[i]
                for i, x in enumerate(out_m)
            ]
            last_ok = (fixed_g, fixed_t, fixed_m)
            still_cyr = (
                _tags_contain_cyrillic(fixed_g)
                or _tags_contain_cyrillic(fixed_t)
                or _tags_contain_cyrillic(fixed_m)
            )
            if not still_cyr:
                async with _tag_localization_lock():
                    for lst_src, lst_out in (
                        (genres, fixed_g),
                        (themes, fixed_t),
                        (moods, fixed_m),
                    ):
                        for a, b in zip(lst_src, lst_out, strict=True):
                            if _CYRILLIC_RE.search(a):
                                _tag_en_cache[_norm_tag_key(a)] = b
                return fixed_g, fixed_t, fixed_m
            g_in, t_in, m_in = fixed_g, fixed_t, fixed_m

        result = last_ok if last_ok else (genres, themes, moods)
        return result

    # ------------------------------------------------------------------
    # Prompt builders
    # ------------------------------------------------------------------

    @staticmethod
    def _build_enrichment_prompt(book: Book, locale: AppLocale) -> str:
        if locale == "ru":
            return (
                f'You are a literary analyst. Analyze the book '
                f'"{book.title}" by {book.author}.\n\n'
                f'Search the internet for professional and reader reviews of this '
                f'book. Based on your findings, extract the following structured '
                f'data and return it as a single JSON object:\n\n'
                f'{{\n'
                f'  "genres": ["основной жанр", "дополнительный жанр"],\n'
                f'  "themes": ["тема1", "тема2", "тема3"],\n'
                f'  "mood": "на русском: краткое настроение (1–2 слова, например '
                f'мрачное, приподнятое, философское)",\n'
                f'  "complexity": "light | moderate | complex",\n'
                f'  "similar_authors": ["author1", "author2"]\n'
                f'}}\n\n'
                f'Use Russian only for "genres", "themes", and "mood": short '
                f'labels (1–3 words). Do NOT use Latin in those fields (forbidden: '
                f'"fiction", "coming-of-age", "uplifting", "dark"). '
                f'Other string fields may stay English where noted.\n\n'
                f'Return ONLY valid JSON. No markdown, no explanations.'
            )
        return (
            f'You are a literary analyst. Analyze the book '
            f'"{book.title}" by {book.author}.\n\n'
            f'Search the internet for professional and reader reviews of this '
            f'book. Based on your findings, extract the following structured '
            f'data and return it as a single JSON object:\n\n'
            f'{{\n'
            f'  "genres": ["primary genre", "secondary genre"],\n'
            f'  "themes": ["theme1", "theme2", "theme3"],\n'
            f'  "mood": "short mood in English (1–2 words, e.g. dark, uplifting, '
            f'philosophical)",\n'
            f'  "complexity": "light | moderate | complex",\n'
            f'  "similar_authors": ["Author One", "Author Two"]\n'
            f'}}\n\n'
            f'Use English only for "genres", "themes", and "mood": short '
            f'labels (1–3 words). Do NOT use Cyrillic in those fields. '
            f'Author names may use their usual Latin spelling.\n\n'
            f'Return ONLY valid JSON. No markdown, no explanations.'
        )

    @staticmethod
    def _build_profile_summary_prompt(
        profile: ReaderProfile,
        locale: AppLocale,
    ) -> str:
        genres = ", ".join(
            f"{t.name} ({t.weight:.0%})" for t in profile.top_genres[:8]
        )
        themes = ", ".join(
            f"{t.name} ({t.weight:.0%})" for t in profile.top_themes[:10]
        )
        moods = ", ".join(profile.preferred_moods) or "not determined"
        authors = ", ".join(profile.favorite_authors[:10]) or "not determined"

        if locale == "ru":
            return (
                f"Based on the following structured reading preferences, write a "
                f"concise 3-5 sentence portrait of this reader's literary taste. "
                f"Address the reader as \u00abВы\u00bb (formal Russian).\n\n"
                f"Top genres: {genres}\n"
                f"Key themes: {themes}\n"
                f"Preferred moods: {moods}\n"
                f"Preferred complexity: {profile.preferred_complexity or 'varied'}\n"
                f"Favorite authors: {authors}\n"
                f"Books analyzed: {profile.books_analyzed}\n\n"
                f"Write in Russian. Be specific and insightful, not generic."
            )
        return (
            f"Based on the following structured reading preferences, write a "
            f"concise 3-5 sentence portrait of this reader's literary taste. "
            f"Address the reader as \"you\" (plain English).\n\n"
            f"Top genres: {genres}\n"
            f"Key themes: {themes}\n"
            f"Preferred moods: {moods}\n"
            f"Preferred complexity: {profile.preferred_complexity or 'varied'}\n"
            f"Favorite authors: {authors}\n"
            f"Books analyzed: {profile.books_analyzed}\n\n"
            f"Write in English. Be specific and insightful, not generic."
        )

    @staticmethod
    def _build_recommendation_prompt(
        profile: ReaderProfile,
        read_books: list[Book],
        num: int,
        locale: AppLocale,
    ) -> str:
        read_list = "\n".join(
            f"- {b.title} / {b.author}" for b in read_books
        )

        genres = ", ".join(t.name for t in profile.top_genres[:8])
        themes = ", ".join(t.name for t in profile.top_themes[:10])
        moods = ", ".join(profile.preferred_moods) or "varied"
        authors = ", ".join(profile.favorite_authors[:10]) or "various"

        if locale == "ru":
            return (
                f"You are an experienced literary critic and personal "
                f"recommendation service. Your task is to find books the reader "
                f"will love.\n\n"
                f"### Reader taste (structured signals only)\n"
                f"Use this block ONLY to choose titles. Do NOT paste, summarize, "
                f"or paraphrase it in any user-facing text. No prose portrait of "
                f"the reader is provided on purpose.\n"
                f"Top genres: {genres}\n"
                f"Key themes: {themes}\n"
                f"Preferred moods: {moods}\n"
                f"Preferred complexity: "
                f"{profile.preferred_complexity or 'varied'}\n"
                f"Favorite authors: {authors}\n\n"
                f"### Books already read (EXCLUDE all of these):\n"
                f"{read_list}\n\n"
                f"### Task\n"
                f"Search the internet and recommend exactly {num} books.\n\n"
                f"### Rules\n"
                f"1. Recommend ONLY specific real books (title + author). "
                f"Do NOT invent books.\n"
                f"2. EXCLUDE every book from the \u00abalready read\u00bb list.\n"
                f"3. IGNORE compilations, \u00abtop-10\u00bb lists, and "
                f"\u00abbest books about X\u00bb articles.\n"
                f"4. At least 70% of recommendations must precisely match the "
                f"reader's preferences. The remaining may be \u00abintentional "
                f"randomness\u00bb \u2014 books from adjacent genres that share "
                f"mood or thematic DNA with the reader's taste.\n"
                f"5. Field \u00abreasoning\u00bb: 2\u20134 sentences in Russian "
                f"about the BOOK only. Spoiler-free. Use third person or "
                f"impersonal style (роман, действие, автор, произведение).\n"
                f"6. In \u00abreasoning\u00bb it is FORBIDDEN to address the "
                f"reader, describe their tastes, or explain why the pick suits "
                f"them: do not use \u00abвы\u00bb, \u00abвам\u00bb, \u00abваш"
                f"\u00bb, \u00abтебе\u00bb, \u00abчитатель предпочитает\u00bb, or "
                f"similar. Do NOT name books from the reader's library.\n"
                f"7. Each \u00abreasoning\u00bb must open and read differently "
                f"from the others (no shared template).\n"
                f"8. Fields \u00abgenres\u00bb and \u00abthemes\u00bb: Russian only "
                f"— \u00abgenres\u00bb: 1\u20132 short labels; \u00abthemes\u00bb: "
                f"2\u20135 short tags for THIS book. Prefer overlap with the "
                f"reader's \u00abTop genres\u00bb and \u00abKey themes\u00bb when "
                f"accurate.\n\n"
                f"### Response format\n"
                f"Return a JSON array (no wrapping object):\n"
                f"[\n"
                f'  {{\n'
                f'    "title": "Book Title",\n'
                f'    "author": "Author Name",\n'
                f'    "genres": ["жанр1", "жанр2"],\n'
                f'    "themes": ["тема1", "тема2", "тема3"],\n'
                f'    "reasoning": "neutral third-person book blurb only"\n'
                f"  }}\n"
                f"]\n\n"
                f"Return ONLY valid JSON. No markdown, no extra text."
            )
        return (
            f"You are an experienced literary critic and personal "
            f"recommendation service. Your task is to find books the reader "
            f"will love.\n\n"
            f"### Reader taste (structured signals only)\n"
            f"Use this block ONLY to choose titles. Do NOT paste, summarize, "
            f"or paraphrase it in any user-facing text.\n"
            f"Top genres: {genres}\n"
            f"Key themes: {themes}\n"
            f"Preferred moods: {moods}\n"
            f"Preferred complexity: "
            f"{profile.preferred_complexity or 'varied'}\n"
            f"Favorite authors: {authors}\n\n"
            f"### Books already read (EXCLUDE all of these):\n"
            f"{read_list}\n\n"
            f"### Task\n"
            f"Search the internet and recommend exactly {num} books.\n\n"
            f"### Rules\n"
            f"1. Recommend ONLY specific real books (title + author). "
            f"Do NOT invent books.\n"
            f"2. EXCLUDE every book from the already read list.\n"
            f"3. IGNORE compilations, top-10 lists, and "
            f"best-books-about-X articles.\n"
            f"4. At least 70% of recommendations must precisely match the "
            f"reader's preferences. The remaining may be intentional "
            f"randomness: adjacent genres that share mood or thematic DNA.\n"
            f"5. Field reasoning: 2–4 sentences in English about the BOOK only. "
            f"Spoiler-free. Third person or neutral (the novel, the author, "
            f"the story).\n"
            f"6. In reasoning it is FORBIDDEN to address the reader, describe "
            f"their tastes, or explain why the pick suits them. Do NOT name "
            f"books from the reader's library.\n"
            f"7. Each reasoning must open and read differently from the others.\n"
            f"8. Fields genres and themes: English only — genres: 1–2 short "
            f"labels; themes: 2–5 short tags for THIS book. Prefer overlap with "
            f"the reader signals when accurate.\n\n"
            f"### Response format\n"
            f"Return a JSON array (no wrapping object):\n"
            f"[\n"
            f'  {{\n'
            f'    "title": "Book Title",\n'
            f'    "author": "Author Name",\n'
            f'    "genres": ["genre1", "genre2"],\n'
            f'    "themes": ["theme1", "theme2", "theme3"],\n'
            f'    "reasoning": "neutral third-person book blurb only"\n'
            f"  }}\n"
            f"]\n\n"
            f"Return ONLY valid JSON. No markdown, no extra text."
        )
