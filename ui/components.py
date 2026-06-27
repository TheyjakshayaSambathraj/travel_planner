"""
components.py
-------------
All Streamlit UI components for TripMind AI.
Includes: custom navigation, saved-trips panel, destination hero image,
smart budget intelligence, destination info card, dashboard, trip results.

v2.1 – Production fixes:
  * Removed duplicate render_saved_trips_panel call from render_custom_nav
  * Added unique key= to every button and download_button
  * Removed dead code (to_dest, unused imports)
  * Added origin_city field to input panel
  * Fixed download button ID conflicts
"""
from __future__ import annotations

import html
from typing import Callable, Optional

import streamlit as st

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest
from services.destination_intel import (
    analyze_budget_feasibility,
    fetch_wikipedia_data,
)
from services.hotel_estimator import estimate_hotel_cost
from services.llm.llm_manager import LLMManager
from services.pdf_exporter import TravelDossierExporter
from services.trip_history_db import TripHistoryDB
from ui.theme import APP_VERSION
from utils.env_bootstrap import get_configured_provider_names
from utils.trip_helpers import extract_trip_score, parse_trip_record


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

NAV_ITEMS = [
    ("🏠", "New Trip", "new_trip"),
    ("📂", "Saved Trips", "saved_trips"),
    ("📊", "Dashboard", "dashboard"),
    ("⬇", "Downloads", "downloads"),
    ("⚙", "Settings", "settings"),
    ("ℹ", "About", "about"),
]


def _esc(text: str) -> str:
    return html.escape(str(text))


# ---------------------------------------------------------------------------
# Dashboard metric updater
# ---------------------------------------------------------------------------

def update_dashboard_metrics(
    request: Optional[TravelRequest] = None,
    trip_package: Optional[TravelPackage] = None,
) -> None:
    """Central function — call after every action to keep metrics fresh."""
    st.session_state["_dashboard_request"] = request
    st.session_state["_dashboard_trip"] = trip_package


# ---------------------------------------------------------------------------
# Custom Navigation Panel
# ---------------------------------------------------------------------------

