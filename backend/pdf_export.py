"""
PDF export module for Veckosmak.

Generates printable shopping lists and menu summaries as PDF documents
using ReportLab. All output uses A4 page size and Swedish typography.
"""

from io import BytesIO
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm, mm
from reportlab.platypus import (
    BaseDocTemplate,
    Frame,
    NextPageTemplate,
    PageBreak,
    PageTemplate,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PAGE_WIDTH, PAGE_HEIGHT = A4
MARGIN = 1.8 * cm

BRAND_GREEN = colors.HexColor("#2D7D46")
BRAND_GREEN_LIGHT = colors.HexColor("#E8F5E9")
OFFER_STAR_COLOR = colors.HexColor("#FF9800")
TEXT_DARK = colors.HexColor("#212121")
TEXT_SECONDARY = colors.HexColor("#616161")
BORDER_LIGHT = colors.HexColor("#E0E0E0")

CATEGORY_LABELS: dict[str, str] = {
    "produce": "Frukt & grönt",
    "meat": "Kött & chark",
    "fish": "Fisk & skaldjur",
    "dairy": "Mejeri",
    "pantry": "Skafferi",
    "bakery": "Bröd",
    "frozen": "Fryst",
    "other": "Övrigt",
}

CATEGORY_ORDER = list(CATEGORY_LABELS.keys())

DAY_LABELS: dict[str, str] = {
    "monday": "Måndag",
    "tuesday": "Tisdag",
    "wednesday": "Onsdag",
    "thursday": "Torsdag",
    "friday": "Fredag",
    "saturday": "Lördag",
    "sunday": "Söndag",
}

# ---------------------------------------------------------------------------
# Styles
# ---------------------------------------------------------------------------


def _build_styles() -> dict[str, ParagraphStyle]:
    """Return a dict of named ParagraphStyle objects."""
    base = getSampleStyleSheet()

    return {
        "title": ParagraphStyle(
            "VTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=BRAND_GREEN,
            alignment=TA_LEFT,
            spaceAfter=2 * mm,
        ),
        "subtitle": ParagraphStyle(
            "VSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=14,
            textColor=TEXT_SECONDARY,
            spaceAfter=6 * mm,
        ),
        "section": ParagraphStyle(
            "VSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=16,
            textColor=BRAND_GREEN,
            spaceBefore=6 * mm,
            spaceAfter=3 * mm,
        ),
        "category": ParagraphStyle(
            "VCategory",
            parent=base["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEXT_DARK,
            spaceBefore=4 * mm,
            spaceAfter=2 * mm,
        ),
        "body": ParagraphStyle(
            "VBody",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=10,
            leading=13,
            textColor=TEXT_DARK,
        ),
        "body_small": ParagraphStyle(
            "VBodySmall",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=9,
            leading=12,
            textColor=TEXT_SECONDARY,
        ),
        "body_bold": ParagraphStyle(
            "VBodyBold",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=13,
            textColor=TEXT_DARK,
        ),
        "footer": ParagraphStyle(
            "VFooter",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8,
            leading=10,
            textColor=TEXT_SECONDARY,
            alignment=TA_CENTER,
        ),
        "total_label": ParagraphStyle(
            "VTotalLabel",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=TEXT_DARK,
            alignment=TA_RIGHT,
        ),
        "total_value": ParagraphStyle(
            "VTotalValue",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            textColor=BRAND_GREEN,
            alignment=TA_RIGHT,
        ),
        "offer_tag": ParagraphStyle(
            "VOfferTag",
            parent=base["Normal"],
            fontName="Helvetica-Bold",
            fontSize=9,
            leading=11,
            textColor=OFFER_STAR_COLOR,
        ),
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _format_amount(amount: float, unit: str) -> str:
    """Format an amount + unit string, dropping unnecessary decimals."""
    if amount == int(amount):
        return f"{int(amount)} {unit}"
    return f"{amount:.1f} {unit}"


def _format_kr(value: float) -> str:
    """Format a monetary value in SEK."""
    if value == int(value):
        return f"{int(value)} kr"
    return f"{value:.2f} kr"


def _day_sort_key(day: str) -> int:
    """Return sort index for a weekday string."""
    order = list(DAY_LABELS.keys())
    try:
        return order.index(day.lower())
    except ValueError:
        return 99


def _header_footer(canvas, doc, menu: dict):
    """Draw page header line and footer on every page."""
    canvas.saveState()

    # Top rule
    canvas.setStrokeColor(BRAND_GREEN)
    canvas.setLineWidth(1.5)
    canvas.line(MARGIN, PAGE_HEIGHT - MARGIN + 4 * mm, PAGE_WIDTH - MARGIN, PAGE_HEIGHT - MARGIN + 4 * mm)

    # Footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(TEXT_SECONDARY)
    footer_text = "Veckosmak — Priserna är uppskattade baserat på veckans erbjudanden"
    canvas.drawCentredString(PAGE_WIDTH / 2, 12 * mm, footer_text)
    canvas.drawRightString(PAGE_WIDTH - MARGIN, 12 * mm, f"Sida {doc.page}")

    canvas.restoreState()


def _group_items_by_category(items: list[dict]) -> list[tuple[str, list[dict]]]:
    """Group shopping list items by category, in canonical order."""
    groups: dict[str, list[dict]] = {}
    for item in items:
        cat = item.get("category", "other")
        groups.setdefault(cat, []).append(item)

    result = []
    for cat_key in CATEGORY_ORDER:
        if cat_key in groups:
            result.append((cat_key, groups[cat_key]))
    # Any categories not in CATEGORY_ORDER go at the end
    for cat_key, cat_items in groups.items():
        if cat_key not in CATEGORY_ORDER:
            result.append((cat_key, cat_items))
    return result


# ---------------------------------------------------------------------------
# Header / summary builders
# ---------------------------------------------------------------------------


def _build_header(menu: dict, styles: dict) -> list:
    """Return flowables for the page header with branding and week info."""
    elements = []

    elements.append(Paragraph("Veckosmak", styles["title"]))

    store = menu.get("store_name", "")
    week = menu.get("week_number", "")
    year = menu.get("year", "")
    date_range = menu.get("date_range", "")

    subtitle_parts = []
    if store:
        subtitle_parts.append(store)
    if week and year:
        subtitle_parts.append(f"Vecka {week}, {year}")
    if date_range:
        subtitle_parts.append(date_range)

    if subtitle_parts:
        elements.append(Paragraph(" · ".join(subtitle_parts), styles["subtitle"]))

    return elements


def _build_savings_summary(menu: dict, styles: dict) -> list:
    """Return flowables for the cost/savings summary box."""
    elements = []

    total_cost = menu.get("total_cost", 0)
    total_savings = menu.get("total_savings", 0)
    savings_pct = menu.get("savings_percentage", 0)
    shopping = menu.get("shopping_list", {})
    items_on_offer = shopping.get("items_on_offer", 0)

    data = []
    data.append(["Uppskattad totalkostnad:", _format_kr(total_cost)])
    if total_savings > 0:
        data.append(["Besparing:", f"{_format_kr(total_savings)} ({savings_pct:.0f}%)"])
    if items_on_offer > 0:
        data.append(["Varor på erbjudande:", str(items_on_offer)])

    if not data:
        return elements

    col_widths = [10 * cm, 5 * cm]
    t = Table(data, colWidths=col_widths)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), BRAND_GREEN_LIGHT),
                ("TEXTCOLOR", (0, 0), (0, -1), TEXT_DARK),
                ("TEXTCOLOR", (1, 0), (1, -1), BRAND_GREEN),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 8),
                ("RIGHTPADDING", (0, 0), (-1, -1), 8),
                ("BOX", (0, 0), (-1, -1), 0.5, BRAND_GREEN),
                ("ROUNDEDCORNERS", [3, 3, 3, 3]),
            ]
        )
    )
    elements.append(t)
    elements.append(Spacer(1, 4 * mm))
    return elements


