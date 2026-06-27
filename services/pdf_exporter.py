from __future__ import annotations

from datetime import datetime
from io import BytesIO
from typing import Dict, List, Optional, Any
import urllib.request

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    HRFlowable,
    Image,
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
    BRAND_BLUE = colors.HexColor("#3B82F6")
    BRAND_PURPLE = colors.HexColor("#8B5CF6")
    BRAND_EMERALD = colors.HexColor("#10B981")
    BRAND_AMBER = colors.HexColor("#F59E0B")
    BRAND_RED = colors.HexColor("#EF4444")
    DARK = colors.HexColor("#0F172A")
    MUTED = colors.HexColor("#64748B")
    LIGHT_BG = colors.HexColor("#F8FAFC")
    SLATE = colors.HexColor("#1E293B")

    def __init__(self) -> None:
        self._styles = None

    def export(
        self,
        request: TravelRequest,
        trip_package: TravelPackage,
        wiki_data: Optional[Dict[str, Any]] = None,
        budget_intel: Optional[Dict[str, Any]] = None,
        hotel_data: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=48,
            leftMargin=48,
            topMargin=54,
            bottomMargin=54,
        )
        styles = self._build_styles()
        story: List = []

        # Cover with destination hero image
        self._add_cover(story, styles, request, trip_package, wiki_data)
        story.append(PageBreak())

        # Destination facts (new)
        if wiki_data:
            self._add_destination_facts(story, styles, request.destination, wiki_data)

        # Budget intelligence (new)
        if budget_intel:
            self._add_budget_intelligence(story, styles, request, budget_intel, hotel_data)

        self._add_executive_summary(story, styles, trip_package)
        self._add_trip_metrics(story, styles, request, trip_package)
        self._add_destination_intelligence(story, styles, trip_package)
        self._add_itinerary(story, styles, trip_package)
        self._add_budget(story, styles, trip_package)
        self._add_food_guide(story, styles, trip_package)
        self._add_packing(story, styles, trip_package)
        self._add_safety(story, styles, trip_package)
        self._add_insights(story, styles, trip_package)

        doc.build(story, onFirstPage=self._footer, onLaterPages=self._footer)
        pdf_bytes = buffer.getvalue()
        buffer.close()
        return pdf_bytes

    def _build_styles(self):
        if self._styles is not None:
            return self._styles
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle(
            name="CoverBrand", parent=styles["Title"],
            fontSize=30, leading=34, alignment=TA_CENTER,
            textColor=self.BRAND_BLUE, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="CoverHero", parent=styles["Heading1"],
            fontSize=24, leading=28, alignment=TA_CENTER,
            textColor=colors.white, spaceAfter=12,
        ))
        styles.add(ParagraphStyle(
            name="CoverMeta", parent=styles["BodyText"],
            fontSize=11, leading=16, alignment=TA_CENTER,
            textColor=self.MUTED,
        ))
        styles.add(ParagraphStyle(
            name="SectionHead", parent=styles["Heading2"],
            fontSize=16, leading=20, textColor=self.BRAND_PURPLE,
            spaceBefore=14, spaceAfter=8,
        ))
        styles.add(ParagraphStyle(
            name="SubHead", parent=styles["Heading3"],
            fontSize=12, leading=15, textColor=self.BRAND_BLUE,
            spaceBefore=8, spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            name="Body", parent=styles["BodyText"],
            fontSize=10, leading=14, textColor=self.DARK, spaceAfter=6,
        ))
        styles.add(ParagraphStyle(
            name="DossierBullet", parent=styles["BodyText"],
            fontSize=10, leading=14, leftIndent=14, bulletIndent=4,
            textColor=self.DARK, spaceAfter=3,
        ))
        styles.add(ParagraphStyle(
            name="AlertHead", parent=styles["BodyText"],
            fontSize=11, leading=14, textColor=colors.white,
            fontName="Helvetica-Bold", spaceAfter=4,
        ))
        styles.add(ParagraphStyle(
            name="AlertBody", parent=styles["BodyText"],
            fontSize=9, leading=13, textColor=colors.HexColor("#E2E8F0"),
            spaceAfter=3,
        ))
        self._styles = styles
        return styles

    def _footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(self.MUTED)
        canvas.drawString(48, 32, "Generated by TripMind AI")
        canvas.drawRightString(A4[0] - 48, 32, f"Page {canvas.getPageNumber()}")
        canvas.restoreState()

    def _section_rule(self, story) -> None:
        story.append(HRFlowable(
            width="100%", thickness=1,
            color=colors.HexColor("#E2E8F0"),
            spaceBefore=4, spaceAfter=10,
        ))

    def _fetch_image(self, url: str) -> Optional[bytes]:
        """Fetch image bytes from URL with timeout."""
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "TripMindAI/1.0"})
            with urllib.request.urlopen(req, timeout=6) as resp:
                return resp.read()
        except Exception:
            return None

    def _add_cover(
        self,
        story,
        styles,
        request: TravelRequest,
        trip_package: TravelPackage,
        wiki_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        intelligence = trip_package.summary.trip_intelligence
        analytics = trip_package.summary.analytics_summary
        generated = datetime.utcnow().strftime("%B %d, %Y")

        story.append(Spacer(1, 0.4 * inch))
        story.append(Paragraph("TripMind AI", styles["CoverBrand"]))
        story.append(Paragraph("Professional Travel Dossier", styles["CoverMeta"]))
        story.append(Spacer(1, 0.3 * inch))

        # Destination Hero Image
        image_added = False
        if wiki_data and wiki_data.get("image_url"):
            img_bytes = self._fetch_image(wiki_data["image_url"])
            if img_bytes:
                try:
                    img_buf = BytesIO(img_bytes)
                    img = Image(img_buf, width=6.3 * inch, height=2.5 * inch)
                    img.hAlign = "CENTER"

                    # Destination name overlay via table
                    img_table = Table(
                        [[img]],
                        colWidths=[6.3 * inch],
                        hAlign="CENTER",
                    )
                    img_table.setStyle(TableStyle([
                        ("TOPPADDING", (0, 0), (-1, -1), 0),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                        ("LEFTPADDING", (0, 0), (-1, -1), 0),
                        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
                        ("ROUNDEDCORNERS", [8, 8, 8, 8]),
                    ]))
                    story.append(img_table)
                    story.append(Spacer(1, 0.1 * inch))
                    image_added = True
                except Exception:
                    pass

        # Destination title banner
        dest_text = request.destination
        if wiki_data and wiki_data.get("country") and wiki_data["country"] != request.destination:
            dest_text = f"{request.destination}, {wiki_data['country']}"

        banner = Table(
            [[Paragraph(f"<b>{dest_text}</b>", styles["CoverHero"])]],
            colWidths=[6.3 * inch],
            hAlign="CENTER",
        )
        banner.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), self.BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, -1), colors.white),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("TOPPADDING", (0, 0), (-1, -1), 14),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 14),
            ("ROUNDEDCORNERS", [8, 8, 8, 8]),
        ]))
        story.append(banner)
        story.append(Spacer(1, 0.2 * inch))

        # Wikipedia extract
        if wiki_data and wiki_data.get("extract"):
            extract = wiki_data["extract"][:300] + ("…" if len(wiki_data["extract"]) > 300 else "")
            story.append(Paragraph(extract, styles["CoverMeta"]))
            story.append(Spacer(1, 0.15 * inch))

        story.append(Paragraph(
            f"{request.persona}  ·  {request.days} Days  ·  ₹{request.budget:,}",
            styles["CoverMeta"],
        ))
        story.append(Spacer(1, 0.2 * inch))

        score_table = Table(
            [
                ["Trip Score", "Budget Fit", "Est. Cost"],
                [
                    f"{intelligence.trip_score}/100",
                    f"{intelligence.budget_fit}/100",
                    f"₹{analytics.estimated_total_cost:,}",
                ],
            ],
            colWidths=[2.1 * inch, 2.1 * inch, 2.1 * inch],
            hAlign="CENTER",
        )
        score_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_PURPLE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ALIGN", (0, 0), (-1, -1), "CENTER"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 10),
        ]))
        story.append(score_table)
        story.append(Spacer(1, 0.2 * inch))
        story.append(Paragraph(f"Generated on {generated}", styles["CoverMeta"]))

    def _add_destination_facts(
        self,
        story,
        styles,
        destination: str,
        wiki_data: Dict[str, Any],
    ) -> None:
        story.append(Paragraph("Destination Facts", styles["SectionHead"]))
        self._section_rule(story)

        facts = []
        if wiki_data.get("country"):
            facts.append(["Country", wiki_data["country"]])
        if wiki_data.get("currency"):
            sym = wiki_data.get("currency_symbol", "")
            facts.append(["Currency", f"{wiki_data['currency']} {sym}".strip()])
        if wiki_data.get("language"):
            facts.append(["Language", wiki_data["language"]])
        if wiki_data.get("timezone"):
            facts.append(["Timezone", wiki_data["timezone"]])
        if wiki_data.get("visa_hint"):
            facts.append(["Visa Requirement", wiki_data["visa_hint"]])
        if wiki_data.get("description"):
            facts.append(["Description", wiki_data["description"]])
        if wiki_data.get("extract") and len(wiki_data["extract"]) > 50:
            extract = wiki_data["extract"][:400]
            story.append(Paragraph(extract, styles["Body"]))
            story.append(Spacer(1, 0.1 * inch))

        if facts:
            data = [["Field", "Value"]] + facts
            table = Table(data, colWidths=[1.8 * inch, 4.0 * inch], hAlign="LEFT")
            table.setStyle(TableStyle([
                ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_BLUE),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
                ("PADDING", (0, 0), (-1, -1), 8),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]))
            story.append(table)
            story.append(Spacer(1, 0.15 * inch))

    def _add_budget_intelligence(
        self,
        story,
        styles,
        request: TravelRequest,
        budget_intel: Dict[str, Any],
        hotel_data: Optional[Dict[str, Any]] = None,
    ) -> None:
        story.append(Paragraph("Budget Intelligence", styles["SectionHead"]))
        self._section_rule(story)

        dest_cur = budget_intel.get("dest_currency", "USD")
        dest_sym = budget_intel.get("dest_symbol", "$")
        rate = budget_intel.get("rate", 1.0)
        label = budget_intel.get("budget_label", "Adequate")
        is_feasible = budget_intel.get("is_feasible", True)

        # Currency conversion
        if dest_cur != "INR":
            converted = budget_intel.get("converted_budget", 0)
            story.append(Paragraph(
                f"<b>Budget Conversion:</b> ₹{request.budget:,} INR = "
                f"{dest_sym}{converted:,.0f} {dest_cur} "
                f"(Rate: 1 INR = {dest_sym}{rate:.4f})",
                styles["Body"],
            ))

        # Feasibility verdict
        verdict_color = self.BRAND_EMERALD if is_feasible else self.BRAND_RED
        verdict_text = f"Budget Status: {label}"
        verdict_table = Table(
            [[Paragraph(f"<b>{verdict_text}</b>", styles["AlertHead"])]],
            colWidths=[5.8 * inch],
            hAlign="LEFT",
        )
        verdict_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, -1), verdict_color),
            ("PADDING", (0, 0), (-1, -1), 10),
            ("ROUNDEDCORNERS", [6, 6, 6, 6]),
        ]))
        story.append(verdict_table)
        story.append(Spacer(1, 0.12 * inch))

        # Cost breakdown
        items_data = budget_intel.get("items", {})
        hotel_total = hotel_data["total_inr"] if hotel_data else items_data.get("hotel_estimate_inr", 0)
        breakdown = [
            ["Category", "Estimated (INR)", "Notes"],
            ["✈ Flights (Round Trip)", f"₹{items_data.get('flight_estimate_inr', 0):,.0f}",
             budget_intel.get("flight_note", "Heuristic estimate")],
            ["🏨 Hotel", f"₹{hotel_total:,.0f}",
             hotel_data["tier_label"] if hotel_data else "Estimated"],
            ["🍽 Food", f"₹{items_data.get('food_estimate_inr', 0):,.0f}",
             f"{request.days} days"],
            ["🎯 Activities", f"₹{items_data.get('activities_estimate_inr', 0):,.0f}",
             "Tours & experiences"],
            ["🚗 Local Transport", f"₹{items_data.get('transport_local_inr', 0):,.0f}",
             "Within destination"],
            ["🛡 Emergency Buffer", f"₹{items_data.get('emergency_buffer_inr', 0):,.0f}",
             "5% safety reserve"],
            ["TOTAL ESTIMATED", f"₹{budget_intel.get('min_total_inr', 0):,.0f}", ""],
        ]
        table = Table(breakdown, colWidths=[2.0 * inch, 1.8 * inch, 2.0 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_EMERALD),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -2), [colors.white, self.LIGHT_BG]),
            ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#E2E8F0")),
            ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.12 * inch))

        # Warning/reasons
        if not is_feasible and budget_intel.get("reasons"):
            story.append(Paragraph("Budget Concerns:", styles["SubHead"]))
            for reason in budget_intel["reasons"]:
                story.append(Paragraph(f"• {reason}", styles["DossierBullet"]))
            rec_min = budget_intel.get("recommended_min_inr", 0)
            rec_max = budget_intel.get("recommended_max_inr", 0)
            story.append(Paragraph(
                f"Recommended minimum budget: ₹{rec_min:,.0f} – ₹{rec_max:,.0f} INR",
                styles["Body"],
            ))

        story.append(Spacer(1, 0.1 * inch))

    def _add_executive_summary(self, story, styles, trip_package: TravelPackage) -> None:
        story.append(Paragraph("Executive Summary", styles["SectionHead"]))
        self._section_rule(story)
        story.append(Paragraph(trip_package.summary.overall_summary, styles["Body"]))
        if trip_package.summary.highlights:
            story.append(Paragraph("Highlights", styles["SubHead"]))
            for item in trip_package.summary.highlights:
                story.append(Paragraph(f"• {item}", styles["DossierBullet"]))

    def _add_trip_metrics(self, story, styles, request: TravelRequest, trip_package: TravelPackage) -> None:
        intelligence = trip_package.summary.trip_intelligence
        analytics = trip_package.summary.analytics_summary
        story.append(Paragraph("Trip Metrics", styles["SectionHead"]))
        self._section_rule(story)
        data = [
            ["Metric", "Value"],
            ["Trip Score", f"{intelligence.trip_score}/100"],
            ["Budget Fit", f"{intelligence.budget_fit}/100"],
            ["Estimated Cost", f"₹{analytics.estimated_total_cost:,}"],
            ["Difficulty", f"{analytics.difficulty_score}/100"],
            ["Duration", f"{request.days} days"],
            ["Persona", request.persona],
            ["Trip Type", trip_package.summary.trip_type],
        ]
        table = Table(data, colWidths=[2.2 * inch, 3.5 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_BLUE),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.15 * inch))

    def _add_destination_intelligence(self, story, styles, trip_package: TravelPackage) -> None:
        research = trip_package.research
        story.append(Paragraph("Destination Research", styles["SectionHead"]))
        self._section_rule(story)
        story.append(Paragraph(research.destination_overview, styles["Body"]))
        story.append(Paragraph(f"<b>Best time to visit:</b> {research.best_time_to_visit}", styles["Body"]))
        for label, items in (
            ("Popular Areas", research.popular_areas),
            ("Local Transport", research.local_transport),
            ("Key Highlights", research.key_highlights),
        ):
            if items:
                story.append(Paragraph(label, styles["SubHead"]))
                for item in items:
                    story.append(Paragraph(f"• {item}", styles["DossierBullet"]))

    def _add_itinerary(self, story, styles, trip_package: TravelPackage) -> None:
        story.append(PageBreak())
        story.append(Paragraph("Daily Itinerary", styles["SectionHead"]))
        self._section_rule(story)
        for day in trip_package.itinerary.days:
            story.append(Paragraph(f"Day {day.day}", styles["SubHead"]))
            evening_items = list(day.evening)
            night_items = evening_items[-1:] if len(evening_items) > 1 else []
            evening_display = evening_items[:-1] if len(evening_items) > 1 else evening_items

            for label, items in (
                ("Morning", day.morning),
                ("Afternoon", day.afternoon),
                ("Evening", evening_display),
                ("Night", night_items),
            ):
                story.append(Paragraph(label, styles["Body"]))
                if not items:
                    story.append(Paragraph("• Free time / rest", styles["DossierBullet"]))
                for item in items:
                    location = f" — {item.location}" if item.location else ""
                    story.append(Paragraph(f"• <b>{item.activity}</b>{location}", styles["DossierBullet"]))
            story.append(Spacer(1, 0.12 * inch))
            story.append(HRFlowable(
                width="100%", thickness=0.5,
                color=colors.HexColor("#E2E8F0"), spaceAfter=8,
            ))

    def _add_budget(self, story, styles, trip_package: TravelPackage) -> None:
        budget = trip_package.budget
        story.append(Paragraph("Budget Breakdown", styles["SectionHead"]))
        self._section_rule(story)
        categories = [
            ("Accommodation", budget.accommodation),
            ("Food", budget.food),
            ("Transport", budget.transport),
            ("Activities", budget.activities),
            ("Emergency Buffer", budget.emergency_buffer),
        ]
        total = sum(amount for _, amount in categories) or 1
        data = [["Category", "Amount", "Share"]]
        for name, amount in categories:
            pct = round(amount / total * 100, 1)
            data.append([name, f"₹{amount:,}", f"{pct}%"])
        table = Table(data, colWidths=[2.0 * inch, 1.8 * inch, 1.0 * inch], hAlign="LEFT")
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), self.BRAND_EMERALD),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, self.LIGHT_BG]),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
            ("PADDING", (0, 0), (-1, -1), 8),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
        ]))
        story.append(table)
        story.append(Spacer(1, 0.1 * inch))
        story.append(Paragraph(budget.allocation_reasoning, styles["Body"]))

    def _add_food_guide(self, story, styles, trip_package: TravelPackage) -> None:
        food = trip_package.food
        story.append(Paragraph("Food Guide", styles["SectionHead"]))
        self._section_rule(story)
        for label, items in (
            ("Must Try", food.must_try_foods),
            ("Street Food", food.street_foods),
            ("Restaurants", food.recommended_restaurants),
            ("Tips", food.food_tips),
        ):
            if items:
                story.append(Paragraph(label, styles["SubHead"]))
                for item in items:
                    story.append(Paragraph(f"• {item}", styles["DossierBullet"]))

    def _add_packing(self, story, styles, trip_package: TravelPackage) -> None:
        packing = trip_package.packing
        story.append(Paragraph("Packing Checklist", styles["SectionHead"]))
        self._section_rule(story)
        for label, items in (
            ("Documents", packing.documents),
            ("Electronics", packing.electronics),
            ("Weather", packing.weather_items),
            ("Essentials", packing.essentials),
        ):
            if items:
                story.append(Paragraph(label, styles["SubHead"]))
                for item in items:
                    story.append(Paragraph(f"☐ {item}", styles["DossierBullet"]))

    def _add_safety(self, story, styles, trip_package: TravelPackage) -> None:
        safety = trip_package.safety
        story.append(PageBreak())
        story.append(Paragraph("Safety Guide", styles["SectionHead"]))
        self._section_rule(story)
        for label, items in (
            ("Travel Tips", safety.travel_tips),
            ("Warnings", safety.warnings),
            ("Local Etiquette", safety.local_etiquette),
            ("Emergency Contacts", safety.emergency_contacts),
        ):
            if items:
                story.append(Paragraph(label, styles["SubHead"]))
                for item in items:
                    story.append(Paragraph(f"• {item}", styles["DossierBullet"]))

    def _add_insights(self, story, styles, trip_package: TravelPackage) -> None:
        insights = trip_package.summary.ai_insights
        story.append(Paragraph("Travel Insights", styles["SectionHead"]))
        self._section_rule(story)
        for label, items in (
            ("Money Saving Tips", insights.money_saving_tips),
            ("Hidden Gems", insights.hidden_gems),
            ("Best Experiences", insights.best_experiences),
            ("Avoid", insights.avoid),
            ("Local Secrets", insights.local_secrets),
        ):
            if items:
                story.append(Paragraph(label, styles["SubHead"]))
                for item in items:
                    story.append(Paragraph(f"• {item}", styles["DossierBullet"]))
