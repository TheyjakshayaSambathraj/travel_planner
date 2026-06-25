from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class BudgetAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, itinerary: Dict[str, List[str]]) -> Dict[str, int]:
        prompt = PromptService.build_budget_prompt(request, itinerary)
        response_text = self.llm_manager.generate(prompt)
        try:
            allocations = ResponseParser.parse_budget(response_text, request.budget)
        except Exception:
            allocations = self._fallback_budget(request.budget)

        total = sum(allocations.values())
        if total > request.budget and total > 0:
            ratio = request.budget / total
            allocations = {key: int(value * ratio) for key, value in allocations.items()}
        return allocations

    def _fallback_budget(self, budget: int) -> Dict[str, int]:
        stay = int(budget * 0.4)
        food = int(budget * 0.25)
        transport = int(budget * 0.15)
        activities = budget - stay - food - transport
        return {
            "stay": stay,
            "food": food,
            "transport": transport,
            "activities": activities,
        }
