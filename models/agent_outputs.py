from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, Field, validator

from models.feasibility import FeasibilityOutput
from models.trip_intelligence import AIInsights, AnalyticsSummary, TripIntelligence


class TimelineItem(BaseModel):
    activity: str = Field(..., min_length=1)
    location: str = Field(default="")

    @validator("activity", "location", pre=True)
    def strip_text(cls, value):
        if isinstance(value, str):
            return value.strip()
        return value


class ResearchOutput(BaseModel):
    destination_overview: str = Field(..., min_length=1)
    best_time_to_visit: str = Field(..., min_length=1)
    popular_areas: List[str] = Field(default_factory=list)
    local_transport: List[str] = Field(default_factory=list)
    key_highlights: List[str] = Field(default_factory=list)

    @validator("popular_areas", "local_transport", "key_highlights", pre=True)
    def normalize_list_fields(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


class ItineraryDay(BaseModel):
    day: int = Field(..., ge=1)
    morning: List[TimelineItem] = Field(default_factory=list)
    afternoon: List[TimelineItem] = Field(default_factory=list)
    evening: List[TimelineItem] = Field(default_factory=list)

    @validator("morning", "afternoon", "evening", pre=True)
    def normalize_activities(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [{"activity": item, "location": ""} for item in items if item]
        cleaned = []
        for item in value:
            if isinstance(item, dict):
                activity = str(item.get("activity", "")).strip()
                location = str(item.get("location", "")).strip()
                if activity:
                    cleaned.append({"activity": activity, "location": location})
            else:
                text = str(item).strip()
                if text:
                    cleaned.append({"activity": text, "location": ""})
        return cleaned


class ItineraryOutput(BaseModel):
    days: List[ItineraryDay] = Field(default_factory=list)


class BudgetOutput(BaseModel):
    accommodation: int = Field(..., ge=0)
    food: int = Field(..., ge=0)
    transport: int = Field(..., ge=0)
    activities: int = Field(..., ge=0)
    emergency_buffer: int = Field(..., ge=0)
    allocation_reasoning: str = Field(..., min_length=1)


class FoodOutput(BaseModel):
    must_try_foods: List[str] = Field(default_factory=list)
    street_foods: List[str] = Field(default_factory=list)
    recommended_restaurants: List[str] = Field(default_factory=list)
    food_tips: List[str] = Field(default_factory=list)

    @validator("must_try_foods", "street_foods", "recommended_restaurants", "food_tips", pre=True)
    def normalize_food_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


class PackingOutput(BaseModel):
    essentials: List[str] = Field(default_factory=list)
    weather_items: List[str] = Field(default_factory=list)
    electronics: List[str] = Field(default_factory=list)
    documents: List[str] = Field(default_factory=list)

    @validator("essentials", "weather_items", "electronics", "documents", pre=True)
    def normalize_packing_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


class SafetyOutput(BaseModel):
    travel_tips: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    local_etiquette: List[str] = Field(default_factory=list)
    emergency_contacts: List[str] = Field(default_factory=list)

    @validator("travel_tips", "warnings", "local_etiquette", "emergency_contacts", pre=True)
    def normalize_safety_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


class TripSummaryOutput(BaseModel):
    trip_score: float = Field(..., ge=0, le=10)
    trip_type: str = Field(..., min_length=1)
    estimated_total_cost: int = Field(..., ge=0)
    highlights: List[str] = Field(default_factory=list)
    best_experiences: List[str] = Field(default_factory=list)
    overall_summary: str = Field(..., min_length=1)
    trip_intelligence: TripIntelligence
    ai_insights: AIInsights
    analytics_summary: AnalyticsSummary

    @validator("highlights", "best_experiences", pre=True)
    def normalize_summary_lists(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split("\n")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            text = str(item).strip()
            if text:
                cleaned.append(text)
        return cleaned


class TravelPackage(BaseModel):
    feasibility: FeasibilityOutput
    research: ResearchOutput
    itinerary: ItineraryOutput
    budget: BudgetOutput
    food: FoodOutput
    packing: PackingOutput
    safety: SafetyOutput
    summary: TripSummaryOutput
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def as_dict(self):
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()
