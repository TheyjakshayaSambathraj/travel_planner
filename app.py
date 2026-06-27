from __future__ import annotations

from utils.env_bootstrap import bootstrap_env

bootstrap_env()

import streamlit as st

from orchestrator.travel_orchestrator import TravelOrchestrator
from services.llm.base_provider import LLMAPIError
from services.pdf_exporter import TravelDossierExporter
from services.trip_history_db import TripHistoryDB
from ui.components import (
    build_progress_callback,
    render_error_card,
    render_hero_section,
    render_input_panel,
    render_loading_panel,
    render_persistent_dashboard,
    render_sidebar,
    render_trip_results,
)
from ui.theme import inject_theme
from utils.trip_helpers import parse_trip_record
from utils.validators import ValidationError, build_travel_request, sanitize_interests


PERSONA_OPTIONS = [
    "Backpacker",
    "Photographer",
    "Food Explorer",
    "Digital Nomad",
    "Family Traveler",
    "Luxury Escapist",
    "Nightlife Explorer",
]

INTEREST_OPTIONS = [
    "Beaches",
    "Food",
    "Culture",
    "Adventure",
    "Shopping",
    "Nightlife",
    "Nature",
    "History",
    "Wellness",
    "Photography",
    "Workspaces",
    "Family Activities",
]

ACCOMMODATION_OPTIONS = [
    "Any",
    "Hostel",
    "Budget Hotel",
    "Boutique Hotel",
    "Resort",
    "Homestay",
]

TRANSPORT_OPTIONS = [
    "Flexible",
    "Public Transit",
    "Rental Car",
    "Walking",
    "Rideshare",
    "Train",
]


