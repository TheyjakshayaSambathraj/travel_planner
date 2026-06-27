"""
hotel_estimator.py
------------------
Estimates hotel/accommodation costs based on:
  - Destination cost-of-living tier
  - Travel persona
  - Accommodation type preference
"""
from __future__ import annotations

from typing import Dict, Any, Tuple

# Destination hotel tier: avg nightly rate in INR
# Tiers: budget / mid / luxury

HOTEL_TIERS: Dict[str, Dict[str, Dict[str, int]]] = {
    # (domestic India)
    "domestic": {
        "budget": {"min": 500, "avg": 1200, "max": 2500},
        "mid": {"min": 2000, "avg": 4000, "max": 8000},
        "luxury": {"min": 7000, "avg": 15000, "max": 40000},
    },
    # Short-haul (SE Asia, Maldives, Sri Lanka, Nepal, Dubai)
    "short_haul": {
        "budget": {"min": 1000, "avg": 2500, "max": 5000},
        "mid": {"min": 4000, "avg": 8000, "max": 18000},
        "luxury": {"min": 15000, "avg": 35000, "max": 100000},
    },
    # Medium-haul (Japan, Turkey, Greece)
    "medium_haul": {
        "budget": {"min": 2000, "avg": 5000, "max": 9000},
        "mid": {"min": 7000, "avg": 14000, "max": 28000},
        "luxury": {"min": 25000, "avg": 55000, "max": 150000},
    },
    # Long-haul (Europe, UK, Australia)
    "long_haul": {
        "budget": {"min": 3500, "avg": 7000, "max": 13000},
        "mid": {"min": 10000, "avg": 20000, "max": 40000},
        "luxury": {"min": 35000, "avg": 80000, "max": 250000},
    },
    # Ultra long-haul (USA, Canada)
    "ultra_long_haul": {
        "budget": {"min": 5000, "avg": 10000, "max": 18000},
        "mid": {"min": 15000, "avg": 28000, "max": 55000},
        "luxury": {"min": 45000, "avg": 100000, "max": 350000},
    },
}

# Persona → hotel tier mapping
PERSONA_TIER: Dict[str, str] = {
    "Backpacker": "budget",
    "Photographer": "budget",
    "Food Explorer": "mid",
    "Digital Nomad": "budget",
    "Family Traveler": "mid",
    "Luxury Escapist": "luxury",
    "Nightlife Explorer": "mid",
}

# Accommodation type → tier override
ACCOMMODATION_TIER: Dict[str, str] = {
    "Any": "",             # use persona default
    "Hostel": "budget",
    "Budget Hotel": "budget",
    "Boutique Hotel": "mid",
    "Resort": "luxury",
    "Homestay": "budget",
}

# Confidence label based on tier match
CONFIDENCE_LABELS = {
    "high": "High (based on destination tier + persona)",
    "medium": "Medium (estimated from regional averages)",
    "low": "Low (limited data for this destination)",
}


def estimate_hotel_cost(
    destination: str,
    days: int,
    persona: str = "Backpacker",
    accommodation_type: str = "Any",
    flight_tier: str = "medium_haul",
) -> Dict[str, Any]:
    """
    Estimate hotel nightly rate and total accommodation cost in INR.

    Returns:
        dict with avg_nightly_inr, total_inr, tier_label, confidence, nights, note
    """
    # Determine hotel tier
    acc_tier = ACCOMMODATION_TIER.get(accommodation_type, "")
    persona_tier = PERSONA_TIER.get(persona, "mid")
    hotel_tier = acc_tier if acc_tier else persona_tier

    # Get rates
    tier_rates = HOTEL_TIERS.get(flight_tier, HOTEL_TIERS["medium_haul"])
    rates = tier_rates.get(hotel_tier, tier_rates["mid"])

    avg_nightly = rates["avg"]
    min_nightly = rates["min"]
    max_nightly = rates["max"]
    total = avg_nightly * days

    # Confidence
    if flight_tier in HOTEL_TIERS and hotel_tier in HOTEL_TIERS[flight_tier]:
        confidence = "high"
    elif flight_tier in HOTEL_TIERS:
        confidence = "medium"
    else:
        confidence = "low"

    # Human-readable tier label
    tier_label_map = {
        "budget": "Budget / Hostel",
        "mid": "Mid-range / Boutique",
        "luxury": "Luxury / Resort",
    }

    return {
        "avg_nightly_inr": avg_nightly,
        "min_nightly_inr": min_nightly,
        "max_nightly_inr": max_nightly,
        "total_inr": total,
        "nights": days,
        "hotel_tier": hotel_tier,
        "tier_label": tier_label_map.get(hotel_tier, "Mid-range"),
        "confidence": confidence,
        "confidence_label": CONFIDENCE_LABELS[confidence],
        "note": f"Estimated for {days} nights at {destination} ({tier_label_map.get(hotel_tier, 'mid-range')} level)",
    }
