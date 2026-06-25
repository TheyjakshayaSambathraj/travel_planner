from __future__ import annotations

from typing import Dict, List

from models.travel_request import TravelRequest


class PromptService:
    @staticmethod
    def _format_interests(interests: List[str]) -> str:
        if not interests:
            return "- None provided"
        return "\n".join(f"- {interest}" for interest in interests)

    @classmethod
    def build_itinerary_prompt(cls, request: TravelRequest) -> str:
        return f"""You are an expert travel planner.
Role: Itinerary specialist.
Task: Generate a realistic day-wise travel itinerary.
Constraints:
- Destination: {request.destination}
- Days: {request.days}
- Budget: {request.budget}
- Travel Style: {request.travel_style}
- Interests:
{cls._format_interests(request.interests)}
Desired Output Format:
- Return valid JSON only.
- Use keys day1, day2, ... with each value being a list of activity strings.
- Keep activities realistic and concise.
Example:
{{
  "day1": ["Arrive and check in", "Explore the old town"],
  "day2": ["Visit a museum", "Try local street food"]
}}"""

    @classmethod
    def build_budget_prompt(cls, request: TravelRequest, itinerary: Dict[str, List[str]]) -> str:
        return f"""You are an expert travel budget planner.
Role: Budget specialist.
Task: Allocate the total budget across stay, food, transport, and activities.
Constraints:
- Destination: {request.destination}
- Days: {request.days}
- Budget: {request.budget}
- Travel Style: {request.travel_style}
- Interests:
{cls._format_interests(request.interests)}
- Itinerary context: {itinerary}
- The total allocation must not exceed the budget.
Desired Output Format:
- Return valid JSON only.
- Use integer values.
- Keys must be stay, food, transport, activities.
Example:
{{
  "stay": 6000,
  "food": 3000,
  "transport": 2500,
  "activities": 3500
}}"""

    @classmethod
    def build_food_prompt(cls, request: TravelRequest) -> str:
        return f"""You are a local food travel expert.
Role: Food specialist.
Task: Recommend must-try local dishes and restaurant ideas.
Constraints:
- Destination: {request.destination}
- Travel Style: {request.travel_style}
- Interests:
{cls._format_interests(request.interests)}
Desired Output Format:
- Return valid JSON only.
- Use keys must_try and recommended_restaurants.
- Each value must be a list of strings.
Example:
{{
  "must_try": ["Dish 1", "Dish 2"],
  "recommended_restaurants": ["Restaurant 1", "Restaurant 2"]
}}"""

    @classmethod
    def build_packing_prompt(cls, request: TravelRequest) -> str:
        return f"""You are a practical packing assistant.
Role: Packing specialist.
Task: Generate a packing checklist.
Constraints:
- Destination: {request.destination}
- Days: {request.days}
- Travel Style: {request.travel_style}
- Interests:
{cls._format_interests(request.interests)}
Desired Output Format:
- Return valid JSON only.
- Use keys essentials and travel_items.
- Each value must be a list of strings.
Example:
{{
  "essentials": ["ID proof", "Chargers"],
  "travel_items": ["Reusable bottle", "Day bag"]
}}"""

    @classmethod
    def build_safety_prompt(cls, request: TravelRequest) -> str:
        return f"""You are a travel safety advisor.
Role: Safety specialist.
Task: Provide useful safety tips and warnings for the trip.
Constraints:
- Destination: {request.destination}
- Days: {request.days}
- Travel Style: {request.travel_style}
- Interests:
{cls._format_interests(request.interests)}
Desired Output Format:
- Return valid JSON only.
- Use keys tips and warnings.
- Each value must be a list of strings.
Example:
{{
  "tips": ["Keep copies of documents", "Use trusted transport"],
  "warnings": ["Avoid isolated areas at night"]
}}"""
