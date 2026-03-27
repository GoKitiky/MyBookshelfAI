from __future__ import annotations

import asyncio
import logging

from app.locale import AppLocale
from app.models import Book, EnrichedBook
from app.services.cache import CacheNamespace, get_cached, make_key, set_cache
from app.services.llm import LLMClient
from config import config

logger = logging.getLogger(__name__)

NS = CacheNamespace.ENRICHED_BOOKS


class EnrichmentService:
    def __init__(self, llm: LLMClient) -> None:
        self._llm = llm
        self._enrich_sem = asyncio.Semaphore(config.ENRICH_MAX_CONCURRENT)

    @staticmethod
    def _cache_keys_for_book(locale: AppLocale, book: Book) -> list[str]:
        """Locale-scoped key first; legacy key (no locale) treated as ru."""
        primary = make_key(locale, book.title, book.author)
        if locale == "ru":
            return [primary, make_key(book.title, book.author)]
        return [primary]

    async def enrich_books(
        self,
        books: list[Book],
        force: bool = False,
        *,
        locale: AppLocale = "ru",
    ) -> list[EnrichedBook]:
        sorted_books = sorted(
            books, key=lambda b: (b.rating or 0), reverse=True,
        )

        async def one(book: Book) -> EnrichedBook:
            if not force:
                cached = await self._get_cached_enriched(book, locale=locale)
                if cached is not None:
                    return cached
            async with self._enrich_sem:
                if not force:
                    cached = await self._get_cached_enriched(book, locale=locale)
                    if cached is not None:
                        return cached
                return await self._enrich_from_llm(book, locale=locale)

        return list(await asyncio.gather(*(one(b) for b in sorted_books)))

    async def enrich_single(
        self,
        book: Book,
        force: bool = False,
        *,
        locale: AppLocale = "ru",
    ) -> EnrichedBook:
        return await self._enrich_single(book, force=force, locale=locale)

    async def _get_cached_enriched(
        self,
        book: Book,
        *,
        locale: AppLocale,
    ) -> EnrichedBook | None:
        for cache_key in self._cache_keys_for_book(locale, book):
            cached = await get_cached(NS, cache_key)
            if cached is not None:
                return EnrichedBook.model_validate(cached)
        return None

    async def _enrich_from_llm(
        self,
        book: Book,
        *,
        locale: AppLocale,
    ) -> EnrichedBook:
        cache_key = make_key(locale, book.title, book.author)
        logger.info("Enriching '%s' by %s via LLM", book.title, book.author)
        enriched = await self._llm.enrich_book(book, locale=locale)
        await set_cache(NS, cache_key, enriched.model_dump())
        return enriched

    async def _enrich_single(
        self,
        book: Book,
        force: bool = False,
        *,
        locale: AppLocale = "ru",
    ) -> EnrichedBook:
        if not force:
            hit = await self._get_cached_enriched(book, locale=locale)
            if hit is not None:
                return hit
        async with self._enrich_sem:
            if not force:
                hit = await self._get_cached_enriched(book, locale=locale)
                if hit is not None:
                    return hit
            return await self._enrich_from_llm(book, locale=locale)

    async def get_enriched(
        self,
        book: Book,
        *,
        locale: AppLocale = "ru",
    ) -> EnrichedBook | None:
        """Return cached enrichment or None."""
        return await self._get_cached_enriched(book, locale=locale)
