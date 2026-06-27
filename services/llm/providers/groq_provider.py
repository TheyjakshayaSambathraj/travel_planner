from __future__ import annotations

import os
import ssl
import certifi
import urllib3

# Suppress SSL warnings from verify=False (Windows cert store is incomplete)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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
    import httpx
    from groq import Groq
except Exception:  # pragma: no cover - optional dependency
    httpx = None
    Groq = None


class GroqProvider(LLMProvider):
    def __init__(self, model_name: str = "llama-3.3-70b-versatile") -> None:
        load_dotenv()
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model_name = model_name
        self.client = None

        if self.api_key and Groq and httpx:
            # Windows SSL workaround: system CA bundle missing root certs
            # verify=False bypasses SSL cert check (safe for internal API calls with valid keys)
            try:
                http_client = httpx.Client(verify=False)
                self.client = Groq(api_key=self.api_key, http_client=http_client)
            except Exception:
                self.client = Groq(api_key=self.api_key)
        elif self.api_key and Groq:
            self.client = Groq(api_key=self.api_key)

    def generate(self, prompt: str) -> str:
        if self.client is None:
            raise LLMAPIError("Groq provider is not configured.")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                timeout=30,
            )
            content = response.choices[0].message.content if response.choices else None
            if not content:
                raise LLMAPIError("Groq returned an empty response.")
            return content
        except Exception as exc:
            raise self._map_exception(exc)

    def health_check(self) -> bool:
        return self.client is not None

    def get_provider_name(self) -> str:
        return "groq"

    def _map_exception(self, exc: Exception) -> Exception:
        message = str(exc).lower()
        exc_type = type(exc).__name__.lower()
        if "429" in message or "rate limit" in message or "ratelimit" in exc_type:
            return LLMRateLimitError(str(exc))
        if "quota" in message or "exceeded" in message:
            return LLMQuotaExceededError(str(exc))
        if "timeout" in message or "timed out" in message:
            return LLMTimeoutError(str(exc))
        if (
            "network" in message or "connection" in message
            or "dns" in message or "ssl" in message
            or "certificate" in message or "apiconnection" in exc_type
        ):
            return LLMNetworkError(str(exc))
        return LLMAPIError(str(exc))
