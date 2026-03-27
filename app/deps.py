"""FastAPI dependencies."""

from __future__ import annotations

from typing import Annotated

from fastapi import Header

from app.locale import (
    AppLocale,
    DEFAULT_APP_LOCALE,
    locale_from_accept_language,
    parse_app_locale_header,
)


def pipeline_locale(
    x_app_locale: Annotated[str | None, Header(alias="X-App-Locale")] = None,
    accept_language: Annotated[str | None, Header(alias="Accept-Language")] = None,
) -> AppLocale:
    """Locale from X-App-Locale, else first matching tag in Accept-Language, else ru."""
    if x_app_locale is not None and str(x_app_locale).strip():
        return parse_app_locale_header(x_app_locale)
    guessed = locale_from_accept_language(accept_language)
    if guessed is not None:
        return guessed
    return DEFAULT_APP_LOCALE
