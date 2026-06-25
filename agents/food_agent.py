from __future__ import annotations

from models.agent_outputs import FoodOutput, ResearchOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class FoodAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput) -> FoodOutput:
        prompt = PromptService.build_food_prompt(request, self._payload(research))
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_food(response_text)
        except Exception:
            return self._fallback_food(request)

    def _fallback_food(self, request: TravelRequest) -> FoodOutput:
        return FoodOutput(
            must_try_foods=[
                f"Signature dish from {request.destination}",
                "Popular local breakfast specialty",
                "Regional dessert",
            ],
            street_foods=["Local savory snack", "Seasonal street bite"],
            recommended_restaurants=[
                f"Well-reviewed heritage restaurant in {request.destination}",
                "Busy neighborhood cafe",
                "Local family-run eatery",
            ],
            food_tips=["Try signature dishes early in the trip", "Book popular venues ahead of time"],
        )

    @staticmethod
    def _payload(value: ResearchOutput):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
