"""Server-side match scores: profile tags vs recommended book metadata."""

from __future__ import annotations

from typing import Any

from app.models import ReaderProfile


def _norm(s: str) -> str:
    s = s.strip().lower().replace("ё", "е")
    return " ".join(s.split())


def _matches_tag(tag_name: str, blobs: list[str]) -> bool:
    t = _norm(tag_name)
    if len(t) < 2:
        return False
    for b in blobs:
        nb = _norm(b)
        if not nb:
            continue
        if t == nb or t in nb or nb in t:
            return True
    return False


def _author_affinity(profile: ReaderProfile, author: str) -> float:
    na = _norm(author)
    if not na:
        return 0.0
    for fav in profile.favorite_authors:
        fn = _norm(fav)
        if not fn:
            continue
        if fn in na or na in fn:
            return 1.0
    return 0.0


def raw_profile_overlap(
    profile: ReaderProfile,
    book_genres: list[str],
    book_themes: list[str],
    author: str,
) -> float:
    """Scalar in ~[0, 1] from weighted genre/theme overlap plus small author term."""
    blobs = [x for x in book_genres if isinstance(x, str)] + [
        x for x in book_themes if isinstance(x, str)
    ]

    max_g = sum(t.weight for t in profile.top_genres[:8]) or 1e-9
    max_t = sum(t.weight for t in profile.top_themes[:10]) or 1e-9

    g_hit = sum(
        t.weight for t in profile.top_genres if _matches_tag(t.name, blobs)
    )
    t_hit = sum(
        t.weight for t in profile.top_themes if _matches_tag(t.name, blobs)
    )

    g_part = min(1.0, g_hit / max_g)
    t_part = min(1.0, t_hit / max_t)

    # Themes often carry more signal than coarse genres from the model.
    base = 0.42 * g_part + 0.48 * t_part + 0.10 * _author_affinity(profile, author)

    if not blobs:
        base = max(base, 0.12)

    return max(0.0, min(1.0, base))


def spread_match_scores(raw: list[float]) -> list[float]:
    """Map a batch of raw scores to a visible [0.52, 0.96] band; handles ties."""
    if not raw:
        return raw
    lo, hi = min(raw), max(raw)
    if hi - lo < 1e-9:
        n = len(raw)
        step = 0.28 / max(n - 1, 1)
        return [max(0.0, min(1.0, 0.93 - i * step)) for i in range(n)]
    return [
        max(0.0, min(1.0, 0.52 + 0.44 * (x - lo) / (hi - lo))) for x in raw
    ]


def match_scores_for_recommendation_dicts(
    profile: ReaderProfile, items: list[dict]
) -> list[float]:
    """One score per dict row (same order), from profile overlap + batch spread."""
    raws: list[float] = []
    for item in items:
        if not isinstance(item, dict):
            raws.append(0.0)
            continue
        genres = item.get("genres", [])
        themes = item.get("themes", [])
        if not isinstance(genres, list):
            genres = []
        if not isinstance(themes, list):
            themes = []
        g = [str(x) for x in genres if x is not None]
        th = [str(x) for x in themes if x is not None]
        author = str(item.get("author", ""))
        raws.append(raw_profile_overlap(profile, g, th, author))
    return spread_match_scores(raws)


def _row_match_score(row: Any) -> float:
    if isinstance(row, dict):
        v = row.get("match_score")
        if isinstance(v, (int, float)):
            return float(v)
    return 0.0


def apply_match_scores_to_recommendation_dicts(
    items: list[Any],
    profile: ReaderProfile,
) -> list[Any]:
    """Attach computed ``match_score`` to each recommendation dict (e.g. cache refresh)."""
    if not items:
        return items
    indices = [i for i, x in enumerate(items) if isinstance(x, dict)]
    if not indices:
        return items
    dict_rows: list[dict] = [items[i] for i in indices]
    scores = match_scores_for_recommendation_dicts(profile, dict_rows)
    out = list(items)
    for idx, ms in zip(indices, scores, strict=True):
        row = dict(out[idx])
        row["match_score"] = ms
        out[idx] = row
    # Highest match first for API and recommendations UI
    out.sort(key=_row_match_score, reverse=True)
    return out
