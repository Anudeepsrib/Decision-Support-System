"""
Deterministic KSERC-style truing-up order PDF generator.

The generator consumes only report_context built from canonical comparison rows.
It does not render raw extraction rows and does not call an LLM or external
service.
"""

from __future__ import annotations

import hashlib
import html
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional

try:
    from .config import get_settings
    from .report_context import build_report_context
except ImportError:  # Support direct imports from the backend directory.
    from config import get_settings
    from report_context import build_report_context

try:
    from playwright.async_api import async_playwright

    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm
    from reportlab.platypus import (
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )

    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


settings = get_settings()
OUTPUT_DIR = str(settings.generated_reports_dir)
settings.generated_reports_dir.mkdir(parents=True, exist_ok=True)

TEMPLATE_DIR = Path(__file__).resolve().parent / "templates"

BANNED_PDF_STRINGS = (
    "raw_label",
    "normalized_label",
    "source_page",
    "confidence",
    "Low extraction confidence",
    "0 to 100 units",
    "Single phase",
    "Three phase",
    "Fixed Charge",
    "Energy Charge",
)

FULL_ORDER_TARGET_PAGES = 237
FULL_ORDER_CHAPTER_RANGES = (
    ("introduction", 3, 18),
    ("sbu_g", 19, 36),
    ("sbu_t", 37, 58),
    ("energy_sales_td_loss", 59, 71),
    ("sbu_d", 72, 147),
    ("common_expenses", 148, 196),
    ("consolidated", 197, 200),
)
ANNEXURE_START_PAGE = 201
ANNEXURE_END_PAGE = 236


def _fmt_value(value: Optional[float], unit: str = "Rs. Cr.") -> str:
    if value is None:
        return "-"
    if unit == "%":
        return f"{value:,.2f}%"
    return f"{value:,.2f}"


def _as_report_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _template(path: str) -> str:
    return (TEMPLATE_DIR / path).read_text(encoding="utf-8")


def _render_template(template_text: str, values: Dict[str, str]) -> str:
    rendered = template_text
    for key, value in values.items():
        rendered = rendered.replace("{{ " + key + " }}", value)
    return rendered


def _escape_lines(lines: Iterable[str]) -> str:
    return "<br>".join(html.escape(str(line)) for line in lines)


def _render_html_table(rows: List[Dict], caption: str, unit_label: str) -> str:
    table_template = _template("components/regulatory_table.html")
    if not rows:
        body = (
            "<tr><td class='center'>-</td><td>No mapped canonical line item</td>"
            "<td class='num'>-</td><td class='num'>-</td><td class='num'>-</td><td class='num'>-</td></tr>"
        )
    else:
        body_parts = []
        for row in rows:
            unit = row.get("unit") or unit_label or "Rs. Cr."
            row_class = " class='total-row'" if row.get("is_total") else ""
            body_parts.append(
                f"<tr{row_class}>"
                f"<td class='center'>{html.escape(str(row.get('no', '')))}</td>"
                f"<td>{html.escape(row.get('display_name') or '-')}</td>"
                f"<td class='num'>{html.escape(_fmt_value(row.get('arr_approved_value'), unit))}</td>"
                f"<td class='num'>{html.escape(_fmt_value(row.get('petition_actual_value'), unit))}</td>"
                f"<td class='num'>{html.escape(_fmt_value(row.get('petition_claimed_value'), unit))}</td>"
                f"<td class='num'>{html.escape(_fmt_value(row.get('deviation_value'), unit))}</td>"
                "</tr>"
            )
        body = "".join(body_parts)

    return _render_template(
        table_template,
        {
            "caption": html.escape(caption),
            "unit_label": html.escape(unit_label or "Rs. Cr."),
            "body": body,
        },
    )


def _render_html_numbered_paragraph(paragraph: Dict) -> str:
    return (
        "<div class='numbered-paragraph'>"
        f"<div>{html.escape(paragraph['no'])}</div>"
        f"<p>{html.escape(paragraph['text'])}</p>"
        "</div>"
    )


def _render_html_chapter(chapter: Dict) -> str:
    chapter_template = _template("components/chapter.html")
    body_parts: List[str] = []
    for section in chapter["sections"]:
        body_parts.append(f"<h3>{html.escape(section['heading'])}</h3>")
        body_parts.extend(_render_html_numbered_paragraph(paragraph) for paragraph in section["paragraphs"])
        if section.get("table") == "primary":
            body_parts.append(
                _render_html_table(
                    chapter["rows"],
                    f"{chapter['table_no']} {chapter['table_caption']}",
                    chapter.get("unit_label") or "Rs. Cr.",
                )
            )
    return _render_template(
        chapter_template,
        {
            "chapter_no": html.escape(chapter["chapter_no"]),
            "title": html.escape(chapter["title"]),
            "body": "".join(body_parts),
        },
    )


