from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

APP_ROOT = Path(__file__).resolve().parents[1]
_ENV_BOOTSTRAPPED = False

PROVIDER_ENV_KEYS = {
    "gemini": "GEMINI_API_KEY",
    "groq": "GROQ_API_KEY",
    "openrouter": "OPENROUTER_API_KEY",
    "openai": "OPENAI_API_KEY",
}


def bootstrap_env() -> None:
    """Load .env from app root (and parent) before provider initialization."""
    global _ENV_BOOTSTRAPPED
    if _ENV_BOOTSTRAPPED:
        return
    load_dotenv(APP_ROOT / ".env")
    load_dotenv(APP_ROOT.parent / ".env")
    _ENV_BOOTSTRAPPED = True


def get_configured_provider_names() -> list[str]:
    bootstrap_env()
    configured: list[str] = []
    for name, env_key in PROVIDER_ENV_KEYS.items():
        if os.getenv(env_key, "").strip():
            configured.append(name)
    return configured
