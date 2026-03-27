"""Planned reads and blacklist (from recommendations), stored in SQLite."""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from app.services.library_db import (
    get_reading_lists,
    reading_list_remove,
    reading_list_toggle,
)

router = APIRouter(prefix="/api/reading-lists", tags=["reading-lists"])

ListTarget = Literal["planned", "blacklist"]


class ToggleBody(BaseModel):
    target: ListTarget
    title: str = Field(..., min_length=1)
    author: str = Field(..., min_length=1)
    genres: list[str] = Field(default_factory=list)
    reasoning: str = ""

    @field_validator("title", "author", mode="before")
    @classmethod
    def strip_text(cls, v: object) -> object:
        if isinstance(v, str):
            return v.strip()
        return v


def _serialize_entry(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["book_id"],
        "title": row["title"],
        "author": row["author"],
        "genres": row["genres"],
        "reasoning": row.get("reasoning") or "",
        "created_at": row["created_at"],
    }


@router.get("")
async def api_get_reading_lists() -> dict[str, Any]:
    data = get_reading_lists()
    return {
        "planned": [_serialize_entry(r) for r in data["planned"]],
        "blacklist": [_serialize_entry(r) for r in data["blacklist"]],
    }


@router.post("/toggle")
async def api_toggle_reading_list(body: ToggleBody) -> dict[str, Any]:
    in_planned, in_blacklist = reading_list_toggle(
        body.target,
        body.title,
        body.author,
        genres=body.genres,
        reasoning=body.reasoning,
    )
    return {"planned": in_planned, "blacklist": in_blacklist}


@router.delete("/planned/{book_id}")
async def api_remove_planned(book_id: str) -> dict[str, str]:
    if not reading_list_remove("planned", book_id):
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}


@router.delete("/blacklist/{book_id}")
async def api_remove_blacklist(book_id: str) -> dict[str, str]:
    if not reading_list_remove("blacklist", book_id):
        raise HTTPException(404, "Entry not found")
    return {"status": "deleted"}
