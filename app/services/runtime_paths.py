"""Runtime path helpers for local, container, and desktop environments."""

from __future__ import annotations

import os
from pathlib import Path

DATA_DIR_ENV = "MYBOOKSHELFAI_DATA_DIR"
DEFAULT_DATA_DIR = Path("data")


def get_data_dir() -> Path:
    """Return the directory used for persistent app data."""
    raw_override = os.environ.get(DATA_DIR_ENV, "").strip()
    if not raw_override:
        return DEFAULT_DATA_DIR
    return Path(raw_override).expanduser()


def ensure_data_dir() -> Path:
    """Create and return the persistent app data directory."""
    data_dir = get_data_dir()
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_cache_db_path() -> Path:
    """Return the absolute/relative path to the SQLite cache database file."""
    return get_data_dir() / "cache.db"
