from __future__ import annotations

from typing import List

from services.llm.base_provider import LLMProvider
from services.llm.providers.gemini_provider import GeminiProvider
from services.llm.providers.groq_provider import GroqProvider
from services.llm.providers.openai_provider import OpenAIProvider
from services.llm.providers.openrouter_provider import OpenRouterProvider


class ProviderRegistry:
    """Provider registry with explicit priority ordering for failover."""

    @staticmethod
    def get_default_providers() -> List[LLMProvider]:
        return [
            GeminiProvider(),
            GroqProvider(),
            OpenRouterProvider(),
            OpenAIProvider(),
        ]
