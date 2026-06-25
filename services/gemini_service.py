from __future__ import annotations

import json
import os
import re
from typing import Dict, List

from dotenv import load_dotenv

try:
    import google.generativeai as genai
except Exception:  # pragma: no cover - optional dependency fallback
    genai = None


class GeminiService:
    def __init__(self, model_name: str = "gemini-2.5-flash") -> None:
        load_dotenv()
        self.api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.model_name = model_name
        self.client_ready = False

        if self.api_key and genai is not None:
            genai.configure(api_key=self.api_key)
            self.client_ready = True

    def generate(self, prompt: str) -> str:
        if self.client_ready:
            try:
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(prompt)
                text = getattr(response, "text", None)
                if text:
                    return text
                raise RuntimeError("Gemini returned an empty response.")
            except Exception as exc:
                raise RuntimeError(f"Gemini generation failed: {exc}") from exc

        return self._fallback_generate(prompt)

    def _fallback_generate(self, prompt: str) -> str:
        prompt_lower = prompt.lower()
        if "stay" in prompt_lower and "activities" in prompt_lower:
            return self._fallback_budget(prompt)
        if "day1" in prompt_lower and "itinerary" in prompt_lower:
            return self._fallback_itinerary(prompt)
        if "must_try" in prompt_lower or "food" in prompt_lower and "restaurants" in prompt_lower:
            return self._fallback_food(prompt)
        if "packing" in prompt_lower and "essentials" in prompt_lower:
            return self._fallback_packing(prompt)
        if "safety" in prompt_lower and "warnings" in prompt_lower:
            return self._fallback_safety(prompt)
        return json.dumps({"message": "Gemini is unavailable and no fallback was matched."})

    def _extract_value(self, prompt: str, label: str, default: str = "") -> str:
        match = re.search(rf"{label}:\s*(.*)", prompt, re.IGNORECASE)
        if match:
            return match.group(1).strip()
        return default

    def _extract_interests(self, prompt: str) -> List[str]:
        interests = []
        capture = False
        for line in prompt.splitlines():
            stripped = line.strip()
            if stripped.lower() == "- interests:" or stripped.lower() == "interests:":
                capture = True
                continue
            if capture:
                if stripped.startswith("-"):
                    item = stripped.lstrip("- ").strip()
                    if item and item.lower() != "none provided":
                        interests.append(item)
                elif stripped:
                    break
        return interests

    def _fallback_itinerary(self, prompt: str) -> str:
        destination = self._extract_value(prompt, "Destination", "the destination")
        days_text = self._extract_value(prompt, "Days", "3")
        try:
            days = max(1, int(re.findall(r"\d+", days_text)[0]))
        except Exception:
            days = 3
        interests = self._extract_interests(prompt)
        base_interest = interests[0] if interests else "local highlights"

        itinerary: Dict[str, List[str]] = {}
        for day in range(1, days + 1):
            itinerary[f"day{day}"] = [
                f"Start the day with a relaxed breakfast in {destination}",
                f"Explore {destination} and focus on {base_interest}",
                f"End with dinner featuring local specialties",
            ]
        return json.dumps(itinerary, ensure_ascii=False)

    def _fallback_budget(self, prompt: str) -> str:
        budget_text = self._extract_value(prompt, "Budget", "10000")
        try:
            budget = max(1, int(re.findall(r"\d+", budget_text.replace(",", ""))[0]))
        except Exception:
            budget = 10000
        allocations = {
            "stay": int(budget * 0.4),
            "food": int(budget * 0.25),
            "transport": int(budget * 0.15),
            "activities": budget - int(budget * 0.4) - int(budget * 0.25) - int(budget * 0.15),
        }
        return json.dumps(allocations, ensure_ascii=False)

    def _fallback_food(self, prompt: str) -> str:
        destination = self._extract_value(prompt, "Destination", "the destination")
        payload = {
            "must_try": [f"Signature local dish from {destination}", "Popular street food", "Regional dessert"],
            "recommended_restaurants": [f"Heritage restaurant in {destination}", "Well-rated local cafe", "Busy neighborhood eatery"],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _fallback_packing(self, prompt: str) -> str:
        payload = {
            "essentials": ["ID documents", "Wallet", "Chargers", "Medications"],
            "travel_items": ["Reusable water bottle", "Comfortable shoes", "Power bank", "Day backpack"],
        }
        return json.dumps(payload, ensure_ascii=False)

    def _fallback_safety(self, prompt: str) -> str:
        payload = {
            "tips": ["Keep digital copies of important documents", "Use trusted transport providers", "Stay aware of local customs"],
            "warnings": ["Avoid isolated areas late at night", "Do not leave valuables unattended"],
        }
        return json.dumps(payload, ensure_ascii=False)
