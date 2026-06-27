from __future__ import annotations

import html
from typing import Callable, Optional

import streamlit as st

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest
from services.llm.llm_manager import LLMManager
from services.pdf_exporter import TravelDossierExporter
from services.trip_history_db import TripHistoryDB
from ui.theme import AGENT_COUNT, APP_VERSION, PROVIDERS
from utils.env_bootstrap import get_configured_provider_names
from utils.trip_helpers import apply_request_to_inputs, extract_trip_score, parse_trip_record


WORKFLOW_STAGES = [
    "Validating Trip",
    "Researching Destination",
    "Planning Itinerary",
    "Optimizing Budget",
    "Finding Food",
    "Packing Essentials",
    "Safety Analysis",
    "AI Summary",
    "Finalizing Travel Package",
]

STAGE_KEYWORDS = {
    "validating": 0,
    "researching": 1,
    "planning": 2,
    "optimizing": 3,
    "finding": 4,
    "packing": 5,
    "safety": 6,
    "summary": 7,
    "finalizing": 8,
}

BUDGET_EXPLANATIONS = {
    "Accommodation": "Lodging aligned with your persona and trip duration.",
    "Food": "Daily meals, local dining, and specialty food experiences.",
    "Transport": "Local transit, transfers, and getting between attractions.",
    "Activities": "Tours, tickets, entertainment, and paid experiences.",
    "Emergency Buffer": "Safety reserve for unexpected costs and flexibility.",
}

TIME_DURATIONS = {
    "Morning": "2–3 hours",
    "Afternoon": "3–4 hours",
    "Evening": "2–3 hours",
    "Night": "2–4 hours",
}

TIME_TIPS = {
    "Morning": "Start early to beat crowds at popular spots.",
    "Afternoon": "Stay hydrated and plan indoor breaks during peak heat.",
    "Evening": "Book restaurants ahead on weekends.",
    "Night": "Check last transport times before heading out.",
}


def _esc(text: str) -> str:
    return html.escape(str(text))


