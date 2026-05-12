"""
MVP PDF Generator — Generates KSERC-style truing-up draft orders.

Uses WeasyPrint to generate A4 PDF documents with:
- KSERC header and branding
- ARR comparison tables
- Variance analysis with color-coded flags
- Officer remarks
- Summary recommendations
- "DRAFT GENERATED FOR REVIEW" watermark
"""

import hashlib
import html as html_lib
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

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


# ─── Output Directory ───

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "output"
)
os.makedirs(OUTPUT_DIR, exist_ok=True)


def _variance_color(variance_pct: Optional[float]) -> str:
    """Get color for variance highlighting."""
    if variance_pct is None:
        return "#6B7280"  # gray
    if abs(variance_pct) < 5:
        return "#059669"  # green
    if abs(variance_pct) < 15:
        return "#D97706"  # amber
    return "#DC2626"  # red


def _fmt_money(value: Optional[float]) -> str:
    return f"{value:,.2f}" if value is not None else "-"


def _fmt_percent(value: Optional[float]) -> str:
    return f"{value:+.1f}%" if value is not None else "-"


def _decision_badge(decision_class: str) -> str:
    """Generate HTML badge for decision classification."""
    if decision_class == "AI_AUTO":
        return '<span style="background:#059669;color:#fff;padding:2px 8px;border-radius:3px;font-size:9px;">✓ AUTO-APPROVED</span>'
    elif decision_class == "REVIEW_REQUIRED":
        return '<span style="background:#DC2626;color:#fff;padding:2px 8px;border-radius:3px;font-size:9px;">⚠ REVIEW REQUIRED</span>'
    return '<span style="background:#6B7280;color:#fff;padding:2px 8px;border-radius:3px;font-size:9px;">◌ PENDING</span>'


