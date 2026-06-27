from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Type, TypeVar

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

ModelType = TypeVar("ModelType")


class ResponseParser:
    @staticmethod
    def _extract_json_block(text: str) -> str:
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1)

        object_match = re.search(r"\{.*\}", text, re.DOTALL)
        if object_match:
            return object_match.group(0)

        raise ValueError("No JSON object found in LLM response.")

    @classmethod
    def parse_json(cls, text: str) -> Dict[str, Any]:
        json_text = cls._extract_json_block(text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError("LLM response was not valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("LLM response must be a JSON object.")
        return parsed

    @staticmethod
    def _validate_model(model_class: Type[ModelType], payload: Dict[str, Any]) -> ModelType:
        if hasattr(model_class, "model_validate"):
            return model_class.model_validate(payload)  # type: ignore[attr-defined]
        return model_class.parse_obj(payload)  # type: ignore[attr-defined]

    @staticmethod
    def _as_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split("\n") if item.strip()]
        return []

    @classmethod
    def _as_activity_list(cls, value: Any) -> List[Dict[str, str]]:
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [{"activity": item, "location": ""} for item in items if item]
        if not isinstance(value, list):
            return []

        activities: List[Dict[str, str]] = []
        for item in value:
            if isinstance(item, dict):
                activity = str(item.get("activity", "")).strip()
                location = str(item.get("location", "")).strip()
                if activity:
                    activities.append({"activity": activity, "location": location})
            elif isinstance(item, str) and item.strip():
                activities.append({"activity": item.strip(), "location": ""})
        return activities

    @classmethod
    def parse_itinerary(cls, text: str, days: int) -> ItineraryOutput:
        parsed = cls.parse_json(text)
        days_payload = parsed.get("days", [])
        if not isinstance(days_payload, list):
            raise ValueError("Itinerary response must contain a days array.")

        if len(days_payload) != days:
            raise ValueError("Itinerary response did not include all requested days.")

        normalized_days = []
        for day_payload in days_payload:
            if not isinstance(day_payload, dict):
                raise ValueError("Each itinerary day must be an object.")
            normalized_days.append(
                {
                    "day": day_payload.get("day", 0),
                    "morning": cls._as_activity_list(day_payload.get("morning", [])),
                    "afternoon": cls._as_activity_list(day_payload.get("afternoon", [])),
                    "evening": cls._as_activity_list(day_payload.get("evening", [])),
                }
            )

        return cls._validate_model(ItineraryOutput, {"days": normalized_days})

    @classmethod
    def parse_budget(cls, text: str, budget: int) -> BudgetOutput:
        parsed = cls.parse_json(text)
        model = cls._validate_model(BudgetOutput, parsed)
        total = model.accommodation + model.food + model.transport + model.activities + model.emergency_buffer
        if total > budget and total > 0:
            raise ValueError("Budget allocation exceeds the available budget.")
        return model

    @classmethod
    def parse_food(cls, text: str) -> FoodOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(FoodOutput, parsed)

    @classmethod
    def parse_packing(cls, text: str) -> PackingOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(PackingOutput, parsed)

    @classmethod
    def parse_safety(cls, text: str) -> SafetyOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(SafetyOutput, parsed)

    @classmethod
    def parse_research(cls, text: str) -> ResearchOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(ResearchOutput, parsed)

    @classmethod
    def parse_summary(cls, text: str) -> TripSummaryOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(TripSummaryOutput, parsed)

    @classmethod
    def parse_feasibility(cls, text: str) -> FeasibilityOutput:
        parsed = cls.parse_json(text)
        return cls._validate_model(FeasibilityOutput, parsed)
