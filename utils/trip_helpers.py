from __future__ import annotations

import json

import streamlit as st

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest


def model_to_dict(model):
    if hasattr(model, "model_dump"):
        return model.model_dump()
    return model.dict()


def parse_trip_record(record: dict) -> tuple[TravelRequest, TravelPackage]:
    request = TravelRequest.parse_obj(json.loads(record["request_json"]))
    package = TravelPackage.parse_obj(json.loads(record["package_json"]))
    return request, package


def apply_request_to_inputs(request: TravelRequest) -> None:
    st.session_state.destination_input = request.destination
    st.session_state.persona_input = request.persona
    st.session_state.days_input = request.days
    st.session_state.budget_input = request.budget
    st.session_state.interests_input = list(request.interests)
    st.session_state.custom_interests_input = ", ".join(request.interests)


def extract_trip_score(record: dict) -> str:
    try:
        summary = json.loads(record.get("summary_json", "{}"))
        intelligence = summary.get("trip_intelligence") or {}
        if intelligence.get("trip_score") is not None:
            return f"{intelligence['trip_score']}/100"
        if summary.get("trip_score") is not None:
            score = float(summary["trip_score"])
            return f"{int(score * 10 if score <= 10 else score):.0f}/100"
    except (json.JSONDecodeError, TypeError, ValueError):
        pass
    return "—"
