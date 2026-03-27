from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv


def _load_environment() -> None:
    env_path = Path(__file__).parent.absolute() / ".env"
    if env_path.exists():
        load_dotenv(env_path, override=True)


_load_environment()


class Config:
    @property
    def LLM_API_KEY(self) -> str:
        return os.environ.get("LLM_API_KEY", "")

    @property
    def LLM_BASE_URL(self) -> str:
        return os.environ.get("LLM_BASE_URL", "https://routerai.ru/api/v1")

    @property
    def LLM_MODEL_ENRICH(self) -> str:
        return os.environ.get(
            "LLM_MODEL_ENRICH", "openai/gpt-4o-mini-search-preview"
        )

    @property
    def LLM_MODEL_PROFILE(self) -> str:
        return os.environ.get("LLM_MODEL_PROFILE", "openai/gpt-4o-mini")

    @property
    def LLM_MODEL_RECOMMEND(self) -> str:
        return os.environ.get(
            "LLM_MODEL_RECOMMEND", "openai/gpt-4o-mini-search-preview"
        )

    @property
    def DEBUG(self) -> bool:
        return os.environ.get("DEBUG", "false").lower() in ("true", "1", "yes")

    @property
    def ENRICH_MAX_CONCURRENT(self) -> int:
        """Max parallel LLM enrich calls (cached books do not consume slots)."""
        raw = os.environ.get("ENRICH_MAX_CONCURRENT", "4").strip()
        try:
            n = int(raw)
        except ValueError:
            return 4
        return max(1, min(n, 32))

    def get_llm_setting(self, key: str) -> str:
        """Check settings DB first, then fall back to env-based property."""
        from app.services.settings_db import get_setting

        db_value = get_setting(key)
        if db_value:
            return db_value

        _property_map: dict[str, str] = {
            "llm_api_key": "LLM_API_KEY",
            "llm_base_url": "LLM_BASE_URL",
            "llm_model_enrich": "LLM_MODEL_ENRICH",
            "llm_model_profile": "LLM_MODEL_PROFILE",
            "llm_model_recommend": "LLM_MODEL_RECOMMEND",
        }
        prop = _property_map.get(key)
        if prop:
            return getattr(self, prop)
        return ""


config = Config()