def render_custom_nav(history_db: TripHistoryDB, llm_manager: LLMManager) -> None:
    """Render the top navbar with hamburger + custom slide-in nav panel."""

    # Provider status
    status_map = llm_manager.get_provider_status()
    configured = [n for n, s in status_map.items() if s.get("configured")]
    if not configured:
        configured = get_configured_provider_names()
    provider_name = (
        llm_manager.get_active_provider()
        or llm_manager.get_primary_configured_provider()
        or (configured[0] if configured else "—")
    )

    active_page = st.session_state.get("active_page", "new_trip")

    # ── Top navbar ──────────────────────────────────────────────────────────
    st.markdown(
        '<div class="tm-topbar" id="tm-topbar">'
        '<button class="tm-hamburger" onclick="toggleNav()" title="Toggle Navigation">&#9776;</button>'
        '<div class="tm-topbar-brand">&#9992;&#65039; TripMind AI</div>'
        '<div class="tm-topbar-actions">'
        '<span style="font-size:0.78rem;color:var(--text-muted);">'
        f'<span style="color:#10b981;">&#9679;</span> {_esc(provider_name.title())}'
        '</span>'
        '</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    # ── Nav panel items ──────────────────────────────────────────────────────
    nav_items_html = ""
    for icon, label, page_key in NAV_ITEMS:
        active_cls = "active" if active_page == page_key else ""
        nav_items_html += (
            f'<div class="tm-nav-item {active_cls}" onclick="navigateTo(\'{page_key}\')" id="nav-{page_key}">'
            f'<span class="tm-nav-item-icon">{icon}</span>'
            f'<span>{label}</span>'
            '</div>'
        )

    nav_html = (
        '<div class="tm-nav-overlay" id="tm-nav-overlay" onclick="closeNav()"></div>'
        '<div class="tm-nav" id="tm-nav">'
        '<div class="tm-nav-header">'
        '<div class="tm-nav-brand">&#9992;&#65039; TripMind</div>'
        '<button class="tm-nav-close" onclick="closeNav()">&#10005;</button>'
        '</div>'
        '<div style="padding: 0.5rem 0; overflow-y: auto; flex: 1;">'
        '<div class="tm-nav-section">Navigation</div>'
        f'{nav_items_html}'
        '</div>'
        '<div class="tm-nav-footer">'
        '<div class="tm-nav-status">'
        '<div class="tm-status-dot"></div>'
        f'<span>{_esc(provider_name.title())} &middot; v{APP_VERSION}</span>'
        '</div>'
        '</div>'
        '</div>'
        '<script>'
        '(function() {'
        '    function toggleNav() {'
        '        var nav = document.getElementById("tm-nav");'
        '        var overlay = document.getElementById("tm-nav-overlay");'
        '        if (!nav || !overlay) return;'
        '        var isOpen = nav.classList.contains("open");'
        '        if (isOpen) {'
        '            nav.classList.remove("open");'
        '            overlay.classList.remove("visible");'
        '        } else {'
        '            nav.classList.add("open");'
        '            overlay.classList.add("visible");'
        '        }'
        '    }'
        '    function closeNav() {'
        '        var nav = document.getElementById("tm-nav");'
        '        var overlay = document.getElementById("tm-nav-overlay");'
        '        if (nav) nav.classList.remove("open");'
        '        if (overlay) overlay.classList.remove("visible");'
        '    }'
        '    function navigateTo(page) {'
        '        closeNav();'
        '    }'
        '    window.toggleNav = toggleNav;'
        '    window.closeNav = closeNav;'
        '    window.navigateTo = navigateTo;'
        '})();'
        '</script>'
    )
    st.markdown(nav_html, unsafe_allow_html=True)
    # NOTE: render_saved_trips_panel is NOT called here — it is called from app.py only.


# ---------------------------------------------------------------------------
# Saved Trips Panel (inline, shown when toggled from the action bar)
# ---------------------------------------------------------------------------

def render_saved_trips_panel(history_db: TripHistoryDB) -> None:
    """Render the saved trips panel as an expandable inline section."""
    with st.container():
        st.markdown(
            '<div class="page-section">'
            '<div class="page-section-title">&#128194; Saved Trips</div>'
            '<div class="page-section-subtitle">Browse, open, or manage your trip history</div>'
            '</div>',
            unsafe_allow_html=True,
        )

        col_search, col_close = st.columns([4, 1])
        with col_search:
            search_query = st.text_input(
                "Search trips",
                placeholder="🔍 Search destination or persona...",
                key="saved_trips_search",
                label_visibility="collapsed",
            )
        with col_close:
            if st.button("✕ Close", key="btn_close_saved_trips", use_container_width=True):
                st.session_state["show_saved_trips_panel"] = False
                st.rerun()

        trips = (
            history_db.search_trips(search_query.strip(), limit=50)
            if search_query and search_query.strip()
            else history_db.list_recent_trips(limit=50)
        )

        if not trips:
            st.markdown(
                '<div style="text-align:center;padding:3rem;color:var(--text-muted);">'
                '<div style="font-size:2.5rem;margin-bottom:0.75rem;">&#128506;&#65039;</div>'
                '<div style="font-weight:600;">No saved trips yet</div>'
                '<div style="font-size:0.85rem;margin-top:0.3rem;">Generate a trip to build your history.</div>'
                '</div>',
                unsafe_allow_html=True,
            )
        else:
            st.caption(f"Showing {len(trips)} trip{'s' if len(trips) != 1 else ''} · sorted by newest")
            for trip in trips:
                created_at = trip.get("created_at", "")
                date_label = created_at[:10] if created_at else "Unknown date"
                score = extract_trip_score(trip)
                tid = trip["trip_id"]
                dest = trip.get("destination", "Trip")
                persona = trip.get("persona", "")
                duration = trip.get("duration", "")

                with st.container(border=True):
                    h_col, s_col = st.columns([5, 1])
                    with h_col:
                        st.markdown(f"**{_esc(dest)}**")
                        st.caption(
                            f"📅 {date_label}  ·  👤 {_esc(persona)}  ·  🗓 {duration} days"
                        )
                    with s_col:
                        if score != "—":
                            st.markdown(
                                f"<div style='text-align:right;font-size:0.85rem;font-weight:700;"
                                f"color:var(--blue-light);margin-top:0.25rem;'>⭐ {score}</div>",
                                unsafe_allow_html=True,
                            )

                    c1, c2, c3 = st.columns(3)
                    if c1.button(
                        "📂 Open", key=f"btn_open_{tid}", use_container_width=True, type="primary"
                    ):
                        record = history_db.load_trip(tid)
                        if record:
                            req, pkg = parse_trip_record(record)
                            st.session_state.loaded_trip_id = tid
                            st.session_state.show_results = True
                            st.session_state.fresh_generation = False
                            st.session_state.current_request = req
                            st.session_state.current_trip = pkg
                            update_dashboard_metrics(req, pkg)
                        st.session_state["show_saved_trips_panel"] = False
                        st.rerun()
                    if c2.button(
                        "⧉ Duplicate", key=f"btn_dup_{tid}", use_container_width=True
                    ):
                        new_id = history_db.duplicate_trip(tid)
                        st.session_state.save_message = (
                            "Trip duplicated." if new_id else "Could not duplicate."
                        )
                        st.rerun()
                    if c3.button(
                        "🗑 Delete", key=f"btn_del_{tid}", use_container_width=True
                    ):
                        history_db.delete_trip(tid)
                        if st.session_state.get("loaded_trip_id") == tid:
                            st.session_state.loaded_trip_id = None
                            st.session_state.current_request = None
                            st.session_state.current_trip = None
                            st.session_state.show_results = False
                            update_dashboard_metrics()
                        st.session_state.save_message = "Trip deleted."
                        st.rerun()

        st.markdown('<hr class="divider-line">', unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Destination Hero Image
# ---------------------------------------------------------------------------

def render_destination_hero(
    destination: str,
    country: str = "",
    days: int = 0,
    score: str = "—",
    wiki_data: Optional[dict] = None,
) -> None:
    """Display hero banner with destination image (Wikipedia) or gradient fallback."""
    image_url = wiki_data.get("image_url") if wiki_data else None
    desc = wiki_data.get("description", "") if wiki_data else ""
    country = country or (wiki_data.get("country", "") if wiki_data else "")

    meta_html = ""
    if country:
        meta_html += f'<span class="dest-hero-badge">📍 {_esc(country)}</span>'
    if days:
        meta_html += f'<span class="dest-hero-badge">🗓 {days} days</span>'
    if score and score != "—":
        meta_html += f'<span class="dest-hero-score">⭐ {_esc(score)}</span>'

    if image_url:
        _desc_html = f'<div style="font-size:0.9rem;color:rgba(255,255,255,0.65);margin-top:0.3rem;">{_esc(desc)}</div>' if desc else ''
        st.markdown(
            '<div class="dest-hero-banner">'
            f'<img class="dest-hero-img" src="{_esc(image_url)}" alt="{_esc(destination)}" />'
            '<div class="dest-hero-overlay"></div>'
            '<div class="dest-hero-content">'
            '<div>'
            f'<div class="dest-hero-title">{_esc(destination)}</div>'
            f'{_desc_html}'
            '</div>'
            '<div class="dest-hero-meta">'
            f'{meta_html}'
            '</div>'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )
    else:
        _sub_html = f'<div class="dest-hero-fallback-sub">{_esc(desc or country)}</div>' if (desc or country) else ''
        st.markdown(
            '<div class="dest-hero-fallback">'
            '<div class="dest-hero-fallback-icon">&#127757;</div>'
            f'<div class="dest-hero-fallback-title">{_esc(destination)}</div>'
            f'{_sub_html}'
            '<div style="position:absolute;bottom:1.5rem;right:1.5rem;display:flex;gap:0.5rem;">'
            f'{meta_html}'
            '</div>'
            '</div>',
            unsafe_allow_html=True,
        )


# ---------------------------------------------------------------------------
# Destination Info Card
# ---------------------------------------------------------------------------

def render_destination_info_card(wiki_data: dict) -> None:
    """Show country, currency, language, timezone, visa, description as a grid."""
    items = []
    if wiki_data.get("country"):
        items.append(("🌍 Country", wiki_data["country"]))
    if wiki_data.get("currency"):
        symbol = wiki_data.get("currency_symbol", "")
        items.append(("💰 Currency", f"{wiki_data['currency']} {symbol}".strip()))
    if wiki_data.get("language"):
        items.append(("🗣 Language", wiki_data["language"]))
    if wiki_data.get("timezone"):
        items.append(("⏰ Timezone", wiki_data["timezone"]))
    if wiki_data.get("visa_hint"):
        items.append(("🛂 Visa", wiki_data["visa_hint"]))
    if wiki_data.get("description"):
        items.append(("📝 About", wiki_data["description"]))

    if not items:
        return

    items_html = ""
    for label, value in items:
        items_html += (
            '<div class="dest-info-item">'
            f'<div class="dest-info-label">{_esc(label)}</div>'
            f'<div class="dest-info-value">{_esc(str(value))}</div>'
            '</div>'
        )

    _card_html = (
        '<div class="dest-info-card">'
        '<div style="font-size:0.85rem;font-weight:700;color:var(--text-muted);'
        'text-transform:uppercase;letter-spacing:0.07em;margin-bottom:1rem;">'
        'Destination Intelligence'
        '</div>'
        f'<div class="dest-info-grid">{items_html}</div>'
        '</div>'
    )
    st.markdown(_card_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Smart Budget Intelligence
# ---------------------------------------------------------------------------

def render_smart_budget(request: TravelRequest, trip_package: Optional[TravelPackage] = None) -> None:
    """Show budget intelligence panel with exchange rates and feasibility."""

    origin = st.session_state.get("origin_city_input", "").strip() or "Chennai"
    cache_key = f"_budget_intel_{request.destination}_{request.budget}_{request.days}_{origin}"
    if cache_key not in st.session_state:
        with st.spinner("Analyzing budget feasibility…"):
            analysis = analyze_budget_feasibility(
                request.budget, request.destination, request.days, origin=origin
            )
            acc_type = "Any"
            for interest in request.interests:
                if interest.startswith("Accommodation:"):
                    acc_type = interest.split(":")[1].strip()
                    break
            hotel = estimate_hotel_cost(
                request.destination, request.days, request.persona,
                acc_type, analysis["tier"]
            )
            st.session_state[cache_key] = (analysis, hotel)
    else:
        analysis, hotel = st.session_state[cache_key]

    dest_sym = analysis["dest_symbol"]
    dest_cur = analysis["dest_currency"]
    rate = analysis["rate"]
    items = analysis["items"]
    label = analysis["budget_label"]

    badge_cls_map = {
        "Comfortable": "comfortable",
        "Adequate": "adequate",
        "Tight": "tight",
        "Insufficient": "critical",
    }
    badge_cls = badge_cls_map.get(label, "adequate")

    converted = analysis["converted_budget"]
    conv_display = f"{dest_sym}{converted:,.0f}" if dest_cur != "INR" else "—"

    exchange_source_label = analysis.get("exchange_source_label", "Fallback rates")
    flight_label_badge = (
        '<span style="font-size:0.65rem;background:rgba(16,185,129,0.15);'
        'color:#10b981;border-radius:4px;padding:1px 5px;margin-left:4px;'
        'font-weight:600;">LIVE</span>'
        if analysis.get("flight_source") == "amadeus"
        else '<span style="font-size:0.65rem;background:rgba(148,163,184,0.12);'
        'color:var(--text-muted);border-radius:4px;padding:1px 5px;margin-left:4px;">EST.</span>'
    )
    exchange_badge = (
        '<span style="font-size:0.65rem;background:rgba(16,185,129,0.15);'
        'color:#10b981;border-radius:4px;padding:1px 5px;margin-left:4px;font-weight:600;">LIVE</span>'
        if analysis.get("rate_source") == "live"
        else '<span style="font-size:0.65rem;background:rgba(148,163,184,0.12);'
        'color:var(--text-muted);border-radius:4px;padding:1px 5px;margin-left:4px;">CACHED</span>'
    )

    flight_inr = items.get("flight_estimate_inr", 0)
    hotel_inr = hotel["total_inr"]
    food_inr = items.get("food_estimate_inr", 0)
    act_inr = items.get("activities_estimate_inr", 0)
    transport_inr = items.get("transport_local_inr", 0)
    emergency_inr = items.get("emergency_buffer_inr", 0)

    budget_items = [
        (f"✈️ Flights (RT){flight_label_badge}", f"₹{flight_inr:,.0f}", analysis["flight_note"]),
        ("🏨 Hotel", f"₹{hotel_inr:,.0f}", hotel["tier_label"]),
        ("🍽 Food", f"₹{food_inr:,.0f}", f"{request.days} days"),
        ("🎯 Activities", f"₹{act_inr:,.0f}", "Tours & experiences"),
        ("🚗 Local Transport", f"₹{transport_inr:,.0f}", "Within destination"),
        ("🛡 Emergency", f"₹{emergency_inr:,.0f}", "5% safety buffer"),
    ]

    items_html = ""
    for item_label, item_amount, item_note in budget_items:
        items_html += (
            '<div class="budget-item">'
            f'<div class="budget-item-label">{item_label}</div>'
            f'<div class="budget-item-amount">{_esc(item_amount)}</div>'
            f'<div class="budget-item-note">{_esc(item_note)}</div>'
            '</div>'
        )

    min_inr = analysis["min_total_inr"]
    rec_min = analysis["recommended_min_inr"]
    rec_max = analysis["recommended_max_inr"]

    if not analysis["is_feasible"]:
        alert_cls = "budget-alert-warning"
        shortfall = analysis["shortfall_inr"]
        alert_title = _esc(f"⚠️ Budget Alert — ₹{request.budget:,} INR may be insufficient")
        reasons_html = "".join(
            f'<div class="budget-reason">{_esc(r)}</div>' for r in analysis["reasons"]
        )
        alert_body = (
            f'<div style="margin-bottom:0.5rem;">Estimated minimum: '
            f'<strong>₹{rec_min:,.0f} – ₹{rec_max:,.0f} INR</strong></div>'
            f'<div style="margin-bottom:0.3rem;color:var(--text-muted);font-size:0.8rem;">'
            f'Shortfall: ₹{shortfall:,.0f}</div>'
            f'{reasons_html}'
        )
    elif label == "Tight":
        alert_cls = "budget-alert-tight"
        alert_title = _esc(f"⚡ Budget is tight for {request.days} days in {request.destination}")
        alert_body = "Budget covers the basics but leaves little room for flexibility or unexpected expenses."
    else:
        alert_cls = "budget-alert-success"
        word = "comfortable" if label == "Comfortable" else "adequate"
        alert_title = _esc(f"✅ Budget looks {word} for this trip")
        alert_body = _esc(f"Estimated cost ₹{min_inr:,.0f} is within your budget of ₹{request.budget:,}.")

    conv_row_html = ""
    if dest_cur != "INR":
        conv_row_html = (
            '<div class="budget-conversion-row">'
            '<div class="budget-currency-block">'
            '<div class="budget-currency-label">Your Budget</div>'
            f'<div class="budget-currency-amount">&#8377;{request.budget:,}</div>'
            '<div class="budget-currency-code">INR</div>'
            '</div>'
            '<div class="budget-arrow">&rarr;</div>'
            '<div class="budget-currency-block">'
            '<div class="budget-currency-label">Converted</div>'
            f'<div class="budget-currency-amount">{_esc(conv_display)}</div>'
            f'<div class="budget-currency-code">{_esc(dest_cur)} &middot; Rate: 1 INR = {_esc(dest_sym)}{rate:.4f}</div>'
            '</div>'
            '</div>'
        )

    origin_note = (
        f"Flight estimate from {_esc(origin)} to {_esc(request.destination)}"
        if origin else ""
    )
    _breakdown_suffix = ""
    if origin_note:
        _breakdown_suffix += (
            f'<span style="font-weight:400;text-transform:none;letter-spacing:0;'
            f'margin-left:0.5rem;color:var(--text-muted);">&middot; {origin_note}</span>'
        )
    _breakdown_suffix += exchange_badge

    _card_html = (
        '<div class="budget-intel-card">'
        '<div class="budget-header">'
        '<div class="budget-title">&#x1F4A1; Budget Intelligence</div>'
        f'<div class="budget-badge {badge_cls}">{_esc(label)}</div>'
        '</div>'
        + conv_row_html
        + '<div style="font-size:0.78rem;font-weight:700;text-transform:uppercase;'
        'letter-spacing:0.07em;color:var(--text-muted);margin-bottom:0.75rem;">'
        f'Estimated Cost Breakdown {_breakdown_suffix}'
        '</div>'
        f'<div class="budget-items-grid">{items_html}</div>'
        f'<div class="{alert_cls}">'
        f'<div class="budget-alert-title">{alert_title}</div>'
        f'<div class="budget-alert-body">{alert_body}</div>'
        '</div>'
        '</div>'
    )
    st.markdown(_card_html, unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Hero Section
# ---------------------------------------------------------------------------

def render_hero_section() -> None:
    badges = [
        "Multi-Agent",
        "AI Research",
        "Budget Optimizer",
        "PDF Export",
        "Trip History",
        "Provider Failover",
        "Live Exchange Rates",
        "Wikipedia Intel",
    ]
    badge_html = "".join(f'<span class="feature-badge">✓ {_esc(b)}</span>' for b in badges)
    st.markdown(
        '<div class="hero-container page-section">'
        '<div class="hero-title">&#9992;&#65039; TripMind AI</div>'
        '<div class="hero-subtitle">Plan an Entire Trip in Under 30 Seconds</div>'
        '<div class="hero-tagline">Multi-Agent AI Travel Intelligence Platform &middot; Real-Time Budget Analysis &middot; Live Destination Data</div>'
        f'<div class="badge-row">{badge_html}</div>'
        '</div>',
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Persistent Dashboard
# ---------------------------------------------------------------------------

def render_persistent_dashboard(
    request: Optional[TravelRequest],
    trip_package: Optional[TravelPackage],
) -> None:
    st.markdown(
        '<div class="dashboard-panel page-section">'
        '<div class="page-section-title">&#128202; Trip Dashboard</div>'
        '<div class="page-section-subtitle">Live metrics &mdash; updated after every action</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    row1 = st.columns(4)
    row2 = st.columns(4)

    dash_req = st.session_state.get("_dashboard_request") or request
    dash_pkg = st.session_state.get("_dashboard_trip") or trip_package

    if dash_req and dash_pkg:
        intelligence = dash_pkg.summary.trip_intelligence
        analytics = dash_pkg.summary.analytics_summary
        metrics = [
            ("Trip Score", f"{intelligence.trip_score}/100"),
            ("Budget Fit", f"{intelligence.budget_fit}/100"),
            ("Estimated Cost", f"₹{analytics.estimated_total_cost:,}"),
            ("Difficulty", f"{analytics.difficulty_score}/100"),
            ("Duration", f"{dash_req.days} days"),
            ("Persona", dash_req.persona),
            ("Destination", dash_req.destination),
            ("Trip Type", dash_pkg.summary.trip_type),
        ]
    else:
        destination_label = st.session_state.get("destination_input") or "—"
        persona_label = st.session_state.get("persona_input") or "—"
        days_val = st.session_state.get("days_input")
        days_label = f"{days_val} days" if days_val else "—"
        budget_val = st.session_state.get("budget_input")
        budget_label = f"₹{budget_val:,}" if budget_val else "—"
        metrics = [
            ("Trip Score", "—"),
            ("Budget Fit", "—"),
            ("Estimated Cost", "—"),
            ("Difficulty", "—"),
            ("Duration", days_label),
            ("Persona", persona_label),
            ("Destination", destination_label),
            ("Budget", budget_label),
        ]

    for col, (label, value) in zip(row1 + row2, metrics):
        col.metric(label, value)

    if not dash_pkg:
        st.caption("Fill in your trip details below and generate to populate live metrics.")


# ---------------------------------------------------------------------------
# Input Panel  (includes origin city for flight estimation)
# ---------------------------------------------------------------------------

def render_input_panel(
    persona_options: list[str],
    interest_options: list[str],
    accommodation_options: list[str],
    transport_options: list[str],
) -> tuple:
    st.markdown(
        """
        <div class="page-section">
            <div class="page-section-title">🗺 Plan Your Trip</div>
            <div class="page-section-subtitle">Tell us where you're going and we'll handle the rest</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.container(border=True):
        col_left, col_right = st.columns([3, 2])

        with col_left:
            origin_city = st.text_input(
                "From City (Origin)",
                key="origin_city_input",
                placeholder="e.g. Chennai, Mumbai, Delhi",
                help="Your departure city — used for flight cost estimation.",
            )
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
                "Budget (₹ INR)",
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

    return (
        destination,
        persona,
        int(days),
        int(budget),
        interests,
        custom_interests,
        accommodation,
        transportation,
        origin_city,
    )


# ---------------------------------------------------------------------------
# Progress / Loading
# ---------------------------------------------------------------------------

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
        stage_container.markdown(
            "\n".join(f"**{line}**" if line.startswith("→") else line for line in lines)
        )

    return update_progress


def render_loading_panel(progress_bar, stage_container) -> None:
    st.markdown("### 🧳 Building Your Travel Package")
    progress_bar.progress(0.05)
    stage_container.markdown(f"**→ {WORKFLOW_STAGES[0]}**")


# ---------------------------------------------------------------------------
# Banners
# ---------------------------------------------------------------------------

def render_success_banner() -> None:
    st.success("🎉 Your Trip Plan is Ready — explore your dossier below or download the PDF.")


def render_error_card(title: str, message: str) -> None:
    st.error(f"**{title}** — {message}")


def render_feasibility_banner(trip_package: TravelPackage) -> None:
    feasibility = trip_package.feasibility
    if feasibility.feasible:
        st.success(
            f"✅ Feasibility {feasibility.confidence_score}% — this trip looks realistic for your persona."
        )
    else:
        st.warning(
            f"⚠️ Feasibility {feasibility.confidence_score}% — consider adjusting budget or duration."
        )
        for item in feasibility.issues or []:
            st.caption(f"• {item}")
        for item in feasibility.recommendations or []:
            st.caption(f"→ {item}")


# ---------------------------------------------------------------------------
# Itinerary / Budget / Food / Packing / Safety tabs
# ---------------------------------------------------------------------------

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
                    st.checkbox(
                        item,
                        value=False,
                        disabled=True,
                        key=f"pack_{idx}_{i}_{hash(item) % 100000}",
                    )


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


# ---------------------------------------------------------------------------
# Action Buttons row (shown at top of trip results when fresh generation)
# ---------------------------------------------------------------------------

def render_action_buttons(
    request: TravelRequest,
    trip_package: TravelPackage,
    pdf_exporter: TravelDossierExporter,
    button_suffix: str = "top",
) -> None:
    """Render action buttons. button_suffix ensures unique keys per call site."""
    btn1, btn2, btn3, btn4 = st.columns(4)

    wiki_cache_key = f"_wiki_{request.destination}"
    wiki_data = st.session_state.get(wiki_cache_key)
    _origin = st.session_state.get("origin_city_input", "").strip() or "Chennai"
    budget_cache_key = f"_budget_intel_{request.destination}_{request.budget}_{request.days}_{_origin}"
    budget_intel = st.session_state.get(budget_cache_key)

    try:
        pdf_bytes = pdf_exporter.export(
            request, trip_package,
            wiki_data=wiki_data,
            budget_intel=budget_intel[0] if budget_intel else None,
            hotel_data=budget_intel[1] if budget_intel else None,
        )
        btn1.download_button(
            "⬇ Download Dossier",
            data=pdf_bytes,
            file_name=f"tripmind-{request.destination.lower().replace(' ', '-')}.pdf",
            mime="application/pdf",
            use_container_width=True,
            type="primary",
            key=f"btn_download_pdf_{button_suffix}",
        )
    except Exception:
        btn1.error("PDF unavailable")

    if btn2.button("💾 Save Trip", use_container_width=True, key=f"btn_save_{button_suffix}"):
        st.session_state.save_message = "Trip is already saved in your history."

    if btn3.button("➕ New Trip", use_container_width=True, type="primary", key=f"btn_new_{button_suffix}"):
        _reset_session_state()
        st.rerun()

    if btn4.button("📂 Saved Trips", use_container_width=True, key=f"btn_saved_{button_suffix}"):
        st.session_state["show_saved_trips_panel"] = True
        st.rerun()


def _reset_session_state() -> None:
    """Clear all trip state and return to planning page."""
    keys_to_clear = [
        "current_request", "current_trip", "loaded_trip_id",
        "show_results", "fresh_generation", "save_message",
        "show_saved_trips_panel", "_dashboard_request", "_dashboard_trip",
        "active_page",
    ]
    for key in keys_to_clear:
        st.session_state.pop(key, None)
    for key in list(st.session_state.keys()):
        if key.startswith("_budget_intel_") or key.startswith("_wiki_"):
            st.session_state.pop(key, None)
    st.session_state["destination_input"] = ""
    st.session_state["origin_city_input"] = ""
    st.session_state["show_results"] = False
    update_dashboard_metrics()


# ---------------------------------------------------------------------------
# Trip Results (main renderer)
# ---------------------------------------------------------------------------

def render_trip_results(
    trip_package: TravelPackage,
    request: TravelRequest,
    pdf_exporter: TravelDossierExporter,
    show_success: bool = False,
) -> None:
    # ── Wikipedia data (cached per destination) ─────────────────────────────
    wiki_cache_key = f"_wiki_{request.destination}"
    if wiki_cache_key not in st.session_state:
        with st.spinner("Fetching destination data…"):
            wiki_data = fetch_wikipedia_data(request.destination)
            st.session_state[wiki_cache_key] = wiki_data
    wiki_data = st.session_state[wiki_cache_key]

    # ── Destination Hero Banner ─────────────────────────────────────────────
    intelligence = trip_package.summary.trip_intelligence
    score_str = f"{intelligence.trip_score}/100"
    render_destination_hero(
        destination=request.destination,
        country=wiki_data.get("country", ""),
        days=request.days,
        score=score_str,
        wiki_data=wiki_data,
    )

    # ── Destination Info Card ───────────────────────────────────────────────
    render_destination_info_card(wiki_data)

    # ── Section header ──────────────────────────────────────────────────────
    st.markdown(
        '<div class="page-section">'
        '<div class="page-section-title">&#127919; Trip Results</div>'
        '<div class="page-section-subtitle">Your complete travel intelligence package</div>'
        '</div>',
        unsafe_allow_html=True,
    )

    if show_success:
        render_success_banner()

    render_feasibility_banner(trip_package)

    # ── Smart Budget Intelligence ───────────────────────────────────────────
    render_smart_budget(request, trip_package)

    # ── Action buttons (fresh generation only) ──────────────────────────────
    if show_success:
        render_action_buttons(request, trip_package, pdf_exporter, button_suffix="top")

    # ── Tabs ────────────────────────────────────────────────────────────────
    tabs = st.tabs(["📋 Summary", "🗓 Itinerary", "💰 Budget", "🍽 Food", "🎒 Packing", "🛡 Safety"])

    with tabs[0]:
        with st.expander("Executive Summary", expanded=True):
            st.markdown(trip_package.summary.overall_summary)
            if trip_package.summary.highlights:
                st.markdown("**Highlights**")
                for item in trip_package.summary.highlights:
                    st.markdown(f"- {item}")

        with st.expander("AI Insights", expanded=True):
            render_insights_section(trip_package)

        with st.expander("Destination Intelligence", expanded=False):
            st.markdown(trip_package.research.destination_overview)
            st.caption(f"Best time to visit: {trip_package.research.best_time_to_visit}")
            for area in trip_package.research.popular_areas:
                st.caption(f"📍 {area}")

        # Download button — only when NOT a fresh generation (i.e., viewing saved trip)
        if not show_success:
            wiki_d = st.session_state.get(wiki_cache_key)
            _origin = st.session_state.get("origin_city_input", "").strip() or "Chennai"
            budget_cache_key2 = (
                f"_budget_intel_{request.destination}_{request.budget}_{request.days}_{_origin}"
            )
            budget_i = st.session_state.get(budget_cache_key2)
            try:
                pdf_bytes = pdf_exporter.export(
                    request, trip_package,
                    wiki_data=wiki_d,
                    budget_intel=budget_i[0] if budget_i else None,
                    hotel_data=budget_i[1] if budget_i else None,
                )
                st.download_button(
                    "⬇ Download Travel Dossier",
                    data=pdf_bytes,
                    file_name=f"tripmind-{request.destination.lower().replace(' ', '-')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                    key="btn_download_pdf_summary_tab",
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


# ---------------------------------------------------------------------------
# Sidebar (legacy shim — kept for backward compat)
# ---------------------------------------------------------------------------

def render_sidebar(history_db: TripHistoryDB, llm_manager: LLMManager) -> None:
    """Legacy shim — calls render_custom_nav."""
    render_custom_nav(history_db, llm_manager)
