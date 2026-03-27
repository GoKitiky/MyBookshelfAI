#!/usr/bin/env python3
"""Load the 20-book enrichment test fixture (title, author, rating only; no reviews)."""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_FIXTURE = ROOT / "data" / "fixtures" / "enrich_test_20.json"
DB_PATH = ROOT / "data" / "cache.db"

# App imports expect project root on path
sys.path.insert(0, str(ROOT))

from app.services.cache import CacheNamespace  # noqa: E402
from app.services.library_db import upsert_book  # noqa: E402


def _clear_books(conn: sqlite3.Connection) -> int:
    cur = conn.execute("DELETE FROM books")
    conn.commit()
    return cur.rowcount


def _reset_llm_caches(conn: sqlite3.Connection) -> int:
    namespaces = (
        CacheNamespace.ENRICHED_BOOKS.value,
        CacheNamespace.READER_PROFILE.value,
        CacheNamespace.RECOMMENDATIONS.value,
    )
    cur = conn.execute(
        f"DELETE FROM cache WHERE namespace IN ({','.join('?' * len(namespaces))})",
        namespaces,
    )
    conn.commit()
    return cur.rowcount


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Upsert books from enrich_test_20.json (empty review).",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=DEFAULT_FIXTURE,
        help="Path to JSON array of {title, author, rating}",
    )
    parser.add_argument(
        "--clear-library",
        action="store_true",
        help="Remove all rows from books before loading",
    )
    parser.add_argument(
        "--reset-caches",
        action="store_true",
        help="Clear enriched_books, reader_profile, and recommendations cache rows",
    )
    args = parser.parse_args()

    if not args.fixture.is_file():
        print(f"Fixture not found: {args.fixture}", file=sys.stderr)
        return 1

    raw = json.loads(args.fixture.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        print("Fixture must be a JSON array", file=sys.stderr)
        return 1

    conn = sqlite3.connect(str(DB_PATH))
    try:
        if args.clear_library:
            n = _clear_books(conn)
            print(f"Cleared library: {n} book row(s) removed")
        if args.reset_caches:
            n = _reset_llm_caches(conn)
            print(f"Reset LLM caches: {n} cache row(s) removed")
    finally:
        conn.close()

    # upsert_book uses its own connections
    # Reversed so prepending each new row keeps fixture JSON order in the UI.
    for i, row in reversed(list(enumerate(raw, start=1))):
        if not isinstance(row, dict):
            print(f"Item {i} is not an object", file=sys.stderr)
            return 1
        title = str(row.get("title", "")).strip()
        author = str(row.get("author", "")).strip()
        rating = row.get("rating")
        if not title or not author:
            print(f"Item {i}: title and author are required", file=sys.stderr)
            return 1
        if rating is not None:
            r = int(rating)
            if not (1 <= r <= 5):
                print(f"Item {i}: rating must be 1–5", file=sys.stderr)
                return 1
        else:
            r = None

        upsert_book(title=title, author=author, rating=r, review="", notes_md="")

    print(f"Loaded {len(raw)} book(s) from {args.fixture}")
    print(
        "Enrich via API: POST /api/pipeline/books/enrich "
        "(add ?force=true to bypass cache if you skipped --reset-caches)",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
