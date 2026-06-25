from __future__ import annotations

import os

import requests
from dotenv import load_dotenv

from services.llm.base_provider import (
    LLMAPIError,
    LLMNetworkError,
    LLMProvider,
    LLMQuotaExceededError,
    LLMRateLimitError,
    LLMTimeoutError,
)


class OpenRouterProvider(LLMProvider):
    def __init__(self, model_name: str = "openai/gpt-4o-mini") -> None:
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model_name = model_name
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMAPIError("OpenRouter provider is not configured.")

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
            )

            if response.status_code == 429:
                raise LLMRateLimitError(response.text)
            if response.status_code in {401, 403}:
                raise LLMQuotaExceededError(response.text)
            if response.status_code >= 400:
                raise LLMAPIError(response.text)

            payload = response.json()
            content = payload.get("choices", [{}])[0].get("message", {}).get("content")
            if not content:
                raise LLMAPIError("OpenRouter returned an empty response.")
            return content
        except requests.Timeout as exc:
            raise LLMTimeoutError(str(exc))
        except requests.ConnectionError as exc:
            raise LLMNetworkError(str(exc))
        except requests.RequestException as exc:
            raise LLMAPIError(str(exc))

    def health_check(self) -> bool:
        return bool(self.api_key)

    def get_provider_name(self) -> str:
        return "openrouter"
