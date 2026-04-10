from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from app.services.runtime_paths import get_cache_db_path

DB_PATH = get_cache_db_path()

# Default TTLs per namespace (hours)
_DEFAULT_TTL: dict[str, int] = {
    "enriched_books": 720,    # 30 days
    "reader_profile": 168,    # 7 days
    "recommendations": 72,    # 3 days
}


class CacheNamespace(str, Enum):
    ENRICHED_BOOKS = "enriched_books"
    READER_PROFILE = "reader_profile"
    RECOMMENDATIONS = "recommendations"


def init_cache() -> None:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS cache (
            namespace TEXT NOT NULL,
            key       TEXT NOT NULL,
            value     TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            expires_at TIMESTAMP NOT NULL,
            PRIMARY KEY (namespace, key)
        )
    """)
    conn.commit()
    conn.close()


def make_key(*args: Any) -> str:
    content = json.dumps(args, sort_keys=True, ensure_ascii=False)
    return hashlib.md5(content.encode()).hexdigest()


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(str(DB_PATH))


async def get_cached(namespace: CacheNamespace, key: str) -> Any | None:
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT value, expires_at FROM cache WHERE namespace = ? AND key = ?",
            (namespace.value, key),
        ).fetchone()
    finally:
        conn.close()

    if not row:
        return None

    value, expires_at = row
    if datetime.now() > datetime.fromisoformat(expires_at):
        return None

    return json.loads(value)


async def set_cache(
    namespace: CacheNamespace,
    key: str,
    value: Any,
    ttl_hours: int | None = None,
) -> None:
    ttl = ttl_hours or _DEFAULT_TTL.get(namespace.value, 168)
    now = datetime.now()
    expires = now + timedelta(hours=ttl)

    conn = _conn()
    try:
        conn.execute(
            """INSERT OR REPLACE INTO cache
               (namespace, key, value, created_at, expires_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                namespace.value,
                key,
                json.dumps(value, ensure_ascii=False),
                now.isoformat(),
                expires.isoformat(),
            ),
        )
        conn.commit()
    finally:
        conn.close()


async def get_cached_or_compute(
    namespace: CacheNamespace,
    key: str,
    compute_func: Any,
    ttl_hours: int | None = None,
) -> Any:
    cached = await get_cached(namespace, key)
    if cached is not None:
        return cached

    result = await compute_func()
    await set_cache(namespace, key, result, ttl_hours)
    return result


async def invalidate(namespace: CacheNamespace, key: str | None = None) -> int:
    """Delete cache entries. If key is None, delete all entries in namespace."""
    conn = _conn()
    try:
        if key is None:
            cursor = conn.execute(
                "DELETE FROM cache WHERE namespace = ?", (namespace.value,)
            )
        else:
            cursor = conn.execute(
                "DELETE FROM cache WHERE namespace = ? AND key = ?",
                (namespace.value, key),
            )
        conn.commit()
        return cursor.rowcount
    finally:
        conn.close()
