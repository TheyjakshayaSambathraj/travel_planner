from __future__ import annotations

import os
import certifi

import requests
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


class OpenRouterProvider(LLMProvider):
    def __init__(self, model_name: str = "openai/gpt-4o-mini") -> None:
        load_dotenv()
        self.api_key = os.getenv("OPENROUTER_API_KEY", "").strip()
        self.model_name = model_name
        self.endpoint = "https://openrouter.ai/api/v1/chat/completions"
        # Windows SSL fix: use certifi CA bundle
        self._certifi = certifi.where()

    def generate(self, prompt: str) -> str:
        if not self.api_key:
            raise LLMAPIError("OpenRouter provider is not configured.")

        try:
            response = requests.post(
                self.endpoint,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                    "HTTP-Referer": "https://tripmind.ai",
                    "X-Title": "TripMind AI",
                },
                json={
                    "model": self.model_name,
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=30,
                verify=False,  # Windows SSL bypass — cert store missing root CAs
            )

            if response.status_code == 429:
                raise LLMRateLimitError(response.text)
            if response.status_code in {401, 403}:
                raise LLMQuotaExceededError(response.text)
            if response.status_code >= 400:
                raise LLMAPIError(f"HTTP {response.status_code}: {response.text[:300]}")

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
        except (LLMRateLimitError, LLMQuotaExceededError, LLMAPIError):
            raise
        except Exception as exc:
            raise LLMAPIError(str(exc))

    def health_check(self) -> bool:
        return bool(self.api_key)

    def get_provider_name(self) -> str:
        return "openrouter"
