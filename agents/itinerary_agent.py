from __future__ import annotations

from models.agent_outputs import ItineraryDay, ItineraryOutput, ResearchOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class ItineraryAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput) -> ItineraryOutput:
        prompt = PromptService.build_itinerary_prompt(request, self._payload(research))
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_itinerary(response_text, request.days)
        except Exception:
            return self._fallback_itinerary(request)

    def _fallback_itinerary(self, request: TravelRequest) -> ItineraryOutput:
        first_interest = request.interests[0] if request.interests else "local highlights"
        days = []
        for day in range(1, request.days + 1):
            days.append(
                ItineraryDay(
                    day=day,
                    morning=[f"Breakfast and city orientation in {request.destination}"],
                    afternoon=[f"Visit a highlight related to {first_interest}"],
                    evening=["Enjoy dinner with a relaxed evening plan"],
                )
            )
        return ItineraryOutput(days=days)

    @staticmethod
    def _payload(value: ResearchOutput):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