def generate_order_html(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> str:
    """
    Generate HTML for a KSERC-style truing-up draft order.
    """
    now = datetime.utcnow()
    order_date = now.strftime("%d.%m.%Y")
    
    # Aggregate stats
    total_items = len(comparisons)
    auto_items = sum(1 for c in comparisons if c.get("decision_class") == "AI_AUTO")
    review_items = total_items - auto_items
    
    total_approved = sum(c.get("approved_value", 0) or 0 for c in comparisons)
    total_actual = sum(c.get("actual_value", 0) or 0 for c in comparisons)
    total_claimed = sum(c.get("claimed_value", 0) or 0 for c in comparisons)
    total_variance = total_actual - total_approved
    
    # Build comparison table rows
    comparison_rows = ""
    for c in comparisons:
        approved = c.get("approved_value")
        actual = c.get("actual_value")
        claimed = c.get("claimed_value")
        variance = c.get("variance")
        variance_pct = c.get("variance_percent")
        decision = c.get("decision_class", "PENDING")
        
        approved_str = f"₹{approved:,.2f}" if approved is not None else "—"
        actual_str = f"₹{actual:,.2f}" if actual is not None else "—"
        claimed_str = f"₹{claimed:,.2f}" if claimed is not None else "—"
        variance_str = f"₹{variance:,.2f}" if variance is not None else "—"
        variance_pct_str = f"{variance_pct:+.1f}%" if variance_pct is not None else "—"
        
        color = _variance_color(variance_pct)
        badge = _decision_badge(decision)
        
        # Check if there's a review for this item
        review_note = ""
        for r in reviews:
            if r.get("comparison_id") == c.get("id"):
                action = r.get("action", "")
                comment = r.get("officer_comment", "")
                review_note = f'<div style="font-size:9px;color:#4B5563;margin-top:4px;">Officer: {action.upper()} — {comment}</div>'
                break

        provenance_bits = []
        if c.get("approved_source_page"):
            provenance_bits.append(f"ARR p.{c.get('approved_source_page')}")
        if c.get("actual_source_page"):
            provenance_bits.append(f"Petition p.{c.get('actual_source_page')}")
        if provenance_bits:
            review_note += f'<div style="font-size:8px;color:#6B7280;margin-top:3px;">Source: {"; ".join(provenance_bits)}</div>'
        
        comparison_rows += f"""
        <tr>
            <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;">{html_lib.escape(str(c.get('canonical_name', '')))}{review_note}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{approved_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{actual_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{claimed_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;color:{color};font-weight:600;">{variance_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;color:{color};">{variance_pct_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:center;font-size:11px;">{badge}</td>
        </tr>
        """
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>KSERC Truing-Up Order — FY {financial_year}</title>
</head>
<body>
    <!-- SECTION 1: HEADER -->
    <div style="text-align:center;margin-bottom:30px;">
        <h1 style="font-size:18px;font-weight:bold;margin-bottom:8px;letter-spacing:1px;">
            KERALA STATE ELECTRICITY REGULATORY COMMISSION
        </h1>
        <p style="font-size:11px;color:#6B7280;margin:0;">Thiruvananthapuram, Kerala, India</p>
        <div style="border-top:2px solid #1F2937;border-bottom:1px solid #9CA3AF;margin:15px 0;padding:8px 0;">
            <h2 style="font-size:14px;font-weight:bold;margin:0;">
                TRUING-UP ORDER FOR FY {financial_year}
            </h2>
            <p style="font-size:11px;color:#6B7280;margin:4px 0 0 0;">
                Case ID: {case_id} &nbsp;|&nbsp; Order Date: {order_date}
            </p>
        </div>
        <p style="color:#DC2626;font-weight:bold;font-size:12px;">
            ⚠ DRAFT GENERATED FOR REVIEW — NOT FOR OFFICIAL USE
        </p>
    </div>

    <!-- SECTION 2: INTRODUCTION -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            1. INTRODUCTION
        </h3>
        <p style="text-align:justify;line-height:1.7;font-size:11px;">
            The Kerala State Electricity Regulatory Commission ("the Commission") hereby issues
            this Truing-Up Order for the Financial Year {financial_year} for Kerala State
            Electricity Board Ltd. (KSEBL). This Order is the outcome of the Truing-Up process
            mandated under the KSERC Multi-Year Tariff (MYT) Framework for the Control Period
            2022-27. The Commission has reviewed the Petition filed by the Utility, compared
            the Approved Annual Revenue Requirement (ARR) against Actual audited figures, and
            applied the applicable regulatory norms.
        </p>
    </div>

    <!-- SECTION 3: ARR BASELINE SUMMARY -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            2. ARR BASELINE SUMMARY
        </h3>
        <p style="text-align:justify;line-height:1.7;font-size:11px;">
            The approved ARR baseline extracted from the ARR Approval Order for FY
            {financial_year} aggregates to <strong>₹{total_approved:,.2f} Cr.</strong>
            across the normalized line items available for comparison.
        </p>
    </div>

    <!-- SECTION 4: PETITION SUMMARY -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            3. PETITION SUMMARY
        </h3>
        <p style="text-align:justify;line-height:1.7;font-size:11px;">
            The Petition extracted actual audited values totaling
            <strong>₹{total_actual:,.2f} Cr.</strong> and claimed values totaling
            <strong>₹{total_claimed:,.2f} Cr.</strong>. The figures below are generated
            from source tables with page-level provenance retained for officer review.
        </p>
    </div>

    <!-- SECTION 5: ARR COMPARISON TABLE -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            4. COMPARISON TABLE — APPROVED vs ACTUAL vs CLAIMED
        </h3>
        <p style="font-size:11px;margin-bottom:10px;">
            The following table presents a line-by-line comparison of the Approved ARR against
            the Actual audited and Claimed figures as submitted in the Truing-Up Petition.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:11px;">
            <thead>
                <tr style="background-color:#F3F4F6;">
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:left;">Line Item</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Approved (Rs. Cr.)</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Actual (Rs. Cr.)</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Claimed (Rs. Cr.)</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Variance (Rs. Cr.)</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Variance %</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:center;">Status</th>
                </tr>
            </thead>
            <tbody>
                {comparison_rows}
            </tbody>
            <tfoot>
                <tr style="background-color:#EFF6FF;font-weight:bold;">
                    <td style="border:1px solid #D1D5DB;padding:8px;">TOTAL</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;">₹{total_approved:,.2f}</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;">₹{total_actual:,.2f}</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;">₹{total_claimed:,.2f}</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;color:{_variance_color(total_variance / total_approved * 100 if total_approved else 0)};">₹{total_variance:,.2f}</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;">{(total_variance / total_approved * 100 if total_approved else 0):+.1f}%</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:center;">—</td>
                </tr>
            </tfoot>
        </table>
    </div>

    <!-- SECTION 6: VARIANCE ANALYSIS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            5. VARIANCE ANALYSIS
        </h3>
        <table style="width:60%;border-collapse:collapse;margin:15px 0;">
            <tr>
                <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;font-weight:bold;">Total Line Items Analyzed</td>
                <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{total_items}</td>
            </tr>
            <tr style="background:#F0FDF4;">
                <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;font-weight:bold;color:#059669;">Auto-Approved (variance &lt; 15%)</td>
                <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;color:#059669;">{auto_items}</td>
            </tr>
            <tr style="background:#FEF2F2;">
                <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;font-weight:bold;color:#DC2626;">Review Required (variance ≥ 15%)</td>
                <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;color:#DC2626;">{review_items}</td>
            </tr>
            <tr>
                <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;font-weight:bold;">Total Revenue Gap</td>
                <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;font-weight:bold;">₹{total_variance:,.2f} Cr.</td>
            </tr>
        </table>
    </div>

    <!-- SECTION 7: AI OBSERVATIONS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            6. AI OBSERVATIONS
        </h3>
        <p style="font-size:11px;line-height:1.7;">
            The DSS applies deterministic variance checks only. Items with variance below
            15% and sufficient extraction confidence are routed as AI_AUTO; items at or
            above 15%, missing values, or low confidence are routed to REVIEW_REQUIRED.
        </p>
    </div>

    <!-- SECTION 8: OFFICER REMARKS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            7. OFFICER REMARKS
        </h3>
        <p style="font-size:11px;line-height:1.7;">
            This draft order has been prepared by the AI Decision Support System and reviewed
            by <strong>{officer_name}</strong>. Items marked as "REVIEW REQUIRED" have been
            flagged for detailed examination due to significant variance or low extraction
            confidence.
        </p>
        <p style="font-size:11px;line-height:1.7;color:#6B7280;">
            <em>Note: The Commission must exercise final authority on all flagged items before
            this order can be finalized. AI-generated recommendations serve as decision support
            only and do not constitute regulatory decisions.</em>
        </p>
    </div>

    <!-- SECTION 9: FINAL SUMMARY -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            8. FINAL SUMMARY
        </h3>
        <ol style="font-size:11px;line-height:2;">
            <li>The Commission approves <strong>{auto_items}</strong> line items where the variance is within acceptable limits.</li>
            <li><strong>{review_items}</strong> items require detailed manual review by the regulatory officer.</li>
            <li>The total revenue gap of <strong>₹{total_variance:,.2f} Cr.</strong> is subject to final determination.</li>
            <li>All decisions are traceable to source documents with page-level provenance.</li>
        </ol>
    </div>

    <!-- FOOTER -->
    <div style="border-top:2px solid #1F2937;padding-top:20px;margin-top:40px;">
        <div style="display:flex;justify-content:space-between;margin-top:40px;">
            <div style="width:30%;text-align:center;">
                <p style="margin:0;font-weight:bold;font-size:11px;">{officer_name}</p>
                <p style="margin:4px 0;font-size:9px;color:#6B7280;">Prepared By</p>
            </div>
            <div style="width:30%;text-align:center;">
                <p style="margin:0;font-weight:bold;font-size:11px;">[Reviewing Officer]</p>
                <p style="margin:4px 0;font-size:9px;color:#6B7280;">Reviewed By</p>
            </div>
            <div style="width:30%;text-align:center;">
                <p style="margin:0;font-weight:bold;font-size:11px;">[Chairman, KSERC]</p>
                <p style="margin:4px 0;font-size:9px;color:#6B7280;">Approved By</p>
            </div>
        </div>
        <p style="text-align:center;margin-top:30px;font-size:9px;color:#9CA3AF;">
            Case ID: {case_id} &nbsp;|&nbsp; Generated: {now.isoformat()} &nbsp;|&nbsp;
            AI Decision Support System v1.0-MVP
        </p>
    </div>
</body>
</html>"""
    
    return html


def _reportlab_watermark(canvas, doc):
    """Draw draft watermark and footer on each generated page."""
    canvas.saveState()
    width, height = A4
    canvas.setFont("Helvetica-Bold", 28)
    canvas.setFillColor(colors.Color(0.8, 0.1, 0.1, alpha=0.12))
    canvas.translate(width / 2, height / 2)
    canvas.rotate(35)
    canvas.drawCentredString(0, 0, "DRAFT GENERATED FOR REVIEW")
    canvas.restoreState()

    canvas.saveState()
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.grey)
    canvas.drawCentredString(width / 2, 1.1 * cm, f"Page {doc.page}")
    canvas.restoreState()


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(html_lib.escape(str(text)), style)


def _generate_order_pdf_reportlab(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("PDF generation unavailable. Install playwright or reportlab.")

    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)

    doc = SimpleDocTemplate(
        file_path,
        pagesize=A4,
        rightMargin=1.4 * cm,
        leftMargin=1.4 * cm,
        topMargin=1.8 * cm,
        bottomMargin=1.8 * cm,
    )

    styles = getSampleStyleSheet()
    title = ParagraphStyle(
        "KSERCTitle",
        parent=styles["Title"],
        alignment=TA_CENTER,
        fontName="Helvetica-Bold",
        fontSize=14,
        leading=18,
        spaceAfter=8,
    )
    subtitle = ParagraphStyle(
        "KSERCSubtitle",
        parent=styles["Normal"],
        alignment=TA_CENTER,
        fontSize=9,
        textColor=colors.HexColor("#4B5563"),
        spaceAfter=10,
    )
    section = ParagraphStyle(
        "KSERCSection",
        parent=styles["Heading3"],
        fontName="Helvetica-Bold",
        fontSize=10,
        leading=13,
        textColor=colors.HexColor("#111827"),
        spaceBefore=8,
        spaceAfter=5,
    )
    body = ParagraphStyle(
        "KSERCBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        alignment=TA_JUSTIFY,
        spaceAfter=6,
    )
    small = ParagraphStyle(
        "KSERCSmall",
        parent=styles["BodyText"],
        fontSize=7,
        leading=9,
    )

    total_items = len(comparisons)
    auto_items = sum(1 for c in comparisons if c.get("decision_class") == "AI_AUTO")
    review_items = total_items - auto_items
    total_approved = sum(c.get("approved_value", 0) or 0 for c in comparisons)
    total_actual = sum(c.get("actual_value", 0) or 0 for c in comparisons)
    total_claimed = sum(c.get("claimed_value", 0) or 0 for c in comparisons)
    total_variance = total_actual - total_approved

    review_by_comp = {r.get("comparison_id"): r for r in reviews}
    story = [
        _p("KERALA STATE ELECTRICITY REGULATORY COMMISSION", title),
        _p("Thiruvananthapuram, Kerala, India", subtitle),
        _p(f"TRUING-UP ORDER FOR FY {financial_year}", title),
        _p(f"Case ID: {case_id} | Generated: {datetime.utcnow().strftime('%d.%m.%Y')}", subtitle),
        _p("DRAFT GENERATED FOR REVIEW", ParagraphStyle(
            "DraftNotice",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#B91C1C"),
            spaceAfter=12,
        )),
    ]

    sections = [
        ("1. Introduction",
         f"The Commission has reviewed the ARR Approval Order and the Truing-Up Petition for FY {financial_year}. This draft order compares approved baseline values against actual audited and claimed values extracted from the uploaded PDFs."),
        ("2. ARR Baseline Summary",
         f"The approved ARR baseline extracted from the ARR Approval Order totals Rs. {total_approved:,.2f} Cr. across the normalized comparison rows."),
        ("3. Petition Summary",
         f"The Petition extracted actual audited values totaling Rs. {total_actual:,.2f} Cr. and claimed values totaling Rs. {total_claimed:,.2f} Cr."),
        ("4. Comparison Tables",
         "The following table presents ARR approved, actual, claimed, variance, review routing, and source page traceability."),
    ]
    for heading, text in sections:
        story.append(_p(heading, section))
        story.append(_p(text, body))

    table_data = [[
        "Line Item",
        "ARR Approved",
        "Actual",
        "Claimed",
        "Variance",
        "Variance %",
        "Status / Source",
    ]]
    for c in comparisons:
        source = []
        if c.get("approved_source_page"):
            source.append(f"ARR p.{c.get('approved_source_page')}")
        if c.get("actual_source_page"):
            source.append(f"Petition p.{c.get('actual_source_page')}")
        status = c.get("decision_class", "PENDING")
        if c.get("flag_reason"):
            status = f"{status}\n{c.get('flag_reason')}"
        if source:
            status = f"{status}\n{'; '.join(source)}"
        review = review_by_comp.get(c.get("id"))
        if review:
            status = f"{status}\nOfficer: {review.get('action', '').upper()}"

        table_data.append([
            _p(c.get("canonical_name", ""), small),
            _fmt_money(c.get("approved_value")),
            _fmt_money(c.get("actual_value")),
            _fmt_money(c.get("claimed_value")),
            _fmt_money(c.get("variance")),
            _fmt_percent(c.get("variance_percent")),
            _p(status, small),
        ])

    table_data.append([
        "TOTAL",
        _fmt_money(total_approved),
        _fmt_money(total_actual),
        _fmt_money(total_claimed),
        _fmt_money(total_variance),
        _fmt_percent(total_variance / total_approved * 100 if total_approved else 0),
        "-",
    ])

    comparison_table = Table(
        table_data,
        colWidths=[4.0 * cm, 2.15 * cm, 2.15 * cm, 2.15 * cm, 2.0 * cm, 1.75 * cm, 3.1 * cm],
        repeatRows=1,
    )
    comparison_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E5E7EB")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 7),
        ("ALIGN", (1, 1), (5, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9CA3AF")),
        ("BACKGROUND", (0, -1), (-1, -1), colors.HexColor("#EFF6FF")),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("LEFTPADDING", (0, 0), (-1, -1), 4),
        ("RIGHTPADDING", (0, 0), (-1, -1), 4),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(comparison_table)
    story.append(Spacer(1, 10))

    remaining_sections = [
        ("5. Variance Analysis",
         f"{auto_items} line items are within auto-routing tolerance. {review_items} line items require officer review due to variance, missing values, or confidence thresholds. Total variance is Rs. {total_variance:,.2f} Cr."),
        ("6. AI Observations",
         "The DSS applies deterministic normalization and variance checks. It does not fabricate values; all numeric values in this draft come from extracted rows and persisted comparison records."),
        ("7. Officer Remarks",
         f"This draft has been prepared for review by {officer_name}. Officer comments and edits captured in the workbench are reflected in the comparison table where available."),
        ("8. Final Summary",
         "This draft order is generated for internal review only. The Commission must confirm all REVIEW_REQUIRED items before issuing any final regulatory order."),
    ]
    for heading, text in remaining_sections:
        story.append(_p(heading, section))
        story.append(_p(text, body))

    doc.build(story, onFirstPage=_reportlab_watermark, onLaterPages=_reportlab_watermark)

    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    file_size = os.path.getsize(file_path)

    return {
        "file_path": file_path,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": file_size,
    }


async def generate_order_pdf(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    """
    Generate a KSERC-style PDF order using Playwright.
    
    Returns dict with file_path, file_hash, file_size.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return _generate_order_pdf_reportlab(
            case_id, financial_year, comparisons, reviews, officer_name
        )
    
    from playwright.async_api import async_playwright
    
    html_content = generate_order_html(
        case_id, financial_year, comparisons, reviews, officer_name
    )
    
    # CSS for PDF styling
    css_content = """
        <style>
        body {
            font-family: "Times New Roman", Georgia, serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #1F2937;
        }
        table {
            page-break-inside: auto;
        }
        tr {
            page-break-inside: avoid;
            page-break-after: auto;
        }
        </style>
    """
    html_content = html_content.replace('</head>', f'{css_content}\\n</head>')
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    # Generate PDF using headless chromium. If the browser binary is absent,
    # fall back to ReportLab so demo PDF generation still succeeds.
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.set_content(html_content, wait_until="networkidle")
            await page.pdf(
                path=file_path,
                format="A4",
                print_background=True,
                display_header_footer=True,
                header_template="""<div style='font-size: 16pt; color: rgba(220, 38, 38, 0.12); font-weight: bold; text-align: center; width: 100%;'>DRAFT GENERATED FOR REVIEW</div>""",
                footer_template="""<div style='font-size: 9pt; color: #9CA3AF; text-align: center; width: 100%;'>Page <span class='pageNumber'></span> of <span class='totalPages'></span></div>""",
                margin={"top": "2.5cm", "bottom": "2.5cm", "left": "2cm", "right": "2cm"}
            )
            await browser.close()
    except Exception:
        return _generate_order_pdf_reportlab(
            case_id, financial_year, comparisons, reviews, officer_name
        )
    
    # Calculate hash and size
    with open(file_path, "rb") as f:
        file_hash = hashlib.sha256(f.read()).hexdigest()
    file_size = os.path.getsize(file_path)
    
    return {
        "file_path": file_path,
        "filename": filename,
        "file_hash": file_hash,
        "file_size": file_size,
    }
