from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from services.llm.base_provider import LLMAPIError, LLMProvider, LLMProviderError


logger = logging.getLogger("tripmind.llm")
if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)


class LLMManager:
    def __init__(
        self,
        providers: List[LLMProvider],
        cooldown_seconds: int = 300,
        max_retries: int = 2,
    ) -> None:
        self.providers = providers
        self.cooldown_seconds = cooldown_seconds
        self.max_retries = max_retries
        self.provider_status: Dict[str, Dict[str, Optional[object]]] = {}
        self.last_response_metadata: Optional[Dict[str, str]] = None

        for provider in self.providers:
            name = provider.get_provider_name()
            is_healthy = provider.health_check()
            self.provider_status[name] = {
                "provider_name": name,
                "healthy": is_healthy,
                "failure_count": 0,
                "last_failure_time": None,
                "cooldown_until": None,
            }
            if not is_healthy:
                logger.warning(f"[WARNING] Provider not healthy at startup: {name}")

    def generate(self, prompt: str) -> str:
        last_error: Optional[Exception] = None

        for provider in self.providers:
            name = provider.get_provider_name()
            if not self._is_provider_available(provider):
                continue

            logger.info(f"[INFO] Trying provider: {name}")

            for attempt in range(self.max_retries + 1):
                try:
                    response = provider.generate_standardized(prompt)
                    self._mark_provider_success(name)
                    self.last_response_metadata = response
                    logger.info(f"[INFO] Successful response from provider: {name}")
                    return response.get("content", "")
                except LLMProviderError as exc:
                    last_error = exc
                    logger.warning(
                        f"[WARNING] Provider failure: {name} | attempt={attempt + 1} | error={exc}"
                    )
                    if attempt < self.max_retries:
                        backoff_seconds = 2**attempt
                        time.sleep(backoff_seconds)
                        continue
                except Exception as exc:  # pragma: no cover - defensive fallback
                    last_error = exc
                    logger.error(
                        f"[ERROR] Unexpected provider error: {name} | attempt={attempt + 1} | error={exc}"
                    )
                    if attempt < self.max_retries:
                        backoff_seconds = 2**attempt
                        time.sleep(backoff_seconds)
                        continue

                self._mark_provider_failure(name)
                logger.warning(f"[WARNING] Failing over from provider: {name}")
                break

        raise LLMAPIError(f"All providers failed. Last error: {last_error}")

    def get_provider_status(self) -> Dict[str, Dict[str, Optional[object]]]:
        return self.provider_status

    def _is_provider_available(self, provider: LLMProvider) -> bool:
        name = provider.get_provider_name()
        status = self.provider_status[name]

        if not provider.health_check():
            status["healthy"] = False
            return False

        cooldown_until = status.get("cooldown_until")
        if isinstance(cooldown_until, datetime):
            if datetime.utcnow() < cooldown_until:
                return False

            status["healthy"] = True
            status["cooldown_until"] = None
            logger.info(f"[INFO] Provider recovered and re-enabled: {name}")

        return True

    def _mark_provider_failure(self, provider_name: str) -> None:
        status = self.provider_status[provider_name]
        status["healthy"] = False
        status["failure_count"] = int(status["failure_count"] or 0) + 1
        status["last_failure_time"] = datetime.utcnow().isoformat() + "Z"
        status["cooldown_until"] = datetime.utcnow() + timedelta(seconds=self.cooldown_seconds)

    def _mark_provider_success(self, provider_name: str) -> None:
        status = self.provider_status[provider_name]
        status["healthy"] = True
        status["cooldown_until"] = None