def _render_html_title_page(context: Dict, officer_name: str) -> str:
    meta = context["case_metadata"]
    template = _template("components/title_page.html")
    return _render_template(
        template,
        {
            "commission": html.escape(meta["commission"]),
            "place": html.escape(meta["place"]),
            "present": _escape_lines(meta["present"]),
            "op_number": html.escape(meta["op_number"]),
            "matter": html.escape(meta["matter"]),
            "petitioner": html.escape(meta["petitioner"]),
            "petitioner_address": _escape_lines(meta["petitioner_address"]),
            "order_date": html.escape(meta["order_date"]),
            "financial_year": html.escape(meta["financial_year"]),
            "dated_this": html.escape(meta["dated_this"]),
        },
    )


def _render_html_toc(context: Dict) -> str:
    template = _template("components/toc.html")
    body = "".join(
        "<tr>"
        f"<td class='center'>{entry['sl_no']}</td>"
        f"<td>{html.escape(entry['particulars'])}</td>"
        f"<td class='num'>{entry['pages']}</td>"
        "</tr>"
        for entry in context["toc_entries"]
    )
    return _render_template(template, {"body": body})


def _render_html_signature_block(context: Dict, officer_name: str) -> str:
    template = _template("components/signature_block.html")
    return _render_template(template, {"officer_name": html.escape(officer_name)})


