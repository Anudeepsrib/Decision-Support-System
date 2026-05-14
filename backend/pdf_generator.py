"""
Deterministic KSERC-style draft order PDF generator.

The generator consumes a report_context built from canonical comparison rows.
It does not render raw extraction rows and does not call an LLM.
"""

from __future__ import annotations

import hashlib
import html
import os
from datetime import datetime
from typing import Dict, List, Optional

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


def _fmt_percent(value: Optional[float]) -> str:
    return "NA" if value is None else f"{value:+.2f}%"


def _status_label(status: Optional[str]) -> str:
    return (status or "INCOMPLETE_DATA").replace("_", " ")


def _chapter_heading(chapter: Dict) -> str:
    return f"{chapter['chapter_no']} - {chapter['title']}"


def _render_html_paragraph(text: str) -> str:
    return f"<p>{html.escape(text)}</p>"


def _render_html_table(rows: List[Dict], caption: str) -> str:
    if not rows:
        return "<p>No canonical comparison rows were mapped for this chapter.</p>"

    body = []
    for row in rows:
        row_class = "total-row" if row.get("is_total") else ""
        unit = row.get("unit") or "Rs. Cr."
        body.append(
            f"<tr class='{row_class}'>"
            f"<td>{row['no']}</td>"
            f"<td>{html.escape(row['display_name'])}</td>"
            f"<td class='num'>{html.escape(_fmt_value(row.get('arr_approved_value'), unit))}</td>"
            f"<td class='num'>{html.escape(_fmt_value(row.get('petition_actual_value'), unit))}</td>"
            f"<td class='num'>{html.escape(_fmt_value(row.get('petition_claimed_value'), unit))}</td>"
            f"<td class='num'>{html.escape(_fmt_value(row.get('deviation_value'), unit))}<br><span>{html.escape(_fmt_percent(row.get('deviation_percent')))}</span></td>"
            f"<td>{html.escape(_status_label(row.get('status')))}</td>"
            "</tr>"
        )

    return f"""
    <p class="caption">{html.escape(caption)}</p>
    <table>
        <thead>
            <tr>
                <th style="width:6%;">No</th>
                <th style="width:30%;">Particulars</th>
                <th>MYT Order / ARR Approved</th>
                <th>Actual</th>
                <th>Sought for TU / Claimed</th>
                <th>Deviation from Approval</th>
                <th>Status</th>
            </tr>
        </thead>
        <tbody>{''.join(body)}</tbody>
    </table>
    """


def _render_summary_html(summary: Dict) -> str:
    rows = [
        ("Approved ARR Baseline", summary.get("approved")),
        ("Actual Petition Total", summary.get("actual")),
        ("Claimed Petition Total", summary.get("claimed")),
        ("Deviation from Approval", summary.get("deviation")),
        ("Acceptable Variance Items", summary.get("acceptable")),
        ("Review Required Items", summary.get("review_required")),
        ("Incomplete Data Items", summary.get("incomplete")),
    ]
    body_parts = []
    for label, value in rows:
        if "Items" in label:
            formatted = str(value or 0)
        else:
            formatted = _fmt_value(_as_report_float(value), "Rs. Cr.")
        body_parts.append(
            f"<tr><td>{html.escape(label)}</td><td class='num'>{html.escape(formatted)}</td></tr>"
        )
    body = "".join(body_parts)
    return f"""
    <p class="caption">Table 7.1: Consolidated truing-up summary</p>
    <table class="summary-table"><tbody>{body}</tbody></table>
    """


