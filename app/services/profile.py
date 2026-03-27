from __future__ import annotations

import logging
import re
from collections import Counter

from app.locale import AppLocale
from app.models import EnrichedBook, ReaderProfile, WeightedTag
from app.services.cache import CacheNamespace, get_cached, make_key, set_cache
from app.services.llm import LLMClient

logger = logging.getLogger(__name__)

NS = CacheNamespace.READER_PROFILE

_TAG_LATIN_RE = re.compile(r"[A-Za-z]")
_CYRILLIC_RE = re.compile(r"[\u0400-\u04FF]")


def _tags_contain_latin(tags: list[str]) -> bool:
    return any(_TAG_LATIN_RE.search(t) for t in tags if isinstance(t, str))


def _reader_profile_tags_contain_latin(profile: ReaderProfile) -> bool:
    return (
        _tags_contain_latin([t.name for t in profile.top_genres])
        or _tags_contain_latin([t.name for t in profile.top_themes])
        or _tags_contain_latin(profile.preferred_moods)
    )


def _tags_contain_cyrillic(tags: list[str]) -> bool:
    return any(_CYRILLIC_RE.search(t) for t in tags if isinstance(t, str))


def _reader_profile_tags_contain_cyrillic(profile: ReaderProfile) -> bool:
    return (
        _tags_contain_cyrillic([t.name for t in profile.top_genres])
        or _tags_contain_cyrillic([t.name for t in profile.top_themes])
        or _tags_contain_cyrillic(profile.preferred_moods)
    )


