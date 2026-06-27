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
logger.setLevel(logging.ERROR)

_startup_logged = False


class LLMManager:
    def __init__(
        self,
        providers: List[LLMProvider],
        cooldown_seconds: int = 300,
        max_retries: int = 2,
    ) -> None:
        global _startup_logged
        self.providers = providers
        self.cooldown_seconds = cooldown_seconds
        self.max_retries = max_retries
        self.provider_status: Dict[str, Dict[str, Optional[object]]] = {}
        self.last_response_metadata: Optional[Dict[str, str]] = None
        self.active_provider_name: Optional[str] = None
        self.last_failover_event: Optional[Dict[str, str]] = None

        configured: List[str] = []
        unconfigured: List[str] = []
        for provider in self.providers:
            name = provider.get_provider_name()
            is_configured = provider.health_check()
            self.provider_status[name] = {
                "provider_name": name,
                "configured": is_configured,
                "healthy": is_configured,
                "failure_count": 0,
                "last_failure_time": None,
                "cooldown_until": None,
            }
            if is_configured:
                configured.append(name)
            else:
                unconfigured.append(name)

        if not _startup_logged:
            _startup_logged = True
            if configured:
                logger.setLevel(logging.INFO)
                logger.info("TripMind AI started — providers loaded: %s", ", ".join(configured))
                logger.setLevel(logging.ERROR)
            if unconfigured:
                logger.warning(
                    "Missing API keys for: %s (configure .env to enable)",
                    ", ".join(unconfigured),
                )

    def generate(self, prompt: str) -> str:
        last_error: Optional[Exception] = None
        previous_provider = self.active_provider_name

        for provider in self.providers:
            name = provider.get_provider_name()
            if not self._is_provider_available(provider):
                continue

            for attempt in range(self.max_retries + 1):
                try:
                    response = provider.generate_standardized(prompt)
                    self._mark_provider_success(name)
                    self.active_provider_name = name
                    self.last_response_metadata = response
                    if previous_provider and previous_provider != name:
                        self.last_failover_event = {
                            "from": previous_provider,
                            "to": name,
                            "timestamp": datetime.utcnow().isoformat() + "Z",
                        }
                        logger.setLevel(logging.INFO)
                        logger.info("Provider switched: %s -> %s", previous_provider, name)
                        logger.setLevel(logging.ERROR)
                    return response.get("content", "")
                except LLMProviderError as exc:
                    last_error = exc
                    if attempt < self.max_retries:
                        time.sleep(2**attempt)
                        continue
                except Exception as exc:  # pragma: no cover - defensive fallback
                    last_error = exc
                    if attempt < self.max_retries:
                        time.sleep(2**attempt)
                        continue

                self._mark_provider_failure(name)
                logger.error("Provider failed: %s", name)
                break

        raise LLMAPIError(f"All providers failed. Last error: {last_error}")

    def get_provider_status(self) -> Dict[str, Dict[str, Optional[object]]]:
        return self.provider_status

    def get_active_provider(self) -> Optional[str]:
        return self.active_provider_name

    def get_primary_configured_provider(self) -> Optional[str]:
        for provider in self.providers:
            name = provider.get_provider_name()
            if self.provider_status.get(name, {}).get("configured"):
                return name
        return None

    def has_fallback_available(self) -> bool:
        available = [
            name
            for name, status in self.provider_status.items()
            if status.get("configured") and self._status_available(name)
        ]
        return len(available) > 1

    def _status_available(self, name: str) -> bool:
        status = self.provider_status.get(name, {})
        if not status.get("configured"):
            return False
        cooldown_until = status.get("cooldown_until")
        if isinstance(cooldown_until, datetime) and datetime.utcnow() < cooldown_until:
            return False
        return True

    def _is_provider_available(self, provider: LLMProvider) -> bool:
        name = provider.get_provider_name()
        status = self.provider_status[name]

        if not status.get("configured"):
            return False

        cooldown_until = status.get("cooldown_until")
        if isinstance(cooldown_until, datetime):
            if datetime.utcnow() < cooldown_until:
                return False
            status["cooldown_until"] = None
            status["healthy"] = True

        return bool(status.get("healthy", True))

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
