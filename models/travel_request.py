from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, validator


class TravelRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    days: int = Field(..., ge=1)
    budget: int = Field(..., ge=1)
    travel_style: str = Field(..., min_length=1)
    interests: List[str] = Field(default_factory=list)

    @validator("destination", "travel_style", pre=True)
    def strip_text(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @validator("interests", pre=True)
    def normalize_interests(cls, value):
        if value is None:
            return []
        if isinstance(value, str):
            items = [item.strip() for item in value.split(",")]
            return [item for item in items if item]
        cleaned = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    cleaned.append(stripped)
        return cleaned
