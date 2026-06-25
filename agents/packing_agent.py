from __future__ import annotations

from models.agent_outputs import PackingOutput, ResearchOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class PackingAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput) -> PackingOutput:
        prompt = PromptService.build_packing_prompt(request, self._payload(research))
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_packing(response_text)
        except Exception:
            return self._fallback_packing(request, research)

    def _fallback_packing(self, request: TravelRequest, research: ResearchOutput) -> PackingOutput:
        climate_hint = research.best_time_to_visit.lower()
        weather_items = ["Light jacket" if "cool" in climate_hint or "winter" in climate_hint else "Compact umbrella"]
        return PackingOutput(
            essentials=["ID proof", "Wallet", "Basic medication"],
            weather_items=weather_items,
            electronics=["Phone charger", "Power bank"],
            documents=["Tickets", "Hotel confirmation", "Emergency contact list"],
        )

    @staticmethod
    def _payload(value: ResearchOutput):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
