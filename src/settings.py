"""
settings.py
===========
12-factor configuration via environment variables (Phase 4/5).

Unlike `config.py` (ML hyper-parameters and paths that are part of the model),
this holds *operational* settings that change per environment: database URL,
API auth, rate limits, CORS. Everything has a safe local default so the demo
runs with zero configuration, but production can override via env vars or a
`.env` file.
"""

from __future__ import annotations

from pathlib import Path

try:
    from pydantic_settings import BaseSettings, SettingsConfigDict
    from pydantic import Field
    _HAVE_PYDANTIC_SETTINGS = True
except Exception:  # pragma: no cover - fallback if not installed
    _HAVE_PYDANTIC_SETTINGS = False

_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_DB = f"sqlite:///{_PROJECT_ROOT / 'fraudshield.db'}"


if _HAVE_PYDANTIC_SETTINGS:
    class Settings(BaseSettings):
        model_config = SettingsConfigDict(
            env_prefix="FRAUDSHIELD_", env_file=".env", extra="ignore")

        # Persistence. SQLite by default; set to a postgresql://... URL in prod.
        database_url: str = _DEFAULT_DB

        # Auth. If empty, the API is OPEN (good for the local demo). Set a value
        # to require `X-API-Key: <value>` on scoring/training/dataset endpoints.
        api_key: str = ""

        # Rate limit (requests/minute per client) for the scoring endpoints.
        rate_limit: str = "120/minute"

        # CORS origins (comma-separated). "*" for the demo.
        cors_origins: str = "*"

        # Toggle persistence of every score to the audit DB.
        persist_scores: bool = True

        @property
        def auth_required(self) -> bool:
            return bool(self.api_key)

        @property
        def cors_list(self) -> list[str]:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    settings = Settings()

else:  # minimal fallback so the app still imports without pydantic-settings
    import os

    class _Fallback:
        database_url = os.environ.get("FRAUDSHIELD_DATABASE_URL", _DEFAULT_DB)
        api_key = os.environ.get("FRAUDSHIELD_API_KEY", "")
        rate_limit = os.environ.get("FRAUDSHIELD_RATE_LIMIT", "120/minute")
        cors_origins = os.environ.get("FRAUDSHIELD_CORS_ORIGINS", "*")
        persist_scores = os.environ.get("FRAUDSHIELD_PERSIST_SCORES", "1") not in ("0", "false")

        @property
        def auth_required(self) -> bool:
            return bool(self.api_key)

        @property
        def cors_list(self) -> list[str]:
            return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    settings = _Fallback()
