from __future__ import annotations

from models.agent_outputs import BudgetOutput, ItineraryOutput, ResearchOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class BudgetAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput, itinerary: ItineraryOutput) -> BudgetOutput:
        prompt = PromptService.build_budget_prompt(request, self._payload(research), self._payload(itinerary))
        try:
            response_text = self.llm_manager.generate(prompt)
            allocations = ResponseParser.parse_budget(response_text, request.budget)
        except Exception:
            allocations = self._fallback_budget(request.budget)
        return allocations

    def _fallback_budget(self, budget: int) -> BudgetOutput:
        emergency_buffer = int(budget * 0.1)
        remaining = max(budget - emergency_buffer, 0)
        accommodation = int(remaining * 0.4)
        food = int(remaining * 0.25)
        transport = int(remaining * 0.15)
        activities = remaining - accommodation - food - transport
        return BudgetOutput(
            accommodation=accommodation,
            food=food,
            transport=transport,
            activities=activities,
            emergency_buffer=emergency_buffer,
            allocation_reasoning="Fallback allocation reserves a 10% emergency buffer and prioritizes accommodation and food.",
        )

    @staticmethod
    def _payload(value):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