class ProfileBuilder:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm

    @staticmethod
    def _profile_cache_keys(locale: AppLocale, book_ids: list[str]) -> list[str]:
        sorted_ids = sorted(book_ids)
        primary = make_key(locale, *sorted_ids)
        if locale == "ru":
            return [primary, make_key(*sorted_ids)]
        return [primary]

    async def build_profile(
        self,
        enriched_books: list[EnrichedBook],
        force: bool = False,
        *,
        locale: AppLocale = "ru",
    ) -> ReaderProfile:
        book_ids = sorted(eb.book.get_id() for eb in enriched_books)

        if not force:
            for cache_key in self._profile_cache_keys(locale, book_ids):
                cached = await get_cached(NS, cache_key)
                if cached is None:
                    continue
                prof = ReaderProfile.model_validate(cached)
                if locale == "ru" and _reader_profile_tags_contain_latin(prof):
                    continue
                if locale == "en" and _reader_profile_tags_contain_cyrillic(prof):
                    continue
                return prof

        if locale == "ru":
            enriched_books = await self._enriched_books_ru_reader_labels(
                enriched_books,
            )
        else:
            enriched_books = await self._enriched_books_en_reader_labels(
                enriched_books,
            )
        profile = self._aggregate(enriched_books)

        logger.info("Generating profile summary via LLM (%d books)", len(enriched_books))
        profile.summary = await self._llm.summarize_profile(profile, locale=locale)

        store_key = make_key(locale, *book_ids)
        await set_cache(NS, store_key, profile.model_dump())
        return profile

    async def _enriched_books_ru_reader_labels(
        self,
        enriched_books: list[EnrichedBook],
    ) -> list[EnrichedBook]:
        """One LLM pass over unique genres, themes, and moods so cached
        English enrichments still produce an all-Russian profile."""
        g_repr: dict[str, str] = {}
        t_repr: dict[str, str] = {}
        m_repr: dict[str, str] = {}
        for eb in enriched_books:
            for g in eb.genres:
                if isinstance(g, str):
                    k = g.lower().strip()
                    if k and k not in g_repr:
                        g_repr[k] = g.strip()
            for t in eb.themes:
                if isinstance(t, str):
                    k = t.lower().strip()
                    if k and k not in t_repr:
                        t_repr[k] = t.strip()
            if isinstance(eb.mood, str):
                mk = eb.mood.lower().strip()
                if mk and mk not in m_repr:
                    m_repr[mk] = eb.mood.strip()

        ug = [g_repr[k] for k in sorted(g_repr)]
        ut = [t_repr[k] for k in sorted(t_repr)]
        um = [m_repr[k] for k in sorted(m_repr)]
        if not ug and not ut and not um:
            return enriched_books
        if (
            not _tags_contain_latin(ug)
            and not _tags_contain_latin(ut)
            and not _tags_contain_latin(um)
        ):
            return enriched_books

        ug_ru, ut_ru, um_ru = await self._llm.localize_tag_vocab_ru(
            ug, ut, um,
        )
        g_map = {
            ug[i].lower().strip(): ug_ru[i].strip() for i in range(len(ug))
        }
        t_map = {
            ut[i].lower().strip(): ut_ru[i].strip() for i in range(len(ut))
        }
        m_map = {
            um[i].lower().strip(): um_ru[i].strip() for i in range(len(um))
        }

        out: list[EnrichedBook] = []
        for eb in enriched_books:
            new_genres = [
                g_map.get(str(g).lower().strip(), str(g).strip())
                for g in eb.genres
            ]
            new_themes = [
                t_map.get(str(t).lower().strip(), str(t).strip())
                for t in eb.themes
            ]
            mood_raw = str(eb.mood).strip() if isinstance(eb.mood, str) else ""
            new_mood = (
                m_map.get(mood_raw.lower(), mood_raw) if mood_raw else ""
            )
            out.append(
                eb.model_copy(
                    update={
                        "genres": new_genres,
                        "themes": new_themes,
                        "mood": new_mood,
                    },
                ),
            )
        return out

    async def _enriched_books_en_reader_labels(
        self,
        enriched_books: list[EnrichedBook],
    ) -> list[EnrichedBook]:
        """Normalize Cyrillic-heavy labels to English for an English UI."""
        g_repr: dict[str, str] = {}
        t_repr: dict[str, str] = {}
        m_repr: dict[str, str] = {}
        for eb in enriched_books:
            for g in eb.genres:
                if isinstance(g, str):
                    k = g.lower().strip()
                    if k and k not in g_repr:
                        g_repr[k] = g.strip()
            for t in eb.themes:
                if isinstance(t, str):
                    k = t.lower().strip()
                    if k and k not in t_repr:
                        t_repr[k] = t.strip()
            if isinstance(eb.mood, str):
                mk = eb.mood.lower().strip()
                if mk and mk not in m_repr:
                    m_repr[mk] = eb.mood.strip()

        ug = [g_repr[k] for k in sorted(g_repr)]
        ut = [t_repr[k] for k in sorted(t_repr)]
        um = [m_repr[k] for k in sorted(m_repr)]
        if not ug and not ut and not um:
            return enriched_books
        if (
            not _tags_contain_cyrillic(ug)
            and not _tags_contain_cyrillic(ut)
            and not _tags_contain_cyrillic(um)
        ):
            return enriched_books

        ug_en, ut_en, um_en = await self._llm.localize_tag_vocab_en(ug, ut, um)
        g_map = {
            ug[i].lower().strip(): ug_en[i].strip() for i in range(len(ug))
        }
        t_map = {
            ut[i].lower().strip(): ut_en[i].strip() for i in range(len(ut))
        }
        m_map = {
            um[i].lower().strip(): um_en[i].strip() for i in range(len(um))
        }

        out: list[EnrichedBook] = []
        for eb in enriched_books:
            new_genres = [
                g_map.get(str(g).lower().strip(), str(g).strip())
                for g in eb.genres
            ]
            new_themes = [
                t_map.get(str(t).lower().strip(), str(t).strip())
                for t in eb.themes
            ]
            mood_raw = str(eb.mood).strip() if isinstance(eb.mood, str) else ""
            new_mood = (
                m_map.get(mood_raw.lower(), mood_raw) if mood_raw else ""
            )
            out.append(
                eb.model_copy(
                    update={
                        "genres": new_genres,
                        "themes": new_themes,
                        "mood": new_mood,
                    },
                ),
            )
        return out

    # ------------------------------------------------------------------
    # Aggregation
    # ------------------------------------------------------------------

    @staticmethod
    def _aggregate(enriched_books: list[EnrichedBook]) -> ReaderProfile:
        genre_weights: Counter[str] = Counter()
        theme_weights: Counter[str] = Counter()
        mood_counts: Counter[str] = Counter()
        complexity_counts: Counter[str] = Counter()
        author_weights: Counter[str] = Counter()
        total_weight = 0.0

        for eb in enriched_books:
            weight = eb.book.rating or 1
            total_weight += weight

            for genre in eb.genres:
                genre_weights[genre.lower().strip()] += weight
            for theme in eb.themes:
                theme_weights[theme.lower().strip()] += weight
            if eb.mood:
                mood_counts[eb.mood.lower().strip()] += 1
            if eb.complexity:
                complexity_counts[eb.complexity.lower().strip()] += 1
            if eb.book.author and eb.book.author != "Unknown":
                author_weights[eb.book.author] += weight

        if total_weight == 0:
            total_weight = 1.0

        top_genres = [
            WeightedTag(name=name, weight=round(count / total_weight, 3))
            for name, count in genre_weights.most_common(10)
        ]
        top_themes = [
            WeightedTag(name=name, weight=round(count / total_weight, 3))
            for name, count in theme_weights.most_common(15)
        ]
        preferred_moods = [mood for mood, _ in mood_counts.most_common(5)]
        preferred_complexity = (
            complexity_counts.most_common(1)[0][0] if complexity_counts else ""
        )
        favorite_authors = [
            author for author, _ in author_weights.most_common(10)
        ]

        return ReaderProfile(
            top_genres=top_genres,
            top_themes=top_themes,
            preferred_moods=preferred_moods,
            preferred_complexity=preferred_complexity,
            favorite_authors=favorite_authors,
            books_analyzed=len(enriched_books),
        )