# ---------------------------------------------------------------------------
# Shopping list builder
# ---------------------------------------------------------------------------


def _build_shopping_list_section(menu: dict, styles: dict) -> list:
    """Return flowables for the grouped shopping list."""
    elements = []
    shopping = menu.get("shopping_list", {})
    items = shopping.get("items", [])

    if not items:
        elements.append(Paragraph("Inga varor i inköpslistan.", styles["body"]))
        return elements

    elements.append(Paragraph("Inköpslista", styles["section"]))

    grouped = _group_items_by_category(items)
    available_width = PAGE_WIDTH - 2 * MARGIN

    for cat_key, cat_items in grouped:
        cat_label = CATEGORY_LABELS.get(cat_key, cat_key.capitalize())
        elements.append(Paragraph(cat_label, styles["category"]))

        col_widths = [
            available_width * 0.38,  # name
            available_width * 0.18,  # amount
            available_width * 0.14,  # price
            available_width * 0.30,  # offer info
        ]

        # Header row
        header = [
            Paragraph("<b>Vara</b>", styles["body_small"]),
            Paragraph("<b>Mängd</b>", styles["body_small"]),
            Paragraph("<b>Pris</b>", styles["body_small"]),
            Paragraph("<b>Erbjudande</b>", styles["body_small"]),
        ]
        rows = [header]

        for item in cat_items:
            name = item.get("ingredient_name", "")
            amount = item.get("total_amount", 0)
            unit = item.get("unit", "")
            price = item.get("estimated_price", 0)
            is_on_offer = item.get("is_on_offer", False)
            matched = item.get("matched_offer")

            # Star marker for items on offer
            if is_on_offer:
                name_text = f'<font color="{OFFER_STAR_COLOR.hexval()}">★</font> {name}'
            else:
                name_text = name

            offer_text = ""
            if matched and isinstance(matched, dict):
                offer_product = matched.get("product_name", "")
                offer_price = matched.get("offer_price")
                if offer_product:
                    offer_text = offer_product
                    if offer_price is not None:
                        offer_text += f" ({_format_kr(offer_price)})"

            rows.append(
                [
                    Paragraph(name_text, styles["body"]),
                    Paragraph(_format_amount(amount, unit), styles["body"]),
                    Paragraph(_format_kr(price), styles["body"]),
                    Paragraph(offer_text, styles["body_small"]) if offer_text else "",
                ]
            )

        t = Table(rows, colWidths=col_widths, repeatRows=1)
        t.setStyle(
            TableStyle(
                [
                    # Header styling
                    ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN_LIGHT),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    # Grid
                    ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_GREEN),
                    ("LINEBELOW", (0, 1), (-1, -1), 0.25, BORDER_LIGHT),
                    # Padding
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                    ("LEFTPADDING", (0, 0), (-1, -1), 4),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                    # Alignment
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ]
            )
        )
        elements.append(t)
        elements.append(Spacer(1, 2 * mm))

    # Total row
    total_cost = shopping.get("total_estimated_cost", 0)
    if total_cost > 0:
        elements.append(Spacer(1, 2 * mm))
        total_data = [["Totalt:", _format_kr(total_cost)]]
        total_table = Table(total_data, colWidths=[available_width * 0.7, available_width * 0.3])
        total_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (0, 0), "RIGHT"),
                    ("ALIGN", (1, 0), (1, 0), "RIGHT"),
                    ("FONTNAME", (0, 0), (-1, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("TEXTCOLOR", (1, 0), (1, 0), BRAND_GREEN),
                    ("LINEABOVE", (0, 0), (-1, 0), 1, BRAND_GREEN),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                ]
            )
        )
        elements.append(total_table)

    return elements


