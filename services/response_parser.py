from __future__ import annotations

import json
import re
from typing import Any, Dict, List


class ResponseParser:
    @staticmethod
    def _extract_json_block(text: str) -> str:
        fenced_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, re.DOTALL)
        if fenced_match:
            return fenced_match.group(1)

        object_match = re.search(r"\{.*\}", text, re.DOTALL)
        if object_match:
            return object_match.group(0)

        raise ValueError("No JSON object found in Gemini response.")

    @classmethod
    def parse_json(cls, text: str) -> Dict[str, Any]:
        json_text = cls._extract_json_block(text)
        try:
            parsed = json.loads(json_text)
        except json.JSONDecodeError as exc:
            raise ValueError("Gemini response was not valid JSON.") from exc

        if not isinstance(parsed, dict):
            raise ValueError("Gemini response must be a JSON object.")
        return parsed

    @staticmethod
    def _as_list(value: Any) -> List[str]:
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()]
        if isinstance(value, str):
            return [item.strip() for item in value.split("\n") if item.strip()]
        return []

    @classmethod
    def parse_itinerary(cls, text: str, days: int) -> Dict[str, List[str]]:
        parsed = cls.parse_json(text)
        itinerary: Dict[str, List[str]] = {}
        for day_index in range(1, days + 1):
            key = f"day{day_index}"
            itinerary[key] = cls._as_list(parsed.get(key, []))
        return itinerary

    @classmethod
    def parse_budget(cls, text: str, budget: int) -> Dict[str, int]:
        parsed = cls.parse_json(text)
        allocations = {
            "stay": int(parsed.get("stay", 0) or 0),
            "food": int(parsed.get("food", 0) or 0),
            "transport": int(parsed.get("transport", 0) or 0),
            "activities": int(parsed.get("activities", 0) or 0),
        }
        total = sum(allocations.values())
        if total > budget and total > 0:
            ratio = budget / total
            allocations = {key: int(value * ratio) for key, value in allocations.items()}
        return allocations

    @classmethod
    def parse_food(cls, text: str) -> Dict[str, List[str]]:
        parsed = cls.parse_json(text)
        return {
            "must_try": cls._as_list(parsed.get("must_try", [])),
            "recommended_restaurants": cls._as_list(parsed.get("recommended_restaurants", [])),
        }

    @classmethod
    def parse_packing(cls, text: str) -> Dict[str, List[str]]:
        parsed = cls.parse_json(text)
        return {
            "essentials": cls._as_list(parsed.get("essentials", [])),
            "travel_items": cls._as_list(parsed.get("travel_items", [])),
        }

    @classmethod
    def parse_safety(cls, text: str) -> Dict[str, List[str]]:
        parsed = cls.parse_json(text)
        return {
            "tips": cls._as_list(parsed.get("tips", [])),
            "warnings": cls._as_list(parsed.get("warnings", [])),
        }
