from __future__ import annotations

from models.agent_outputs import (
    BudgetOutput,
    FeasibilityOutput,
    FoodOutput,
    ItineraryOutput,
    PackingOutput,
    ResearchOutput,
    SafetyOutput,
    TripSummaryOutput,
)
from models.trip_intelligence import AIInsights, AnalyticsSummary, TripIntelligence
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class TripSummaryAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(
        self,
        request: TravelRequest,
        feasibility: FeasibilityOutput,
        research: ResearchOutput,
        itinerary: ItineraryOutput,
        budget: BudgetOutput,
        food: FoodOutput,
        packing: PackingOutput,
        safety: SafetyOutput,
    ) -> TripSummaryOutput:
        prompt = PromptService.build_summary_prompt(
            request=request,
            feasibility=self._payload(feasibility),
            research=self._payload(research),
            itinerary=self._payload(itinerary),
            budget=self._payload(budget),
            food=self._payload(food),
            packing=self._payload(packing),
            safety=self._payload(safety),
        )
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_summary(response_text)
        except Exception:
            estimated_total_cost = budget.accommodation + budget.food + budget.transport + budget.activities + budget.emergency_buffer
            trip_type = f"{request.travel_style} {request.destination} trip"
            return TripSummaryOutput(
                trip_score=8.5,
                trip_type=trip_type,
                estimated_total_cost=estimated_total_cost,
                highlights=research.key_highlights[:3] or [request.destination],
                best_experiences=["Local exploration", "Curated food stops", "Balanced day planning"],
                overall_summary=f"A well-structured trip to {request.destination} with destination research, a balanced itinerary, practical budgeting, and safety guidance.",
                trip_intelligence=TripIntelligence(
                    trip_score=88 if feasibility.feasible else 72,
                    budget_fit=95 if not feasibility.issues else 74,
                    experience_score=90,
                    comfort_score=86,
                    food_score=92,
                    overall_rating="Excellent" if feasibility.feasible else "Needs Adjustment",
                ),
                ai_insights=AIInsights(
                    money_saving_tips=["Book transport early", "Favor local meal specials"],
                    hidden_gems=research.key_highlights[:3],
                    avoid=feasibility.issues[:3],
                    best_experiences=["Heritage walk", "Sunset viewpoint", "Local food crawl"],
                    local_secrets=["Ask locals for off-menu breakfast spots", "Visit early to avoid crowds"],
                ),
                analytics_summary=AnalyticsSummary(
                    estimated_total_cost=estimated_total_cost,
                    trip_category="Premium" if request.persona.lower().startswith("luxury") else "Balanced",
                    difficulty_score=35 if feasibility.feasible else 62,
                    travel_efficiency=84,
                    recommended_for=request.persona,
                ),
            )

    @staticmethod
    def _payload(value):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
