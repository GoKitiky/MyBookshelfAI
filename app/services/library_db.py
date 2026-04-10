"""SQLite-backed book library with CRUD operations."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Sequence
from datetime import datetime, timezone
from typing import Any, Literal

from app.models import Book
from app.services.runtime_paths import get_cache_db_path

ReadingListKind = Literal["planned", "blacklist"]

DB_PATH = get_cache_db_path()


class BookIdentityConflictError(Exception):
    """Another row already exists for the same title+author identity."""

    pass


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_books_table() -> None:
    """Create the books table if it doesn't exist."""
    conn = _conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS books (
                id          TEXT PRIMARY KEY,
                title       TEXT NOT NULL,
                author      TEXT NOT NULL,
                rating      INTEGER,
                review      TEXT DEFAULT '',
                tags        TEXT DEFAULT '[]',
                notes_md    TEXT DEFAULT '',
                source_path TEXT DEFAULT '',
                position    INTEGER DEFAULT 0,
                created_at  TIMESTAMP NOT NULL,
                updated_at  TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def init_reading_lists_table() -> None:
    """Create reading_list_entries for planned reads and blacklist."""
    conn = _conn()
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS reading_list_entries (
                list_kind   TEXT NOT NULL
                    CHECK(list_kind IN ('planned', 'blacklist')),
                book_id     TEXT NOT NULL,
                title       TEXT NOT NULL,
                author      TEXT NOT NULL,
                genres      TEXT NOT NULL DEFAULT '[]',
                reasoning   TEXT DEFAULT '',
                created_at  TIMESTAMP NOT NULL,
                PRIMARY KEY (list_kind, book_id)
            )
            """
        )
        conn.commit()
    finally:
        conn.close()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _book_id(title: str, author: str) -> str:
    raw = f"{title.lower().strip()}:{author.lower().strip()}"
    return hashlib.md5(raw.encode()).hexdigest()


def book_identity_id(title: str, author: str) -> str:
    """Stable id for a title+author pair (matches books.id and reading-list keys)."""
    return _book_id(title, author)


def get_blacklisted_book_ids() -> set[str]:
    """Identity ids of titles the user chose to hide from recommendations."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT book_id FROM reading_list_entries WHERE list_kind = 'blacklist'"
        ).fetchall()
        return {str(r[0]) for r in rows}
    finally:
        conn.close()


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["tags"] = json.loads(d.get("tags") or "[]")
    return d


# Whitelisted ORDER BY clauses for list_books (never interpolate user input here).
_LIST_SORT_SQL: dict[str, str] = {
    "default": "position ASC, title COLLATE NOCASE ASC",
    "title": "title COLLATE NOCASE ASC, author COLLATE NOCASE ASC",
    # Non-null ratings first (highest first), then unrated, stable by title.
    "rating": "rating IS NULL ASC, rating DESC, title COLLATE NOCASE ASC",
    "added": "created_at DESC, title COLLATE NOCASE ASC",
}


