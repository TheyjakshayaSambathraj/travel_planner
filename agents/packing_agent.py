from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class PackingAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest) -> Dict[str, List[str]]:
        prompt = PromptService.build_packing_prompt(request)
        response_text = self.llm_manager.generate(prompt)
        try:
            return ResponseParser.parse_packing(response_text)
        except Exception:
            return self._fallback_packing()

    def _fallback_packing(self) -> Dict[str, List[str]]:
        return {
            "essentials": ["ID proof", "Wallet", "Phone charger", "Medication"],
            "travel_items": ["Reusable bottle", "Comfortable shoes", "Power bank", "Day bag"],
        }