# ---------------------------------------------------------------------------
# Menu overview builder
# ---------------------------------------------------------------------------


def _build_menu_overview(menu: dict, styles: dict) -> list:
    """Return flowables for the daily menu overview table."""
    elements = []
    meals = menu.get("meals", [])

    if not meals:
        return elements

    elements.append(Paragraph("Veckomeny", styles["section"]))

    available_width = PAGE_WIDTH - 2 * MARGIN
    col_widths = [
        available_width * 0.15,  # day
        available_width * 0.45,  # recipe
        available_width * 0.18,  # cook time
        available_width * 0.22,  # cost
    ]

    header = [
        Paragraph("<b>Dag</b>", styles["body_small"]),
        Paragraph("<b>Recept</b>", styles["body_small"]),
        Paragraph("<b>Tillagningstid</b>", styles["body_small"]),
        Paragraph("<b>Kostnad</b>", styles["body_small"]),
    ]
    rows = [header]

    sorted_meals = sorted(meals, key=lambda m: _day_sort_key(m.get("day", "")))

    for meal in sorted_meals:
        day_key = meal.get("day", "")
        day_label = DAY_LABELS.get(day_key.lower(), day_key.capitalize())

        recipe = meal.get("recipe", {})
        title = recipe.get("title", "—")
        cook_time = recipe.get("cook_time_minutes")
        cost = meal.get("estimated_cost", 0)

        time_text = f"{cook_time} min" if cook_time else "—"

        rows.append(
            [
                Paragraph(f"<b>{day_label}</b>", styles["body"]),
                Paragraph(title, styles["body"]),
                Paragraph(time_text, styles["body"]),
                Paragraph(_format_kr(cost), styles["body"]),
            ]
        )

    t = Table(rows, colWidths=col_widths, repeatRows=1)
    t.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), BRAND_GREEN_LIGHT),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, BRAND_GREEN),
                ("LINEBELOW", (0, 1), (-1, -1), 0.25, BORDER_LIGHT),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ]
        )
    )
    elements.append(t)
    return elements


