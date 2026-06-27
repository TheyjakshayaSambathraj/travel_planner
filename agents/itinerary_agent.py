from __future__ import annotations

from typing import Dict, List, Set

from models.agent_outputs import ItineraryDay, ItineraryOutput, ResearchOutput, TimelineItem
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.prompt_service import PromptService
from services.response_parser import ResponseParser


class ItineraryAgent:
    def __init__(self, llm_manager: LLMManager) -> None:
        self.llm_manager = llm_manager

    def generate(self, request: TravelRequest, research: ResearchOutput) -> ItineraryOutput:
        research_payload = self._payload(research)
        prompt = PromptService.build_itinerary_prompt(request, research_payload)
        try:
            response_text = self.llm_manager.generate(prompt)
            itinerary = ResponseParser.parse_itinerary(response_text, request.days)
        except Exception:
            itinerary = self._fallback_itinerary(request, research)

        return self._ensure_unique_itinerary(request, research, itinerary)

    def _ensure_unique_itinerary(
        self,
        request: TravelRequest,
        research: ResearchOutput,
        itinerary: ItineraryOutput,
    ) -> ItineraryOutput:
        for _ in range(3):
            duplicate_days = self._find_duplicate_days(itinerary)
            if not duplicate_days:
                return itinerary

            used = self._collect_signatures(itinerary)
            updated_days = list(itinerary.days)
            for day_num in duplicate_days:
                regenerated = self._regenerate_day(
                    request,
                    research,
                    day_num,
                    sorted(used),
                )
                if regenerated:
                    updated_days = self._replace_day(updated_days, regenerated)
                    used = self._collect_signatures(ItineraryOutput(days=updated_days))

            itinerary = ItineraryOutput(days=updated_days)

        return itinerary

    def _regenerate_day(
        self,
        request: TravelRequest,
        research: ResearchOutput,
        day_number: int,
        excluded: List[str],
    ) -> ItineraryDay | None:
        prompt = PromptService.build_itinerary_day_prompt(
            request,
            self._payload(research),
            day_number,
            excluded,
        )
        try:
            response_text = self.llm_manager.generate(prompt)
            parsed = ResponseParser.parse_json(response_text)
            day_payload = parsed.get("day") if isinstance(parsed.get("day"), dict) else parsed
            if not isinstance(day_payload, dict):
                return None
            return ItineraryDay(
                day=day_number,
                morning=day_payload.get("morning", []),
                afternoon=day_payload.get("afternoon", []),
                evening=day_payload.get("evening", []),
            )
        except Exception:
            return self._fallback_day(request, research, day_number, excluded)

    def _fallback_itinerary(self, request: TravelRequest, research: ResearchOutput) -> ItineraryOutput:
        days = [
            self._fallback_day(request, research, day, [])
            for day in range(1, request.days + 1)
        ]
        return ItineraryOutput(days=days)

    def _fallback_day(
        self,
        request: TravelRequest,
        research: ResearchOutput,
        day_number: int,
        excluded: List[str],
    ) -> ItineraryDay:
        areas = research.popular_areas or [f"District {day_number}", f"Old Town {request.destination}"]
        highlights = research.key_highlights or ["local market", "heritage quarter", "waterfront"]
        area = areas[(day_number - 1) % len(areas)]
        highlight = highlights[(day_number - 1) % len(highlights)]
        total_days = request.days

        if day_number == 1:
            morning = TimelineItem(activity=f"Arrive and check in near {area}", location=area)
            afternoon = TimelineItem(activity=f"Orientation walk through {area}", location=request.destination)
            evening = TimelineItem(activity=f"Welcome dinner featuring local cuisine", location=area)
        elif day_number == total_days:
            morning = TimelineItem(activity=f"Relaxed breakfast in {area}", location=area)
            afternoon = TimelineItem(activity=f"Souvenir shopping at {highlight}", location=request.destination)
            evening = TimelineItem(activity="Departure and airport/station transfer", location=request.destination)
        else:
            morning = TimelineItem(
                activity=f"Explore {highlight} with a guided visit",
                location=request.destination,
            )
            afternoon = TimelineItem(
                activity=f"Discover hidden streets in {area}",
                location=area,
            )
            evening = TimelineItem(
                activity=f"Evening experience aligned with {request.persona} in {area}",
                location=area,
            )

        for item in (morning, afternoon, evening):
            signature = self._signature(item)
            if signature in excluded:
                item.activity = f"{item.activity} (alternate route day {day_number})"

        return ItineraryDay(day=day_number, morning=[morning], afternoon=[afternoon], evening=[evening])

    @staticmethod
    def _signature(item: TimelineItem) -> str:
        activity = item.activity.lower().strip()
        location = item.location.lower().strip()
        return f"{activity}|{location}" if location else activity

    def _collect_signatures(self, itinerary: ItineraryOutput) -> Set[str]:
        signatures: Set[str] = set()
        for day in itinerary.days:
            for item in self._iter_items(day):
                signatures.add(self._signature(item))
        return signatures

    def _find_duplicate_days(self, itinerary: ItineraryOutput) -> List[int]:
        seen: Dict[str, int] = {}
        duplicate_days: List[int] = []
        for day in itinerary.days:
            day_has_duplicate = False
            for item in self._iter_items(day):
                signature = self._signature(item)
                if not signature:
                    continue
                if signature in seen:
                    day_has_duplicate = True
                    break
                seen[signature] = day.day
            if day_has_duplicate or self._days_are_identical(day, itinerary):
                duplicate_days.append(day.day)
        return sorted(set(duplicate_days))

    @staticmethod
    def _iter_items(day: ItineraryDay) -> List[TimelineItem]:
        return list(day.morning) + list(day.afternoon) + list(day.evening)

    def _days_are_identical(self, day: ItineraryDay, itinerary: ItineraryOutput) -> bool:
        current = [self._signature(item) for item in self._iter_items(day)]
        for other in itinerary.days:
            if other.day == day.day:
                continue
            other_sigs = [self._signature(item) for item in self._iter_items(other)]
            if current and current == other_sigs:
                return True
        return False

    @staticmethod
    def _replace_day(days: List[ItineraryDay], new_day: ItineraryDay) -> List[ItineraryDay]:
        return [new_day if day.day == new_day.day else day for day in days]

    @staticmethod
    def _payload(value: ResearchOutput):
        if hasattr(value, "model_dump"):
            return value.model_dump()
        return value.dict()
