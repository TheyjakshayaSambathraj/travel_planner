from __future__ import annotations

import streamlit as st

from models.travel_request import TravelRequest
from orchestrator.travel_orchestrator import TravelOrchestrator
from utils.validators import ValidationError, build_travel_request, sanitize_interests


st.set_page_config(
    page_title="TripMind AI",
    page_icon="✈️",
    layout="wide",
    initial_sidebar_state="collapsed",
)


def initialize_session_state() -> None:
    if "orchestrator" not in st.session_state:
        st.session_state.orchestrator = TravelOrchestrator()


def render_section_header() -> None:
    st.title("TripMind AI")
    st.caption("AI-Powered Personalized Travel Planning")


def render_summary_card(request: TravelRequest) -> None:
    with st.container(border=True):
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Destination", request.destination)
        col2.metric("Days", request.days)
        col3.metric("Budget", f"₹{request.budget:,}")
        col4.metric("Travel Style", request.travel_style)

        if request.interests:
            st.write("**Interests**")
            st.write(", ".join(request.interests))


def render_trip_results(trip_package) -> None:
    tabs = st.tabs(["Itinerary", "Budget", "Food Recommendations", "Packing List", "Travel Tips"])

    with tabs[0]:
        for day, activities in trip_package.itinerary.items():
            with st.expander(day.replace("_", " ").title(), expanded=True):
                for item in activities:
                    st.write(f"- {item}")

    with tabs[1]:
        budget = trip_package.budget
        total_allocated = sum(budget.values())
        cols = st.columns(4)
        for index, (category, amount) in enumerate(budget.items()):
            cols[index % 4].metric(category.title(), f"₹{amount:,.0f}")
        st.info(f"Total allocated: ₹{total_allocated:,.0f}")

    with tabs[2]:
        st.write("**Must try**")
        for item in trip_package.food.get("must_try", []):
            st.write(f"- {item}")
        st.write("**Recommended restaurants**")
        for item in trip_package.food.get("recommended_restaurants", []):
            st.write(f"- {item}")

    with tabs[3]:
        st.write("**Essentials**")
        for item in trip_package.packing.get("essentials", []):
            st.write(f"- {item}")
        st.write("**Travel items**")
        for item in trip_package.packing.get("travel_items", []):
            st.write(f"- {item}")

    with tabs[4]:
        st.write("**Tips**")
        for item in trip_package.safety.get("tips", []):
            st.write(f"- {item}")
        st.write("**Warnings**")
        for item in trip_package.safety.get("warnings", []):
            st.write(f"- {item}")

        with st.expander("Raw trip package"):
            st.json(trip_package.as_dict())


def main() -> None:
    initialize_session_state()
    render_section_header()

    st.markdown(
        "Create a destination-aware itinerary, budget breakdown, food suggestions, packing list, and safety guidance in one flow."
    )

    with st.container(border=True):
        col1, col2 = st.columns([2, 1])

        with col1:
            destination = st.text_input("Destination", placeholder="e.g. Goa, Jaipur, Tokyo")
            travel_style = st.selectbox(
                "Travel Style",
                ["Budget Traveler", "Comfort Traveler", "Luxury Traveler", "Backpacker", "Family Trip"],
                index=0,
            )
            interests = st.multiselect(
                "Interests",
                [
                    "Beaches",
                    "Food",
                    "Culture",
                    "Adventure",
                    "Shopping",
                    "Nightlife",
                    "Nature",
                    "History",
                    "Wellness",
                ],
            )
            custom_interests = st.text_input(
                "Additional interests",
                placeholder="Comma-separated, for example: photography, museums, cafes",
            )

        with col2:
            days = st.number_input("Number of Days", min_value=1, max_value=30, value=4, step=1)
            budget = st.number_input("Budget", min_value=1, max_value=10_000_000, value=15_000, step=500)

    generate_button = st.button("Generate Trip", type="primary", use_container_width=True)

    if generate_button:
        try:
            request = build_travel_request(
                destination=destination,
                days=int(days),
                budget=int(budget),
                travel_style=travel_style,
                interests=sanitize_interests(interests, custom_interests),
            )

            render_summary_card(request)

            progress_placeholder = st.empty()
            progress_placeholder.info("Generating itinerary...")

            def update_progress(message: str) -> None:
                progress_placeholder.info(message)

            with st.spinner("Creating your TripMind plan..."):
                trip_package = st.session_state.orchestrator.generate_trip(
                    request,
                    progress_callback=update_progress,
                )
            progress_placeholder.success("Trip plan generated successfully.")
            render_trip_results(trip_package)
        except ValidationError as error:
            st.error(str(error))
        except ValueError as error:
            st.error(str(error))
        except Exception:
            st.error("Trip generation failed. Please check your Gemini API key or try again.")


if __name__ == "__main__":
    main()
