"""
destination_intel.py
--------------------
Provides destination intelligence:
  - Wikipedia REST API for destination images and facts
  - ExchangeRate-API (free, no key) for live currency conversion
  - Amadeus Flight API for real flight prices (optional, falls back to heuristics)
  - Budget feasibility analysis
"""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, Optional, Tuple

import certifi
import requests
import urllib3

# Suppress SSL warnings from verify=False (Windows cert store is incomplete)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

from dotenv import load_dotenv

load_dotenv()

_log = logging.getLogger("tripmind.intel")
if not _log.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[TripMind] %(message)s"))
    _log.addHandler(_h)
_log.setLevel(logging.INFO)

# Shared requests session with SSL bypass (Windows cert store missing root CAs)
_session = requests.Session()
_session.verify = False


# ---------------------------------------------------------------------------
# Country → currency / language / timezone lookup (offline fallback)
# ---------------------------------------------------------------------------

COUNTRY_DATA: Dict[str, Dict[str, str]] = {
    "France": {"currency": "EUR", "symbol": "€", "language": "French", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required for non-EU"},
    "Paris": {"currency": "EUR", "symbol": "€", "language": "French", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required for non-EU", "country": "France"},
    "Italy": {"currency": "EUR", "symbol": "€", "language": "Italian", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required"},
    "Rome": {"currency": "EUR", "symbol": "€", "language": "Italian", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Italy"},
    "Venice": {"currency": "EUR", "symbol": "€", "language": "Italian", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Italy"},
    "Milan": {"currency": "EUR", "symbol": "€", "language": "Italian", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Italy"},
    "Spain": {"currency": "EUR", "symbol": "€", "language": "Spanish", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required"},
    "Barcelona": {"currency": "EUR", "symbol": "€", "language": "Spanish/Catalan", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Spain"},
    "Madrid": {"currency": "EUR", "symbol": "€", "language": "Spanish", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Spain"},
    "Germany": {"currency": "EUR", "symbol": "€", "language": "German", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required"},
    "Berlin": {"currency": "EUR", "symbol": "€", "language": "German", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Germany"},
    "United Kingdom": {"currency": "GBP", "symbol": "£", "language": "English", "timezone": "GMT (UTC+0)", "visa_hint": "UK visa required (not Schengen)"},
    "London": {"currency": "GBP", "symbol": "£", "language": "English", "timezone": "GMT (UTC+0)", "visa_hint": "UK visa required", "country": "United Kingdom"},
    "Japan": {"currency": "JPY", "symbol": "¥", "language": "Japanese", "timezone": "JST (UTC+9)", "visa_hint": "Visa-on-arrival for many nationalities"},
    "Tokyo": {"currency": "JPY", "symbol": "¥", "language": "Japanese", "timezone": "JST (UTC+9)", "visa_hint": "Visa-on-arrival for Indians", "country": "Japan"},
    "Kyoto": {"currency": "JPY", "symbol": "¥", "language": "Japanese", "timezone": "JST (UTC+9)", "visa_hint": "Visa-on-arrival for Indians", "country": "Japan"},
    "Osaka": {"currency": "JPY", "symbol": "¥", "language": "Japanese", "timezone": "JST (UTC+9)", "visa_hint": "Visa-on-arrival for Indians", "country": "Japan"},
    "Thailand": {"currency": "THB", "symbol": "฿", "language": "Thai", "timezone": "ICT (UTC+7)", "visa_hint": "Visa-on-arrival for Indians (30 days)"},
    "Bangkok": {"currency": "THB", "symbol": "฿", "language": "Thai", "timezone": "ICT (UTC+7)", "visa_hint": "Visa-on-arrival for Indians", "country": "Thailand"},
    "Phuket": {"currency": "THB", "symbol": "฿", "language": "Thai", "timezone": "ICT (UTC+7)", "visa_hint": "Visa-on-arrival for Indians", "country": "Thailand"},
    "Chiang Mai": {"currency": "THB", "symbol": "฿", "language": "Thai", "timezone": "ICT (UTC+7)", "visa_hint": "Visa-on-arrival for Indians", "country": "Thailand"},
    "Singapore": {"currency": "SGD", "symbol": "S$", "language": "English/Malay/Tamil", "timezone": "SGT (UTC+8)", "visa_hint": "Visa-free for Indians (30 days)"},
    "Malaysia": {"currency": "MYR", "symbol": "RM", "language": "Malay", "timezone": "MYT (UTC+8)", "visa_hint": "Visa-free for Indians (30 days)"},
    "Kuala Lumpur": {"currency": "MYR", "symbol": "RM", "language": "Malay", "timezone": "MYT (UTC+8)", "visa_hint": "Visa-free for Indians", "country": "Malaysia"},
    "Bali": {"currency": "IDR", "symbol": "Rp", "language": "Bahasa Indonesia", "timezone": "WITA (UTC+8)", "visa_hint": "Visa-on-arrival for Indians (30 days)", "country": "Indonesia"},
    "Indonesia": {"currency": "IDR", "symbol": "Rp", "language": "Bahasa Indonesia", "timezone": "WIB (UTC+7)", "visa_hint": "Visa-on-arrival for Indians"},
    "Dubai": {"currency": "AED", "symbol": "د.إ", "language": "Arabic", "timezone": "GST (UTC+4)", "visa_hint": "Visa-on-arrival for Indians (14/30 days)", "country": "UAE"},
    "UAE": {"currency": "AED", "symbol": "د.إ", "language": "Arabic", "timezone": "GST (UTC+4)", "visa_hint": "Visa-on-arrival for Indians"},
    "Maldives": {"currency": "MVR", "symbol": "Rf", "language": "Dhivehi", "timezone": "MVT (UTC+5)", "visa_hint": "Visa-on-arrival for all nationalities (30 days)", "country": "Maldives"},
    "Sri Lanka": {"currency": "LKR", "symbol": "Rs", "language": "Sinhala/Tamil", "timezone": "IST (UTC+5:30)", "visa_hint": "ETA required (apply online)"},
    "Colombo": {"currency": "LKR", "symbol": "Rs", "language": "Sinhala", "timezone": "IST (UTC+5:30)", "visa_hint": "ETA required", "country": "Sri Lanka"},
    "Nepal": {"currency": "NPR", "symbol": "Rs", "language": "Nepali", "timezone": "NPT (UTC+5:45)", "visa_hint": "Visa-on-arrival for Indians (free)"},
    "Kathmandu": {"currency": "NPR", "symbol": "Rs", "language": "Nepali", "timezone": "NPT (UTC+5:45)", "visa_hint": "Visa-on-arrival for Indians (free)", "country": "Nepal"},
    "India": {"currency": "INR", "symbol": "₹", "language": "Hindi/English", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required for Indian citizens"},
    "Goa": {"currency": "INR", "symbol": "₹", "language": "Konkani/English", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Mumbai": {"currency": "INR", "symbol": "₹", "language": "Hindi/Marathi", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Delhi": {"currency": "INR", "symbol": "₹", "language": "Hindi", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Jaipur": {"currency": "INR", "symbol": "₹", "language": "Hindi/Rajasthani", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Varanasi": {"currency": "INR", "symbol": "₹", "language": "Hindi", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Manali": {"currency": "INR", "symbol": "₹", "language": "Hindi/Pahadi", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Leh": {"currency": "INR", "symbol": "₹", "language": "Ladakhi/Hindi", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Ooty": {"currency": "INR", "symbol": "₹", "language": "Tamil", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "Coorg": {"currency": "INR", "symbol": "₹", "language": "Kodava/Kannada", "timezone": "IST (UTC+5:30)", "visa_hint": "No visa required", "country": "India"},
    "New York": {"currency": "USD", "symbol": "$", "language": "English", "timezone": "EST (UTC-5)", "visa_hint": "US B1/B2 visa required for Indians", "country": "USA"},
    "USA": {"currency": "USD", "symbol": "$", "language": "English", "timezone": "EST/PST (UTC-5/-8)", "visa_hint": "US visa required for Indians"},
    "Los Angeles": {"currency": "USD", "symbol": "$", "language": "English", "timezone": "PST (UTC-8)", "visa_hint": "US B1/B2 visa required", "country": "USA"},
    "Australia": {"currency": "AUD", "symbol": "A$", "language": "English", "timezone": "AEST (UTC+10)", "visa_hint": "Australian ETA required"},
    "Sydney": {"currency": "AUD", "symbol": "A$", "language": "English", "timezone": "AEST (UTC+10)", "visa_hint": "Australian ETA required", "country": "Australia"},
    "Melbourne": {"currency": "AUD", "symbol": "A$", "language": "English", "timezone": "AEST (UTC+10)", "visa_hint": "Australian ETA required", "country": "Australia"},
    "Canada": {"currency": "CAD", "symbol": "CA$", "language": "English/French", "timezone": "EST (UTC-5)", "visa_hint": "Canadian visa required for Indians"},
    "Toronto": {"currency": "CAD", "symbol": "CA$", "language": "English", "timezone": "EST (UTC-5)", "visa_hint": "Canadian visa required", "country": "Canada"},
    "Vietnam": {"currency": "VND", "symbol": "₫", "language": "Vietnamese", "timezone": "ICT (UTC+7)", "visa_hint": "E-visa or visa-on-arrival for Indians"},
    "Ho Chi Minh City": {"currency": "VND", "symbol": "₫", "language": "Vietnamese", "timezone": "ICT (UTC+7)", "visa_hint": "E-visa required", "country": "Vietnam"},
    "Hanoi": {"currency": "VND", "symbol": "₫", "language": "Vietnamese", "timezone": "ICT (UTC+7)", "visa_hint": "E-visa required", "country": "Vietnam"},
    "Greece": {"currency": "EUR", "symbol": "€", "language": "Greek", "timezone": "EET (UTC+2)", "visa_hint": "Schengen visa required"},
    "Athens": {"currency": "EUR", "symbol": "€", "language": "Greek", "timezone": "EET (UTC+2)", "visa_hint": "Schengen visa required", "country": "Greece"},
    "Santorini": {"currency": "EUR", "symbol": "€", "language": "Greek", "timezone": "EET (UTC+2)", "visa_hint": "Schengen visa required", "country": "Greece"},
    "Switzerland": {"currency": "CHF", "symbol": "Fr", "language": "German/French/Italian", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required"},
    "Zurich": {"currency": "CHF", "symbol": "Fr", "language": "German", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Switzerland"},
    "Amsterdam": {"currency": "EUR", "symbol": "€", "language": "Dutch", "timezone": "CET (UTC+1)", "visa_hint": "Schengen visa required", "country": "Netherlands"},
    "Portugal": {"currency": "EUR", "symbol": "€", "language": "Portuguese", "timezone": "WET (UTC+0)", "visa_hint": "Schengen visa required"},
    "Lisbon": {"currency": "EUR", "symbol": "€", "language": "Portuguese", "timezone": "WET (UTC+0)", "visa_hint": "Schengen visa required", "country": "Portugal"},
    "Turkey": {"currency": "TRY", "symbol": "₺", "language": "Turkish", "timezone": "TRT (UTC+3)", "visa_hint": "E-visa required for Indians"},
    "Istanbul": {"currency": "TRY", "symbol": "₺", "language": "Turkish", "timezone": "TRT (UTC+3)", "visa_hint": "E-visa required", "country": "Turkey"},
    "Morocco": {"currency": "MAD", "symbol": "د.م.", "language": "Arabic/Berber", "timezone": "WET (UTC+0)", "visa_hint": "Visa required for Indians"},
    "Marrakech": {"currency": "MAD", "symbol": "د.م.", "language": "Arabic/French", "timezone": "WET (UTC+0)", "visa_hint": "Visa required for Indians", "country": "Morocco"},
    "South Africa": {"currency": "ZAR", "symbol": "R", "language": "Zulu/Afrikaans/English", "timezone": "SAST (UTC+2)", "visa_hint": "Visa required for Indians"},
    "Cape Town": {"currency": "ZAR", "symbol": "R", "language": "Afrikaans/English", "timezone": "SAST (UTC+2)", "visa_hint": "Visa required for Indians", "country": "South Africa"},
}

# ---------------------------------------------------------------------------
# Flight distance tiers: (min budget INR, max budget INR, typical airline note)
# ---------------------------------------------------------------------------

FLIGHT_TIERS: Dict[str, Dict[str, Any]] = {
    # Domestic India
    "domestic": {
        "min_inr": 2500, "max_inr": 8000,
        "note": "Low-cost carrier (IndiGo/SpiceJet)",
        "destinations": [
            "Goa", "Mumbai", "Delhi", "Jaipur", "Varanasi", "Manali", "Leh", "Ooty", "Coorg", "India",
            # South India
            "Chennai", "Bangalore", "Bengaluru", "Hyderabad", "Kochi", "Cochin", "Thiruvananthapuram",
            "Trivandrum", "Pondicherry", "Puducherry", "Mysore", "Mysuru", "Coimbatore", "Madurai",
            "Hampi", "Munnar", "Varkala", "Alleppey", "Alappuzha", "Wayanad", "Kodaikanal",
            "Thrissur", "Kozhikode", "Calicut", "Visakhapatnam", "Vizag", "Tirupati",
            # North India
            "Agra", "Udaipur", "Jodhpur", "Jaisalmer", "Amritsar", "Chandigarh", "Shimla",
            "Dharamshala", "McLeod Ganj", "Rishikesh", "Haridwar", "Dehradun", "Mussoorie",
            "Jim Corbett", "Nainital", "Lansdowne", "Almora", "Auli",
            "Lucknow", "Mathura", "Vrindavan", "Prayagraj", "Allahabad",
            # East & Northeast India
            "Kolkata", "Darjeeling", "Gangtok", "Sikkim", "Shillong", "Meghalaya",
            "Guwahati", "Kaziranga", "Tawang",
            # West India
            "Pune", "Aurangabad", "Nashik", "Lonavala", "Mahabaleshwar", "Kolhapur",
            "Ahmedabad", "Vadodara", "Surat", "Rajkot",
            # Islands
            "Andaman", "Port Blair", "Lakshadweep",
        ],
    },
    # Short-haul international (South Asia / SE Asia)
    "short_haul": {
        "min_inr": 8000, "max_inr": 25000,
        "note": "Budget international (AirAsia/IndiGo)",
        "destinations": ["Maldives", "Sri Lanka", "Colombo", "Nepal", "Kathmandu", "Bangkok", "Phuket",
                         "Chiang Mai", "Thailand", "Malaysia", "Kuala Lumpur", "Singapore", "Bali", "Indonesia",
                         "Dubai", "UAE", "Vietnam", "Ho Chi Minh City", "Hanoi"],
    },
    # Medium-haul (East Asia / Middle East)
    "medium_haul": {
        "min_inr": 25000, "max_inr": 60000,
        "note": "Full-service carrier (Air India/Emirates)",
        "destinations": ["Japan", "Tokyo", "Kyoto", "Osaka", "China", "Hong Kong", "South Korea", "Seoul",
                         "Turkey", "Istanbul", "Greece", "Athens", "Santorini"],
    },
    # Long-haul (Europe / Australia)
    "long_haul": {
        "min_inr": 55000, "max_inr": 120000,
        "note": "Full-service international (Air India/Lufthansa)",
        "destinations": ["France", "Paris", "Italy", "Rome", "Venice", "Milan", "Spain", "Barcelona", "Madrid",
                         "Germany", "Berlin", "United Kingdom", "London", "Switzerland", "Zurich", "Amsterdam",
                         "Portugal", "Lisbon", "Morocco", "Marrakech", "South Africa", "Cape Town",
                         "Netherlands"],
    },
    # Ultra long-haul (Americas / Oceania)
    "ultra_long_haul": {
        "min_inr": 80000, "max_inr": 200000,
        "note": "Long-haul international (may require layover)",
        "destinations": ["USA", "New York", "Los Angeles", "Canada", "Toronto", "Australia", "Sydney", "Melbourne"],
    },
}

# Minimum viable budget per day (INR equivalent) by destination tier
DAILY_MIN_BUDGET: Dict[str, int] = {
    "domestic": 1500,
    "short_haul": 3500,
    "medium_haul": 7000,
    "long_haul": 12000,
    "ultra_long_haul": 15000,
}

# Hardcoded exchange rates from INR (fallback when API is down)
FALLBACK_RATES: Dict[str, float] = {
    "USD": 0.012,
    "EUR": 0.011,
    "GBP": 0.0095,
    "JPY": 1.80,
    "THB": 0.41,
    "SGD": 0.016,
    "AUD": 0.019,
    "AED": 0.044,
    "IDR": 189.0,
    "MYR": 0.056,
    "LKR": 3.6,
    "NPR": 1.6,
    "VND": 290.0,
    "TRY": 0.40,
    "CHF": 0.011,
    "CAD": 0.016,
    "ZAR": 0.22,
    "MVR": 0.19,
    "MAD": 0.12,
    "INR": 1.0,
}


# Common Indian keywords for heuristic domestic detection
_INDIA_KEYWORDS = {
    "pradesh", "pur", "puri", "ganj", "nagar", "puram", "abad", "garh",
    "wadi", "wala", "khand", "kota", "durg", "bhopal", "raipur", "patna",
    "ranchi", "imphal", "aizawl", "kohima", "agartala", "dispur", "panaji",
    "port blair", "kavaratti", "itanagar",
}


def _is_likely_indian(destination: str) -> bool:
    """Heuristic check: does the destination look like an Indian city/state?"""
    dest_lower = destination.lower().strip()
    for keyword in _INDIA_KEYWORDS:
        if dest_lower.endswith(keyword) or keyword in dest_lower:
            return True
    # Wikipedia response might tell us via country data
    return False


def _get_flight_tier(destination: str) -> str:
    """Determine flight tier for a destination."""
    dest_lower = destination.lower().strip()
    for tier, data in FLIGHT_TIERS.items():
        for known_dest in data["destinations"]:
            if known_dest.lower() in dest_lower or dest_lower in known_dest.lower():
                return tier
    # Heuristic: check for Indian-sounding destination names
    if _is_likely_indian(destination):
        return "domestic"
    # Fallback: guess based on offline country data lookup
    info = _lookup_country_data(destination)
    currency = info.get("currency", "USD")
    if currency == "INR":
        return "domestic"
    elif currency in ("THB", "SGD", "MYR", "IDR", "LKR", "NPR", "MVR", "AED", "VND"):
        return "short_haul"
    elif currency in ("JPY", "TRY"):
        return "medium_haul"
    elif currency in ("EUR", "GBP", "CHF"):
        return "long_haul"
    else:
        # Unknown international — default to long_haul (safer than ultra_long_haul)
        return "long_haul"


def _lookup_country_data(destination: str) -> Dict[str, str]:
    """Match destination to country data (fuzzy)."""
    dest_clean = destination.strip()
    # Exact match first
    if dest_clean in COUNTRY_DATA:
        return COUNTRY_DATA[dest_clean]
    # Case-insensitive match
    dest_lower = dest_clean.lower()
    for key, val in COUNTRY_DATA.items():
        if key.lower() == dest_lower:
            return val
    # Partial match
    for key, val in COUNTRY_DATA.items():
        if dest_lower in key.lower() or key.lower() in dest_lower:
            return val
    return {}


def fetch_wikipedia_data(destination: str) -> Dict[str, Any]:
    """
    Fetch destination data from Wikipedia REST API.
    Returns dict with keys: image_url, description, extract, country, currency,
    language, timezone, visa_hint, population.
    """
    result: Dict[str, Any] = {
        "image_url": None,
        "description": "",
        "extract": "",
        "country": "",
        "currency": "USD",
        "currency_symbol": "$",
        "language": "",
        "timezone": "",
        "visa_hint": "",
        "population": "",
        "best_season": "",
        "flag_emoji": "🌍",
    }

    # Fill from offline lookup first
    info = _lookup_country_data(destination)
    if info:
        result["currency"] = info.get("currency", "USD")
        result["currency_symbol"] = info.get("symbol", "$")
        result["language"] = info.get("language", "")
        result["timezone"] = info.get("timezone", "")
        result["visa_hint"] = info.get("visa_hint", "")
        result["country"] = info.get("country", destination)
    elif _is_likely_indian(destination):
        # Unknown but looks like an Indian destination
        result["currency"] = "INR"
        result["currency_symbol"] = "Rs"
        result["language"] = "Hindi/English"
        result["timezone"] = "IST (UTC+5:30)"
        result["visa_hint"] = "No visa required for Indian citizens"
        result["country"] = "India"

    # Wikipedia REST API
    query = destination.replace(" ", "_")
    try:
        url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{query}"
        _log.info("[Wikipedia] GET %s", url)
        response = _session.get(url, timeout=6, headers={"User-Agent": "TripMindAI/1.0"})
        _log.info("[Wikipedia] HTTP %s", response.status_code)
        if response.status_code == 200:
            data = response.json()
            result["description"] = data.get("description", "")
            result["extract"] = data.get("extract", "")[:500]
            thumbnail = data.get("thumbnail") or data.get("originalimage")
            if thumbnail and thumbnail.get("source"):
                result["image_url"] = thumbnail["source"]
            # Try to extract country from description
            desc = data.get("description", "")
            if "," in desc:
                parts = [p.strip() for p in desc.split(",")]
                if parts:
                    result["country"] = result["country"] or parts[-1]
    except Exception:
        pass

    return result


def fetch_exchange_rate(from_currency: str = "INR", to_currency: str = "EUR") -> Tuple[float, str]:
    """
    Fetch live exchange rate from free ExchangeRate-API (no key required).
    Returns: (rate, source) where source is 'live' or 'fallback'.
    Falls back to hardcoded rates on SSL/network errors.
    """
    if from_currency == to_currency:
        return 1.0, "identity"
    try:
        url = f"https://api.exchangerate-api.com/v4/latest/{from_currency}"
        _log.info("[Exchange Rate] Request: GET %s", url)
        resp = _session.get(url, timeout=6)
        _log.info("[Exchange Rate] Response: HTTP %s", resp.status_code)
        if resp.status_code == 200:
            data = resp.json()
            rates = data.get("rates", {})
            if to_currency in rates:
                rate = float(rates[to_currency])
                _log.info(
                    "[Exchange Rate] Live rate: 1 %s = %.6f %s",
                    from_currency, rate, to_currency,
                )
                return rate, "live"
            else:
                _log.warning("[Exchange Rate] Currency %s not in response", to_currency)
        else:
            _log.warning("[Exchange Rate] Non-200 response: %s", resp.text[:200])
    except requests.exceptions.SSLError as exc:
        _log.error("[Exchange Rate] SSL error (using fallback): %s", exc)
    except Exception as exc:
        _log.warning("[Exchange Rate] Request failed (%s), using fallback", exc)

    # Fallback: hardcoded rates
    _log.info("[Exchange Rate] Using hardcoded fallback rate for %s → %s", from_currency, to_currency)
    if from_currency == "INR":
        return FALLBACK_RATES.get(to_currency, 0.012), "fallback"
    inr_to_target = FALLBACK_RATES.get(to_currency, 0.012)
    inr_to_source = FALLBACK_RATES.get(from_currency, 1.0)
    if inr_to_source == 0:
        return 1.0, "fallback"
    return inr_to_target / inr_to_source, "fallback"


# ---------------------------------------------------------------------------
# Amadeus Flight API integration
# ---------------------------------------------------------------------------
_amadeus_token: Optional[str] = None
_amadeus_token_expiry: float = 0.0


def _get_amadeus_token() -> Optional[str]:
    """Fetch (or reuse cached) OAuth2 access token from Amadeus."""
    global _amadeus_token, _amadeus_token_expiry
    client_id = os.getenv("AMADEUS_CLIENT_ID", "").strip()
    client_secret = os.getenv("AMADEUS_CLIENT_SECRET", "").strip()
    if not client_id or not client_secret:
        return None
    # Reuse cached token if still valid
    if _amadeus_token and time.time() < _amadeus_token_expiry - 30:
        return _amadeus_token
    try:
        _log.info("[Amadeus] Fetching OAuth2 token...")
        resp = _session.post(
            "https://test.api.amadeus.com/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            },
            timeout=10,
        )
        _log.info("[Amadeus] Token response: HTTP %s", resp.status_code)
        if resp.status_code == 200:
            payload = resp.json()
            _amadeus_token = payload.get("access_token")
            _amadeus_token_expiry = time.time() + int(payload.get("expires_in", 1800))
            _log.info("[Amadeus] Token obtained, expires in %ds", payload.get("expires_in", 1800))
            return _amadeus_token
        else:
            _log.error("[Amadeus] Token fetch failed: %s", resp.text[:300])
    except Exception as exc:
        _log.error("[Amadeus] Token request error: %s", exc)
    return None


# IATA code lookup for common Indian/international cities
_IATA_CODES: Dict[str, str] = {
    "Chennai": "MAA", "Mumbai": "BOM", "Delhi": "DEL", "Bangalore": "BLR",
    "Bengaluru": "BLR", "Hyderabad": "HYD", "Kolkata": "CCU", "Kochi": "COK",
    "Cochin": "COK", "Goa": "GOI", "Ahmedabad": "AMD", "Pune": "PNQ",
    "Jaipur": "JAI", "Lucknow": "LKO", "Varanasi": "VNS", "Amritsar": "ATQ",
    "Coimbatore": "CJB", "Visakhapatnam": "VTZ", "Vizag": "VTZ",
    "Leh": "IXL", "Srinagar": "SXR", "Chandigarh": "IXC",
    "Tokyo": "NRT", "Osaka": "KIX", "Kyoto": "KIX",
    "Bangkok": "BKK", "Phuket": "HKT", "Singapore": "SIN",
    "Dubai": "DXB", "Kuala Lumpur": "KUL", "Bali": "DPS",
    "London": "LHR", "Paris": "CDG", "Rome": "FCO", "Berlin": "BER",
    "Amsterdam": "AMS", "Barcelona": "BCN", "Madrid": "MAD",
    "New York": "JFK", "Los Angeles": "LAX", "Toronto": "YYZ",
    "Sydney": "SYD", "Melbourne": "MEL",
    "Istanbul": "IST", "Athens": "ATH", "Zurich": "ZRH",
    "Colombo": "CMB", "Kathmandu": "KTM", "Maldives": "MLE",
    "Hong Kong": "HKG", "Seoul": "ICN", "Hanoi": "HAN",
    "Ho Chi Minh City": "SGN", "Lisbon": "LIS", "Cape Town": "CPT",
    "Marrakech": "RAK",
}


def fetch_amadeus_flight_price(
    origin: str,
    destination: str,
    travel_date: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    """
    Fetch real flight price from Amadeus Flight Offers Search API.
    Returns dict with price_inr, currency, source='amadeus' or None if unavailable.
    """
    token = _get_amadeus_token()
    if not token:
        _log.info("[Amadeus] No credentials configured — skipping live flight search")
        return None

    origin_iata = _IATA_CODES.get(origin, origin[:3].upper())
    dest_iata = _IATA_CODES.get(destination, destination[:3].upper())
    # Default travel date: 30 days from today
    if not travel_date:
        from datetime import date, timedelta
        travel_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")

    try:
        _log.info(
            "[Amadeus] Flight search: %s → %s on %s",
            origin_iata, dest_iata, travel_date,
        )
        resp = _session.get(
            "https://test.api.amadeus.com/v2/shopping/flight-offers",
            headers={"Authorization": f"Bearer {token}"},
            params={
                "originLocationCode": origin_iata,
                "destinationLocationCode": dest_iata,
                "departureDate": travel_date,
                "adults": 1,
                "nonStop": "false",
                "max": 5,
            },
            timeout=15,
        )
        _log.info("[Amadeus] Response: HTTP %s", resp.status_code)
        if resp.status_code != 200:
            _log.error("[Amadeus] Error response: %s", resp.text[:400])
            return None

        data = resp.json()
        offers = data.get("data", [])
        if not offers:
            _log.warning("[Amadeus] No flight offers found for %s → %s", origin_iata, dest_iata)
            return None

        # Take the cheapest offer
        prices = []
        for offer in offers:
            try:
                price_str = offer["price"]["grandTotal"]
                currency = offer["price"]["currency"]
                prices.append((float(price_str), currency))
            except (KeyError, ValueError):
                continue

        if not prices:
            return None

        prices.sort(key=lambda x: x[0])
        cheapest_price, currency = prices[0]

        # Convert to INR
        rate, rate_source = fetch_exchange_rate(currency, "INR")
        price_inr = round(cheapest_price * rate, 0)

        _log.info(
            "[Amadeus] Cheapest flight: %s %.2f ≈ ₹%.0f (rate source: %s)",
            currency, cheapest_price, price_inr, rate_source,
        )
        return {
            "price_inr": price_inr,
            "price_original": cheapest_price,
            "currency": currency,
            "origin_iata": origin_iata,
            "dest_iata": dest_iata,
            "travel_date": travel_date,
            "source": "amadeus",
            "num_offers_checked": len(prices),
        }
    except Exception as exc:
        _log.error("[Amadeus] Flight search failed: %s", exc)
        return None


def estimate_flight_cost(
    destination: str,
    budget_inr: int,
    origin: str = "Chennai",
    travel_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Estimate round-trip flight cost.
    Tries Amadeus API first (if configured), then falls back to heuristics.
    Returns dict with min_inr, max_inr, mid_inr, tier, note, source, and currency conversion.
    """
    tier = _get_flight_tier(destination)
    tier_data = FLIGHT_TIERS[tier]

    # Get destination currency
    info = _lookup_country_data(destination)
    dest_currency = info.get("currency", "USD")
    dest_symbol = info.get("symbol", "$")
    rate, rate_source = fetch_exchange_rate("INR", dest_currency) if dest_currency != "INR" else (1.0, "identity")

    # --- Try Amadeus live flight price ---
    amadeus_result = fetch_amadeus_flight_price(origin, destination, travel_date)
    if amadeus_result:
        one_way_inr = amadeus_result["price_inr"]
        round_trip_inr = one_way_inr * 2
        _log.info("[Flight] Using Amadeus live price: ₹%.0f one-way, ₹%.0f round-trip", one_way_inr, round_trip_inr)
        return {
            "min_inr": int(one_way_inr * 1.8),
            "max_inr": int(one_way_inr * 2.5),
            "mid_inr": int(round_trip_inr),
            "tier": tier,
            "note": f"Live price via Amadeus ({amadeus_result['origin_iata']} → {amadeus_result['dest_iata']})",
            "currency": dest_currency,
            "symbol": dest_symbol,
            "converted_min": round(int(one_way_inr * 1.8) * rate, 0),
            "converted_max": round(int(one_way_inr * 2.5) * rate, 0),
            "converted_mid": round(round_trip_inr * rate, 0),
            "rate_inr_to_dest": rate,
            "rate_source": rate_source,
            "source": "amadeus",
            "amadeus_details": amadeus_result,
        }

    # --- Heuristic fallback ---
    min_inr = tier_data["min_inr"]
    max_inr = tier_data["max_inr"]
    mid_inr = (min_inr + max_inr) // 2
    _log.info(
        "[Flight] Using heuristic estimate for %s: ₹%d–₹%d (tier: %s)",
        destination, min_inr, max_inr, tier,
    )
    return {
        "min_inr": min_inr,
        "max_inr": max_inr,
        "mid_inr": mid_inr,
        "tier": tier,
        "note": tier_data["note"] + " (estimated)",
        "currency": dest_currency,
        "symbol": dest_symbol,
        "converted_min": round(min_inr * rate, 0),
        "converted_max": round(max_inr * rate, 0),
        "converted_mid": round(mid_inr * rate, 0),
        "rate_inr_to_dest": rate,
        "rate_source": rate_source,
        "source": "heuristic",
    }


def analyze_budget_feasibility(
    budget_inr: int,
    destination: str,
    days: int,
    origin: str = "Chennai",
    travel_date: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Full budget intelligence analysis with live API data.
    Uses Amadeus flight prices and live exchange rates where available.
    Returns feasibility verdict, itemized estimates, and currency conversion.
    """
    tier = _get_flight_tier(destination)
    flight = estimate_flight_cost(destination, budget_inr, origin=origin, travel_date=travel_date)
    daily_min = DAILY_MIN_BUDGET[tier]

    # Info from offline lookup
    info = _lookup_country_data(destination)
    if not info and _is_likely_indian(destination):
        dest_currency = "INR"
        dest_symbol = "\u20b9"
    else:
        dest_currency = info.get("currency", "USD")
        dest_symbol = info.get("symbol", "$")

    rate, rate_source = (
        fetch_exchange_rate("INR", dest_currency)
        if dest_currency != "INR"
        else (1.0, "identity")
    )

    # Itemized estimates (in INR)
    # flight["mid_inr"] is already round-trip when source=amadeus, one-way*2 when heuristic
    flight_mid_inr = flight["mid_inr"]
    hotel_per_night = daily_min * 0.4 * days
    food_per_day    = daily_min * 0.3 * days
    activities      = daily_min * 0.15 * days
    transport_local = daily_min * 0.1 * days
    emergency       = max(3000, budget_inr * 0.05)

    # For heuristic, mid_inr is one-way — multiply by 2 for round-trip
    if flight.get("source") == "heuristic":
        flight_rt_inr = flight_mid_inr * 2
    else:
        flight_rt_inr = flight_mid_inr  # Amadeus already returns round-trip cost

    min_total_inr = (
        flight_rt_inr + hotel_per_night + food_per_day
        + activities + transport_local + emergency
    )

    converted_budget    = round(budget_inr * rate, 0)
    converted_min_total = round(min_total_inr * rate, 0)

    is_feasible = budget_inr >= (min_total_inr * 0.85)
    budget_pct  = round(budget_inr / max(min_total_inr, 1) * 100, 0)

    reasons = []
    if not is_feasible:
        if flight_rt_inr > budget_inr * 0.5:
            reasons.append(
                f"Flights alone cost \u20b9{flight_rt_inr:,.0f} round-trip"
                " (exceeds half your budget)"
            )
        if hotel_per_night > budget_inr * 0.3:
            reasons.append(
                f"Accommodation for {days} nights estimated \u20b9{hotel_per_night:,.0f}"
            )
        if days > 7 and tier in ("long_haul", "ultra_long_haul"):
            reasons.append(
                f"{days}-day long-haul trip requires significant accommodation budget"
            )
        reasons.append("Visa, travel insurance, and incidentals not yet included")

    if budget_pct >= 150:
        budget_label = "Comfortable"
        budget_color = "#10b981"
    elif budget_pct >= 100:
        budget_label = "Adequate"
        budget_color = "#3b82f6"
    elif budget_pct >= 70:
        budget_label = "Tight"
        budget_color = "#f59e0b"
    else:
        budget_label = "Insufficient"
        budget_color = "#ef4444"

    flight_source_label = (
        "Live (Amadeus)" if flight.get("source") == "amadeus" else "Estimated (heuristic)"
    )
    exchange_source_label = "Live API" if rate_source == "live" else "Fallback rates"

    _log.info(
        "[Budget] %s | Flight: %s | Exchange: %s | Feasible: %s",
        destination, flight_source_label, exchange_source_label, is_feasible,
    )

    return {
        "is_feasible": is_feasible,
        "budget_label": budget_label,
        "budget_color": budget_color,
        "budget_pct": budget_pct,
        "tier": tier,
        "dest_currency": dest_currency,
        "dest_symbol": dest_symbol,
        "rate": rate,
        "rate_source": rate_source,
        "original_budget_inr": budget_inr,
        "converted_budget": converted_budget,
        "min_total_inr": round(min_total_inr, 0),
        "converted_min_total": converted_min_total,
        "items": {
            "flight_estimate_inr": round(flight_rt_inr, 0),
            "hotel_estimate_inr": round(hotel_per_night, 0),
            "food_estimate_inr": round(food_per_day, 0),
            "activities_estimate_inr": round(activities, 0),
            "transport_local_inr": round(transport_local, 0),
            "emergency_buffer_inr": round(emergency, 0),
        },
        "flight_note": flight["note"],
        "flight_source": flight.get("source", "heuristic"),
        "flight_source_label": flight_source_label,
        "exchange_source_label": exchange_source_label,
        "reasons": reasons,
        "shortfall_inr": max(0, min_total_inr - budget_inr),
        "recommended_min_inr": round(min_total_inr * 1.15, 0),
        "recommended_max_inr": round(min_total_inr * 1.5, 0),
    }