# ---------------------------------------------------------------------------
# Recipe detail builder
# ---------------------------------------------------------------------------


def _build_recipe_details(menu: dict, styles: dict) -> list:
    """Return flowables with full recipe instructions for each day."""
    elements = []
    meals = menu.get("meals", [])

    if not meals:
        return elements

    elements.append(Paragraph("Recept", styles["section"]))

    sorted_meals = sorted(meals, key=lambda m: _day_sort_key(m.get("day", "")))

    for i, meal in enumerate(sorted_meals):
        day_key = meal.get("day", "")
        day_label = DAY_LABELS.get(day_key.lower(), day_key.capitalize())
        recipe = meal.get("recipe", {})
        title = recipe.get("title", "—")
        cook_time = recipe.get("cook_time_minutes")
        ingredients = recipe.get("ingredients", [])
        instructions = recipe.get("instructions", [])

        # Day + title
        time_suffix = f"  ·  {cook_time} min" if cook_time else ""
        elements.append(
            Paragraph(f"<b>{day_label}: {title}</b>{time_suffix}", styles["category"])
        )

        # Ingredients
        if ingredients:
            elements.append(Paragraph("<b>Ingredienser:</b>", styles["body"]))
            for ing in ingredients:
                name = ing.get("name", "")
                amount = ing.get("amount", 0)
                unit = ing.get("unit", "")
                if amount and unit:
                    line = f"• {_format_amount(amount, unit)} {name}"
                elif amount:
                    line = f"• {amount} {name}"
                else:
                    line = f"• {name}"
                elements.append(Paragraph(line, styles["body"]))
            elements.append(Spacer(1, 2 * mm))

        # Instructions
        if instructions:
            elements.append(Paragraph("<b>Gör så här:</b>", styles["body"]))
            for step_num, step in enumerate(instructions, 1):
                elements.append(Paragraph(f"{step_num}. {step}", styles["body"]))
            elements.append(Spacer(1, 2 * mm))

        if i < len(sorted_meals) - 1:
            elements.append(Spacer(1, 4 * mm))

    return elements


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def generate_shopping_list_pdf(menu: dict) -> bytes:
    """Generate a PDF containing the shopping list and cost summary.

    Args:
        menu: A WeeklyMenu dict.

    Returns:
        PDF file contents as bytes.
    """
    buf = BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 8 * mm,
        title="Veckosmak — Inköpslista",
        author="Veckosmak",
    )

    elements: list = []
    elements.extend(_build_header(menu, styles))
    elements.extend(_build_savings_summary(menu, styles))
    elements.extend(_build_shopping_list_section(menu, styles))

    # Active filters note
    filters = menu.get("active_filters", [])
    if filters:
        elements.append(Spacer(1, 4 * mm))
        filter_text = "Aktiva filter: " + ", ".join(filters)
        elements.append(Paragraph(filter_text, styles["body_small"]))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, menu),
              onLaterPages=lambda c, d: _header_footer(c, d, menu))

    return buf.getvalue()


def generate_menu_pdf(menu: dict) -> bytes:
    """Generate a full PDF with menu overview, recipes, and shopping list.

    Args:
        menu: A WeeklyMenu dict.

    Returns:
        PDF file contents as bytes.
    """
    buf = BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=MARGIN,
        rightMargin=MARGIN,
        topMargin=MARGIN,
        bottomMargin=MARGIN + 8 * mm,
        title="Veckosmak — Veckomeny",
        author="Veckosmak",
    )

    elements: list = []

    # Header + summary
    elements.extend(_build_header(menu, styles))
    elements.extend(_build_savings_summary(menu, styles))

    # Menu overview table
    elements.extend(_build_menu_overview(menu, styles))

    # Recipe details
    elements.append(Spacer(1, 4 * mm))
    elements.extend(_build_recipe_details(menu, styles))

    # Page break before shopping list
    elements.append(PageBreak())
    elements.extend(_build_shopping_list_section(menu, styles))

    # Active filters note
    filters = menu.get("active_filters", [])
    if filters:
        elements.append(Spacer(1, 4 * mm))
        filter_text = "Aktiva filter: " + ", ".join(filters)
        elements.append(Paragraph(filter_text, styles["body_small"]))

    doc.build(elements, onFirstPage=lambda c, d: _header_footer(c, d, menu),
              onLaterPages=lambda c, d: _header_footer(c, d, menu))

    return buf.getvalue()
