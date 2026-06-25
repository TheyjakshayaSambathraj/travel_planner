from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class ItineraryAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest) -> Dict[str, List[str]]:
        prompt = PromptService.build_itinerary_prompt(request)
        response_text = self.llm_manager.generate(prompt)
        try:
            return ResponseParser.parse_itinerary(response_text, request.days)
        except Exception:
            return self._fallback_itinerary(request)

    def _fallback_itinerary(self, request: TravelRequest) -> Dict[str, List[str]]:
        itinerary: Dict[str, List[str]] = {}
        first_interest = request.interests[0] if request.interests else "local highlights"
        for day in range(1, request.days + 1):
            itinerary[f"day{day}"] = [
                f"Breakfast and city orientation in {request.destination}",
                f"Visit a highlight related to {first_interest}",
                "Enjoy dinner with a relaxed evening plan",
            ]
        return itinerary
