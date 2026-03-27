from __future__ import annotations

import hashlib

from pydantic import BaseModel, Field


class Book(BaseModel):
    title: str
    author: str
    rating: int | None = None
    review: str = ""
    tags: list[str] = Field(default_factory=list)
    source_path: str = ""

    def get_id(self) -> str:
        raw = f"{self.title.lower().strip()}:{self.author.lower().strip()}"
        return hashlib.md5(raw.encode()).hexdigest()

    def to_context(self) -> str:
        parts = [f"'{self.title}' by {self.author}"]
        if self.rating:
            parts.append(f"rating: {self.rating}/5")
        if self.review:
            parts.append(f"review: {self.review[:500]}")
        return ". ".join(parts)


class EnrichedBook(BaseModel):
    book: Book
    genres: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    mood: str = ""
    complexity: str = ""
    similar_authors: list[str] = Field(default_factory=list)


class WeightedTag(BaseModel):
    name: str
    weight: float


class ReaderProfile(BaseModel):
    top_genres: list[WeightedTag] = Field(default_factory=list)
    top_themes: list[WeightedTag] = Field(default_factory=list)
    preferred_moods: list[str] = Field(default_factory=list)
    preferred_complexity: str = ""
    favorite_authors: list[str] = Field(default_factory=list)
    summary: str = ""
    books_analyzed: int = 0


class Recommendation(BaseModel):
    title: str
    author: str
    genres: list[str] = Field(default_factory=list)
    themes: list[str] = Field(default_factory=list)
    reasoning: str = ""
    match_score: float = 0.0
