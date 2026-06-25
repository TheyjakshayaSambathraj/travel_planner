from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel, Field


class TravelPackage(BaseModel):
    itinerary: Dict[str, List[str]] = Field(default_factory=dict)
    budget: Dict[str, int] = Field(default_factory=dict)
    food: Dict[str, List[str]] = Field(default_factory=dict)
    packing: Dict[str, List[str]] = Field(default_factory=dict)
    safety: Dict[str, List[str]] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    def as_dict(self) -> Dict[str, Any]:
        if hasattr(self, "model_dump"):
            return self.model_dump()
        return self.dict()
