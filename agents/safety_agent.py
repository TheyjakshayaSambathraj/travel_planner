from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class SafetyAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest) -> Dict[str, List[str]]:
        prompt = PromptService.build_safety_prompt(request)
        response_text = self.llm_manager.generate(prompt)
        try:
            return ResponseParser.parse_safety(response_text)
        except Exception:
            return self._fallback_safety()

    def _fallback_safety(self) -> Dict[str, List[str]]:
        return {
            "tips": [
                "Keep copies of important documents",
                "Use trusted transport providers",
                "Stay aware of local customs",
            ],
            "warnings": [
                "Avoid isolated areas late at night",
                "Do not leave valuables unattended",
            ],
        }
