"""Reading list (planned / blacklist) persistence."""

from __future__ import annotations

import app.services.library_db as lib_db
from app.services.library_db import (
    get_reading_lists,
    init_books_table,
    init_reading_lists_table,
    reading_list_remove,
    reading_list_toggle,
)


def test_reading_list_toggle_planned_and_mutual_exclusion(tmp_path, monkeypatch):
    monkeypatch.setattr(lib_db, "DB_PATH", tmp_path / "rl.db")
    init_books_table()
    init_reading_lists_table()

    p, b = reading_list_toggle("planned", "The Book", "Author One")
    assert p is True and b is False

    p, b = reading_list_toggle("blacklist", "The Book", "Author One")
    assert p is False and b is True

    p, b = reading_list_toggle("planned", "The Book", "Author One")
    assert p is True and b is False

    p, b = reading_list_toggle("planned", "The Book", "Author One")
    assert p is False and b is False


def test_get_reading_lists_and_remove(tmp_path, monkeypatch):
    monkeypatch.setattr(lib_db, "DB_PATH", tmp_path / "rl2.db")
    init_books_table()
    init_reading_lists_table()

    reading_list_toggle("planned", "A", "B", genres=["fic"], reasoning="why")
    reading_list_toggle("blacklist", "X", "Y")

    data = get_reading_lists()
    assert len(data["planned"]) == 1
    assert data["planned"][0]["title"] == "A"
    assert data["planned"][0]["genres"] == ["fic"]

    bid = data["planned"][0]["book_id"]
    assert reading_list_remove("planned", bid) is True
    assert reading_list_remove("planned", bid) is False

    data = get_reading_lists()
    assert len(data["planned"]) == 0
