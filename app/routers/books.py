"""REST API for the books library (CRUD + markdown file import)."""

from __future__ import annotations

import logging
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from pydantic import BaseModel, Field, field_validator

from app.deps import pipeline_locale
from app.locale import AppLocale
from app.services.demo_seed import (
    ensure_demo_library_seeded,
    mark_library_emptied_by_user,
)
from app.services.library_db import (
    BookIdentityConflictError,
    delete_book,
    get_all_books,
    get_book,
    import_books,
    list_books,
    update_book,
    upsert_book,
)
from app.services.md_parser import parse_md_content

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/books", tags=["books"])

LibraryListSort = Literal["default", "title", "rating", "added"]


class BookUpdate(BaseModel):
    title: str | None = None
    author: str | None = None
    rating: int | None = None
    review: str | None = None
    tags: list[str] | None = None
    notes_md: str | None = None

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v

    @field_validator("title", "author")
    @classmethod
    def non_empty_when_set(cls, v: str | None) -> str | None:
        if v is not None and not v:
            raise ValueError("title and author cannot be empty")
        return v

    @field_validator("rating")
    @classmethod
    def rating_range(cls, v: int | None) -> int | None:
        if v is not None and not (1 <= v <= 5):
            raise ValueError("rating must be between 1 and 5")
        return v


class BookCreate(BaseModel):
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    rating: int | None = Field(None, ge=1, le=5)
    review: str = ""
    tags: list[str] | None = None
    notes_md: str = ""

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


# ------------------------------------------------------------------
# List / detail
# ------------------------------------------------------------------


@router.post("")
async def api_create_book(body: BookCreate) -> dict[str, Any]:
    """Create or merge a book by title and author (same identity as markdown import)."""
    return upsert_book(
        title=body.title,
        author=body.author,
        rating=body.rating,
        review=body.review,
        tags=body.tags,
        notes_md=body.notes_md,
        source_path="",
    )


@router.get("")
async def api_list_books(
    page: int = Query(1, ge=1),
    per_page: int = Query(12, ge=1, le=100),
    q: str = Query("", description="Search by title or author"),
    sort: Annotated[
        LibraryListSort,
        Query(
            description=(
                "default: import/add order; title: A–Z; rating: high to low; "
                "added: newest first"
            ),
        ),
    ] = "default",
    locale: AppLocale = Depends(pipeline_locale),
) -> dict[str, Any]:
    await ensure_demo_library_seeded(locale)
    return list_books(page=page, per_page=per_page, query=q, sort=sort)


# Declared before /{book_id} so "import" is not captured as a book id.
@router.post("/import")
async def api_import_books(
    files: list[UploadFile] = File(..., description="Markdown files to import"),
) -> dict[str, Any]:
    books = []
    skipped: list[str] = []

    for f in files:
        name = f.filename or "unknown.md"
        if not name.endswith(".md"):
            skipped.append(name)
            logger.warning("Skipping non-.md file: %s", name)
            continue

        content = (await f.read()).decode("utf-8")
        book = parse_md_content(content, name)
        if book:
            books.append(book)

    result = import_books(books)

    if skipped:
        result["skipped_files"] = skipped

    return result


@router.get("/{book_id}")
async def api_get_book(book_id: str) -> dict[str, Any]:
    book = get_book(book_id)
    if not book:
        raise HTTPException(404, "Book not found")
    return book


# ------------------------------------------------------------------
# Update / delete
# ------------------------------------------------------------------


@router.put("/{book_id}")
async def api_update_book(book_id: str, body: BookUpdate) -> dict[str, Any]:
    fields = body.model_dump(exclude_unset=True)
    try:
        updated = update_book(book_id, **fields)
    except BookIdentityConflictError:
        raise HTTPException(
            status_code=409,
            detail="A book with this title and author already exists",
        )
    if not updated:
        raise HTTPException(404, "Book not found")
    return updated


@router.delete("/{book_id}")
async def api_delete_book(book_id: str) -> dict[str, str]:
    if not delete_book(book_id):
        raise HTTPException(404, "Book not found")
    if not get_all_books():
        mark_library_emptied_by_user()
    return {"status": "deleted"}