def generate_order_html(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> str:
    """Generate deterministic KSERC-style HTML from report_context."""
    context = build_report_context(case_id, financial_year, comparisons, reviews, officer_name)
    meta = context["case_metadata"]
    chapters = context["chapters"]

    toc_items = "".join(
        f"<li>{html.escape(_chapter_heading(chapters[key]))}</li>"
        for key in context["chapter_sequence"]
    )

    parts = [
        "<!DOCTYPE html>",
        "<html lang='en'>",
        "<head>",
        "<meta charset='UTF-8'>",
        f"<title>KSERC Draft Truing-Up Order - FY {html.escape(financial_year)}</title>",
        "<style>",
        "@page { size: A4; margin: 2cm 1.7cm 2.1cm 1.7cm; }",
        "body { font-family: 'Times New Roman', Georgia, serif; color: #111; font-size: 11pt; line-height: 1.55; }",
        ".cover { text-align: center; min-height: 88vh; display: flex; flex-direction: column; justify-content: center; page-break-after: always; }",
        ".commission { font-size: 16pt; font-weight: bold; letter-spacing: .3px; margin-bottom: 10px; }",
        ".title { border-top: 1.5px solid #111; border-bottom: 1px solid #111; margin: 28px 0; padding: 16px 0; }",
        ".draft { font-weight: bold; margin-top: 20px; }",
        ".toc { page-break-after: always; }",
        ".chapter { page-break-before: always; }",
        "h1, h2, h3 { font-family: 'Times New Roman', Georgia, serif; color: #111; }",
        "h1 { font-size: 15pt; text-align: center; }",
        "h2 { font-size: 13pt; text-align: center; margin-top: 0; border-bottom: 1px solid #111; padding-bottom: 6px; }",
        "p { text-align: justify; margin: 0 0 10px 0; }",
        ".caption { font-weight: bold; font-size: 10pt; margin: 12px 0 4px 0; }",
        "table { width: 100%; border-collapse: collapse; margin: 4px 0 14px 0; page-break-inside: auto; }",
        "th, td { border: 1px solid #555; padding: 5px 6px; vertical-align: top; }",
        "th { background: #f0f0f0; font-weight: bold; text-align: center; }",
        "td.num { text-align: right; white-space: nowrap; }",
        ".total-row td { font-weight: bold; }",
        ".signature { margin-top: 36px; display: grid; grid-template-columns: repeat(3, 1fr); gap: 24px; text-align: center; }",
        ".signature div { border-top: 1px solid #111; padding-top: 6px; }",
        ".footer-note { font-size: 9pt; color: #444; margin-top: 24px; }",
        "</style>",
        "</head>",
        "<body>",
        "<section class='cover'>",
        "<div class='commission'>KERALA STATE ELECTRICITY REGULATORY COMMISSION</div>",
        "<div>Thiruvananthapuram</div>",
        "<div class='title'>",
        f"<h1>{html.escape(meta['order_type'].upper())}</h1>",
        f"<h1>TRUING UP OF ACCOUNTS FOR FY {html.escape(financial_year)}</h1>",
        f"<p style='text-align:center;'>Petitioner: {html.escape(meta['petitioner'])}</p>",
        f"<p style='text-align:center;'>Case ID: {html.escape(case_id)} | Date: {html.escape(meta['generated_date'])}</p>",
        "</div>",
        "<div class='draft'>DRAFT FOR INTERNAL REVIEW</div>",
        "</section>",
        "<section class='toc'>",
        "<h1>TABLE OF CONTENTS</h1>",
        f"<ul>{toc_items}<li>FINAL ORDER</li></ul>",
        "</section>",
    ]

    intro = chapters["introduction"]
    parts.append("<section class='chapter'>")
    parts.append(f"<h2>{html.escape(_chapter_heading(intro))}</h2>")
    parts.extend(_render_html_paragraph(paragraph) for paragraph in intro["paragraphs"])
    parts.append("</section>")

    for key in context["chapter_sequence"]:
        if key == "introduction":
            continue
        chapter = chapters[key]
        parts.append("<section class='chapter'>")
        parts.append(f"<h2>{html.escape(_chapter_heading(chapter))}</h2>")
        parts.append(_render_html_paragraph(chapter["opening"]))
        if key == "consolidated":
            parts.append(_render_summary_html(chapter["summary"]))
        else:
            parts.append(_render_html_table(chapter["rows"], f"Table {chapter['chapter_no'].split()[-1]}.1: {chapter['title']}"))
        parts.extend(_render_html_paragraph(observation) for observation in chapter["observations"])
        parts.append("</section>")

    parts.extend([
        "<section class='chapter'>",
        "<h2>FINAL ORDER</h2>",
        _render_html_paragraph("The draft summary above is placed for internal review and verification. Items requiring review shall be examined with source documents before final approval."),
        _render_html_paragraph(context["final_summary"]["disclaimer"]),
        "<div class='signature'>",
        f"<div>{html.escape(officer_name)}<br>Prepared By</div>",
        "<div>[Reviewing Officer]<br>Reviewed By</div>",
        "<div>[Commission Signatory]<br>Approved By</div>",
        "</div>",
        f"<p class='footer-note'>Generated: {html.escape(meta['generated_at'])} | Deterministic KSERC DSS MVP</p>",
        "</section>",
        "</body>",
        "</html>",
    ])

    return "".join(parts)


def _styles():
    styles = getSampleStyleSheet()
    return {
        "cover_title": ParagraphStyle(
            "CoverTitle",
            parent=styles["Title"],
            fontName="Times-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            spaceAfter=12,
        ),
        "cover_subtitle": ParagraphStyle(
            "CoverSubtitle",
            parent=styles["Normal"],
            fontName="Times-Roman",
            fontSize=11,
            leading=15,
            alignment=TA_CENTER,
            spaceAfter=8,
        ),
        "chapter": ParagraphStyle(
            "Chapter",
            parent=styles["Heading2"],
            fontName="Times-Bold",
            fontSize=13,
            leading=16,
            alignment=TA_CENTER,
            spaceBefore=6,
            spaceAfter=12,
        ),
        "body": ParagraphStyle(
            "Body",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=9.5,
            leading=13,
            alignment=TA_JUSTIFY,
            spaceAfter=8,
        ),
        "caption": ParagraphStyle(
            "Caption",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=8.5,
            leading=11,
            alignment=TA_LEFT,
            spaceBefore=8,
            spaceAfter=3,
        ),
        "small_center": ParagraphStyle(
            "SmallCenter",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=8,
            leading=10,
            alignment=TA_CENTER,
        ),
        "cell": ParagraphStyle(
            "Cell",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=7.4,
            leading=9,
            alignment=TA_LEFT,
        ),
        "cell_bold": ParagraphStyle(
            "CellBold",
            parent=styles["BodyText"],
            fontName="Times-Bold",
            fontSize=7.4,
            leading=9,
            alignment=TA_LEFT,
        ),
        "cell_right": ParagraphStyle(
            "CellRight",
            parent=styles["BodyText"],
            fontName="Times-Roman",
            fontSize=7.4,
            leading=9,
            alignment=TA_RIGHT,
        ),
    }


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(str(text)), style)