def list_books(
    page: int = 1,
    per_page: int = 12,
    query: str = "",
    sort: str = "default",
) -> dict[str, Any]:
    """Return paginated books, optionally filtered by title/author search."""
    order_sql = _LIST_SORT_SQL.get(sort, _LIST_SORT_SQL["default"])
    conn = _conn()
    try:
        if query:
            like = f"%{query}%"
            count_row = conn.execute(
                "SELECT COUNT(*) FROM books WHERE title LIKE ? OR author LIKE ?",
                (like, like),
            ).fetchone()
            total = count_row[0]
            rows = conn.execute(
                f"""SELECT * FROM books
                   WHERE title LIKE ? OR author LIKE ?
                   ORDER BY {order_sql}
                   LIMIT ? OFFSET ?""",
                (like, like, per_page, (page - 1) * per_page),
            ).fetchall()
        else:
            count_row = conn.execute("SELECT COUNT(*) FROM books").fetchone()
            total = count_row[0]
            rows = conn.execute(
                f"SELECT * FROM books ORDER BY {order_sql} LIMIT ? OFFSET ?",
                (per_page, (page - 1) * per_page),
            ).fetchall()

        return {
            "books": [_row_to_dict(r) for r in rows],
            "total": total,
            "page": page,
            "per_page": per_page,
            "total_pages": max(1, -(-total // per_page)),
        }
    finally:
        conn.close()


def get_all_books() -> list[dict[str, Any]]:
    """Return every book (used by enrichment / profile pipelines)."""
    conn = _conn()
    try:
        rows = conn.execute(
            "SELECT * FROM books ORDER BY position, title"
        ).fetchall()
        return [_row_to_dict(r) for r in rows]
    finally:
        conn.close()


def get_book(book_id: str) -> dict[str, Any] | None:
    conn = _conn()
    try:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        return _row_to_dict(row) if row else None
    finally:
        conn.close()


def upsert_book(
    title: str,
    author: str,
    *,
    rating: int | None = None,
    review: str = "",
    tags: list[str] | None = None,
    notes_md: str = "",
    source_path: str = "",
) -> dict[str, Any]:
    """Insert or update a book, preserving local notes_md edits on conflict."""
    book_id = _book_id(title, author)
    now = _now_iso()
    tags_json = json.dumps(tags or [])

    conn = _conn()
    try:
        existing = conn.execute(
            "SELECT id, notes_md FROM books WHERE id = ?", (book_id,)
        ).fetchone()

        if existing:
            local_notes = existing["notes_md"] or ""
            final_notes = local_notes if local_notes.strip() else notes_md
            conn.execute(
                """UPDATE books SET
                       rating = COALESCE(?, rating),
                       review = ?,
                       tags = ?,
                       notes_md = ?,
                       source_path = ?,
                       updated_at = ?
                   WHERE id = ?""",
                (rating, review, tags_json, final_notes, source_path, now, book_id),
            )
        else:
            min_row = conn.execute(
                "SELECT COALESCE(MIN(position), 0) AS min_pos FROM books"
            ).fetchone()
            new_position = int(min_row["min_pos"]) - 1
            conn.execute(
                """INSERT INTO books
                       (id, title, author, rating, review, tags, notes_md,
                        source_path, position, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (book_id, title, author, rating, review, tags_json, notes_md,
                 source_path, new_position, now, now),
            )
        conn.commit()
    finally:
        conn.close()

    return get_book(book_id)  # type: ignore[return-value]


def update_book(book_id: str, **fields: Any) -> dict[str, Any] | None:
    """Update fields on an existing book; merges partial payloads.

    Title/author changes recompute the primary key (same scheme as upsert). If that
    identity is already used by another row, raises BookIdentityConflictError.
    """
    existing = get_book(book_id)
    if not existing:
        return None

    allowed = {"title", "author", "rating", "review", "tags", "notes_md"}
    fields = {k: v for k, v in fields.items() if k in allowed}

    if not fields:
        return existing

    title = existing["title"]
    author = existing["author"]
    if "title" in fields:
        title = fields["title"]
    if "author" in fields:
        author = fields["author"]

    new_id = _book_id(title, author)

    rating = existing["rating"]
    if "rating" in fields:
        rating = fields["rating"]

    review = existing["review"]
    if "review" in fields:
        review = fields["review"]

    tags = existing["tags"]
    if "tags" in fields:
        tags = fields["tags"]

    notes_md = existing["notes_md"]
    if "notes_md" in fields:
        notes_md = fields["notes_md"]

    if new_id != book_id:
        if get_book(new_id) is not None:
            raise BookIdentityConflictError()

    tags_json = json.dumps(tags or [])
    now = _now_iso()

    conn = _conn()
    try:
        conn.execute(
            """UPDATE books SET
                   id = ?, title = ?, author = ?, rating = ?, review = ?,
                   tags = ?, notes_md = ?, updated_at = ?
               WHERE id = ?""",
            (new_id, title, author, rating, review, tags_json, notes_md, now, book_id),
        )
        conn.commit()
    finally:
        conn.close()

    return get_book(new_id)


def delete_book(book_id: str) -> bool:
    conn = _conn()
    try:
        cursor = conn.execute("DELETE FROM books WHERE id = ?", (book_id,))
        conn.commit()
        return cursor.rowcount > 0
    finally:
        conn.close()


def import_books(books: Sequence[Book]) -> dict[str, int]:
    """Upsert books from a file import, return counts."""
    created = 0
    updated = 0

    # Insert last in the batch first so ORDER BY position ASC matches source order.
    for book in reversed(list(books)):
        book_id = _book_id(book.title, book.author)
        conn = _conn()
        try:
            exists = conn.execute(
                "SELECT id FROM books WHERE id = ?", (book_id,)
            ).fetchone()
        finally:
            conn.close()

        upsert_book(
            title=book.title,
            author=book.author,
            rating=book.rating,
            review=book.review,
            tags=book.tags,
            notes_md=book.review,
            source_path=book.source_path,
        )

        if exists:
            updated += 1
        else:
            created += 1

    return {"created": created, "updated": updated, "total": len(books)}


def _reading_list_row(row: sqlite3.Row) -> dict[str, Any]:
    d = dict(row)
    d["genres"] = json.loads(d.get("genres") or "[]")
    return d


def _reading_list_has(conn: sqlite3.Connection, kind: str, book_id: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM reading_list_entries WHERE list_kind = ? AND book_id = ?",
        (kind, book_id),
    ).fetchone()
    return row is not None


def reading_list_toggle(
    target: ReadingListKind,
    title: str,
    author: str,
    *,
    genres: list[str] | None = None,
    reasoning: str = "",
) -> tuple[bool, bool]:
    """Toggle membership in planned or blacklist (mutually exclusive). Returns
    (in_planned, in_blacklist) after the operation.
    """
    book_id = _book_id(title, author)
    now = _now_iso()
    genres_json = json.dumps(list(genres or []))
    reasoning = reasoning or ""

    conn = _conn()
    try:
        in_planned = _reading_list_has(conn, "planned", book_id)
        in_blacklist = _reading_list_has(conn, "blacklist", book_id)

        if target == "planned":
            if in_planned:
                conn.execute(
                    "DELETE FROM reading_list_entries WHERE list_kind = ? AND book_id = ?",
                    ("planned", book_id),
                )
                in_planned = False
            else:
                conn.execute(
                    "DELETE FROM reading_list_entries WHERE book_id = ?",
                    (book_id,),
                )
                conn.execute(
                    """INSERT INTO reading_list_entries
                       (list_kind, book_id, title, author, genres, reasoning, created_at)
                       VALUES ('planned', ?, ?, ?, ?, ?, ?)""",
                    (book_id, title.strip(), author.strip(), genres_json, reasoning, now),
                )
                in_planned = True
                in_blacklist = False
        else:
            if in_blacklist:
                conn.execute(
                    "DELETE FROM reading_list_entries WHERE list_kind = ? AND book_id = ?",
                    ("blacklist", book_id),
                )
                in_blacklist = False
            else:
                conn.execute(
                    "DELETE FROM reading_list_entries WHERE book_id = ?",
                    (book_id,),
                )
                conn.execute(
                    """INSERT INTO reading_list_entries
                       (list_kind, book_id, title, author, genres, reasoning, created_at)
                       VALUES ('blacklist', ?, ?, ?, ?, ?, ?)""",
                    (book_id, title.strip(), author.strip(), genres_json, reasoning, now),
                )
                in_blacklist = True
                in_planned = False

        conn.commit()
        return in_planned, in_blacklist
    finally:
        conn.close()


def reading_list_remove(kind: ReadingListKind, book_id: str) -> bool:
    conn = _conn()
    try:
        cur = conn.execute(
            "DELETE FROM reading_list_entries WHERE list_kind = ? AND book_id = ?",
            (kind, book_id),
        )
        conn.commit()
        return cur.rowcount > 0
    finally:
        conn.close()


def get_reading_lists() -> dict[str, list[dict[str, Any]]]:
    conn = _conn()
    try:
        planned_rows = conn.execute(
            """SELECT list_kind, book_id, title, author, genres, reasoning, created_at
               FROM reading_list_entries
               WHERE list_kind = 'planned'
               ORDER BY created_at DESC"""
        ).fetchall()
        blacklist_rows = conn.execute(
            """SELECT list_kind, book_id, title, author, genres, reasoning, created_at
               FROM reading_list_entries
               WHERE list_kind = 'blacklist'
               ORDER BY created_at DESC"""
        ).fetchall()
        return {
            "planned": [_reading_list_row(r) for r in planned_rows],
            "blacklist": [_reading_list_row(r) for r in blacklist_rows],
        }
    finally:
        conn.close()
