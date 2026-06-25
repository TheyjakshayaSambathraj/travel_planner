from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, validator


class TripIntelligence(BaseModel):
    trip_score: int = Field(..., ge=0, le=100)
    budget_fit: int = Field(..., ge=0, le=100)
    experience_score: int = Field(..., ge=0, le=100)
    comfort_score: int = Field(..., ge=0, le=100)
    food_score: int = Field(..., ge=0, le=100)
    overall_rating: str = Field(..., min_length=1)


class AIInsights(BaseModel):
    money_saving_tips: List[str] = Field(default_factory=list)
    hidden_gems: List[str] = Field(default_factory=list)
    avoid: List[str] = Field(default_factory=list)
    best_experiences: List[str] = Field(default_factory=list)
    local_secrets: List[str] = Field(default_factory=list)

    @validator("money_saving_tips", "hidden_gems", "avoid", "best_experiences", "local_secrets", pre=True)
    def normalize_lists(cls, value):
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


class AnalyticsSummary(BaseModel):
    estimated_total_cost: int = Field(..., ge=0)
    trip_category: str = Field(..., min_length=1)
    difficulty_score: int = Field(..., ge=0, le=100)
    travel_efficiency: int = Field(..., ge=0, le=100)
    recommended_for: str = Field(..., min_length=1)