def _table_cell(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html.escape(str(text)), style)


def _comparison_table(rows: List[Dict], caption: str, styles: Dict[str, ParagraphStyle]) -> List:
    if not rows:
        return [_p("No canonical comparison rows were mapped for this chapter.", styles["body"])]

    data = [[
        _table_cell("No", styles["cell_bold"]),
        _table_cell("Particulars", styles["cell_bold"]),
        _table_cell("MYT Order / ARR Approved", styles["cell_bold"]),
        _table_cell("Actual", styles["cell_bold"]),
        _table_cell("Sought for TU / Claimed", styles["cell_bold"]),
        _table_cell("Deviation from Approval", styles["cell_bold"]),
        _table_cell("Status", styles["cell_bold"]),
    ]]

    for row in rows:
        unit = row.get("unit") or "Rs. Cr."
        deviation = _fmt_value(row.get("deviation_value"), unit)
        deviation_percent = _fmt_percent(row.get("deviation_percent"))
        cell_style = styles["cell_bold"] if row.get("is_total") else styles["cell"]
        right_style = styles["cell_right"]
        data.append([
            _table_cell(row["no"], cell_style),
            _table_cell(row["display_name"], cell_style),
            _table_cell(_fmt_value(row.get("arr_approved_value"), unit), right_style),
            _table_cell(_fmt_value(row.get("petition_actual_value"), unit), right_style),
            _table_cell(_fmt_value(row.get("petition_claimed_value"), unit), right_style),
            _table_cell(f"{deviation}\n{deviation_percent}", right_style),
            _table_cell(_status_label(row.get("status")), cell_style),
        ])

    table = Table(
        data,
        colWidths=[0.8 * cm, 4.0 * cm, 2.4 * cm, 2.1 * cm, 2.5 * cm, 2.5 * cm, 2.5 * cm],
        repeatRows=1,
    )
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#EDEDED")),
        ("FONTNAME", (0, 0), (-1, 0), "Times-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    for index, row in enumerate(rows, start=1):
        if row.get("is_total"):
            style_commands.append(("FONTNAME", (0, index), (-1, index), "Times-Bold"))
            style_commands.append(("BACKGROUND", (0, index), (-1, index), colors.HexColor("#F7F7F7")))
    table.setStyle(TableStyle(style_commands))
    return [_p(caption, styles["caption"]), table, Spacer(1, 8)]


def _summary_table(summary: Dict, styles: Dict[str, ParagraphStyle]) -> List:
    rows = [
        ("Approved ARR Baseline", _fmt_value(summary.get("approved"), "Rs. Cr.")),
        ("Actual Petition Total", _fmt_value(summary.get("actual"), "Rs. Cr.")),
        ("Claimed Petition Total", _fmt_value(summary.get("claimed"), "Rs. Cr.")),
        ("Deviation from Approval", _fmt_value(summary.get("deviation"), "Rs. Cr.")),
        ("Acceptable Variance Items", str(summary.get("acceptable") or 0)),
        ("Review Required Items", str(summary.get("review_required") or 0)),
        ("Incomplete Data Items", str(summary.get("incomplete") or 0)),
    ]
    data = [[_table_cell(label, styles["cell_bold"]), _table_cell(value, styles["cell_right"])] for label, value in rows]
    table = Table(data, colWidths=[11 * cm, 4 * cm])
    table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.35, colors.black),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F7F7F7")),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [_p("Table 7.1: Consolidated truing-up summary", styles["caption"]), table, Spacer(1, 8)]


