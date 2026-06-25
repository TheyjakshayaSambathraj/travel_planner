from __future__ import annotations

from typing import Iterable, List

from models.travel_request import TravelRequest


class ValidationError(ValueError):
    pass


def sanitize_interests(selected_interests: Iterable[str], custom_interests: str) -> List[str]:
    interests: List[str] = []

    for item in selected_interests or []:
        cleaned = item.strip()
        if cleaned and cleaned not in interests:
            interests.append(cleaned)

    if custom_interests:
        for item in custom_interests.split(","):
            cleaned = item.strip()
            if cleaned and cleaned not in interests:
                interests.append(cleaned)

    return interests


def build_travel_request(
    destination: str,
    days: int,
    budget: int,
    travel_style: str,
    interests: List[str],
) -> TravelRequest:
    if not destination or not destination.strip():
        raise ValidationError("Destination cannot be empty.")
    if days < 1:
        raise ValidationError("Number of days must be at least 1.")
    if budget < 1:
        raise ValidationError("Budget must be a positive value.")
    if not travel_style or not travel_style.strip():
        raise ValidationError("Travel style is required.")

    return TravelRequest(
        destination=destination.strip(),
        days=days,
        budget=budget,
        travel_style=travel_style.strip(),
        interests=interests,
    )
