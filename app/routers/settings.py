"""REST API for user-configurable application settings."""

from __future__ import annotations

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.services.llm import LLMClient
from app.services.demo_seed import SETTING_DEMO_LIBRARY
from app.services.settings_db import (
    SETTING_LLM_API_KEY,
    SETTING_LLM_BASE_URL,
    SETTING_LLM_MODEL_PROFILE,
    SETTING_LLM_MODEL_RECOMMEND,
    get_all_settings,
    get_setting,
    set_setting,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _mask_api_key(key: str) -> str:
    """Return the last 4 characters prefixed with ``sk-...``, or empty string."""
    if not key:
        return ""
    return f"sk-...{key[-4:]}"


def _looks_like_masked_api_key(value: str) -> bool:
    """True if ``value`` matches the GET-settings mask (not a full secret)."""
    if not value.startswith("sk-..."):
        return False
    # Same suffix length as _mask_api_key(): last up to 4 characters of the secret
    suffix = value[6:]
    return 1 <= len(suffix) <= 4


def _resolve_api_key_for_test(submitted: str) -> str:
    """Use the stored key when the client still shows the masked placeholder."""
    trimmed = submitted.strip()
    if not trimmed or _looks_like_masked_api_key(trimmed):
        return get_setting(SETTING_LLM_API_KEY) or ""
    return trimmed


def _settings_response() -> dict[str, str]:
    """Build the public settings dict with a masked API key."""
    all_settings = get_all_settings()
    return {
        "api_key": _mask_api_key(all_settings.get(SETTING_LLM_API_KEY, "")),
        "base_url": all_settings.get(SETTING_LLM_BASE_URL, ""),
        "model_profile": all_settings.get(SETTING_LLM_MODEL_PROFILE, ""),
        "model_recommend": all_settings.get(SETTING_LLM_MODEL_RECOMMEND, ""),
    }


class SettingsUpdate(BaseModel):
    api_key: str | None = None
    base_url: str | None = None
    model_profile: str | None = None
    model_recommend: str | None = None


class ConnectionTest(BaseModel):
    api_key: str
    base_url: str
    model: str


@router.get("")
async def api_get_settings() -> dict[str, str]:
    return _settings_response()


@router.put("")
async def api_update_settings(body: SettingsUpdate) -> dict[str, str]:
    field_map = {
        "api_key": SETTING_LLM_API_KEY,
        "base_url": SETTING_LLM_BASE_URL,
        "model_profile": SETTING_LLM_MODEL_PROFILE,
        "model_recommend": SETTING_LLM_MODEL_RECOMMEND,
    }
    for field_name, setting_key in field_map.items():
        value = getattr(body, field_name)
        if value is not None:
            if field_name == "api_key" and _looks_like_masked_api_key(value):
                # UI still shows masked key; do not overwrite the real secret.
                continue
            set_setting(setting_key, value)

    return _settings_response()


@router.post("/test")
async def api_test_connection(body: ConnectionTest) -> dict[str, str]:
    try:
        api_key = _resolve_api_key_for_test(body.api_key)
        client = LLMClient(api_key=api_key, base_url=body.base_url)
        client._chat("Say 'ok'", model=body.model, temperature=0.0)
    except Exception as exc:
        logger.warning("Settings connection test failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    return {"status": "ok"}


@router.get("/status")
async def api_settings_status() -> dict[str, bool]:
    """Public status: whether an API key is configured and if this is a demo library."""
    has_api_key = bool(get_setting(SETTING_LLM_API_KEY))
    demo_library = get_setting(SETTING_DEMO_LIBRARY) == "true"
    return {"has_api_key": has_api_key, "demo_library": demo_library}
