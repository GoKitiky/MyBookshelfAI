"""Parse markdown files (with optional YAML frontmatter) into Book objects."""

from __future__ import annotations

import logging
import os
import re
from urllib.parse import unquote

import frontmatter

from app.models import Book

logger = logging.getLogger(__name__)

_FILENAME_PATTERNS: list[str] = [
    r"\u201c([^\u201d]+)\u201d\s+(.+)",  # \u201cTitle\u201d Author
    r'"([^"]+)"\s+(.+)',  # "Title" Author
    r"\u00ab([^\u00bb]+)\u00bb\s+(.+)",  # \u00abTitle\u00bb Author
    r"\u300a([^\u300b]+)\u300b\s+(.+)",  # \u300aTitle\u300b Author
]

_RATING_PATTERNS: list[tuple[str, int | str]] = [
    (r"(?:оценка|рейтинг|оценил|rate|rating)[\s:]*(\d)\s*[/\-]\s*5", 1),
    (r"(\d)\s+из\s+5", 1),
    (r"\b(\d)\s*/\s*5\b", 1),
    (r"(\d{1,2})\s*/\s*10", "divide"),
    (r"[★⭐]{1,5}", "stars"),
]


def _normalize_upload_filename(filename: str) -> str:
    """Decode URL-encoded multipart filenames (e.g. %22 → \") and drop path segments."""
    base = os.path.basename(filename.replace("\\", "/"))
    return unquote(base)


def _parse_filename(filename: str) -> tuple[str, str]:
    """Extract (title, author) from a filename like 'Title «Author».md'."""
    name = filename.replace(".md", "")

    for pattern in _FILENAME_PATTERNS:
        if match := re.match(pattern, name):
            return match.group(1).strip(), match.group(2).strip()

    # Obsidian / vault style: "1984 «George Orwell».md"
    if match := re.fullmatch(r"(.+)\s+\u00ab([^\u00bb]+)\u00bb", name):
        return match.group(1).strip(), match.group(2).strip()

    parts = name.rsplit(" ", 1)
    if len(parts) == 2:
        return parts[0].strip("\"'"), parts[1]
    return name, "Unknown"


def _extract_rating_from_text(text: str) -> int | None:
    """Try to find a numeric rating (1-5) inside the markdown body."""
    for pattern, group in _RATING_PATTERNS:
        if match := re.search(pattern, text, re.IGNORECASE):
            if group == "stars":
                stars = match.group(0)
                return stars.count("★") + stars.count("⭐")
            if group == "divide":
                num = int(match.group(1))
                return round(num / 2) if num > 5 else num
            return int(match.group(group))
    return None


def parse_md_content(content: str, filename: str) -> Book | None:
    """Parse raw markdown content and a filename into a Book.

    Returns None when neither title nor author can be extracted.
    """
    try:
        post = frontmatter.loads(content)
    except Exception:
        logger.warning("Failed to parse frontmatter for %s", filename, exc_info=True)
        return None

    logical_name = _normalize_upload_filename(filename)
    title, author = _parse_filename(logical_name)
    if not title and not author:
        return None

    return Book(
        title=title,
        author=author,
        rating=_extract_rating_from_text(post.content),
        review=post.content[:2000],
        tags=post.get("tags", []) or [],
        source_path=logical_name,
    )


def parse_md_files(files: list[tuple[str, str]]) -> list[Book]:
    """Parse multiple (filename, content) pairs and return valid Books."""
    books: list[Book] = []
    for filename, content in files:
        try:
            book = parse_md_content(content, filename)
            if book:
                books.append(book)
        except Exception:
            logger.warning("Skipping %s", filename, exc_info=True)
    return books
