from __future__ import annotations

from typing import Callable, Optional

from agents.budget_agent import BudgetAgent
from agents.feasibility_agent import FeasibilityAgent
from agents.food_agent import FoodAgent
from agents.itinerary_agent import ItineraryAgent
from agents.packing_agent import PackingAgent
from agents.research_agent import ResearchAgent
from agents.safety_agent import SafetyAgent
from agents.trip_summary_agent import TripSummaryAgent
from models.agent_outputs import ResearchOutput, TravelPackage
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.llm.provider_registry import ProviderRegistry


class TravelOrchestrator:
    def __init__(self, llm_manager: Optional[LLMManager] = None) -> None:
        self.llm_manager = llm_manager or LLMManager(ProviderRegistry.get_default_providers())
        self.feasibility_agent = FeasibilityAgent(self.llm_manager)
        self.research_agent = ResearchAgent(self.llm_manager)
        self.itinerary_agent = ItineraryAgent(self.llm_manager)
        self.budget_agent = BudgetAgent(self.llm_manager)
        self.food_agent = FoodAgent(self.llm_manager)
        self.packing_agent = PackingAgent(self.llm_manager)
        self.safety_agent = SafetyAgent(self.llm_manager)
        self.summary_agent = TripSummaryAgent(self.llm_manager)

    def generate_trip(
        self,
        request: TravelRequest,
        progress_callback: Optional[Callable[[str], None]] = None,
    ) -> TravelPackage:
        def update(message: str) -> None:
            if progress_callback is not None:
                progress_callback(message)

        update("Validating trip...")
        feasibility = self.feasibility_agent.generate(request)

        update("Researching destination...")
        research = self.research_agent.generate(request.destination)

        update("Planning itinerary...")
        itinerary = self.itinerary_agent.generate(request, research)

        update("Optimizing budget...")
        budget = self.budget_agent.generate(request, research, itinerary)

        update("Finding food...")
        food = self.food_agent.generate(request, research)

        update("Packing essentials...")
        packing = self.packing_agent.generate(request, research)

        update("Safety analysis...")
        safety = self.safety_agent.generate(request, research)

        update("Generating AI summary...")
        summary = self.summary_agent.generate(request, feasibility, research, itinerary, budget, food, packing, safety)

        update("Finalizing travel package...")

        return TravelPackage(
            feasibility=feasibility,
            research=research,
            itinerary=itinerary,
            budget=budget,
            food=food,
            packing=packing,
            safety=safety,
            summary=summary,
        )
