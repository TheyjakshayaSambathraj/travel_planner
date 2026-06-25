from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict


class LLMProviderError(Exception):
    """Base class for provider errors that should trigger retry/failover."""


class LLMRateLimitError(LLMProviderError):
    pass


class LLMQuotaExceededError(LLMProviderError):
    pass


class LLMTimeoutError(LLMProviderError):
    pass


class LLMNetworkError(LLMProviderError):
    pass


class LLMAPIError(LLMProviderError):
    pass


class LLMProvider(ABC):
    @abstractmethod
    def generate(self, prompt: str) -> str:
        """Generate a response string from the provider."""

    @abstractmethod
    def health_check(self) -> bool:
        """Return True when the provider is configured and reachable for use."""

    @abstractmethod
    def get_provider_name(self) -> str:
        """Return a stable provider identifier."""

    def generate_standardized(self, prompt: str) -> Dict[str, str]:
        content = self.generate(prompt)
        return {
            "provider": self.get_provider_name(),
            "content": content,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        }
