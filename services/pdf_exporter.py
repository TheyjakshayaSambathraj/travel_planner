from __future__ import annotations

from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from models.travel_package import TravelPackage
from models.travel_request import TravelRequest


class TravelDossierExporter:
    def export(self, request: TravelRequest, trip_package: TravelPackage) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=36,
            leftMargin=36,
            topMargin=36,
            bottomMargin=36,
        )

        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(name="SectionTitle", parent=styles["Heading2"], textColor=colors.HexColor("#0F766E")))
        styles.add(ParagraphStyle(name="CoverTitle", parent=styles["Title"], alignment=1, textColor=colors.HexColor("#0F172A")))
        styles.add(ParagraphStyle(name="CoverSubTitle", parent=styles["BodyText"], alignment=1, leading=16))

        story = []
        story.append(Spacer(1, 1.2 * inch))
        story.append(Paragraph("TripMind AI", styles["CoverTitle"]))
        story.append(Spacer(1, 0.15 * inch))
        story.append(Paragraph("Travel Dossier", styles["CoverSubTitle"]))
        story.append(Spacer(1, 0.5 * inch))
        story.append(Paragraph(f"Destination: {request.destination}", styles["Heading2"]))
        story.append(Paragraph(f"Persona: {request.persona}", styles["BodyText"]))
        story.append(Paragraph(f"Days: {request.days} | Budget: ₹{request.budget:,}", styles["BodyText"]))
        story.append(Paragraph(f"Trip Score: {trip_package.summary.trip_score:.1f}/10", styles["BodyText"]))
        story.append(PageBreak())

        self._add_section(story, styles, "Executive Summary", [trip_package.summary.overall_summary])
        self._add_section(story, styles, "Destination Intelligence", [trip_package.research.destination_overview, f"Best time to visit: {trip_package.research.best_time_to_visit}"] + trip_package.research.key_highlights)
        self._add_itinerary_section(story, styles, trip_package)
        self._add_budget_section(story, styles, trip_package)
        self._add_list_section(story, styles, "Food Recommendations", trip_package.food.must_try_foods + trip_package.food.street_foods + trip_package.food.recommended_restaurants + trip_package.food.food_tips)
        self._add_list_section(story, styles, "Packing Checklist", trip_package.packing.essentials + trip_package.packing.weather_items + trip_package.packing.electronics + trip_package.packing.documents)
        self._add_list_section(story, styles, "Safety Guide", trip_package.safety.travel_tips + trip_package.safety.warnings + trip_package.safety.local_etiquette + trip_package.safety.emergency_contacts)
        self._add_list_section(story, styles, "Travel Insights", trip_package.summary.ai_insights.money_saving_tips + trip_package.summary.ai_insights.hidden_gems + trip_package.summary.ai_insights.avoid + trip_package.summary.ai_insights.best_experiences + trip_package.summary.ai_insights.local_secrets)

        doc.build(story)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _add_section(self, story, styles, title: str, paragraphs: list[str]) -> None:
        story.append(Paragraph(title, styles["SectionTitle"]))
        story.append(Spacer(1, 0.1 * inch))
        for paragraph in paragraphs:
            story.append(Paragraph(paragraph or "", styles["BodyText"]))
            story.append(Spacer(1, 0.08 * inch))
        story.append(Spacer(1, 0.18 * inch))

    def _add_list_section(self, story, styles, title: str, items: list[str]) -> None:
        story.append(Paragraph(title, styles["SectionTitle"]))
        story.append(Spacer(1, 0.1 * inch))
        for item in items:
            story.append(Paragraph(f"• {item}", styles["BodyText"]))
            story.append(Spacer(1, 0.05 * inch))
        story.append(Spacer(1, 0.15 * inch))

    def _add_budget_section(self, story, styles, trip_package: TravelPackage) -> None:
        story.append(Paragraph("Budget Breakdown", styles["SectionTitle"]))
        story.append(Spacer(1, 0.1 * inch))
        data = [
            ["Category", "Amount"],
            ["Accommodation", f"₹{trip_package.budget.accommodation:,}"],
            ["Food", f"₹{trip_package.budget.food:,}"],
            ["Transport", f"₹{trip_package.budget.transport:,}"],
            ["Activities", f"₹{trip_package.budget.activities:,}"],
            ["Emergency Buffer", f"₹{trip_package.budget.emergency_buffer:,}"],
        ]
        table = Table(data, hAlign="LEFT")
        table.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#0F766E")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                    ("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#0F766E")),
                    ("PADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.append(table)
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(trip_package.budget.allocation_reasoning, styles["BodyText"]))
        story.append(Spacer(1, 0.18 * inch))

    def _add_itinerary_section(self, story, styles, trip_package: TravelPackage) -> None:
        story.append(Paragraph("Complete Itinerary", styles["SectionTitle"]))
        story.append(Spacer(1, 0.1 * inch))
        for day in trip_package.itinerary.days:
            story.append(Paragraph(f"Day {day.day}", styles["Heading3"]))
            for label, items in (("Morning", day.morning), ("Afternoon", day.afternoon), ("Evening", day.evening)):
                story.append(Paragraph(label, styles["BodyText"]))
                for item in items:
                    location_text = f" - {item.location}" if item.location else ""
                    story.append(Paragraph(f"• {item.activity}{location_text}", styles["BodyText"]))
            story.append(Spacer(1, 0.1 * inch))
        story.append(Spacer(1, 0.18 * inch))
