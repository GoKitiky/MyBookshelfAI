from __future__ import annotations

from fastapi import APIRouter, Depends

from app.deps import pipeline_locale
from app.locale import AppLocale
from app.services.cache import CacheNamespace, get_cached
from app.services.demo_seed import ensure_demo_library_seeded
from app.services.library_db import get_all_books

router = APIRouter(prefix="/api/library", tags=["library"])

_LIBRARY_CACHE_NS = CacheNamespace.ENRICHED_BOOKS
_LIBRARY_LIST_KEY = "library_book_list"


@router.get("")
async def get_library(
    locale: AppLocale = Depends(pipeline_locale),
) -> dict:
    """List all books from the database."""
    await ensure_demo_library_seeded(locale)
    rows = get_all_books()
    return {
        "count": len(rows),
        "books": sorted(rows, key=lambda b: b.get("rating") or 0, reverse=True),
    }
