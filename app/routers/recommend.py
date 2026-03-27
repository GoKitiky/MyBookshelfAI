from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import pipeline_locale
from app.locale import AppLocale
from app.models import Book, EnrichedBook, ReaderProfile
from app.services.cache import (
    CacheNamespace,
    get_cached,
    make_key,
    set_cache,
)
from app.services.demo_seed import ensure_demo_library_seeded
from app.services.enrichment import EnrichmentService
from app.services.library_db import book_identity_id, get_all_books, get_blacklisted_book_ids
from app.services.llm import LLMClient
from app.services.recommendation_scoring import (
    apply_match_scores_to_recommendation_dicts,
)
from app.services.profile import ProfileBuilder

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/pipeline", tags=["recommendations"])

_LIBRARY_LIST_KEY = "library_book_list"

# Fixed recommendation list size (UI no longer exposes a count selector).
RECOMMENDATION_COUNT = 5


def _without_blacklist(recs: list[dict], blocked: set[str]) -> list[dict]:
    if not blocked:
        return recs
    return [
        r
        for r in recs
        if book_identity_id(str(r.get("title", "")), str(r.get("author", "")))
        not in blocked
    ]


def _rec_cache_keys(
    locale: AppLocale,
    profile_dump: dict,
    num: int,
) -> list[str]:
    primary = make_key(locale, "recs", profile_dump, num)
    if locale == "ru":
        return [primary, make_key("recs", profile_dump, num)]
    return [primary]


def _get_services() -> tuple[LLMClient, EnrichmentService, ProfileBuilder]:
    llm = LLMClient()
    return llm, EnrichmentService(llm), ProfileBuilder(llm)


async def _load_books(locale: AppLocale) -> list[Book]:
    """Load books from the database (seeds demo library when empty, using UI locale)."""
    await ensure_demo_library_seeded(locale)
    rows = get_all_books()
    if not rows:
        raise HTTPException(400, "No books in library. Import .md files first.")

    return [
        Book(
            title=r["title"],
            author=r["author"],
            rating=r.get("rating"),
            review=r.get("review", ""),
            tags=r.get("tags", []),
            source_path=r.get("source_path", ""),
        )
        for r in rows
    ]


# ------------------------------------------------------------------
# Enrichment
# ------------------------------------------------------------------


