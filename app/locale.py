"""Application locale for pipeline (UI-chosen ru | en)."""

from __future__ import annotations

from typing import Literal

AppLocale = Literal["ru", "en"]

DEFAULT_APP_LOCALE: AppLocale = "ru"


def parse_app_locale_header(value: str | None) -> AppLocale:
    """Parse X-App-Locale; invalid or missing values default to Russian."""
    if value is None or not str(value).strip():
        return DEFAULT_APP_LOCALE
    v = str(value).strip().lower()
    if v == "ru":
        return "ru"
    if v == "en":
        return "en"
    return DEFAULT_APP_LOCALE


def locale_from_accept_language(value: str | None) -> AppLocale | None:
    """Pick ru|en from the first language tag in Accept-Language, if recognized."""
    if value is None or not str(value).strip():
        return None
    for part in value.split(","):
        tag = part.strip().split(";", maxsplit=1)[0].strip().lower()
        if not tag:
            continue
        primary = tag.split("-", maxsplit=1)[0]
        if primary == "en":
            return "en"
        if primary == "ru":
            return "ru"
    return None
