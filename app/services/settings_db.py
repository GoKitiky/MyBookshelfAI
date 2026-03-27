"""SQLite-backed key-value store for user-configurable settings."""

from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("data/cache.db")

SETTING_LLM_API_KEY = "llm_api_key"
SETTING_LLM_BASE_URL = "llm_base_url"
SETTING_LLM_MODEL_ENRICH = "llm_model_enrich"
SETTING_LLM_MODEL_PROFILE = "llm_model_profile"
SETTING_LLM_MODEL_RECOMMEND = "llm_model_recommend"


def _conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


def init_settings_table() -> None:
    """Create the settings table if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = _conn()
    try:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key        TEXT PRIMARY KEY,
                value      TEXT NOT NULL,
                updated_at TIMESTAMP NOT NULL
            )
        """)
        conn.commit()
    finally:
        conn.close()


def get_setting(key: str) -> str | None:
    """Return the value for *key*, or ``None`` if not set."""
    conn = _conn()
    try:
        row = conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ).fetchone()
        return row["value"] if row else None
    finally:
        conn.close()


def set_setting(key: str, value: str) -> None:
    """Insert or update a setting."""
    now = datetime.now(timezone.utc).isoformat()
    conn = _conn()
    try:
        conn.execute(
            """INSERT INTO settings (key, value, updated_at)
               VALUES (?, ?, ?)
               ON CONFLICT(key) DO UPDATE
               SET value = excluded.value, updated_at = excluded.updated_at""",
            (key, value, now),
        )
        conn.commit()
    finally:
        conn.close()


def seed_from_env() -> None:
    """One-time migration: copy env-var values into the DB for keys that are still empty.

    This lets existing deployments (Docker, local .env) keep working after
    the switch to Settings-DB-only API key resolution.  Once the values
    are in the DB the env vars are no longer needed.
    """
    from config import config

    _ENV_MAP: dict[str, str] = {
        SETTING_LLM_API_KEY: config.LLM_API_KEY,
        SETTING_LLM_BASE_URL: config.LLM_BASE_URL,
        SETTING_LLM_MODEL_ENRICH: config.LLM_MODEL_ENRICH,
        SETTING_LLM_MODEL_PROFILE: config.LLM_MODEL_PROFILE,
        SETTING_LLM_MODEL_RECOMMEND: config.LLM_MODEL_RECOMMEND,
    }
    for key, env_value in _ENV_MAP.items():
        if env_value and not get_setting(key):
            set_setting(key, env_value)


def get_all_settings() -> dict[str, str]:
    """Return every stored setting as a ``{key: value}`` mapping."""
    conn = _conn()
    try:
        rows = conn.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: row["value"] for row in rows}
    finally:
        conn.close()
