"""
MVP PDF Generator — Generates KSERC-style truing-up draft orders.

Uses ReportLab by default, with optional Playwright rendering, to generate
A4 PDF documents with:
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
from typing import List, Dict, Optional

try:
    from .config import get_settings
except ImportError:  # Support direct imports from the backend directory.
    from config import get_settings

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

settings = get_settings()
OUTPUT_DIR = str(settings.generated_reports_dir)
settings.generated_reports_dir.mkdir(parents=True, exist_ok=True)


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


def _semantic_section_for_cost_head(cost_head: Optional[str], row_label: Optional[str] = None) -> str:
    if cost_head:
        normalized = cost_head.strip().lower()
    else:
        normalized = (row_label or "").strip().lower()

    if any(token in normalized for token in ("power purchase", "generation", "hydro", "coal", "fuel")):
        return "Generation & Power Purchase"
    if any(token in normalized for token in ("transmission", "wheeling", "t&d", "t d", "t & d", "loss")):
        return "Transmission & Wheeling"
    if any(token in normalized for token in ("o&m", "o & m", "operation", "maintenance", "employee", "repair", "a&g", "a & g")):
        return "Distribution & O&M"
    if any(token in normalized for token in ("interest", "finance", "depreciation", "return on equity", "roe", "return")):
        return "Finance, Depreciation & Return"
    if any(token in normalized for token in ("revenue gap", "arr" , "approved", "claimed", "revenue")):
        return "Revenue Gap & Summary"
    return "Other Regulatory Items"


def _format_currency(value: Optional[float]) -> str:
    return f"₹{value:,.2f}" if value is not None else "—"


def _build_semantic_report(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str,
) -> Dict:
    report = {
        "case_id": case_id,
        "financial_year": financial_year,
        "officer_name": officer_name,
        "generated_at": datetime.utcnow(),
        "total_items": len(comparisons),
        "groups": [],
        "summary": {},
        "findings": [],
        "observations": [],
    }

    review_by_comp = {r.get("comparison_id"): r for r in reviews}
    groups: Dict[str, Dict] = {}

    for c in comparisons:
        category = _semantic_section_for_cost_head(c.get("cost_head"), c.get("canonical_name"))
        group = groups.setdefault(category, {
            "name": category,
            "items": [],
            "approved": 0.0,
            "actual": 0.0,
            "claimed": 0.0,
            "variance": 0.0,
            "auto_count": 0,
            "review_count": 0,
        })
        group["items"].append(c)
        group["approved"] += c.get("approved_value") or 0.0
        group["actual"] += c.get("actual_value") or 0.0
        group["claimed"] += c.get("claimed_value") or 0.0
        group["variance"] += c.get("variance") or 0.0
        if c.get("decision_class") == "AI_AUTO":
            group["auto_count"] += 1
        else:
            group["review_count"] += 1

    # Sort groups in regulatory priority order
    priority = [
        "Generation & Power Purchase",
        "Transmission & Wheeling",
        "Distribution & O&M",
        "Finance, Depreciation & Return",
        "Revenue Gap & Summary",
        "Other Regulatory Items",
    ]
    ordered_groups = sorted(groups.values(), key=lambda g: priority.index(g["name"]) if g["name"] in priority else len(priority))

    for group in ordered_groups:
        items = sorted(group["items"], key=lambda item: abs(item.get("variance") or 0.0), reverse=True)
        group["top_issues"] = items[:5]
        group["total_items"] = len(items)
        group["positive_variance_count"] = sum(1 for item in items if (item.get("variance") or 0) > 0)
        group["negative_variance_count"] = sum(1 for item in items if (item.get("variance") or 0) < 0)
        group["review_notes"] = [review_by_comp.get(item.get("id")) for item in items if review_by_comp.get(item.get("id"))]

    total_approved = sum(c.get("approved_value") or 0.0 for c in comparisons)
    total_actual = sum(c.get("actual_value") or 0.0 for c in comparisons)
    total_claimed = sum(c.get("claimed_value") or 0.0 for c in comparisons)
    total_variance = total_actual - total_approved
    auto_items = sum(1 for c in comparisons if c.get("decision_class") == "AI_AUTO")
    review_items = len(comparisons) - auto_items

    report["groups"] = ordered_groups
    report["summary"] = {
        "total_approved": total_approved,
        "total_actual": total_actual,
        "total_claimed": total_claimed,
        "total_variance": total_variance,
        "auto_items": auto_items,
        "review_items": review_items,
    }

    # Findings and observations
    if total_variance > 0:
        report["findings"].append(
            f"The Petition indicates a net revenue gap of { _format_currency(total_variance) } relative to the approved ARR baseline."
        )
    elif total_variance < 0:
        report["findings"].append(
            f"The Petition indicates a net surplus of { _format_currency(abs(total_variance)) } relative to the approved ARR baseline."
        )
    else:
        report["findings"].append(
            "The Petition totals are in line with the approved ARR baseline with no net variance."
        )

    if review_items:
        report["findings"].append(
            f"{review_items} line item(s) have been flagged for further officer review due to significant variance or low extraction confidence."
        )
    else:
        report["findings"].append(
            "All line items are within auto-routing thresholds and are flagged as suitable for preliminary approval."
        )

    report["observations"].append(
        "The Commission has examined the Petition and ARR Order submissions. The draft order presents structured, chapter-wise findings and supports officer review without relying on a raw extraction dump."
    )
    report["observations"].append(
        "All values in this draft are sourced from extracted comparison rows, and the narrative is based on semantic groupings of the underlying financial categories."
    )

    return report


def _render_summary_table_html(group: Dict) -> str:
    rows = ""
    for item in group.get("top_issues", []):
        rows += f"""
        <tr>
            <td style=\"border:1px solid #D1D5DB;padding:8px;font-size:11px;\">{html_lib.escape(item.get('canonical_name', ''))}</td>
            <td style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;\">{_format_currency(item.get('approved_value'))}</td>
            <td style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;\">{_format_currency(item.get('actual_value'))}</td>
            <td style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;\">{_format_currency(item.get('variance'))}</td>
            <td style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;\">{_fmt_percent(item.get('variance_percent'))}</td>
        </tr>
        """
    return f"""
    <div style=\"margin-top:18px;\">
        <h4 style=\"font-size:12px;font-weight:bold;margin-bottom:8px;\">Summary of Key Issues — {group.get('name')} </h4>
        <table style=\"width:100%;border-collapse:collapse;font-size:11px;\">
            <thead>
                <tr style=\"background-color:#F3F4F6;\">
                    <th style=\"border:1px solid #D1D5DB;padding:8px;text-align:left;\">Item</th>
                    <th style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;\">Approved</th>
                    <th style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;\">Actual</th>
                    <th style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;\">Variance</th>
                    <th style=\"border:1px solid #D1D5DB;padding:8px;text-align:right;\">Variance %</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
    </div>
    """


def _render_chapter_html(group: Dict) -> str:
    heading = group.get("name")
    if not heading:
        heading = "Other Regulatory Items"
    narrative = (
        f"The Commission notes the {group.get('total_items')} items under {heading}. "
        f"Approved amounts total { _format_currency(group.get('approved')) }, actual amounts total { _format_currency(group.get('actual')) }, "
        f"and the aggregate variance is { _format_currency(group.get('variance')) }. "
        f"{group.get('review_count')} item(s) are routed for review." 
    )
    return f"""
    <div style=\"margin-bottom:25px;\">
        <h3 style=\"font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;\">{html_lib.escape(heading)}</h3>
        <p style=\"text-align:justify;line-height:1.7;font-size:11px;\">{html_lib.escape(narrative)}</p>
        {_render_summary_table_html(group)}
    </div>
    """


def _render_findings_html(report: Dict) -> str:
    items = ""
    for finding in report.get("findings", []):
        items += f"<li style=\"margin-bottom:6px;\">{html_lib.escape(finding)}</li>\n"
    return f"""
    <div style=\"margin-bottom:25px;\">
        <h3 style=\"font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;\">Findings and Decisions</h3>
        <ol style=\"font-size:11px;line-height:1.8;\">{items}</ol>
    </div>
    """


def _render_observations_html(report: Dict) -> str:
    items = ""
    for observation in report.get("observations", []):
        items += f"<p style=\"text-align:justify;line-height:1.7;font-size:11px;margin-bottom:10px;\">{html_lib.escape(observation)}</p>\n"
    return f"""
    <div style=\"margin-bottom:25px;\">
        <h3 style=\"font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;\">Commission Observations</h3>
        {items}
    </div>
    """


def _render_objections_html(reviews: List[Dict]) -> str:
    if not reviews:
        return (
            "<div style='margin-bottom:25px;'>"
            "<h3 style='font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;'>Stakeholder Objections and Commission Views</h3>"
            "<p style='text-align:justify;line-height:1.7;font-size:11px;'>"
            "No structured stakeholder objection text was extracted from the uploaded documents in this run."
            "</p>"
            "</div>"
        )

    rows = ""
    for review in reviews:
        rows += (
            "<tr>"
            f"<td style='border:1px solid #D1D5DB;padding:8px;font-size:11px;'>{html_lib.escape(review.get('comparison_id', ''))}</td>"
            f"<td style='border:1px solid #D1D5DB;padding:8px;font-size:11px;'>{html_lib.escape(review.get('action', ''))}</td>"
            f"<td style='border:1px solid #D1D5DB;padding:8px;font-size:11px;'>{html_lib.escape(review.get('officer_comment', ''))}</td>"
            "</tr>"
        )
    return (
        "<div style='margin-bottom:25px;'>"
        "<h3 style='font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;'>Stakeholder Objections and Commission Views</h3>"
        "<p style='text-align:justify;line-height:1.7;font-size:11px;'>The following officer review notes are presented for the Commission's consideration.</p>"
        "<table style='width:100%;border-collapse:collapse;font-size:11px;'>"
        "<thead><tr style='background-color:#F3F4F6;'><th style='border:1px solid #D1D5DB;padding:8px;text-align:left;'>Comparison ID</th>"
        "<th style='border:1px solid #D1D5DB;padding:8px;text-align:left;'>Action</th>"
        "<th style='border:1px solid #D1D5DB;padding:8px;text-align:left;'>Comment</th></tr></thead>"
        f"<tbody>{rows}</tbody>"
        "</table>"
        "</div>"
    )


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

    report = _build_semantic_report(case_id, financial_year, comparisons, reviews, officer_name)
    summary = report["summary"]
    group_map = {g["name"]: g for g in report["groups"]}

    def _render_section(title: str, body_html: str) -> str:
        return f"""
        <div style="margin-bottom:24px;page-break-inside:avoid;">
            <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:6px;margin-bottom:10px;">{html_lib.escape(title)}</h3>
            {body_html}
        </div>
        """

    def _render_paragraph(text: str) -> str:
        return f'<p style="text-align:justify;line-height:1.75;font-size:11px;margin:0 0 12px 0;">{html_lib.escape(text)}</p>'

    def _render_caption(text: str) -> str:
        return f'<p style="font-size:10px;font-weight:bold;margin:10px 0 4px 0;">{html_lib.escape(text)}</p>'

    def _render_totals_table() -> str:
        return f"""
        { _render_caption('Table 5.1: Summary of Approved ARR and Petition totals') }
        <table style="width:100%;border-collapse:collapse;font-size:11px;">
            <tbody>
                <tr>
                    <td style="border:1px solid #9CA3AF;padding:8px;font-weight:bold;width:52%;">Approved ARR Baseline</td>
                    <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;">{_format_currency(summary['total_approved'])}</td>
                </tr>
                <tr style="background:#F3F4F6;">
                    <td style="border:1px solid #9CA3AF;padding:8px;font-weight:bold;">Actual Petition Total</td>
                    <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;">{_format_currency(summary['total_actual'])}</td>
                </tr>
                <tr>
                    <td style="border:1px solid #9CA3AF;padding:8px;font-weight:bold;">Claimed Petition Total</td>
                    <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;">{_format_currency(summary['total_claimed'])}</td>
                </tr>
                <tr style="background:#EFF6FF;">
                    <td style="border:1px solid #9CA3AF;padding:8px;font-weight:bold;">Aggregate Variance</td>
                    <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;color:{_variance_color((summary['total_variance'] / summary['total_approved'] * 100) if summary['total_approved'] else None)};">{_format_currency(summary['total_variance'])}</td>
                </tr>
            </tbody>
        </table>
        """

    def _render_top_issues_table(group: Dict, caption: str) -> str:
        if not group.get('top_issues'):
            return _render_paragraph('The Commission did not identify material variances for this category in the extracted data.')

        rows = ''
        for item in group['top_issues']:
            rows += f"""
            <tr>
                <td style="border:1px solid #9CA3AF;padding:8px;font-size:11px;">{html_lib.escape(item.get('canonical_name', ''))}</td>
                <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;font-size:11px;">{_format_currency(item.get('approved_value'))}</td>
                <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;font-size:11px;">{_format_currency(item.get('actual_value'))}</td>
                <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;font-size:11px;">{_format_currency(item.get('variance'))}</td>
                <td style="border:1px solid #9CA3AF;padding:8px;text-align:right;font-size:11px;">{_fmt_percent(item.get('variance_percent'))}</td>
            </tr>
            """

        return f"""
        { _render_caption(caption) }
        <table style="width:100%;border-collapse:collapse;font-size:11px;">
            <thead>
                <tr style="background-color:#F3F4F6;">
                    <th style="border:1px solid #9CA3AF;padding:8px;text-align:left;">Item</th>
                    <th style="border:1px solid #9CA3AF;padding:8px;text-align:right;">Approved</th>
                    <th style="border:1px solid #9CA3AF;padding:8px;text-align:right;">Actual</th>
                    <th style="border:1px solid #9CA3AF;padding:8px;text-align:right;">Variance</th>
                    <th style="border:1px solid #9CA3AF;padding:8px;text-align:right;">Variance %</th>
                </tr>
            </thead>
            <tbody>
                {rows}
            </tbody>
        </table>
        """

    def _render_sbu_html(number: str, title: str, category: str) -> str:
        group = group_map.get(category, {
            'name': category,
            'total_items': 0,
            'approved': 0.0,
            'actual': 0.0,
            'claimed': 0.0,
            'variance': 0.0,
            'top_issues': [],
            'review_count': 0,
        })
        if group['total_items'] == 0:
            paragraph = f"The Commission did not identify a material issue requiring dedicated review under {category}."
        else:
            paragraph = (
                f"The Commission has reviewed {group['total_items']} item(s) classified under {category}. "
                f"Approved values total {_format_currency(group['approved'])}, actual values total {_format_currency(group['actual'])}, and the aggregate variance is {_format_currency(group['variance'])}. "
                f"{group['review_count']} item(s) have been routed for officer review under this category."
            )
        return _render_section(
            f"{number}. {title}",
            _render_paragraph(paragraph) + _render_top_issues_table(group, f"Table {number}.1: Key review issues for {title}")
        )

    # Build the final HTML document in a safe builder to avoid nested f-string parsing issues.
    html_parts = [
        '<!DOCTYPE html>',
        '<html lang="en">',
        '<head>',
        '    <meta charset="UTF-8">',
        f'    <title>KSERC Truing-Up Order — FY {html_lib.escape(financial_year)}</title>',
        '    <style>',
        '        body { font-family: "Times New Roman", Georgia, serif; font-size: 11pt; line-height: 1.75; color: #111827; margin: 0; }',
        '        .page-body { margin: 0 2cm; }',
        '        p { margin: 0 0 12px 0; }',
        '        table { width: 100%; border-collapse: collapse; margin-top: 6px; margin-bottom: 14px; page-break-inside: auto; }',
        '        th, td { border: 1px solid #9CA3AF; padding: 8px; vertical-align: top; }',
        '        th { background: #F3F4F6; font-weight: bold; }',
        '        .caption { font-size: 10px; margin-bottom: 4px; font-weight: bold; }',
        '        .footnote { font-size: 10px; color: #4B5563; margin-top: 8px; }',
        '        .signature-block { display: flex; justify-content: space-between; margin-top: 30px; }',
        '        .signature-cell { width: 30%; text-align: center; }',
        '    </style>',
        '</head>',
        '<body>',
        '    <div class="page-body">',
        '        <div style="text-align:center;margin-bottom:28px;">',
        '            <h1 style="font-size:18px;font-weight:bold;margin-bottom:8px;letter-spacing:1px;">KERALA STATE ELECTRICITY REGULATORY COMMISSION</h1>',
        '            <p style="font-size:11px;color:#6B7280;margin:0;">Thiruvananthapuram</p>',
        '            <div style="border-top:2px solid #1F2937;border-bottom:1px solid #9CA3AF;margin:15px 0;padding:10px 0;">',
        f'                <h2 style="font-size:14px;font-weight:bold;margin:0;">TRUING-UP ORDER FOR FY {html_lib.escape(financial_year)}</h2>',
        f'                <p style="font-size:11px;color:#6B5560;margin:6px 0 0 0;">OP. No. {html_lib.escape(case_id)} | Date: {html_lib.escape(order_date)}</p>',
        '            </div>',
        '            <p style="color:#B91C1C;font-weight:bold;font-size:12px;margin:0;">DRAFT FOR COMMISSION REVIEW</p>',
        '        </div>',
    ]

    html_parts.append(_render_section('1. Introduction', _render_paragraph('The Commission has examined the ARR Approval Order and the Truing-Up Petition submitted by Kerala State Electricity Board Ltd for the relevant year. This draft order records the Commission\'s review of approved ARR baselines, actual audited figures and claimed amounts extracted from the uploaded documents.')))
    html_parts.append(_render_section('2. Statutory Provisions', _render_paragraph('This draft order is issued pursuant to the KSERC Multi-Year Tariff Regulations and relevant sections of the Electricity Act. The Commission has applied the applicable regulatory provisions in examining the Petition and the approved ARR.')))
    html_parts.append(_render_section('3. MYT Framework References', _render_paragraph('The analysis follows the KSERC MYT framework for the control period, including normative treatment of revenue gaps, cost categories and SBU-level performance. The Commission has used the uploaded detail to align the Petition review with statutory tariff principles.')))
    html_parts.append(_render_section('4. Petition Summary', _render_paragraph(f'The Petition filed by KSEB Ltd has been examined for consistency with the approved ARR baseline. The extracted actual audited values total {_format_currency(summary["total_actual"])}, while claimed amounts total {_format_currency(summary["total_claimed"])}. {summary["auto_items"]} line item(s) are proposed for preliminary approval and {summary["review_items"]} item(s) require detailed officer review.')))
    html_parts.append(_render_section('5. ARR/ERC Summary Tables', _render_paragraph('The following table summarizes the approved ARR baseline, actual Petition audited values and claimed figures as extracted from the uploaded documents.') + _render_totals_table()))
    html_parts.append(_render_section('6. Stakeholder Objections', _render_paragraph('The objections and officer comments recorded in the workbench have been reviewed by the Commission. The following section organizes extracted review notes into the formal order structure.') + _render_objections_html(reviews)))

    commission_views = ''.join(
        f'<p style="text-align:justify;line-height:1.75;font-size:11px;margin:0 0 12px 0;">{html_lib.escape(observation)}</p>'
        for observation in report['observations']
    )
    html_parts.append(_render_section('7. Commission Views', commission_views))
    html_parts.append(_render_sbu_html('8', 'SBU-G Analysis', 'Generation & Power Purchase'))
    html_parts.append(_render_sbu_html('9', 'SBU-T Analysis', 'Transmission & Wheeling'))
    html_parts.append(_render_sbu_html('10', 'SBU-D Analysis', 'Distribution & O&M'))
    html_parts.append(_render_section('11. Consolidated Truing-Up', _render_paragraph(f'On a consolidated basis, the Commission notes an aggregate variance of {_format_currency(summary["total_variance"])} between the approved ARR and the Petition actuals. This draft order presents the truing-up position in accordance with the statutory review and recommends further officer verification where required.') + _render_totals_table()))
    html_parts.append(_render_section('12. Final Approval / Order', _render_paragraph('The Commission hereby directs that this draft truing-up order be placed before the appropriate bench for final approval. All recommendations are subject to final confirmation by the Commission and to any further documentary verifications deemed necessary by the office of the regulatory officer.')))

    html_parts.extend([
        '        <div class="signature-block">',
        '            <div class="signature-cell">',
        f'                <p style="margin:0;font-weight:bold;font-size:11px;">{html_lib.escape(officer_name)}</p>',
        '                <p style="margin:4px 0 0 0;font-size:9px;color:#4B5563;">Prepared By</p>',
        '            </div>',
        '            <div class="signature-cell">',
        '                <p style="margin:0;font-weight:bold;font-size:11px;">[Reviewing Officer]</p>',
        '                <p style="margin:4px 0 0 0;font-size:9px;color:#4B5563;">Reviewed By</p>',
        '            </div>',
        '            <div class="signature-cell">',
        '                <p style="margin:0;font-weight:bold;font-size:11px;">[Chairman, KSERC]</p>',
        '                <p style="margin:4px 0 0 0;font-size:9px;color:#4B5563;">Approved By</p>',
        '            </div>',
        '        </div>',
        f'        <p class="footnote">Case ID: {html_lib.escape(case_id)} | Generated: {html_lib.escape(now.isoformat())} | AI Decision Support System v1.0-MVP</p>',
        '    </div>',
        '</body>',
        '</html>',
    ])

    html = ''.join(html_parts)
    return html


def _generate_order_pdf_reportlab(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("PDF generation unavailable. Install playwright or reportlab.")

    report = _build_semantic_report(case_id, financial_year, comparisons, reviews, officer_name)
    summary = report["summary"]
    group_map = {g["name"]: g for g in report["groups"]}

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
        spaceAfter=4,
    )
    body = ParagraphStyle(
        "KSERCBody",
        parent=styles["BodyText"],
        fontSize=9,
        leading=13,
        alignment=TA_JUSTIFY,
        spaceAfter=8,
    )
    small = ParagraphStyle(
        "KSERCSmall",
        parent=styles["BodyText"],
        fontSize=8,
        leading=10,
        spaceAfter=6,
    )

    story = [
        _p("KERALA STATE ELECTRICITY REGULATORY COMMISSION", title),
        _p("Thiruvananthapuram", subtitle),
        _p(f"TRUING-UP ORDER FOR FY {financial_year}", title),
        _p(f"Case ID: {case_id} | Date: {datetime.utcnow().strftime('%d.%m.%Y')}", subtitle),
        _p("DRAFT FOR COMMISSION REVIEW", ParagraphStyle(
            "DraftNotice",
            parent=styles["Normal"],
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
            fontSize=10,
            textColor=colors.HexColor("#B91C1C"),
            spaceAfter=12,
        )),
    ]

    story.append(_p("1. Introduction", section))
    story.append(_p("The Commission has examined the ARR Approval Order and the Truing-Up Petition submitted by Kerala State Electricity Board Ltd for the relevant year. This draft order records the Commission's review of approved ARR baselines, actual audited figures and claimed amounts extracted from the uploaded documents.", body))

    story.append(_p("2. Statutory Provisions", section))
    story.append(_p("This draft order is issued pursuant to the KSERC Multi-Year Tariff Regulations and the Electricity Act. The Commission has applied applicable regulatory provisions in examining the Petition and the approved ARR.", body))

    story.append(_p("3. MYT Framework References", section))
    story.append(_p("The analysis follows the KSERC MYT framework for the control period, including normative treatment of revenue gaps, cost categories and SBU-level performance.", body))

    story.append(_p("4. Petition Summary", section))
    story.append(_p(f"The Petition filed by KSEB Ltd has been examined for consistency with the approved ARR baseline. The extracted actual audited values total {_format_currency(summary['total_actual'])}, while claimed amounts total {_format_currency(summary['total_claimed'])}. {summary['auto_items']} line item(s) are proposed for preliminary approval and {summary['review_items']} item(s) require detailed officer review.", body))

    summary_table_data = [
        ["Summary", "Amount"],
        ["Approved ARR Baseline", _format_currency(summary['total_approved'])],
        ["Actual Petition Total", _format_currency(summary['total_actual'])],
        ["Claimed Petition Total", _format_currency(summary['total_claimed'])],
        ["Aggregate Variance", _format_currency(summary['total_variance'])],
    ]
    summary_table = Table(summary_table_data, colWidths=[10.5 * cm, 4.5 * cm])
    summary_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F3F4F6")),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9CA3AF")),
        ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]))
    story.append(summary_table)

    def _add_sbu_section(title: str, category: str):
        group = group_map.get(category, None)
        story.append(_p(title, section))
        if not group or group['total_items'] == 0:
            story.append(_p(f"The Commission did not identify a material issue requiring dedicated review under {category}.", body))
            return
        story.append(_p(f"The Commission reviewed {group['total_items']} item(s) classified under {category}. Approved values total {_format_currency(group['approved'])}, actual values total {_format_currency(group['actual'])}, and the aggregate variance is {_format_currency(group['variance'])}.", body))
        story.append(_p("The key items requiring officer attention are listed below.", body))
        top_data = [["Item", "Approved", "Actual", "Variance", "Variance %"]]
        for item in group['top_issues']:
            top_data.append([
                item.get('canonical_name', ''),
                _format_currency(item.get('approved_value')),
                _format_currency(item.get('actual_value')),
                _format_currency(item.get('variance')),
                _fmt_percent(item.get('variance_percent')),
            ])
        story.append(Table(top_data, colWidths=[6.0 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm, 2.2 * cm], repeatRows=1))

    _add_sbu_section("8. SBU-G Analysis", "Generation & Power Purchase")
    _add_sbu_section("9. SBU-T Analysis", "Transmission & Wheeling")
    _add_sbu_section("10. SBU-D Analysis", "Distribution & O&M")

    story.append(_p("11. Consolidated Truing-Up", section))
    story.append(_p(f"On a consolidated basis, the Commission notes an aggregate variance of {_format_currency(summary['total_variance'])} between the approved ARR and the Petition actuals. The draft order proposes further officer verification on items that are routed for review.", body))

    story.append(_p("12. Final Approval / Order", section))
    story.append(_p(f"The Commission hereby directs that this draft order be placed before the appropriate bench for final approval. All recommendations in this draft are evidence-based and subject to final confirmation by the Commission.", body))

    story.append(_p(officer_name, section))
    story.append(_p("Prepared By", small))
    story.append(_p("[Reviewing Officer]", section))
    story.append(_p("Reviewed By", small))
    story.append(_p("[Chairman, KSERC]", section))
    story.append(_p("Approved By", small))

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
    if settings.pdf_engine == "reportlab" or not PLAYWRIGHT_AVAILABLE:
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
