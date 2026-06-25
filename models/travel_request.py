from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field, root_validator, validator


class TravelRequest(BaseModel):
    destination: str = Field(..., min_length=1)
    days: int = Field(..., ge=1)
    budget: int = Field(..., ge=1)
    persona: str = Field(..., min_length=1)
    interests: List[str] = Field(default_factory=list)

    @validator("destination", "persona", pre=True)
    def strip_text(cls, value: str) -> str:
        if isinstance(value, str):
            return value.strip()
        return value

    @root_validator(pre=True)
    def map_legacy_travel_style(cls, values):
        if not values.get("persona") and values.get("travel_style"):
            values["persona"] = values["travel_style"]
        return values

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

    @property
    def travel_style(self) -> str:
        return self.persona
