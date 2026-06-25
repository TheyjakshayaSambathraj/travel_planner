from __future__ import annotations

from typing import Callable, Optional

from agents.budget_agent import BudgetAgent
from agents.food_agent import FoodAgent
from agents.itinerary_agent import ItineraryAgent
from agents.packing_agent import PackingAgent
from agents.safety_agent import SafetyAgent
from models.travel_package import TravelPackage
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.llm.provider_registry import ProviderRegistry


class TravelOrchestrator:
    def __init__(self, llm_manager: Optional[LLMManager] = None) -> None:
        self.llm_manager = llm_manager or LLMManager(ProviderRegistry.get_default_providers())
        self.itinerary_agent = ItineraryAgent(self.llm_manager)
        self.budget_agent = BudgetAgent(self.llm_manager)
        self.food_agent = FoodAgent(self.llm_manager)
        self.packing_agent = PackingAgent(self.llm_manager)
        self.safety_agent = SafetyAgent(self.llm_manager)

    def generate_trip(
        self,
        request: TravelRequest,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TravelPackage:
        def update(message: str) -> None:
            if progress_callback is not None:
                progress_callback(message)

        update("Generating itinerary...")
        itinerary = self.itinerary_agent.generate(request)

        update("Planning budget...")
        budget = self.budget_agent.generate(request, itinerary)

        update("Finding local foods...")
        food = self.food_agent.generate(request)

        update("Preparing packing checklist...")
        packing = self.packing_agent.generate(request)

        update("Generating travel tips...")
        safety = self.safety_agent.generate(request)

        return TravelPackage(
            itinerary=itinerary,
            budget=budget,
            food=food,
            packing=packing,
            safety=safety,
        )