@router.post("/books/enrich")
async def enrich_books(
    force: bool = Query(False, description="Re-enrich even if cached"),
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Enrich all books in the library via LLM + web search."""
    books = await _load_books(locale)
    if not books:
        raise HTTPException(400, "Library is empty. Import .md files first.")

    llm, enrichment, _ = _get_services()
    enriched = await enrichment.enrich_books(books, force=force, locale=locale)

    return {
        "enriched_count": len(enriched),
        "books": [eb.model_dump() for eb in enriched],
    }


@router.get("/books/{book_id}/enriched")
async def get_enriched_book(
    book_id: str,
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Get cached enrichment data for a specific book by its ID."""
    books = await _load_books(locale)
    book = next((b for b in books if b.get_id() == book_id), None)
    if book is None:
        raise HTTPException(404, f"Book {book_id} not found in library")

    llm, enrichment, _ = _get_services()
    cached = await enrichment.get_enriched(book, locale=locale)
    if cached is None:
        raise HTTPException(404, f"Book '{book.title}' has not been enriched yet")

    return cached.model_dump()


# ------------------------------------------------------------------
# Profile
# ------------------------------------------------------------------


@router.post("/profile/build")
async def build_profile(
    force: bool = Query(False, description="Rebuild even if cached"),
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Build a reader preference profile from all enriched books."""
    books = await _load_books(locale)
    llm, enrichment, profile_builder = _get_services()

    enriched: list[EnrichedBook] = []
    for book in books:
        eb = await enrichment.get_enriched(book, locale=locale)
        if eb is not None:
            enriched.append(eb)

    if not enriched:
        raise HTTPException(
            400,
            "No enriched books found. Call POST /api/pipeline/books/enrich first.",
        )

    profile = await profile_builder.build_profile(
        enriched, force=force, locale=locale,
    )
    return profile.model_dump()


@router.get("/profile")
async def get_profile(
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Get the cached reader preference profile."""
    books = await _load_books(locale)
    llm, enrichment, _ = _get_services()

    enriched_ids = []
    for book in books:
        eb = await enrichment.get_enriched(book, locale=locale)
        if eb is not None:
            enriched_ids.append(eb.book.get_id())

    if not enriched_ids:
        raise HTTPException(404, "No profile found. Build one first.")

    cached = None
    for cache_key in ProfileBuilder._profile_cache_keys(locale, enriched_ids):
        cached = await get_cached(CacheNamespace.READER_PROFILE, cache_key)
        if cached is not None:
            break
    if cached is None:
        raise HTTPException(
            404, "No profile found. Call POST /api/pipeline/profile/build."
        )

    return ReaderProfile.model_validate(cached).model_dump()


# ------------------------------------------------------------------
# Readiness (for UI without probing POST .../recommendations)
# ------------------------------------------------------------------


@router.get("/readiness")
async def library_readiness(
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Book and enrichment counts for driving a simple recommendations UI."""
    try:
        books = await _load_books(locale)
    except HTTPException as e:
        if e.status_code == 400:
            return {
                "book_count": 0,
                "enriched_count": 0,
                "needs_sync": True,
                "needs_more_books": False,
                "ready_for_recommendations": False,
            }
        raise

    _, enrichment, _ = _get_services()
    enriched_count = 0
    for book in books:
        eb = await enrichment.get_enriched(book, locale=locale)
        if eb is not None:
            enriched_count += 1

    n = len(books)
    return {
        "book_count": n,
        "enriched_count": enriched_count,
        "needs_sync": n == 0,
        "needs_more_books": n == 1,
        "ready_for_recommendations": n >= 2 and enriched_count > 0,
    }


# ------------------------------------------------------------------
# Recommendations
# ------------------------------------------------------------------


@router.post("/recommendations")
async def get_recommendations(
    refresh: bool = Query(False, description="Ignore cached recommendations"),
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """Generate personalized book recommendations (always five titles)."""
    num = RECOMMENDATION_COUNT
    books = await _load_books(locale)
    if len(books) < 2:
        raise HTTPException(400, f"Need at least 2 books, found {len(books)}.")

    llm, enrichment, profile_builder = _get_services()

    enriched: list[EnrichedBook] = []
    for book in books:
        eb = await enrichment.get_enriched(book, locale=locale)
        if eb is not None:
            enriched.append(eb)

    if not enriched:
        raise HTTPException(
            400,
            "No enriched books. Call POST /api/pipeline/books/enrich first.",
        )

    profile = await profile_builder.build_profile(enriched, locale=locale)

    profile_dump = profile.model_dump()
    rec_keys = _rec_cache_keys(locale, profile_dump, num)
    blocked = get_blacklisted_book_ids()

    if not refresh:
        cached = None
        for cache_key in rec_keys:
            hit = await get_cached(CacheNamespace.RECOMMENDATIONS, cache_key)
            if hit is not None:
                cached = hit
                break
        if cached is not None:
            scored = apply_match_scores_to_recommendation_dicts(cached, profile)
            return {
                "library_size": len(books),
                "recommendations": _without_blacklist(scored, blocked),
                "from_cache": True,
            }

    recommendations = await llm.get_recommendations(
        profile, books, num, locale=locale,
    )
    rec_dicts = apply_match_scores_to_recommendation_dicts(
        [r.model_dump() for r in recommendations],
        profile,
    )

    store_key = rec_keys[0]
    await set_cache(CacheNamespace.RECOMMENDATIONS, store_key, rec_dicts)

    return {
        "library_size": len(books),
        "recommendations": _without_blacklist(rec_dicts, blocked),
        "from_cache": False,
    }
