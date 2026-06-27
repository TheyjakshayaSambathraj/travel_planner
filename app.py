from __future__ import annotations

from utils.env_bootstrap import bootstrap_env

bootstrap_env()

import streamlit as st

from orchestrator.travel_orchestrator import TravelOrchestrator
from services.llm.base_provider import LLMAPIError
from services.pdf_exporter import TravelDossierExporter
from services.trip_history_db import TripHistoryDB
from ui.components import (
    _reset_session_state,
    build_progress_callback,
    render_custom_nav,
    render_error_card,
    render_hero_section,
    render_input_panel,
    render_loading_panel,
    render_persistent_dashboard,
    render_saved_trips_panel,
    render_trip_results,
    update_dashboard_metrics,
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
    initial_sidebar_state="collapsed",
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
        "origin_city_input": "",
        "persona_input": PERSONA_OPTIONS[0],
        "days_input": 4,
        "budget_input": 150000,
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
        "nav_open": False,
        "active_page": "new_trip",
        "show_saved_trips_panel": False,
        "_dashboard_request": None,
        "_dashboard_trip": None,
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def enrich_interests(
    interests: list[str],
    custom_interests: str,
    accommodation: str,
    transportation: str,
    origin_city: str,
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
    if origin_city and origin_city.strip():
        tag = f"Origin: {origin_city.strip()}"
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
    try:
        event = llm_manager.last_failover_event
    except AttributeError:
        return
    if not event or not event.get("from"):
        return
    event_key = f"{event.get('from')}->{event.get('to')}@{event.get('timestamp')}"
    if st.session_state.get("last_failover_toast") != event_key:
        st.session_state.last_failover_toast = event_key
        st.toast(
            f"Provider switched: {event.get('from')} → {event.get('to', 'backup')}"
        )


def main() -> None:
    initialize_session_state()
    inject_theme(
        compact_view=st.session_state.get("compact_view", False),
        animations_enabled=st.session_state.get("animations_enabled", True),
    )

    orchestrator = get_orchestrator()
    history_db = get_history_db()
    pdf_exporter = get_pdf_exporter()

    # ── Custom Navigation ────────────────────────────────────────────────────
    render_custom_nav(history_db, orchestrator.llm_manager)
    maybe_show_failover_toast(orchestrator.llm_manager)

    # ── Saved Trips Panel (single render site — only here in app.py) ─────────
    if st.session_state.get("show_saved_trips_panel"):
        render_saved_trips_panel(history_db)

    # ── Hero Section ─────────────────────────────────────────────────────────
    render_hero_section()

    # ── Dashboard (always visible) ───────────────────────────────────────────
    display_request, display_trip = get_display_trip(history_db)
    if not display_request or not display_trip:
        display_request = st.session_state.get("current_request")
        display_trip = st.session_state.get("current_trip")

    render_persistent_dashboard(display_request, display_trip)

    st.markdown('<hr class="divider-line">', unsafe_allow_html=True)

    # ── Input Panel ──────────────────────────────────────────────────────────
    # render_input_panel now returns 9 values (added origin_city)
    (
        destination,
        persona,
        days,
        budget,
        interests,
        custom_interests,
        accommodation,
        transportation,
        origin_city,
    ) = render_input_panel(
        PERSONA_OPTIONS,
        INTEREST_OPTIONS,
        ACCOMMODATION_OPTIONS,
        TRANSPORT_OPTIONS,
    )

    # ── Action buttons row ───────────────────────────────────────────────────
    btn_col1, btn_col2, btn_col3 = st.columns([4, 1, 1])
    with btn_col1:
        generate_button = st.button(
            "✈️ Generate My Trip Plan",
            type="primary",
            use_container_width=True,
            key="btn_main_generate",
        )
    with btn_col2:
        if st.button(
            "📂 Saved Trips",
            use_container_width=True,
            key="btn_main_saved_trips",
        ):
            st.session_state["show_saved_trips_panel"] = not st.session_state.get(
                "show_saved_trips_panel", False
            )
            st.rerun()
    with btn_col3:
        if st.button("➕ New Trip", use_container_width=True, key="btn_main_new_trip"):
            _reset_session_state()
            st.rerun()

    # ── Toast messages ───────────────────────────────────────────────────────
    if st.session_state.get("save_message"):
        st.toast(st.session_state.save_message)
        st.session_state.save_message = ""

    # ── Generate ─────────────────────────────────────────────────────────────
    if generate_button:
        if not destination or not destination.strip():
            st.error("⚠️ Please enter a destination before generating your trip.")
        else:
            progress_bar = st.progress(0)
            stage_container = st.empty()
            render_loading_panel(progress_bar, stage_container)
            update_progress = build_progress_callback(progress_bar, stage_container)

            try:
                request = build_travel_request(
                    destination=destination.strip(),
                    days=days,
                    budget=budget,
                    persona=persona,
                    interests=enrich_interests(
                        interests,
                        custom_interests,
                        accommodation,
                        transportation,
                        origin_city,
                    ),
                )

                trip_package = orchestrator.generate_trip(
                    request, progress_callback=update_progress
                )
                maybe_show_failover_toast(orchestrator.llm_manager)

                progress_bar.progress(1.0)
                stage_container.empty()

                st.session_state.current_request = request
                st.session_state.current_trip = trip_package
                trip_id = history_db.save_trip(request, trip_package)
                st.session_state.loaded_trip_id = trip_id
                st.session_state.show_results = True
                st.session_state.fresh_generation = True
                st.session_state.save_message = "✅ Trip generated and saved."
                update_dashboard_metrics(request, trip_package)
                st.rerun()

            except ValidationError as error:
                render_error_card("Invalid Input", str(error))
                st.session_state.show_results = False
            except ValueError as error:
                render_error_card("Input Error", str(error))
                st.session_state.show_results = False
            except LLMAPIError:
                render_error_card(
                    "AI Service Unavailable",
                    "All AI providers are temporarily unavailable. "
                    "Check your API keys in .env and try again.",
                )
                st.session_state.show_results = False
            except Exception as exc:
                render_error_card(
                    "Generation Failed",
                    f"We couldn't complete your trip plan. Error: {exc}. "
                    "Please verify your inputs and API configuration, then try again.",
                )
                st.session_state.show_results = False

    # ── Trip Results ──────────────────────────────────────────────────────────
    if st.session_state.get("show_results"):
        request, trip_package = get_display_trip(history_db)
        if request and trip_package:
            update_dashboard_metrics(request, trip_package)

            viewing_saved = (
                bool(st.session_state.get("loaded_trip_id"))
                and not st.session_state.get("fresh_generation")
            )
            if viewing_saved:
                st.info(
                    "📂 Viewing a saved trip. Use **➕ New Trip** to start fresh."
                )
                if st.button(
                    "✕ Clear Loaded Trip",
                    use_container_width=True,
                    key="btn_clear_loaded_trip",
                ):
                    st.session_state.loaded_trip_id = None
                    st.session_state.show_results = False
                    update_dashboard_metrics()
                    st.rerun()

            st.markdown('<hr class="divider-line">', unsafe_allow_html=True)
            render_trip_results(
                trip_package,
                request,
                pdf_exporter,
                show_success=st.session_state.get("fresh_generation", False),
            )
            # Mark as no longer fresh after first render
            if st.session_state.get("fresh_generation"):
                st.session_state.fresh_generation = False


if __name__ == "__main__":
    main()
