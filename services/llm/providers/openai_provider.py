from __future__ import annotations

import os

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
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency import
    OpenAI = None


class OpenAIProvider(LLMProvider):
    def __init__(self, model_name: str = "gpt-4o-mini") -> None:
        load_dotenv()
        self.api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.model_name = model_name
        self.client = OpenAI(api_key=self.api_key) if self.api_key and OpenAI else None

    def generate(self, prompt: str) -> str:
        if self.client is None:
            raise LLMAPIError("OpenAI provider is not configured.")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )
            content = response.choices[0].message.content if response.choices else None
            if not content:
                raise LLMAPIError("OpenAI returned an empty response.")
            return content
        except Exception as exc:
            raise self._map_exception(exc)

    def health_check(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "openai"

    def _map_exception(self, exc: Exception) -> Exception:
        message = str(exc).lower()
        if "429" in message or "rate limit" in message:
            return LLMRateLimitError(str(exc))
        if "quota" in message or "insufficient_quota" in message or "exceeded" in message:
            return LLMQuotaExceededError(str(exc))
        if "timeout" in message or "timed out" in message:
            return LLMTimeoutError(str(exc))
        if "network" in message or "connection" in message or "dns" in message:
            return LLMNetworkError(str(exc))
        return LLMAPIError(str(exc))