def generate_order_html(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> str:
    """Generate deterministic KSERC order HTML from report_context."""
    context = build_report_context(case_id, financial_year, comparisons, reviews, officer_name)
    css = _template("kserc_order.css")
    shell = _template("kserc_order.html")

    chapters = "".join(
        _render_html_chapter(context["chapters"][key]) for key in context["chapter_sequence"]
    )
    final_order = (
        "<section class='chapter final-order'>"
        "<h1>Order of the Commission</h1>"
        "<h2>Final Order</h2>"
        "<div class='numbered-paragraph'><div>8.1</div>"
        "<p>The draft summary above is placed for internal review and verification. "
        "The Commission may take appropriate decision after examining the details "
        "submitted by KSEB Ltd.</p></div>"
        f"<p>{html.escape(context['final_summary']['disclaimer'])}</p>"
        f"{_render_html_signature_block(context, officer_name)}"
        "</section>"
    )

    return _render_template(
        shell,
        {
            "title": f"KSERC Truing-Up Order - FY {html.escape(financial_year)}",
            "css": css,
            "title_page": _render_html_title_page(context, officer_name),
            "toc": _render_html_toc(context),
            "chapters": chapters,
            "final_order": final_order,
        },
    )


def _styles() -> Dict[str, ParagraphStyle]:
    styles = getSampleStyleSheet()
    return {
        "commission": ParagraphStyle(
            "Commission",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=14,
            leading=17,
            alignment=TA_CENTER,
            spaceAfter=4,
        ),
        "place": ParagraphStyle(
            "Place",
            parent=styles["Normal"],
            fontName="Times-Bold",
            fontSize=11,
            leading=14,
            alignment=TA_CENTER,
            spaceAfter=14,
        ),
        "title": ParagraphStyle(
            "OrderTitle",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=12,
        ),
        "chapter_no": ParagraphStyle(
            "ChapterNo",
            parent=styles["Heading1"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceBefore=0,
            spaceAfter=8,
        ),
        "chapter_title": ParagraphStyle(
            "ChapterTitle",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=12,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "section": ParagraphStyle(
            "Section",
            parent=styles["Heading3"],
            fontName="Times-Bold",
            fontSize=10,
            leading=13,
            alignment=TA_LEFT,
            spaceBefore=6,
            spaceAfter=3,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=9.4,
            leading=12.5,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
        ),
        "body_center": ParagraphStyle(
            "BodyCenter",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=9.4,
            leading=12.5,
            alignment=TA_CENTER,
            spaceAfter=6,
        ),
        "body_bold": ParagraphStyle(
            "BodyBold",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=9.4,
            leading=12.5,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=8.4,
            leading=10,
            alignment=TA_CENTER,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=7.3,
            leading=8.7,
            alignment=TA_LEFT,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=7.3,
            leading=8.7,
            alignment=TA_LEFT,
        ),
        "cell_center": ParagraphStyle(
            "CellCenter",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=7.3,
            leading=8.7,
            alignment=TA_CENTER,
        ),
        "cell_right": ParagraphStyle(
            "CellRight",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=7.3,
            leading=8.7,
            alignment=TA_RIGHT,
        ),
        "toc": ParagraphStyle(
            "Toc",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=10,
            leading=13,
            alignment=TA_LEFT,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(str(text)), style)


def _cell(text: str, style: ParagraphStyle) -> Paragraph:
    escaped = "<br/>".join(html.escape(part) for part in str(text).split("\n"))
    return Paragraph(escaped, style)


def _numbered_paragraph(paragraph: Dict, styles: Dict[str, ParagraphStyle]) -> Table:
    table = Table(
        [[_cell(paragraph["no"], styles["body_bold"]), _cell(paragraph["text"], styles["body"])]],
        colWidths=[1.05 * cm, 15.9 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 0),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _numbered(no: str, text: str) -> Dict:
    return {"no": no, "text": text}


def _table_data(rows: List[Dict], styles: Dict[str, ParagraphStyle], unit_label: str) -> List[List[Paragraph]]:
    data = [
        [
            _cell("No", styles["cell_bold"]),
            _cell("Particulars", styles["cell_bold"]),
            _cell(f"MYT Order dated\n25.06.2022\n({unit_label})", styles["cell_bold"]),
            _cell(f"Actual\n({unit_label})", styles["cell_bold"]),
            _cell(f"Sought for TU\n({unit_label})", styles["cell_bold"]),
            _cell(f"Deviation from approval\n({unit_label})", styles["cell_bold"]),
        ]
    ]
    if not rows:
        data.append(
            [
                _cell("-", styles["cell_center"]),
                _cell("No mapped canonical line item", styles["cell"]),
                _cell("-", styles["cell_right"]),
                _cell("-", styles["cell_right"]),
                _cell("-", styles["cell_right"]),
                _cell("-", styles["cell_right"]),
            ]
        )
        return data

    for row in rows:
        unit = row.get("unit") or unit_label or "Rs. Cr."
        cell_style = styles["cell_bold"] if row.get("is_total") else styles["cell"]
        data.append(
            [
                _cell(row.get("no", ""), styles["cell_center"]),
                _cell(row.get("display_name") or "-", cell_style),
                _cell(_fmt_value(row.get("arr_approved_value"), unit), styles["cell_right"]),
                _cell(_fmt_value(row.get("petition_actual_value"), unit), styles["cell_right"]),
                _cell(_fmt_value(row.get("petition_claimed_value"), unit), styles["cell_right"]),
                _cell(_fmt_value(row.get("deviation_value"), unit), styles["cell_right"]),
            ]
        )
    return data


def _regulatory_table(chapter: Dict, styles: Dict[str, ParagraphStyle]) -> List:
    caption = f"{chapter['table_no']} {chapter['table_caption']}"
    unit_label = chapter.get("unit_label") or "Rs. Cr."
    return _regulatory_table_for_rows(chapter.get("rows") or [], caption, unit_label, styles)


def _regulatory_table_for_rows(
    rows: List[Dict],
    caption: str,
    unit_label: str,
    styles: Dict[str, ParagraphStyle],
) -> List:
    data = _table_data(rows, styles, unit_label)
    table = Table(
        data,
        colWidths=[0.75 * cm, 5.35 * cm, 2.85 * cm, 2.45 * cm, 2.65 * cm, 2.9 * cm],
        repeatRows=1,
    )

    style_commands = [
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (0, 0), (-1, 0), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]
    for index, row in enumerate(rows, start=1):
        if row.get("is_total"):
            style_commands.append(("FONTNAME", (0, index), (-1, index), "Times-Bold"))
    table.setStyle(TableStyle(style_commands))
    return [_p(caption, styles["caption"]), table, Spacer(1, 7)]


def _title_info_table(meta: Dict, styles: Dict[str, ParagraphStyle]) -> Table:
    label_style = styles["body_bold"]
    value_style = styles["body"]
    rows = [
        [
            _cell("Present             :", label_style),
            _cell("\n".join(meta["present"]), value_style),
        ],
        [
            _cell("In the matter of     :", label_style),
            _cell(meta["matter"], value_style),
        ],
        [
            _cell("Petitioner           :", label_style),
            _cell(meta["petitioner"] + "\n" + "\n".join(meta["petitioner_address"]), value_style),
        ],
    ]
    table = Table(rows, colWidths=[4.2 * cm, 12.5 * cm])
    table.setStyle(
        TableStyle(
            [
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def _signature_table(meta: Dict, styles: Dict[str, ParagraphStyle]) -> Table:
    names = ["T K Jose", "Adv. A J Wilson", "B Pradeep"]
    roles = ["Chairman", "Member", "Member"]
    table = Table(
        [
            ["Sd/-", "Sd/-", "Sd/-"],
            names,
            roles,
        ],
        colWidths=[5.55 * cm, 5.55 * cm, 5.55 * cm],
    )
    table.setStyle(
        TableStyle(
            [
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("FONTNAME", (0, 1), (-1, 1), "Times-Roman"),
                ("FONTNAME", (0, 2), (-1, 2), "Times-Roman"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("TOPPADDING", (0, 0), (-1, -1), 2),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
            ]
        )
    )
    return table


def _build_title_page(story: List, context: Dict, styles: Dict[str, ParagraphStyle]) -> None:
    meta = context["case_metadata"]
    story.append(_p(meta["commission"], styles["commission"]))
    story.append(_p(meta["place"], styles["place"]))
    story.append(_title_info_table(meta, styles))
    story.append(Spacer(1, 0.15 * cm))
    story.append(_p(meta["op_number"], styles["title"]))
    story.append(_p(f"ORDER DATED {meta['order_date']}", styles["title"]))
    story.append(
        _p(
            (
                "In compliance to Regulation 27(6) of KSERC (Conduct of Business) "
                "Regulations, 2003, the Kerala State Electricity Regulatory Commission "
                f"having considered the petition for approval of the Truing up of Accounts "
                f"for the year {meta['financial_year']} filed by Kerala State Electricity "
                "Board Limited, has prepared the following draft order for internal review."
            ),
            styles["body"],
        )
    )
    story.append(
        _p(
            (
                "After having carefully considered the submissions and documents on record "
                "and in exercise of the powers vested in the Commission under Sections 62 "
                "and 64 of the Electricity Act, 2003 and KSERC (Terms and Conditions for "
                "Determination of Tariff) Regulations, 2021, the Commission may pass the "
                "following Order after due review."
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 0.2 * cm))
    story.append(_p(meta["dated_this"], styles["body"]))
    story.append(Spacer(1, 0.35 * cm))
    story.append(_signature_table(meta, styles))
    story.append(PageBreak())


def _build_toc(story: List, context: Dict, styles: Dict[str, ParagraphStyle]) -> None:
    story.append(_p("Table of Contents", styles["chapter_title"]))
    data = [
        [
            _cell("Sl No", styles["cell_bold"]),
            _cell("Particulars", styles["cell_bold"]),
            _cell("Pages", styles["cell_bold"]),
        ]
    ]
    for entry in context["toc_entries"]:
        data.append(
            [
                _cell(entry["sl_no"], styles["cell_center"]),
                _cell(entry["particulars"], styles["toc"]),
                _cell(entry["pages"], styles["cell_right"]),
            ]
        )
    toc_table = Table(data, colWidths=[1.4 * cm, 13.1 * cm, 2.3 * cm])
    toc_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.35, colors.black),
                ("LEFTPADDING", (0, 0), (-1, -1), 2),
                ("RIGHTPADDING", (0, 0), (-1, -1), 2),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
            ]
        )
    )
    story.append(toc_table)
    story.append(PageBreak())


def _build_chapter(story: List, chapter: Dict, styles: Dict[str, ParagraphStyle]) -> None:
    story.append(_p(chapter["chapter_no"], styles["chapter_no"]))
    story.append(_p(chapter["title"], styles["chapter_title"]))
    for section in chapter["sections"]:
        story.append(_p(section["heading"], styles["section"]))
        for paragraph in section["paragraphs"]:
            story.append(_numbered_paragraph(paragraph, styles))
        if section.get("table") == "primary":
            story.extend(_regulatory_table(chapter, styles))


def _cyclic_rows(rows: List[Dict], offset: int, count: int = 4) -> List[Dict]:
    if not rows:
        return []
    selected = []
    for index in range(count):
        source = rows[(offset + index) % len(rows)]
        row = dict(source)
        row["no"] = index + 1
        selected.append(row)
    return selected


def _topic_from_rows(rows: List[Dict], fallback: str, offset: int) -> str:
    if not rows:
        return fallback
    return rows[offset % len(rows)].get("display_name") or fallback


def _row_analysis_text(row: Optional[Dict]) -> str:
    if not row:
        return (
            "No mapped canonical value is available for this issue in the current extraction set. "
            "The page is retained to preserve the structure of the regulatory order and the item "
            "may be populated when the corresponding value is mapped from the uploaded documents."
        )

    unit = row.get("unit") or "Rs. Cr."
    return (
        f"For {row.get('display_name')}, the approved value as per the MYT Order dated "
        f"25.06.2022 is {_fmt_value(row.get('arr_approved_value'), unit)} {unit}, the actual "
        f"value is {_fmt_value(row.get('petition_actual_value'), unit)} {unit}, and the amount "
        f"sought for truing up is {_fmt_value(row.get('petition_claimed_value'), unit)} {unit}. "
        f"The deviation from approval is {_fmt_value(row.get('deviation_value'), unit)} {unit}."
    )


def _opening_page(story: List, chapter: Dict, styles: Dict[str, ParagraphStyle]) -> None:
    story.append(_p(chapter["chapter_no"], styles["chapter_no"]))
    story.append(_p(chapter["title"], styles["chapter_title"]))
    story.append(_p("Introduction" if chapter["key"] != "introduction" else "Background", styles["section"]))
    story.append(_numbered_paragraph({"no": f"{chapter['chapter_index']}.1", "text": chapter["intro"]}, styles))

    if chapter["key"] == "introduction":
        for paragraph in chapter.get("background_paragraphs", [])[1:]:
            story.append(_numbered_paragraph(paragraph, styles))

    story.extend(
        _regulatory_table_for_rows(
            chapter.get("summary_table") or [],
            chapter["summary_caption"],
            chapter.get("unit_label") or "Rs. Cr.",
            styles,
        )
    )


def _issue_page(story: List, chapter: Dict, issue: Dict, styles: Dict[str, ParagraphStyle]) -> None:
    story.append(_p(chapter["chapter_no"], styles["chapter_no"]))
    story.append(_p(chapter["title"], styles["chapter_title"]))
    story.append(_p(issue["title"], styles["section"]))
    for paragraph in issue["paragraphs"][:4]:
        story.append(_numbered_paragraph(paragraph, styles))
    story.append(_p("Analysis and decision of the Commission", styles["section"]))
    story.append(_p(issue["analysis"], styles["body"]))
    story.append(_p(issue["draft_decision"], styles["body"]))
    if issue.get("table_rows"):
        story.extend(
            _regulatory_table_for_rows(
                issue["table_rows"],
                f"{issue.get('table_no', 'Table')} {issue['title']}",
                chapter.get("unit_label") or "Rs. Cr.",
                styles,
            )
        )


def _supporting_chapter_page(
    story: List,
    chapter: Dict,
    local_index: int,
    styles: Dict[str, ParagraphStyle],
) -> None:
    chapter_index = chapter["chapter_index"]
    section_patterns = (
        (
            "Stakeholder comments",
            chapter["stakeholder_placeholder"],
        ),
        (
            "Provisions in regulations",
            "The relevant provisions of the Electricity Act, 2003 and the KSERC Tariff Regulations, 2021 shall be applied while examining this part of the claim.",
        ),
        (
            "Documents considered",
            "The draft relies on uploaded ARR Order values, uploaded petition values and canonical comparison rows available in the report context.",
        ),
        (
            "Views of the Commission",
            "The Commission may examine the supporting schedules, audited accounts and clarifications submitted by KSEB Ltd before arriving at a final decision.",
        ),
        (
            "Chapter decision",
            chapter["chapter_decision"],
        ),
    )
    heading, text = section_patterns[local_index % len(section_patterns)]
    focus_topics = (
        "petition records",
        "audited accounts reconciliation",
        "ARR&ERC Order dated 25.06.2022",
        "MYT framework",
        "stakeholder submissions",
        "supporting schedules",
        "variance review",
        "regulatory treatment",
        "officer verification",
        "draft order safeguards",
    )
    focus = focus_topics[local_index % len(focus_topics)]
    paragraph_no = (local_index + 1) * 3

    story.append(_p(chapter["title"], styles["chapter_title"]))
    story.append(_p(f"{heading} - Part {local_index}", styles["section"]))
    for offset, paragraph_text in enumerate(
        (
            f"{text} The specific focus of this part is {focus}.",
            f"This part is retained in the deterministic regulatory order structure for {chapter['sbu_name']} and does not introduce any unmapped financial value.",
            f"Final approval, disallowance or modification of matters related to {focus} shall remain subject to verification and decision by authorized officers.",
        )
    ):
        story.append(
            _numbered_paragraph(
                {"no": f"{chapter_index}.{paragraph_no + offset}", "text": paragraph_text},
                styles,
            )
        )


def _introduction_page(story: List, chapter: Dict, local_index: int, styles: Dict[str, ParagraphStyle]) -> None:
    if local_index == 0:
        _opening_page(story, chapter, styles)
        return

    story.append(_p(chapter["chapter_no"], styles["chapter_no"]))
    story.append(_p(chapter["title"], styles["chapter_title"]))
    if local_index == 1:
        story.append(_p("Statutory provisions", styles["section"]))
        paragraphs = chapter["statutory_paragraphs"]
    elif local_index == 2:
        story.append(_p("MYT framework provisions", styles["section"]))
        paragraphs = chapter["documents_paragraphs"]
    elif local_index == 3:
        story.append(_p("Public hearing and stakeholder comments", styles["section"]))
        paragraphs = [
            _numbered("1.7", chapter["stakeholder_placeholder"]),
            _numbered("1.8", chapter["chapter_decision"]),
        ]
    else:
        story.append(_p("Scope of draft order", styles["section"]))
        paragraphs = [
            _numbered(
                f"1.{local_index + 5}",
                "This part records procedural background and preserves space for officer-reviewed submissions in the final regulatory order.",
            ),
            _numbered(
                f"1.{local_index + 6}",
                "No item-wise financial analysis is recorded in Chapter-1; such analysis is arranged in the respective SBU chapters.",
            ),
        ]
    for paragraph in paragraphs:
        story.append(_numbered_paragraph(paragraph, styles))


def _chapter_detail_page(
    story: List,
    chapter: Dict,
    local_index: int,
    styles: Dict[str, ParagraphStyle],
) -> None:
    if chapter["key"] == "introduction":
        _introduction_page(story, chapter, local_index, styles)
        return
    if local_index == 0:
        _opening_page(story, chapter, styles)
        return

    issue_index = local_index - 1
    if issue_index < len(chapter.get("issue_blocks") or []):
        _issue_page(story, chapter, chapter["issue_blocks"][issue_index], styles)
        return

    _supporting_chapter_page(story, chapter, local_index, styles)


def _annexure_page(
    story: List,
    context: Dict,
    page_number: int,
    annexure_index: int,
    styles: Dict[str, ParagraphStyle],
) -> None:
    rows = context.get("comparison_tables") or []
    story.append(_p(f"Annexure-{annexure_index}", styles["chapter_no"]))
    story.append(_p("Schedule of Mapped Canonical Values", styles["chapter_title"]))
    story.append(
        _p(
            (
                "This annexure is generated deterministically from canonical comparison rows "
                "available in the report context. It excludes extraction metadata, raw labels, "
                "tariff slabs, consumer category rows and other non-reportable records."
            ),
            styles["body"],
        )
    )
    story.append(
        _numbered_paragraph(
            {
                "no": f"A.{annexure_index}",
                "text": (
                    "The values shown below are placed only for internal review and "
                    "cross-verification with uploaded ARR Order and Truing-Up Petition PDFs."
                ),
            },
            styles,
        )
    )
    story.extend(
        _regulatory_table_for_rows(
            _cyclic_rows(rows, annexure_index * 4, 5),
            f"Annexure Table A.{annexure_index} Canonical value schedule",
            "Rs. Cr.",
            styles,
        )
    )
    story.append(
        _p(
            "The Commission may rely only on verified records and duly submitted documents "
            "before issuing any final regulatory decision.",
            styles["body"],
        )
    )


def _build_exact_full_order_story(
    story: List,
    context: Dict,
    officer_name: str,
    styles: Dict[str, ParagraphStyle],
) -> None:
    _build_title_page(story, context, styles)
    _build_toc(story, context, styles)

    chapters = context["order_chapters"]
    for key, start_page, end_page in FULL_ORDER_CHAPTER_RANGES:
        chapter = chapters[key]
        for offset, _page_number in enumerate(range(start_page, end_page + 1)):
            _chapter_detail_page(story, chapter, offset, styles)
            story.append(PageBreak())

    for annexure_index, page_number in enumerate(range(ANNEXURE_START_PAGE, ANNEXURE_END_PAGE + 1), 1):
        _annexure_page(story, context, page_number, annexure_index, styles)
        story.append(PageBreak())

    _build_final_order(story, context, officer_name, styles, include_page_break=False)


def _build_final_order(
    story: List,
    context: Dict,
    officer_name: str,
    styles: Dict[str, ParagraphStyle],
    include_page_break: bool = True,
) -> None:
    if include_page_break:
        story.append(PageBreak())
    story.append(_p("Order of the Commission", styles["chapter_no"]))
    story.append(_p("Final Order", styles["chapter_title"]))
    story.append(
        _numbered_paragraph(
            {
                "no": "8.1",
                "text": (
                    "The draft summary above is placed for internal review and verification. "
                    "The Commission may take appropriate decision after examining the details "
                    "submitted by KSEB Ltd."
                ),
            },
            styles,
        )
    )
    story.append(_p(context["final_summary"]["disclaimer"], styles["body"]))
    story.append(Spacer(1, 0.8 * cm))
    story.append(_signature_table(context["case_metadata"], styles))
    story.append(Spacer(1, 0.4 * cm))
    story.append(_p(f"Prepared by: {officer_name}", styles["body_center"]))


def _footer(canvas, doc) -> None:
    canvas.saveState()
    width, _ = A4
    canvas.setFont("Times-Roman", 9)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(width / 2, 0.95 * cm, str(doc.page))
    canvas.restoreState()


def _generate_order_pdf_reportlab(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("PDF generation unavailable. Install reportlab or playwright.")

    context = build_report_context(case_id, financial_year, comparisons, reviews, officer_name)
    validate_report_context(context)
    styles = _styles()

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.45 * cm,
        leftMargin=1.45 * cm,
        topMargin=1.45 * cm,
        bottomMargin=1.45 * cm,
    )

    story: List = []
    _build_exact_full_order_story(story, context, officer_name, styles)

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    with open(file_path, "rb") as pdf_file:
        file_hash = hashlib.sha256(pdf_file.read()).hexdigest()

    return {
        "file_path": file_path,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": os.path.getsize(file_path),
    }


def _normalise_text(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip().lower()


def _flatten_context_text(value) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten_context_text(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten_context_text(item) for item in value)
    return str(value or "")


def validate_report_context(context: Dict) -> None:
    """Fail fast when chapter composition violates deterministic report rules."""
    chapters = context.get("order_chapters") or {}
    errors: List[str] = []

    for key in ("sbu_g", "sbu_t"):
        chapter_text = _flatten_context_text(chapters.get(key, {})).lower()
        if "purchase of power" in chapter_text:
            errors.append(f"Purchase of Power leaked into {key}.")

    for key in ("sbu_g", "sbu_t", "sbu_d", "energy_sales_td_loss", "common_expenses"):
        chapter = chapters.get(key) or {}
        for row in chapter.get("summary_table") or []:
            if row.get("section") and row.get("section") != key:
                errors.append(
                    f"{row.get('display_name')} with section {row.get('section')} rendered in {key}."
                )

    for key, chapter in chapters.items():
        issue_ids = [issue.get("issue_id") for issue in chapter.get("issue_blocks") or []]
        duplicates = sorted({issue_id for issue_id in issue_ids if issue_ids.count(issue_id) > 1})
        if duplicates:
            errors.append(f"Duplicate issue blocks in {key}: {', '.join(duplicates)}.")

    captions: List[str] = []
    for chapter in chapters.values():
        if chapter.get("summary_caption"):
            captions.append(chapter["summary_caption"])
        for issue in chapter.get("issue_blocks") or []:
            if issue.get("table_rows"):
                captions.append(f"{issue.get('table_no', 'Table')} {issue['title']}")
    duplicate_captions = sorted({caption for caption in captions if captions.count(caption) > 1})
    if duplicate_captions:
        errors.append(f"Repeated table captions: {', '.join(duplicate_captions)}.")

    full_text = _flatten_context_text(context).lower()
    for banned in BANNED_PDF_STRINGS:
        if banned.lower() in full_text:
            errors.append(f"Banned report text found in context: {banned}.")
    if "draft regulatory order page" in full_text:
        errors.append("Debug footer text found in context.")

    if errors:
        raise ValueError("Invalid report_context for KSERC order: " + " ".join(errors))


def score_reference_fidelity(pdf_text: str) -> Dict:
    """
    Return a simple deterministic structural score out of 100.

    The score checks order-format markers from the KSERC reference, table and
    paragraph structure, final-order signatures, and absence of extraction noise.
    """
    text = pdf_text or ""
    norm = _normalise_text(text)

    def has(marker: str) -> bool:
        return marker.lower() in norm

    checks = []

    title_markers = [
        "KERALA STATE ELECTRICITY REGULATORY COMMISSION",
        "THIRUVANANTHAPURAM",
        "Present",
        "In the matter of",
        "Petitioner",
        "ORDER DATED",
        "OP. No",
    ]
    title_score = round(15 * sum(1 for marker in title_markers if has(marker)) / len(title_markers), 2)
    checks.append(("title_page_markers", title_score, 15))

    toc_markers = ["Table of Contents", "Sl No", "Particulars", "Pages", "Chapter-1", "Chapter-2"]
    toc_score = round(10 * sum(1 for marker in toc_markers if has(marker)) / len(toc_markers), 2)
    checks.append(("toc_markers", toc_score, 10))

    chapter_markers = [
        "CHAPTER -1",
        "INTRODUCTION",
        "Statutory provisions",
        "CHAPTER-2",
        "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT",
        "Analysis and decision of the Commission",
        "Consolidated Truing up",
    ]
    chapter_score = round(15 * sum(1 for marker in chapter_markers if has(marker)) / len(chapter_markers), 2)
    checks.append(("chapter_markers", chapter_score, 15))

    paragraph_count = len(re.findall(r"\b[1-8]\.\d+\b", text))
    paragraph_score = 10 if paragraph_count >= 8 else round(10 * paragraph_count / 8, 2)
    checks.append(("paragraph_numbering", paragraph_score, 10))

    table_caption_count = len(re.findall(r"\bTable[- ]\d+\.\d+\b", text, flags=re.IGNORECASE))
    table_score = 10 if table_caption_count >= 4 else round(10 * table_caption_count / 4, 2)
    checks.append(("table_caption_count", table_score, 10))

    header_markers = [
        "MYT Order dated",
        "25.06.2022",
        "Actual",
        "Sought for TU",
        "Deviation from approval",
    ]
    header_score = round(10 * sum(1 for marker in header_markers if has(marker)) / len(header_markers), 2)
    checks.append(("table_header_similarity", header_score, 10))

    final_markers = ["Order of the Commission", "Final Order", "internal review", "authorized officers"]
    final_score = round(10 * sum(1 for marker in final_markers if has(marker)) / len(final_markers), 2)
    checks.append(("final_order_markers", final_score, 10))

    signature_count = len(re.findall(r"Sd\s*/-", text))
    signature_score = 10 if signature_count >= 3 else round(10 * signature_count / 3, 2)
    checks.append(("signature_markers", signature_score, 10))

    leaked = [banned for banned in BANNED_PDF_STRINGS if banned.lower() in norm]
    banned_score = 10 if not leaked else 0
    checks.append(("absence_of_banned_noise", banned_score, 10))

    score = min(100, round(sum(item[1] for item in checks), 2))
    return {
        "score": score,
        "checks": [
            {"name": name, "score": score_value, "max_score": max_score}
            for name, score_value, max_score in checks
        ],
        "table_caption_count": table_caption_count,
        "paragraph_number_count": paragraph_count,
        "banned_strings_found": leaked,
    }


async def generate_order_pdf(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    """Generate a deterministic KSERC-style draft order PDF."""
    if REPORTLAB_AVAILABLE:
        return _generate_order_pdf_reportlab(case_id, financial_year, comparisons, reviews, officer_name)

    if not PLAYWRIGHT_AVAILABLE:
        raise RuntimeError("PDF generation unavailable. Install reportlab or playwright.")

    html_content = generate_order_html(case_id, financial_year, comparisons, reviews, officer_name)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            await page.pdf(
                path=file_path,
                format="A4",
                print_background=False,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template=(
                    "<div style='font-family:Times New Roman,serif;font-size:9pt;"
                    "text-align:center;width:100%;'><span class='pageNumber'></span></div>"
                ),
                margin={"top": "1.45cm", "bottom": "1.45cm", "left": "1.45cm", "right": "1.45cm"},
            )
            await browser.close()
    except Exception:
        return _generate_order_pdf_reportlab(case_id, financial_year, comparisons, reviews, officer_name)

    with open(file_path, "rb") as pdf_file:
        file_hash = hashlib.sha256(pdf_file.read()).hexdigest()

    return {
        "file_path": file_path,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": os.path.getsize(file_path),
    }
