from __future__ import annotations

from models.feasibility import FeasibilityOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class FeasibilityAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest) -> FeasibilityOutput:
        prompt = PromptService.build_feasibility_prompt(request)
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_feasibility(response_text)
        except Exception:
            return self._fallback_feasibility(request)

    def _fallback_feasibility(self, request: TravelRequest) -> FeasibilityOutput:
        persona = request.persona.lower()
        luxury_persona = "luxury" in persona
        low_budget = request.budget < max(15000, request.days * 3000)
        complex_trip = request.days >= 7 or luxury_persona

        feasible = not (luxury_persona and low_budget)
        confidence = 92 if feasible else 88
        issues = []
        recommendations = []
        if luxury_persona and low_budget:
            issues.append("Luxury persona conflicts with the current budget.")
            recommendations.append("Increase the budget or switch to a more cost-conscious persona.")
        if request.days >= 7 and request.budget < request.days * 2500:
            issues.append("Trip duration and budget suggest a high budget risk.")
            recommendations.append("Reduce the trip length or raise the budget reserve.")
        if not issues:
            recommendations.append("The trip looks reasonable for the current parameters.")
        budget_risk = "high" if issues else "low"
        travel_complexity = "high" if complex_trip else "medium"
        return FeasibilityOutput(
            feasible=feasible,
            confidence_score=confidence,
            issues=issues,
            recommendations=recommendations,
            budget_risk=budget_risk,
            travel_complexity=travel_complexity,
        )