def render_hero_section() -> None:
    badges = [
        "Multi-Agent",
        "AI Research",
        "Budget Optimizer",
        "PDF Export",
        "Trip History",
        "Provider Failover",
    ]
    badge_html = "".join(f'<span class="feature-badge">✓ {_esc(b)}</span>' for b in badges)
    st.markdown(
        f"""
        <div class="hero-container page-section">
            <div class="hero-title">✈️ TripMind AI</div>
            <div class="hero-subtitle">Plan an Entire Trip in Under 30 Seconds</div>
            <div class="hero-tagline">Multi-Agent AI Travel Intelligence Platform</div>
            <div class="badge-row">{badge_html}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_persistent_dashboard(
    request: Optional[TravelRequest],
    trip_package: Optional[TravelPackage],
) -> None:
    st.markdown(
        """
        <div class="dashboard-panel page-section">
            <div class="page-section-title">Trip Dashboard</div>
            <div class="page-section-subtitle">Live metrics update after every generated trip</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    row1 = st.columns(4)
    row2 = st.columns(4)

    if request and trip_package:
        intelligence = trip_package.summary.trip_intelligence
        analytics = trip_package.summary.analytics_summary
        metrics = [
            ("Trip Score", f"{intelligence.trip_score}/100"),
            ("Budget Fit", f"{intelligence.budget_fit}/100"),
            ("Estimated Cost", f"₹{analytics.estimated_total_cost:,}"),
            ("Difficulty", f"{analytics.difficulty_score}/100"),
            ("Duration", f"{request.days} days"),
            ("Persona", request.persona),
            ("Destination", request.destination),
            ("Trip Type", trip_package.summary.trip_type),
        ]
    else:
        destination_label = st.session_state.get("destination_input") or "—"
        persona_label = st.session_state.get("persona_input") or "—"
        days_label = f"{st.session_state.get('days_input', '—')} days" if st.session_state.get("days_input") else "—"
        metrics = [
            ("Trip Score", "—"),
            ("Budget Fit", "—"),
            ("Estimated Cost", "—"),
            ("Difficulty", "—"),
            ("Duration", days_label),
            ("Persona", persona_label),
            ("Destination", destination_label),
            ("Trip Type", "—"),
        ]

    for col, (label, value) in zip(row1 + row2, metrics):
        col.metric(label, value)

    if not trip_package:
        st.caption("Fill in your trip details below and generate to populate live metrics.")


def render_sidebar(
    history_db: TripHistoryDB,
    llm_manager: LLMManager,
) -> None:
    with st.sidebar:
        st.markdown('<div class="sidebar-brand">✈️ TripMind AI</div>', unsafe_allow_html=True)
        st.caption("Intelligent travel command center")

        st.markdown('<div class="sidebar-section-title">Trip History</div>', unsafe_allow_html=True)
        search_query = st.text_input(
            "Search",
            placeholder="Search destination or persona...",
            key="trip_search",
            label_visibility="collapsed",
        )
        trips = (
            history_db.search_trips(search_query, limit=50)
            if search_query.strip()
            else history_db.list_recent_trips(limit=50)
        )

        if not trips:
            st.caption("No saved trips yet. Generate a trip to build your history.")
        else:
            for trip in trips:
                created_at = trip.get("created_at", "")
                date_label = created_at[:10] if created_at else "Unknown"
                score = extract_trip_score(trip)
                with st.container(border=True):
                    st.markdown(f"**{_esc(trip.get('destination', 'Trip'))}**")
                    st.caption(f"📅 {date_label}")
                    st.caption(f"👤 {_esc(trip.get('persona', ''))}")
                    st.caption(f"⭐ Score: {score}")
                    tid = trip["trip_id"]
                    c1, c2, c3 = st.columns(3)
                    if c1.button("Open", key=f"open_{tid}", use_container_width=True):
                        st.session_state.loaded_trip_id = tid
                        st.session_state.show_results = True
                        st.session_state.fresh_generation = False
                        st.rerun()
                    if c2.button("Dup", key=f"dup_{tid}", use_container_width=True):
                        new_id = history_db.duplicate_trip(tid)
                        st.session_state.save_message = "Trip duplicated." if new_id else "Could not duplicate."
                        st.rerun()
                    if c3.button("Del", key=f"del_{tid}", use_container_width=True):
                        history_db.delete_trip(tid)
                        if st.session_state.get("loaded_trip_id") == tid:
                            st.session_state.loaded_trip_id = None
                            st.session_state.current_request = None
                            st.session_state.current_trip = None
                            st.session_state.show_results = False
                        st.session_state.save_message = "Trip deleted."
                        st.rerun()

        st.markdown('<div class="sidebar-section-title">AI Status</div>', unsafe_allow_html=True)
        status_map = llm_manager.get_provider_status()
        configured = [name for name, status in status_map.items() if status.get("configured")]
        if not configured:
            configured = get_configured_provider_names()

        if configured:
            provider_name = llm_manager.get_active_provider() or llm_manager.get_primary_configured_provider() or configured[0]
            provider_status = status_map.get(provider_name, {})
            is_healthy = provider_status.get("healthy", True) if provider_status else True
            fallback_ready = llm_manager.has_fallback_available() or len(configured) > 1
            st.markdown("🟢 **Active Provider**")
            st.markdown(f"**{provider_name.title()}**")
            st.caption(f"Status: {'Healthy' if is_healthy else 'Unavailable'}")
            st.caption(f"Fallback: {'Ready' if fallback_ready else 'Unavailable'}")
        else:
            st.markdown("🔴 **Not Configured**")
            st.caption("Add at least one API key to your `.env` file.")

        st.markdown('<div class="sidebar-section-title">About</div>', unsafe_allow_html=True)
        with st.expander("About TripMind", expanded=False):
            st.markdown(f"**Version:** {APP_VERSION}")
            st.markdown("**Architecture:** Multi-Agent Orchestrator")
            st.markdown(f"**Agents:** {AGENT_COUNT} specialized AI agents")
            st.markdown(f"**Providers:** {', '.join(PROVIDERS)}")
            st.markdown("**Storage:** SQLite trip history")
            st.caption(
                "Feasibility, research, itinerary, budget, food, packing, safety, and summary agents "
                "collaborate to build your travel dossier."
            )

        st.markdown('<div class="sidebar-section-title">Preferences</div>', unsafe_allow_html=True)
        with st.expander("Preferences", expanded=False):
            st.toggle("Dark Theme", value=True, disabled=True, help="Dark theme is always enabled.")
            st.session_state.compact_view = st.toggle(
                "Compact Mode",
                value=st.session_state.get("compact_view", False),
                key="compact_view_toggle",
            )
            st.session_state.animations_enabled = st.toggle(
                "Animations",
                value=st.session_state.get("animations_enabled", True),
                key="animations_toggle",
            )
            st.session_state.auto_save = st.toggle(
                "Auto Save",
                value=st.session_state.get("auto_save", True),
                disabled=True,
                help="Trips are automatically saved to SQLite after generation.",
                key="auto_save_toggle",
            )


def render_input_panel(
    persona_options: list[str],
    interest_options: list[str],
    accommodation_options: list[str],
    transport_options: list[str],
) -> tuple[str, str, int, int, list[str], str, str, str]:
    st.markdown(
        """
        <div class="page-section">
            <div class="page-section-title">Plan Your Trip</div>
            <div class="page-section-subtitle">Tell us where you're going and we'll handle the rest</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_left, col_right = st.columns([3, 2])

        with col_left:
            destination = st.text_input(
                "Destination",
                key="destination_input",
                placeholder="e.g. Venice, Goa, Tokyo",
                help="Enter a city, region, or country.",
            )
            persona = st.selectbox(
                "Persona",
                persona_options,
                key="persona_input",
                help="Travel style shapes recommendations and pacing.",
            )
            interests = st.multiselect(
                "Interests",
                interest_options,
                key="interests_input",
                help="Select themes to personalize your plan.",
            )
            custom_interests = st.text_input(
                "Additional interests",
                key="custom_interests_input",
                placeholder="Sunrise viewpoints, wine bars, museums...",
            )

        with col_right:
            days = st.number_input(
                "Number of Days",
                min_value=1,
                max_value=30,
                key="days_input",
                step=1,
                help="Trip duration between 1 and 30 days.",
            )
            budget = st.number_input(
                "Budget (₹)",
                min_value=1000,
                max_value=10_000_000,
                key="budget_input",
                step=500,
                help="Total trip budget in Indian Rupees.",
            )
            accommodation = st.selectbox(
                "Accommodation",
                accommodation_options,
                key="accommodation_input",
                help="Preferred lodging style.",
            )
            transportation = st.selectbox(
                "Transportation",
                transport_options,
                key="transportation_input",
                help="How you plan to get around.",
            )

    return destination, persona, int(days), int(budget), interests, custom_interests, accommodation, transportation


def build_progress_callback(progress_bar, stage_container) -> Callable[[str], None]:
    def update_progress(message: str) -> None:
        index = 0
        lowered = message.lower()
        for keyword, idx in STAGE_KEYWORDS.items():
            if keyword in lowered:
                index = idx
                break
        progress_bar.progress((index + 1) / len(WORKFLOW_STAGES))
        lines = []
        for idx, stage in enumerate(WORKFLOW_STAGES):
            if idx < index:
                lines.append(f"✓ {stage}")
            elif idx == index:
                lines.append(f"→ {stage}")
            else:
                lines.append(f"• {stage}")
        stage_container.markdown("\n".join(f"**{line}**" if line.startswith("→") else line for line in lines))

    return update_progress


def render_loading_panel(progress_bar, stage_container) -> None:
    st.markdown("### Building Your Travel Package")
    progress_bar.progress(0.05)
    stage_container.markdown(f"**→ {WORKFLOW_STAGES[0]}**")


def render_success_banner() -> None:
    st.success("🎉 Your Trip Plan is Ready — explore your dossier below or download the PDF.")


def render_error_card(title: str, message: str) -> None:
    st.error(f"**{title}** — {message}")


def render_feasibility_banner(trip_package: TravelPackage) -> None:
    feasibility = trip_package.feasibility
    if feasibility.feasible:
        st.success(f"Feasibility {feasibility.confidence_score}% — this trip looks realistic for your persona.")
    else:
        st.warning(f"Feasibility {feasibility.confidence_score}% — consider adjusting budget or duration.")
        for item in feasibility.issues or []:
            st.caption(f"• {item}")
        for item in feasibility.recommendations or []:
            st.caption(f"→ {item}")


def _split_evening_night(evening_items: list):
    if not evening_items:
        return [], []
    if len(evening_items) == 1:
        return [], evening_items
    return evening_items[:-1], evening_items[-1:]


def _render_activity_card(item, time_label: str) -> None:
    with st.container(border=True):
        st.markdown(f"**{item.activity}**")
        if item.location:
            st.caption(f"📍 {item.location}")
        st.caption(f"⏱ {TIME_DURATIONS.get(time_label, '2–3 hours')}")
        st.caption(f"💡 {TIME_TIPS.get(time_label, 'Plan ahead for the best experience.')}")


def render_itinerary_tab(trip_package: TravelPackage) -> None:
    for day in trip_package.itinerary.days:
        evening, night = _split_evening_night(list(day.evening))
        with st.expander(f"📅 Day {day.day}", expanded=day.day == 1):
            st.markdown(f"##### Day {day.day} Itinerary")
            sections = [
                ("🌅 Morning", day.morning, "Morning"),
                ("☀️ Afternoon", day.afternoon, "Afternoon"),
                ("🌆 Evening", evening, "Evening"),
                ("🌙 Night", night, "Night"),
            ]
            cols = st.columns(4)
            for col, (label, items, time_key) in zip(cols, sections):
                with col:
                    st.markdown(f"**{label}**")
                    if not items:
                        st.caption("Free time / rest")
                    else:
                        for item in items:
                            _render_activity_card(item, time_key)
            st.divider()


def render_budget_tab(trip_package: TravelPackage) -> None:
    budget = trip_package.budget
    categories = [
        ("🏨 Accommodation", "Accommodation", budget.accommodation),
        ("🍽 Food", "Food", budget.food),
        ("🚗 Transport", "Transport", budget.transport),
        ("🎯 Activities", "Activities", budget.activities),
        ("🛡 Emergency Buffer", "Emergency Buffer", budget.emergency_buffer),
    ]
    total = sum(amount for _, _, amount in categories) or 1

    for icon_label, key, amount in categories:
        pct = amount / total
        with st.container(border=True):
            header_col, amount_col = st.columns([3, 1])
            header_col.markdown(f"### {icon_label}")
            amount_col.markdown(f"### ₹{amount:,}")
            st.progress(pct)
            st.caption(f"**{pct * 100:.1f}%** of total budget")
            st.caption(BUDGET_EXPLANATIONS.get(key, ""))

    st.info(budget.allocation_reasoning)


def render_food_tab(trip_package: TravelPackage) -> None:
    food = trip_package.food
    sections = [
        ("⭐ Must Try", food.must_try_foods),
        ("🌮 Street Food", food.street_foods),
        ("🍴 Restaurants", food.recommended_restaurants),
        ("💡 Tips", food.food_tips),
    ]
    c1, c2 = st.columns(2)
    for idx, (title, items) in enumerate(sections):
        with c1 if idx % 2 == 0 else c2:
            with st.expander(title, expanded=True):
                if items:
                    for item in items:
                        with st.container(border=True):
                            st.write(item)
                else:
                    st.caption("No recommendations yet.")


def render_packing_tab(trip_package: TravelPackage) -> None:
    packing = trip_package.packing
    categories = [
        ("📄 Documents", packing.documents),
        ("💻 Electronics", packing.electronics),
        ("🌤 Weather", packing.weather_items),
        ("🎒 Essentials", packing.essentials),
    ]
    cols = st.columns(2)
    for idx, (title, items) in enumerate(categories):
        with cols[idx % 2]:
            with st.expander(title, expanded=True):
                for i, item in enumerate(items):
                    st.checkbox(item, value=False, disabled=True, key=f"pack_{idx}_{i}_{hash(item) % 10000}")


def render_safety_tab(trip_package: TravelPackage) -> None:
    safety = trip_package.safety
    c1, c2 = st.columns(2)
    with c1:
        with st.expander("🛡 Travel Tips", expanded=True):
            for tip in safety.travel_tips:
                with st.container(border=True):
                    st.write(tip)
        with st.expander("🤝 Local Etiquette", expanded=True):
            for item in safety.local_etiquette:
                with st.container(border=True):
                    st.write(item)
    with c2:
        with st.expander("⚠ Warnings", expanded=True):
            for warn in safety.warnings:
                st.warning(warn)
        with st.expander("📞 Emergency Contacts", expanded=True):
            for contact in safety.emergency_contacts:
                with st.container(border=True):
                    st.write(contact)


def render_insights_section(trip_package: TravelPackage) -> None:
    insights = trip_package.summary.ai_insights
    groups = [
        ("💰 Money Saving", insights.money_saving_tips),
        ("💎 Hidden Gem", insights.hidden_gems),
        ("⭐ Best Experience", insights.best_experiences),
        ("🚫 Avoid", insights.avoid),
        ("🔮 Local Secret", insights.local_secrets),
    ]
    c1, c2 = st.columns(2)
    for idx, (title, items) in enumerate(groups):
        with c1 if idx % 2 == 0 else c2:
            for item in items[:3]:
                with st.container(border=True):
                    st.markdown(f"**{title}**")
                    st.write(item)


def render_action_buttons(
    request: TravelRequest,
    trip_package: TravelPackage,
    pdf_exporter: TravelDossierExporter,
) -> None:
    btn1, btn2, btn3, btn4 = st.columns(4)
    try:
        pdf_bytes = pdf_exporter.export(request, trip_package)
        btn1.download_button(
            "⬇ Download Travel Dossier",
            data=pdf_bytes,
            file_name=f"tripmind-{request.destination.lower().replace(' ', '-')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
        )
    except Exception:
        btn1.error("PDF unavailable")

    if btn2.button("💾 Save Trip", use_container_width=True):
        st.session_state.save_message = "Trip is already saved in your history."

    if btn3.button("➕ Generate Another Trip", use_container_width=True):
        st.session_state.show_results = False
        st.session_state.fresh_generation = False
        st.session_state.current_trip = None
        st.session_state.current_request = None
        st.rerun()

    if btn4.button("📂 Open Previous Trip", use_container_width=True):
        st.info("Browse saved trips in the sidebar on the left.")


def render_trip_results(
    trip_package: TravelPackage,
    request: TravelRequest,
    pdf_exporter: TravelDossierExporter,
    show_success: bool = False,
) -> None:
    st.markdown(
        """
        <div class="page-section">
            <div class="page-section-title">Trip Results</div>
            <div class="page-section-subtitle">Your complete travel intelligence package</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if show_success:
        render_success_banner()

    render_feasibility_banner(trip_package)

    if show_success:
        render_action_buttons(request, trip_package, pdf_exporter)

    tabs = st.tabs(["📋 Summary", "🗓 Itinerary", "💰 Budget", "🍽 Food", "🎒 Packing", "🛡 Safety"])

    with tabs[0]:
        with st.expander("Executive Summary", expanded=True):
            st.write(trip_package.summary.overall_summary)
            if trip_package.summary.highlights:
                st.markdown("**Highlights**")
                for item in trip_package.summary.highlights:
                    st.markdown(f"- {item}")

        with st.expander("AI Insights", expanded=True):
            render_insights_section(trip_package)

        with st.expander("Destination Intelligence", expanded=False):
            st.write(trip_package.research.destination_overview)
            st.caption(f"Best time to visit: {trip_package.research.best_time_to_visit}")
            for area in trip_package.research.popular_areas:
                st.caption(f"📍 {area}")

        if not show_success:
            try:
                pdf_bytes = pdf_exporter.export(request, trip_package)
                st.download_button(
                    "⬇ Download Travel Dossier",
                    data=pdf_bytes,
                    file_name=f"tripmind-{request.destination.lower().replace(' ', '-')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )
            except Exception:
                st.error("Travel dossier export failed. Please try again.")

    with tabs[1]:
        render_itinerary_tab(trip_package)
    with tabs[2]:
        render_budget_tab(trip_package)
    with tabs[3]:
        render_food_tab(trip_package)
    with tabs[4]:
        render_packing_tab(trip_package)
    with tabs[5]:
        render_safety_tab(trip_package)
