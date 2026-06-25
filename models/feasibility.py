from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, validator


class FeasibilityOutput(BaseModel):
    feasible: bool
    confidence_score: int = Field(..., ge=0, le=100)
    issues: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)
    budget_risk: str = Field(..., min_length=1)
    travel_complexity: str = Field(..., min_length=1)

    @validator("issues", "recommendations", pre=True)
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
