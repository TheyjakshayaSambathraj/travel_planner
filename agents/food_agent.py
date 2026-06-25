from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class FoodAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest) -> Dict[str, List[str]]:
        prompt = PromptService.build_food_prompt(request)
        response_text = self.llm_manager.generate(prompt)
        try:
            return ResponseParser.parse_food(response_text)
        except Exception:
            return self._fallback_food(request)

    def _fallback_food(self, request: TravelRequest) -> Dict[str, List[str]]:
        return {
            "must_try": [
                f"Signature dish from {request.destination}",
                "Popular local snack",
                "Regional dessert",
            ],
            "recommended_restaurants": [
                f"Well-reviewed heritage restaurant in {request.destination}",
                "Busy neighborhood cafe",
                "Local family-run eatery",
            ],
        }
