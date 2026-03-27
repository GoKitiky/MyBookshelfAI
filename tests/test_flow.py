"""End-to-end integration test: parse -> enrich -> build profile -> recommend.

Run with:
    .venv/bin/python -m pytest tests/test_flow.py -v -s

Requires:
    - LLM_API_KEY set in .env (or via the Settings page) for integration tests
"""
from __future__ import annotations

import asyncio

import pytest

from app.models import Book, EnrichedBook, ReaderProfile, Recommendation
from app.services.cache import init_cache
from app.services.enrichment import EnrichmentService
from app.services.llm import LLMClient
from app.services.md_parser import parse_md_content, parse_md_files
from app.services.profile import ProfileBuilder
from config import config


@pytest.fixture(autouse=True)
def _setup_cache(tmp_path, monkeypatch):
    import app.services.cache as cache_mod

    monkeypatch.setattr(cache_mod, "DB_PATH", tmp_path / "test_cache.db")
    init_cache()


# ------------------------------------------------------------------
# Unit-level checks (no LLM calls)
# ------------------------------------------------------------------


SAMPLE_MD_CONTENT = """\
---
tags: [fiction, classic]
---
A dystopian novel about totalitarianism.
Rating: 5/5
"""

SAMPLE_FILES = [
    ("1984 «George Orwell».md", SAMPLE_MD_CONTENT),
    (
        "Brave New World «Aldous Huxley».md",
        "---\ntags: [fiction, sci-fi]\n---\nA chilling vision of the future.\nоценка 4",
    ),
    (
        "Fahrenheit 451 «Ray Bradbury».md",
        "---\ntags: [fiction, dystopia]\n---\nBooks are banned.\n★★★★☆",
    ),
]


def test_parse_md_content():
    book = parse_md_content(SAMPLE_MD_CONTENT, "1984 «George Orwell».md")
    assert book is not None
    assert book.title == "1984"
    assert book.author == "George Orwell"
    assert book.rating == 5
    assert "fiction" in book.tags


def test_parse_md_url_encoded_filename():
    """Multipart uploads often send quoted titles as %22…%22 (URL-encoded)."""
    book = parse_md_content(SAMPLE_MD_CONTENT, "%221984%22%20George%20Orwell.md")
    assert book is not None
    assert book.title == "1984"
    assert book.author == "George Orwell"


def test_parse_md_files():
    books = parse_md_files(SAMPLE_FILES)
    assert len(books) == 3
    titles = {b.title for b in books}
    assert "1984" in titles
    assert "Brave New World" in titles
    assert "Fahrenheit 451" in titles


def test_book_model():
    book = Book(title="1984", author="George Orwell", rating=5)
    assert book.get_id()
    assert "1984" in book.to_context()
    assert "5/5" in book.to_context()


def test_profile_aggregation():
    enriched = [
        EnrichedBook(
            book=Book(title="A", author="Auth1", rating=5),
            genres=["sci-fi", "dystopia"],
            themes=["freedom", "surveillance"],
            mood="dark",
            complexity="complex",
        ),
        EnrichedBook(
            book=Book(title="B", author="Auth2", rating=3),
            genres=["sci-fi", "thriller"],
            themes=["freedom", "conspiracy"],
            mood="tense",
            complexity="moderate",
        ),
    ]
    profile = ProfileBuilder._aggregate(enriched)
    assert profile.books_analyzed == 2
    assert any(g.name == "sci-fi" for g in profile.top_genres)
    assert any(t.name == "freedom" for t in profile.top_themes)
    assert "Auth1" in profile.favorite_authors


# ------------------------------------------------------------------
# Integration tests (require LLM API key)
# ------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.skipif(not config.LLM_API_KEY, reason="LLM_API_KEY not set")
async def test_full_pipeline():
    """Full pipeline: parse -> enrich -> profile -> recommend."""
    books = parse_md_files(SAMPLE_FILES)
    assert len(books) >= 2, f"Need >=2 books, found {len(books)}"
    print(f"\nParsed {len(books)} books")

    llm = LLMClient()
    enrichment = EnrichmentService(llm)
    profile_builder = ProfileBuilder(llm)

    subset = sorted(books, key=lambda b: (b.rating or 0), reverse=True)[:3]
    enriched = await enrichment.enrich_books(subset)
    assert len(enriched) == len(subset)
    for eb in enriched:
        print(f"  Enriched: {eb.book.title} -> genres={eb.genres}, mood={eb.mood}")

    profile = await profile_builder.build_profile(enriched)
    assert profile.books_analyzed == len(enriched)
    assert profile.summary, "Profile summary is empty"
    print(f"\nProfile summary:\n{profile.summary}")
    print(f"Top genres: {[g.name for g in profile.top_genres]}")

    recs = await llm.get_recommendations(profile, books, num=3)
    assert len(recs) > 0, "No recommendations returned"
    print("\nRecommendations:")
    for r in recs:
        print(f"  - {r.title} by {r.author} (score={r.match_score})")
        print(f"    {r.reasoning}")


if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
