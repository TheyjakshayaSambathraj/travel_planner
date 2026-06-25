from __future__ import annotations

import json
from typing import Dict, Iterable, List

from models.agent_outputs import ItineraryDay
from models.feasibility import FeasibilityOutput
from models.trip_intelligence import AIInsights, AnalyticsSummary, TripIntelligence
from models.travel_request import TravelRequest


class PromptService:
    @staticmethod
    def _format_interests(interests: List[str]) -> str:
        if not interests:
            return "- None provided"
        return "\n".join(f"- {interest}" for interest in interests)

    @staticmethod
    def _format_context_lines(lines: Iterable[str]) -> str:
        return "\n".join(f"- {line}" for line in lines)

    @staticmethod
    def _build_prompt(role: str, task: str, constraints: Iterable[str], output_format: Dict, example: Dict) -> str:
        return f"""You are {role}.
Task: {task}
Constraints:
{PromptService._format_context_lines(constraints)}
Desired Output Format:
{json.dumps(output_format, indent=2, ensure_ascii=False)}
Example:
{json.dumps(example, indent=2, ensure_ascii=False)}"""

    @staticmethod
    def _base_constraints(request: TravelRequest) -> List[str]:
        return [
            f"Destination: {request.destination}",
            f"Days: {request.days}",
            f"Budget: {request.budget}",
            f"Persona: {request.persona}",
            "Interests:",
            PromptService._format_interests(request.interests),
            "Return JSON only.",
            "Do not include markdown or commentary.",
        ]

    @classmethod
    def build_feasibility_prompt(cls, request: TravelRequest) -> str:
        return cls._build_prompt(
            role="a travel feasibility analyst",
            task="Evaluate whether the requested trip is realistic and provide confidence and corrections.",
            constraints=[
                *cls._base_constraints(request),
                "Detect unrealistic budgets, overambitious durations, and mismatched travel personas.",
                "Return JSON only.",
            ],
            output_format={
                "feasible": True,
                "confidence_score": 92,
                "issues": ["..."],
                "recommendations": ["..."],
                "budget_risk": "low",
                "travel_complexity": "medium",
            },
            example={
                "feasible": False,
                "confidence_score": 89,
                "issues": ["Luxury expectations conflict with a low budget"],
                "recommendations": ["Increase budget or switch to a budget-friendly persona"],
                "budget_risk": "high",
                "travel_complexity": "medium",
            },
        )

    @classmethod
    def build_research_prompt(cls, destination: str) -> str:
        return cls._build_prompt(
            role="an expert destination research analyst",
            task="Research the destination and provide concise travel intelligence.",
            constraints=[
                f"Destination: {destination}",
                "Focus on travel-relevant context, attractions, transit, and timing.",
                "Return JSON only.",
            ],
            output_format={
                "destination_overview": "...",
                "best_time_to_visit": "...",
                "popular_areas": ["..."],
                "local_transport": ["..."],
                "key_highlights": ["..."],
            },
            example={
                "destination_overview": "Coastal city with beaches, nightlife, and heritage quarters.",
                "best_time_to_visit": "November to February for cooler weather and outdoor activities.",
                "popular_areas": ["North Goa", "Fontainhas", "Panaji"],
                "local_transport": ["Prepaid taxis", "Scooters", "Local buses"],
                "key_highlights": ["Beaches", "Old Portuguese architecture", "Local seafood"],
            },
        )

    @classmethod
    def build_itinerary_prompt(cls, request: TravelRequest, research: Dict) -> str:
        return cls._build_prompt(
            role="an expert itinerary planner",
            task="Generate a balanced day-wise itinerary using destination research.",
            constraints=[
                *cls._base_constraints(request),
                f"Destination research: {research}",
                "Avoid duplicate locations and balance morning, afternoon, and evening activities.",
                "Tailor activities to the chosen persona.",
            ],
            output_format={
                "days": [
                    {
                        "day": 1,
                        "morning": [{"activity": "...", "location": "..."}],
                        "afternoon": [{"activity": "...", "location": "..."}],
                        "evening": [{"activity": "...", "location": "..."}],
                    }
                ]
            },
            example={
                "days": [
                    {
                        "day": 1,
                        "morning": [{"activity": "Sunrise walk and breakfast", "location": "Miramar Beach"}],
                        "afternoon": [{"activity": "Explore heritage lanes", "location": "Fontainhas"}],
                        "evening": [{"activity": "Dinner by the waterfront", "location": "Panaji promenade"}],
                    },
                    {
                        "day": 2,
                        "morning": [{"activity": "Market stroll", "location": "local bazaar"}],
                        "afternoon": [{"activity": "Museum visit", "location": "city museum"}],
                        "evening": [{"activity": "Sunset viewpoint", "location": "hilltop lookout"}],
                    },
                ]
            },
        )

    @classmethod
    def build_budget_prompt(cls, request: TravelRequest, research: Dict, itinerary: Dict) -> str:
        return cls._build_prompt(
            role="an expert travel budget planner",
            task="Allocate the trip budget with a reserve and provide reasoning.",
            constraints=[
                *cls._base_constraints(request),
                f"Destination research: {research}",
                f"Itinerary: {itinerary}",
                "Do not exceed the total budget.",
                "Include an emergency_buffer reserve.",
                "Explain allocation_reasoning in one concise sentence.",
                "Make the allocation reflect the chosen persona and itinerary intensity.",
            ],
            output_format={
                "accommodation": 0,
                "food": 0,
                "transport": 0,
                "activities": 0,
                "emergency_buffer": 0,
                "allocation_reasoning": "...",
            },
            example={
                "accommodation": 6000,
                "food": 3000,
                "transport": 2000,
                "activities": 2500,
                "emergency_buffer": 1500,
                "allocation_reasoning": "Accommodation gets the largest share because the user requested a comfortable pace and the destination is moderately priced.",
            },
        )

    @classmethod
    def build_food_prompt(cls, request: TravelRequest, research: Dict) -> str:
        return cls._build_prompt(
            role="a local cuisine and restaurant expert",
            task="Recommend authentic local foods and practical dining ideas.",
            constraints=[
                *cls._base_constraints(request),
                f"Destination research: {research}",
                "Focus on authentic local cuisine and avoid generic tourist-only recommendations.",
                "Make suggestions appropriate for the chosen persona.",
            ],
            output_format={
                "must_try_foods": ["..."],
                "street_foods": ["..."],
                "recommended_restaurants": ["..."],
                "food_tips": ["..."],
            },
            example={
                "must_try_foods": ["Regional seafood curry", "Rice cake breakfast"],
                "street_foods": ["Spiced fritters", "Local chaat"],
                "recommended_restaurants": ["Family-run coastal restaurant", "Heritage cafe"],
                "food_tips": ["Book dinner early on weekends", "Try local breakfast spots before 10 AM"],
            },
        )

    @classmethod
    def build_packing_prompt(cls, request: TravelRequest, research: Dict) -> str:
        return cls._build_prompt(
            role="a practical travel packing specialist",
            task="Generate a destination-aware packing checklist.",
            constraints=[
                *cls._base_constraints(request),
                f"Destination research: {research}",
                "Use destination climate context and the chosen persona.",
            ],
            output_format={
                "essentials": ["..."],
                "weather_items": ["..."],
                "electronics": ["..."],
                "documents": ["..."],
            },
            example={
                "essentials": ["ID proof", "Wallet"],
                "weather_items": ["Light jacket", "Umbrella"],
                "electronics": ["Phone charger", "Power bank"],
                "documents": ["Tickets", "Hotel confirmation"],
            },
        )

    @classmethod
    def build_safety_prompt(cls, request: TravelRequest, research: Dict) -> str:
        return cls._build_prompt(
            role="a travel safety advisor",
            task="Provide practical safety guidance and local etiquette.",
            constraints=[
                *cls._base_constraints(request),
                f"Destination research: {research}",
                "Avoid generic advice and focus on practical, destination-specific guidance.",
            ],
            output_format={
                "travel_tips": ["..."],
                "warnings": ["..."],
                "local_etiquette": ["..."],
                "emergency_contacts": ["..."],
            },
            example={
                "travel_tips": ["Carry a local SIM or roaming plan", "Save hotel location offline"],
                "warnings": ["Watch for pickpockets in crowded areas"],
                "local_etiquette": ["Dress modestly at temples"],
                "emergency_contacts": ["Local police: 100", "Ambulance: 108"],
            },
        )

    @classmethod
    def build_summary_prompt(
        cls,
        request: TravelRequest,
        feasibility: Dict,
        research: Dict,
        itinerary: Dict,
        budget: Dict,
        food: Dict,
        packing: Dict,
        safety: Dict,
    ) -> str:
        return cls._build_prompt(
            role="an executive travel planner",
            task="Create a professional trip summary from all planning outputs.",
            constraints=[
                *cls._base_constraints(request),
                f"Feasibility: {feasibility}",
                f"Destination research: {research}",
                f"Itinerary: {itinerary}",
                f"Budget: {budget}",
                f"Food: {food}",
                f"Packing: {packing}",
                f"Safety: {safety}",
                "Trip score must be a float from 0 to 10.",
                "Estimated total cost must be an integer.",
                "Include trip intelligence, AI insights, and analytics summary sections.",
            ],
            output_format={
                "trip_score": 8.7,
                "trip_type": "...",
                "estimated_total_cost": 0,
                "highlights": ["..."],
                "best_experiences": ["..."],
                "overall_summary": "...",
                "trip_intelligence": {
                    "trip_score": 91,
                    "budget_fit": 95,
                    "experience_score": 90,
                    "comfort_score": 88,
                    "food_score": 92,
                    "overall_rating": "Excellent",
                },
                "ai_insights": {
                    "money_saving_tips": ["..."],
                    "hidden_gems": ["..."],
                    "avoid": ["..."],
                    "best_experiences": ["..."],
                    "local_secrets": ["..."],
                },
                "analytics_summary": {
                    "estimated_total_cost": 0,
                    "trip_category": "...",
                    "difficulty_score": 50,
                    "travel_efficiency": 80,
                    "recommended_for": "...",
                },
            },
            example={
                "trip_score": 8.8,
                "trip_type": "Balanced cultural getaway",
                "estimated_total_cost": 12400,
                "highlights": ["Local food crawl", "Scenic sunset plan"],
                "best_experiences": ["Heritage walking tour", "Night market visit"],
                "overall_summary": "A well-balanced trip with strong local culture, manageable costs, and practical planning details.",
                "trip_intelligence": {
                    "trip_score": 91,
                    "budget_fit": 95,
                    "experience_score": 90,
                    "comfort_score": 88,
                    "food_score": 92,
                    "overall_rating": "Excellent",
                },
                "ai_insights": {
                    "money_saving_tips": ["Stay near a transit hub", "Choose lunch specials"],
                    "hidden_gems": ["Quiet sunrise point", "Neighborhood cafe"],
                    "avoid": ["Peak-hour beach traffic"],
                    "best_experiences": ["Heritage walking tour", "Night market visit"],
                    "local_secrets": ["Book sunset tables early"],
                },
                "analytics_summary": {
                    "estimated_total_cost": 12400,
                    "trip_category": "Balanced cultural getaway",
                    "difficulty_score": 35,
                    "travel_efficiency": 82,
                    "recommended_for": "Travelers seeking a balanced mix of culture and food",
                },
            },
        )
