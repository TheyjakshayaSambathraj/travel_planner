from __future__ import annotations

import json

import streamlit as st

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest
from orchestrator.travel_orchestrator import TravelOrchestrator
from services.pdf_exporter import TravelDossierExporter
from services.trip_history_db import TripHistoryDB
from utils.validators import ValidationError, build_travel_request, sanitize_interests


PERSONA_OPTIONS = [
    "Backpacker",
    "Photographer",
    "Food Explorer",
    "Digital Nomad",
    "Family Traveler",
    "Luxury Escapist",
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


st.set_page_config(
    page_title="TripMind AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="expanded",
)


def initialize_session_state() -> None:
    defaults = {
        "orchestrator": TravelOrchestrator(),
        "history_db": TripHistoryDB(),
        "pdf_exporter": TravelDossierExporter(),
        "destination_input": "",
        "persona_input": PERSONA_OPTIONS[0],
        "days_input": 4,
        "budget_input": 15000,
        "interests_input": [],
        "custom_interests_input": "",
        "current_request": None,
        "current_trip": None,
        "loaded_trip_id": None,
        "save_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


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


def render_hero_section() -> None:
    with st.container(border=True):
        left, right = st.columns([3, 2])
        with left:
            st.markdown("# Plan an Entire Trip in Under 30 Seconds")
            st.caption("Powered by Multi-Agent AI Intelligence")
            st.write(
                "Feasibility analysis, persona-driven planning, destination intelligence, visual timeline cards, analytics, trip history, and dossier export in one command center."
            )
        with right:
            st.metric("Provider Layer", "Failover Enabled")
            st.metric("Agent Flow", "Research → Summary")


def render_summary_card(request: TravelRequest, trip_package: TravelPackage) -> None:
    feasibility = trip_package.feasibility
    intelligence = trip_package.summary.trip_intelligence
    with st.container(border=True):
        cols = st.columns(6)
        cols[0].metric("Destination", request.destination)
        cols[1].metric("Persona", request.persona)
        cols[2].metric("Days", request.days)
        cols[3].metric("Trip Score", f"{intelligence.trip_score}/100")
        cols[4].metric("Budget Fit", f"{intelligence.budget_fit}/100")
        cols[5].metric("Feasibility", f"{feasibility.confidence_score}%")


def render_recent_trips_sidebar(history_db: TripHistoryDB) -> None:
    with st.sidebar:
        st.markdown("## Recent Trips")
        recent_trips = history_db.list_recent_trips(limit=8)
        if not recent_trips:
            st.caption("No saved trips yet.")
            return

        for trip in recent_trips:
            created_at = trip.get("created_at", "")
            with st.container(border=True):
                st.write(f"**{trip.get('destination', 'Trip')}**")
                st.caption(f"{trip.get('persona', 'Persona')} • {created_at[:10] if created_at else 'Unknown date'}")
                col_open, col_reuse, col_delete = st.columns(3)
                if col_open.button("Open", key=f"open_{trip['trip_id']}", use_container_width=True):
                    st.session_state.loaded_trip_id = trip["trip_id"]
                    st.rerun()
                if col_reuse.button("Reuse", key=f"reuse_{trip['trip_id']}", use_container_width=True):
                    request, _ = parse_trip_record(trip)
                    apply_request_to_inputs(request)
                    st.session_state.loaded_trip_id = None
                    st.session_state.save_message = "Inputs loaded from saved trip."
                    st.rerun()
                if col_delete.button("Delete", key=f"delete_{trip['trip_id']}", use_container_width=True):
                    history_db.delete_trip(trip["trip_id"])
                    if st.session_state.loaded_trip_id == trip["trip_id"]:
                        st.session_state.loaded_trip_id = None
                        st.session_state.current_request = None
                        st.session_state.current_trip = None
                    st.session_state.save_message = "Trip deleted from history."
                    st.rerun()


def render_feasibility_banner(trip_package: TravelPackage) -> None:
    feasibility = trip_package.feasibility
    if feasibility.feasible:
        st.success(
            f"Feasibility score {feasibility.confidence_score}% - the current request looks realistic for the selected persona."
        )
    else:
        st.warning(
            f"Feasibility score {feasibility.confidence_score}% - the request needs adjustment before it becomes robust."
        )
        if feasibility.issues:
            st.write("**Issues**")
            for item in feasibility.issues:
                st.write(f"- {item}")
        if feasibility.recommendations:
            st.write("**Recommendations**")
            for item in feasibility.recommendations:
                st.write(f"- {item}")


def render_top_metrics(request: TravelRequest, trip_package: TravelPackage) -> None:
    intelligence = trip_package.summary.trip_intelligence
    analytics = trip_package.summary.analytics_summary
    with st.container(border=True):
        row1 = st.columns(5)
        row1[0].metric("Trip Score", f"{intelligence.trip_score}/100")
        row1[1].metric("Budget Fit", f"{intelligence.budget_fit}/100")
        row1[2].metric("Experience", f"{intelligence.experience_score}/100")
        row1[3].metric("Food", f"{intelligence.food_score}/100")
        row1[4].metric("Comfort", f"{intelligence.comfort_score}/100")

        row2 = st.columns(4)
        row2[0].metric("Destination", request.destination)
        row2[1].metric("Persona", request.persona)
        row2[2].metric("Trip Type", trip_package.summary.trip_type)
        row2[3].metric("Estimated Cost", f"₹{analytics.estimated_total_cost:,}")

        st.caption(f"Overall Rating: {intelligence.overall_rating} | Travel Efficiency: {analytics.travel_efficiency}/100")


def render_timeline_tab(trip_package: TravelPackage) -> None:
    for day in trip_package.itinerary.days:
        with st.container(border=True):
            st.markdown(f"### Day {day.day}")
            col1, col2, col3 = st.columns(3)
            sections = [
                (col1, "🌅 Morning", day.morning),
                (col2, "🍽 Afternoon", day.afternoon),
                (col3, "🌃 Evening", day.evening),
            ]
            for column, label, items in sections:
                with column:
                    st.markdown(f"#### {label}")
                    if not items:
                        st.caption("No activities planned.")
                    for item in items:
                        st.markdown(f"**{item.activity}**")
                        if item.location:
                            st.caption(item.location)
                        st.divider()


def render_trip_results(trip_package: TravelPackage, request: TravelRequest) -> None:
    render_feasibility_banner(trip_package)
    render_top_metrics(request, trip_package)

    tabs = st.tabs(["Summary", "Itinerary", "Budget", "Food", "Packing", "Safety"])

    with tabs[0]:
        left, right = st.columns([2, 1])
        with left:
            st.subheader("Executive Summary")
            st.write(trip_package.summary.overall_summary)
            st.write("**Highlights**")
            for item in trip_package.summary.highlights:
                st.write(f"- {item}")
            st.write("**Best Experiences**")
            for item in trip_package.summary.best_experiences:
                st.write(f"- {item}")
        with right:
            st.subheader("AI Insights")
            st.write("**Money Saving Tips**")
            for item in trip_package.summary.ai_insights.money_saving_tips:
                st.write(f"- {item}")
            st.write("**Hidden Gems**")
            for item in trip_package.summary.ai_insights.hidden_gems:
                st.write(f"- {item}")
            st.write("**Avoid**")
            for item in trip_package.summary.ai_insights.avoid:
                st.write(f"- {item}")
            st.write("**Local Secrets**")
            for item in trip_package.summary.ai_insights.local_secrets:
                st.write(f"- {item}")

        with st.expander("Trip Intelligence and Analytics", expanded=False):
            c1, c2, c3 = st.columns(3)
            c1.metric("Trip Score", f"{trip_package.summary.trip_intelligence.trip_score}/100")
            c2.metric("Budget Fit", f"{trip_package.summary.trip_intelligence.budget_fit}/100")
            c3.metric("Efficiency", f"{trip_package.summary.analytics_summary.travel_efficiency}/100")
            st.write(f"**Trip Category:** {trip_package.summary.analytics_summary.trip_category}")
            st.write(f"**Difficulty Score:** {trip_package.summary.analytics_summary.difficulty_score}/100")
            st.write(f"**Recommended For:** {trip_package.summary.analytics_summary.recommended_for}")

        with st.expander("Destination Intelligence", expanded=False):
            st.write(trip_package.research.destination_overview)
            st.write(f"**Best time to visit:** {trip_package.research.best_time_to_visit}")
            st.write("**Popular areas**")
            for item in trip_package.research.popular_areas:
                st.write(f"- {item}")
            st.write("**Local transport**")
            for item in trip_package.research.local_transport:
                st.write(f"- {item}")
            st.write("**Key highlights**")
            for item in trip_package.research.key_highlights:
                st.write(f"- {item}")

        try:
            pdf_bytes = st.session_state.pdf_exporter.export(request, trip_package)
            st.download_button(
                "Download Travel Dossier",
                data=pdf_bytes,
                file_name=f"tripmind-dossier-{request.destination.lower().replace(' ', '-')}.pdf",
                mime="application/pdf",
                use_container_width=True,
            )
        except Exception:
            st.error("Travel dossier export failed. Please try again.")

    with tabs[1]:
        render_timeline_tab(trip_package)

    with tabs[2]:
        budget = trip_package.budget
        cols = st.columns(5)
        cols[0].metric("Accommodation", f"₹{budget.accommodation:,}")
        cols[1].metric("Food", f"₹{budget.food:,}")
        cols[2].metric("Transport", f"₹{budget.transport:,}")
        cols[3].metric("Activities", f"₹{budget.activities:,}")
        cols[4].metric("Emergency", f"₹{budget.emergency_buffer:,}")
        st.info(budget.allocation_reasoning)

    with tabs[3]:
        st.write("**Must try foods**")
        for item in trip_package.food.must_try_foods:
            st.write(f"- {item}")
        st.write("**Street foods**")
        for item in trip_package.food.street_foods:
            st.write(f"- {item}")
        st.write("**Recommended restaurants**")
        for item in trip_package.food.recommended_restaurants:
            st.write(f"- {item}")
        st.write("**Food tips**")
        for item in trip_package.food.food_tips:
            st.write(f"- {item}")

    with tabs[4]:
        st.write("**Essentials**")
        for item in trip_package.packing.essentials:
            st.write(f"- {item}")
        st.write("**Weather items**")
        for item in trip_package.packing.weather_items:
            st.write(f"- {item}")
        st.write("**Electronics**")
        for item in trip_package.packing.electronics:
            st.write(f"- {item}")
        st.write("**Documents**")
        for item in trip_package.packing.documents:
            st.write(f"- {item}")

    with tabs[5]:
        st.write("**Travel tips**")
        for item in trip_package.safety.travel_tips:
            st.write(f"- {item}")
        st.write("**Warnings**")
        for item in trip_package.safety.warnings:
            st.write(f"- {item}")
        st.write("**Local etiquette**")
        for item in trip_package.safety.local_etiquette:
            st.write(f"- {item}")
        st.write("**Emergency contacts**")
        for item in trip_package.safety.emergency_contacts:
            st.write(f"- {item}")

    with st.expander("Raw trip package"):
        st.json(trip_package.as_dict())


def render_main_form() -> tuple[str, str, int, int, list[str], str]:
    with st.container(border=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            destination = st.text_input("Destination", key="destination_input", placeholder="e.g. Goa, Jaipur, Tokyo")
            persona = st.selectbox("Persona", PERSONA_OPTIONS, key="persona_input")
            interests = st.multiselect("Interests", INTEREST_OPTIONS, key="interests_input")
            custom_interests = st.text_input(
                "Additional interests",
                key="custom_interests_input",
                placeholder="Comma-separated, for example: sunrise viewpoints, cafes",
            )

        with col2:
            days = st.number_input("Number of Days", min_value=1, max_value=30, key="days_input", step=1)
            budget = st.number_input("Budget", min_value=1, max_value=10_000_000, key="budget_input", step=500)

    return destination, persona, int(days), int(budget), interests, custom_interests


def load_active_trip(history_db: TripHistoryDB) -> tuple[TravelRequest | None, TravelPackage | None]:
    loaded_trip_id = st.session_state.get("loaded_trip_id")
    if not loaded_trip_id:
        return None, None

    record = history_db.load_trip(loaded_trip_id)
    if not record:
        st.session_state.loaded_trip_id = None
        return None, None

    request, trip_package = parse_trip_record(record)
    return request, trip_package


def main() -> None:
    initialize_session_state()
    history_db: TripHistoryDB = st.session_state.history_db
    render_recent_trips_sidebar(history_db)
    render_hero_section()

    st.markdown("---")
    st.markdown(
        "Build a feasibility-checked, persona-driven travel plan with destination intelligence, analytics, history, and dossier export."
    )

    request_from_history, trip_from_history = load_active_trip(history_db)
    if request_from_history and trip_from_history:
        st.info("Viewing a saved trip from history. Use Reuse to preload its inputs into the planner.")
        if st.button("Clear Loaded Trip", use_container_width=True):
            st.session_state.loaded_trip_id = None
            st.rerun()
        render_summary_card(request_from_history, trip_from_history)
        render_trip_results(trip_from_history, request_from_history)
        st.markdown("---")

    destination, persona, days, budget, interests, custom_interests = render_main_form()
    generate_button = st.button("Generate Trip", type="primary", use_container_width=True)

    if generate_button:
        try:
            request = build_travel_request(
                destination=destination,
                days=days,
                budget=budget,
                persona=persona,
                interests=sanitize_interests(interests, custom_interests),
            )

            progress_placeholder = st.empty()
            progress_bar = st.progress(0)
            status_placeholder = st.empty()
            steps = [
                "✓ Validating Trip",
                "✓ Researching Destination",
                "✓ Building Itinerary",
                "✓ Calculating Budget",
                "✓ Discovering Food",
                "✓ Creating Packing List",
                "✓ Analyzing Safety",
                "✓ Generating Summary",
                "✓ Preparing Insights",
            ]

            def update_progress(message: str) -> None:
                progress_placeholder.info(message)
                index = 0
                for idx, step in enumerate(steps, start=1):
                    if message.lower().replace("...", "").strip() in step.lower():
                        index = idx
                        break
                if index == 0:
                    index = 1
                progress_bar.progress(index / len(steps))
                lines = []
                for idx, step in enumerate(steps, start=1):
                    prefix = "✓" if idx < index else ("→" if idx == index else "•")
                    lines.append(f"{prefix} {step[2:]}")
                status_placeholder.markdown("\n".join(lines))

            with st.spinner("Creating your TripMind plan..."):
                trip_package = st.session_state.orchestrator.generate_trip(request, progress_callback=update_progress)

            st.session_state.current_request = request
            st.session_state.current_trip = trip_package
            trip_id = history_db.save_trip(request, trip_package)
            st.session_state.loaded_trip_id = trip_id
            st.session_state.save_message = "Trip saved to local history."

            progress_placeholder.success("Trip plan generated successfully.")
            progress_bar.progress(1.0)
            render_summary_card(request, trip_package)
            render_trip_results(trip_package, request)
        except ValidationError as error:
            st.error(str(error))
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("Trip generation failed. Please verify your provider keys, budget, and destination inputs.")

    if st.session_state.get("save_message"):
        st.caption(st.session_state.save_message)


if __name__ == "__main__":
    main()
