from __future__ import annotations

from models.agent_outputs import ResearchOutput, SafetyOutput
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class SafetyAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput) -> SafetyOutput:
        prompt = PromptService.build_safety_prompt(request, self._payload(research))
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_safety(response_text)
        except Exception:
            return self._fallback_safety(request, research)

    def _fallback_safety(self, request: TravelRequest, research: ResearchOutput) -> SafetyOutput:
        return SafetyOutput(
            travel_tips=[
                "Keep digital copies of important documents",
                f"Review local transport options listed for {request.destination}",
                "Use trusted transport providers",
            ],
            warnings=[
                "Avoid isolated areas late at night",
                "Do not leave valuables unattended",
            ],
            local_etiquette=["Respect local customs", "Dress appropriately for religious sites"],
            emergency_contacts=["Local police: 100", "Ambulance: 108"],
        )

    @staticmethod
    def _payload(value: ResearchOutput):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
