from __future__ import annotations

import os
from typing import Optional

from dotenv import load_dotenv

from services.llm.base_provider import (
    LLMAPIError,
    LLMNetworkError,
    LLMProvider,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency
    genai = None


class GeminiProvider(LLMProvider):
    # gemini-pro is stable and available on the free tier with google-generativeai SDK
    def __init__(self, model_name: str = "gemini-pro") -> None:
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name
        self.ready = bool(self.api_key and genai is not None)

        if self.ready:
            genai.configure(api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        if not self.ready:
            raise LLMAPIError("Gemini provider is not configured.")

        try:
            model = genai.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            text = getattr(response, "text", None)
            if not text:
                raise LLMAPIError("Gemini returned an empty response.")
            return text
        except Exception as exc:
            raise self._map_exception(exc)

    def health_check(self) -> bool:
        return self.ready

    def get_provider_name(self) -> str:
        return "gemini"

    def _map_exception(self, exc: Exception) -> Exception:
        message = str(exc).lower()
        exc_type = type(exc).__name__
        # ResourceExhausted (429) — maps to rate limit for proper cooldown
        if "resourceexhausted" in exc_type.lower() or "429" in message or "rate limit" in message:
            return LLMRateLimitError(str(exc))
        if "quota" in message or "exceeded" in message or "insufficient" in message:
            return LLMQuotaExceededError(str(exc))
        if "timeout" in message or "timed out" in message:
            return LLMTimeoutError(str(exc))
        if "network" in message or "connection" in message or "dns" in message or "ssl" in message:
            return LLMNetworkError(str(exc))
        return LLMAPIError(str(exc))
