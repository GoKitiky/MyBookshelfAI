from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.deps import pipeline_locale
from app.locale import AppLocale
from app.version import __version__
from app.routers import library, recommend
from app.routers import books as books_router
from app.routers import reading_lists as reading_lists_router
from app.routers import settings as settings_router
from app.services.cache import init_cache
from app.services.demo_seed import clear_demo_books
from app.services.library_db import init_books_table, init_reading_lists_table
from app.services.settings_db import init_settings_table, seed_from_env

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    Path("data").mkdir(exist_ok=True)
    init_cache()
    init_books_table()
    init_reading_lists_table()
    init_settings_table()
    seed_from_env()
    yield


app = FastAPI(
    title="MyBookshelfAI",
    description="Personal book recommendation engine powered by LLM",
    version=__version__,
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(books_router.router)
app.include_router(settings_router.router)
app.include_router(library.router)
app.include_router(recommend.router)
app.include_router(reading_lists_router.router)


@app.post("/api/demo/clear-library")
async def api_clear_demo_library(
    locale: AppLocale = Depends(pipeline_locale),
) -> dict[str, int]:
    """Remove seeded demo books (only when demo mode is active).

    Defined on the app (not under ``/api/books/{id}``) so the path stays unambiguous
    for reverse proxies and older clients.
    """
    try:
        return await clear_demo_books(locale)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