st.set_page_config(
    page_title="TripMind AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


@st.cache_resource(show_spinner=False)
def get_orchestrator() -> TravelOrchestrator:
    return TravelOrchestrator()


@st.cache_resource(show_spinner=False)
def get_history_db() -> TripHistoryDB:
    return TripHistoryDB()


@st.cache_resource(show_spinner=False)
def get_pdf_exporter() -> TravelDossierExporter:
    return TravelDossierExporter()


def initialize_session_state() -> None:
    defaults = {
        "destination_input": "",
        "persona_input": PERSONA_OPTIONS[0],
        "days_input": 4,
        "budget_input": 15000,
        "interests_input": [],
        "custom_interests_input": "",
        "accommodation_input": ACCOMMODATION_OPTIONS[0],
        "transportation_input": TRANSPORT_OPTIONS[0],
        "current_request": None,
        "current_trip": None,
        "loaded_trip_id": None,
        "save_message": "",
        "show_results": False,
        "fresh_generation": False,
        "last_failover_toast": None,
        "compact_view": False,
        "animations_enabled": True,
        "auto_save": True,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def enrich_interests(
    interests: list[str],
    custom_interests: str,
    accommodation: str,
    transportation: str,
) -> list[str]:
    merged = sanitize_interests(interests, custom_interests)
    if accommodation and accommodation != "Any":
        tag = f"Accommodation: {accommodation}"
        if tag not in merged:
            merged.append(tag)
    if transportation and transportation != "Flexible":
        tag = f"Transport: {transportation}"
        if tag not in merged:
            merged.append(tag)
    return merged


def get_display_trip(history_db: TripHistoryDB):
    if st.session_state.get("loaded_trip_id"):
        record = history_db.load_trip(st.session_state.loaded_trip_id)
        if record:
            return parse_trip_record(record)
        st.session_state.loaded_trip_id = None

    request = st.session_state.get("current_request")
    trip = st.session_state.get("current_trip")
    if request and trip:
        return request, trip
    return None, None


def maybe_show_failover_toast(llm_manager) -> None:
    event = llm_manager.last_failover_event
    if not event or not event.get("from"):
        return
    event_key = f"{event.get('from')}->{event.get('to')}@{event.get('timestamp')}"
    if st.session_state.get("last_failover_toast") != event_key:
        st.session_state.last_failover_toast = event_key
        st.toast(f"Switching provider... ({event.get('from')} → {event.get('to', 'backup')})")


def main() -> None:
    initialize_session_state()
    inject_theme(
        compact_view=st.session_state.get("compact_view", False),
        animations_enabled=st.session_state.get("animations_enabled", True),
    )

    orchestrator = get_orchestrator()
    history_db = get_history_db()
    pdf_exporter = get_pdf_exporter()

    render_sidebar(history_db, orchestrator.llm_manager)
    maybe_show_failover_toast(orchestrator.llm_manager)

    render_hero_section()

    display_request, display_trip = get_display_trip(history_db)
    if not display_request or not display_trip:
        display_request = st.session_state.get("current_request")
        display_trip = st.session_state.get("current_trip")

    render_persistent_dashboard(display_request, display_trip)

    st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

    render_input_panel(
        PERSONA_OPTIONS,
        INTEREST_OPTIONS,
        ACCOMMODATION_OPTIONS,
        TRANSPORT_OPTIONS,
    )

    generate_button = st.button("✈️ Generate My Trip Plan", type="primary", use_container_width=True)

    if st.session_state.get("save_message"):
        st.toast(st.session_state.save_message)
        st.session_state.save_message = ""

    if generate_button:
        progress_bar = st.progress(0)
        stage_container = st.empty()
        render_loading_panel(progress_bar, stage_container)
        update_progress = build_progress_callback(progress_bar, stage_container)

        try:
            request = build_travel_request(
                destination=st.session_state.destination_input,
                days=int(st.session_state.days_input),
                budget=int(st.session_state.budget_input),
                persona=st.session_state.persona_input,
                interests=enrich_interests(
                    st.session_state.interests_input,
                    st.session_state.custom_interests_input,
                    st.session_state.accommodation_input,
                    st.session_state.transportation_input,
                ),
            )

            trip_package = orchestrator.generate_trip(request, progress_callback=update_progress)
            maybe_show_failover_toast(orchestrator.llm_manager)

            progress_bar.progress(1.0)
            st.session_state.current_request = request
            st.session_state.current_trip = trip_package
            trip_id = history_db.save_trip(request, trip_package)
            st.session_state.loaded_trip_id = trip_id
            st.session_state.show_results = True
            st.session_state.fresh_generation = True
            st.session_state.save_message = "Trip generated successfully."

        except ValidationError as error:
            render_error_card("Invalid Input", str(error))
            st.session_state.show_results = False
        except ValueError as error:
            render_error_card("Input Error", str(error))
            st.session_state.show_results = False
        except LLMAPIError:
            render_error_card(
                "AI Service Unavailable",
                "All AI providers are temporarily unavailable. Check your API keys in .env and try again.",
            )
            st.session_state.show_results = False
            if st.button("Retry Generation", key="retry_llm"):
                st.rerun()
        except Exception:
            render_error_card(
                "Generation Failed",
                "We couldn't complete your trip plan. Please verify your inputs and API configuration, then try again.",
            )
            st.session_state.show_results = False
            if st.button("Retry Generation", key="retry_generic"):
                st.rerun()

    if st.session_state.get("show_results"):
        request, trip_package = get_display_trip(history_db)
        if request and trip_package:
            viewing_saved = bool(st.session_state.get("loaded_trip_id")) and not st.session_state.get("fresh_generation")
            if viewing_saved:
                st.info("Viewing a saved trip. Use **Open** or **Reuse** from the sidebar to manage history.")
                if st.button("Clear Loaded Trip", use_container_width=True):
                    st.session_state.loaded_trip_id = None
                    st.session_state.show_results = False
                    st.rerun()

            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
            render_trip_results(
                trip_package,
                request,
                pdf_exporter,
                show_success=st.session_state.get("fresh_generation", False),
            )


if __name__ == "__main__":
    main()
