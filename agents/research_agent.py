from __future__ import annotations

from models.agent_outputs import ResearchOutput
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class ResearchAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, destination: str) -> ResearchOutput:
        prompt = PromptService.build_research_prompt(destination)
        try:
            response_text = self.llm_manager.generate(prompt)
            return ResponseParser.parse_research(response_text)
        except Exception:
            return ResearchOutput(
                destination_overview=f"{destination} is a travel destination with local culture, food, and key sightseeing areas.",
                best_time_to_visit="Plan for the best local weather and festival window.",
                popular_areas=[f"Central {destination}", f"Historic {destination}"],
                local_transport=["Local taxis", "Public transport", "Walking"],
                key_highlights=["Local culture", "Popular attractions", "Food experiences"],
            )
