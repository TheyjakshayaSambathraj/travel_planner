from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

from services.llm.base_provider import LLMProvider
from services.llm.providers.gemini_provider import GeminiProvider
from services.llm.providers.groq_provider import GroqProvider
from services.llm.providers.openai_provider import OpenAIProvider
from services.llm.providers.openrouter_provider import OpenRouterProvider

_APP_ROOT = Path(__file__).resolve().parents[2]
_cached_providers: Optional[List[LLMProvider]] = None


class ProviderRegistry:
    """Provider registry with explicit priority ordering for failover."""

    @staticmethod
    def get_default_providers() -> List[LLMProvider]:
        global _cached_providers
        if _cached_providers is None:
            load_dotenv(_APP_ROOT / ".env")
            load_dotenv(_APP_ROOT.parent / ".env")
            _cached_providers = [
                GeminiProvider(),
                GroqProvider(),
                OpenRouterProvider(),
                OpenAIProvider(),
            ]
        return _cached_providers