def _footer(canvas, doc):
    canvas.saveState()
    width, _ = A4
    canvas.setFont("Times-Roman", 8)
    canvas.setFillColor(colors.black)
    canvas.drawCentredString(width / 2, 1.05 * cm, f"Page {doc.page}")
    canvas.setFont("Times-Roman", 7)
    canvas.drawRightString(width - 1.4 * cm, 1.05 * cm, "Draft for internal review")
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
    meta = context["case_metadata"]
    chapters = context["chapters"]
    styles = _styles()

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.35 * cm,
        leftMargin=1.35 * cm,
        topMargin=1.65 * cm,
        bottomMargin=1.65 * cm,
    )

    story: List = [
        Spacer(1, 4.2 * cm),
        _p("KERALA STATE ELECTRICITY REGULATORY COMMISSION", styles["cover_title"]),
        _p("Thiruvananthapuram", styles["cover_subtitle"]),
        Spacer(1, 1 * cm),
        _p(meta["order_type"].upper(), styles["cover_title"]),
        _p(f"TRUING UP OF ACCOUNTS FOR FY {financial_year}", styles["cover_title"]),
        Spacer(1, 0.6 * cm),
        _p(f"Petitioner: {meta['petitioner']}", styles["cover_subtitle"]),
        _p(f"Case ID: {case_id}", styles["cover_subtitle"]),
        _p(f"Date: {meta['generated_date']}", styles["cover_subtitle"]),
        Spacer(1, 1.2 * cm),
        _p("DRAFT FOR INTERNAL REVIEW", styles["cover_title"]),
        PageBreak(),
        _p("TABLE OF CONTENTS", styles["chapter"]),
    ]

    toc_data = []
    for key in context["chapter_sequence"]:
        chapter = chapters[key]
        toc_data.append([chapter["chapter_no"], chapter["title"]])
    toc_data.append(["", "FINAL ORDER"])
    toc_table = Table(toc_data, colWidths=[2.6 * cm, 12.4 * cm])
    toc_table.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.25, colors.white),
        ("FONTNAME", (0, 0), (-1, -1), "Times-Roman"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.extend([toc_table, PageBreak()])

    intro = chapters["introduction"]
    story.append(_p(_chapter_heading(intro), styles["chapter"]))
    for paragraph in intro["paragraphs"]:
        story.append(_p(paragraph, styles["body"]))

    for key in context["chapter_sequence"]:
        if key == "introduction":
            continue
        chapter = chapters[key]
        story.append(PageBreak())
        story.append(_p(_chapter_heading(chapter), styles["chapter"]))
        story.append(_p(chapter["opening"], styles["body"]))
        if key == "consolidated":
            story.extend(_summary_table(chapter["summary"], styles))
        else:
            chapter_no = chapter["chapter_no"].split()[-1]
            story.extend(_comparison_table(
                chapter["rows"],
                f"Table {chapter_no}.1: {chapter['title']}",
                styles,
            ))
        for observation in chapter["observations"]:
            story.append(_p(observation, styles["body"]))

    story.extend([
        PageBreak(),
        _p("FINAL ORDER", styles["chapter"]),
        _p("The draft summary above is placed for internal review and verification. Items requiring review shall be examined with source documents before final approval.", styles["body"]),
        _p(context["final_summary"]["disclaimer"], styles["body"]),
        Spacer(1, 1.4 * cm),
    ])

    signature = Table(
        [
            ["", "", ""],
            [officer_name, "[Reviewing Officer]", "[Commission Signatory]"],
            ["Prepared By", "Reviewed By", "Approved By"],
        ],
        colWidths=[5 * cm, 5 * cm, 5 * cm],
    )
    signature.setStyle(TableStyle([
        ("LINEABOVE", (0, 1), (-1, 1), 0.5, colors.black),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTNAME", (0, 1), (-1, 1), "Times-Bold"),
        ("FONTNAME", (0, 2), (-1, 2), "Times-Roman"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TOPPADDING", (0, 1), (-1, 1), 6),
    ]))
    story.append(signature)
    story.append(Spacer(1, 0.8 * cm))
    story.append(_p(f"Generated: {meta['generated_at']} | Deterministic KSERC DSS MVP", styles["small_center"]))

    doc.build(story, onFirstPage=_footer, onLaterPages=_footer)

    with open(file_path, "rb") as pdf_file:
        file_hash = hashlib.sha256(pdf_file.read()).hexdigest()

    return {
        "file_path": file_path,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": os.path.getsize(file_path),
    }


async def generate_order_pdf(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    """Generate a deterministic KSERC-style draft order PDF."""
    if settings.pdf_engine == "reportlab" or not PLAYWRIGHT_AVAILABLE:
        return _generate_order_pdf_reportlab(case_id, financial_year, comparisons, reviews, officer_name)

    html_content = generate_order_html(case_id, financial_year, comparisons, reviews, officer_name)
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
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
                print_background=True,
                display_header_footer=True,
                header_template="<div></div>",
                footer_template="<div style='font-size:8pt;text-align:center;width:100%;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>",
                margin={"top": "2cm", "bottom": "2cm", "left": "1.7cm", "right": "1.7cm"},
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
