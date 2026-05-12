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
import os
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional

try:
    from weasyprint import HTML, CSS
    WEASYPRINT_AVAILABLE = True
except ImportError:
    WEASYPRINT_AVAILABLE = False


# ─── Output Directory ───

OUTPUT_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "mvp_generated"
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
    total_variance = total_actual - total_approved
    
    # Build comparison table rows
    comparison_rows = ""
    for c in comparisons:
        approved = c.get("approved_value")
        actual = c.get("actual_value")
        variance = c.get("variance")
        variance_pct = c.get("variance_percent")
        decision = c.get("decision_class", "PENDING")
        
        approved_str = f"₹{approved:,.2f}" if approved is not None else "—"
        actual_str = f"₹{actual:,.2f}" if actual is not None else "—"
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
        
        comparison_rows += f"""
        <tr>
            <td style="border:1px solid #D1D5DB;padding:8px;font-size:11px;">{c.get('canonical_name', '')}{review_note}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{approved_str}</td>
            <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;font-size:11px;">{actual_str}</td>
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

    <!-- SECTION 3: REGULATORY FRAMEWORK -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            2. REGULATORY FRAMEWORK
        </h3>
        <p style="text-align:justify;line-height:1.7;font-size:11px;">
            This Order is passed under the provisions of the Electricity Act, 2003
            (Central Act 36 of 2003), specifically Sections 61, 62, and 64, and in
            accordance with the KSERC Multi-Year Tariff Regulations, 2021 (as amended).
        </p>
        <ul style="font-size:11px;line-height:1.8;">
            <li><strong>Regulation 5.1</strong> — O&amp;M Escalation (CPI:WPI 70:30)</li>
            <li><strong>Regulation 6.3</strong> — Normative Interest (SBI EBLR + 2%)</li>
            <li><strong>Regulation 7.4</strong> — T&amp;D Loss Target Trajectory</li>
            <li><strong>Regulation 9.1–9.4</strong> — Gain/Loss Sharing Mechanism</li>
        </ul>
    </div>

    <!-- SECTION 4: ARR COMPARISON TABLE -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            3. ARR COMPARISON — APPROVED vs ACTUAL
        </h3>
        <p style="font-size:11px;margin-bottom:10px;">
            The following table presents a line-by-line comparison of the Approved ARR against
            the Actual audited figures as submitted in the Truing-Up Petition.
        </p>
        <table style="width:100%;border-collapse:collapse;font-size:11px;">
            <thead>
                <tr style="background-color:#F3F4F6;">
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:left;">Line Item</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Approved (Rs. Cr.)</th>
                    <th style="border:1px solid #D1D5DB;padding:8px;text-align:right;">Actual (Rs. Cr.)</th>
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
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;color:{_variance_color(total_variance / total_approved * 100 if total_approved else 0)};">₹{total_variance:,.2f}</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:right;">{(total_variance / total_approved * 100 if total_approved else 0):+.1f}%</td>
                    <td style="border:1px solid #D1D5DB;padding:8px;text-align:center;">—</td>
                </tr>
            </tfoot>
        </table>
    </div>

    <!-- SECTION 5: VARIANCE ANALYSIS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            4. VARIANCE ANALYSIS SUMMARY
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

    <!-- SECTION 6: OFFICER REMARKS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            5. OFFICER REMARKS
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

    <!-- SECTION 7: RECOMMENDATIONS -->
    <div style="margin-bottom:25px;">
        <h3 style="font-size:13px;font-weight:bold;border-bottom:1px solid #1F2937;padding-bottom:5px;">
            6. SUMMARY RECOMMENDATIONS
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


def generate_order_pdf(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: List[Dict],
    officer_name: str = "Demo Officer",
) -> Dict:
    """
    Generate a KSERC-style PDF order.
    
    Returns dict with file_path, file_hash, file_size.
    """
    if not WEASYPRINT_AVAILABLE:
        raise RuntimeError("WeasyPrint is not installed. Run: pip install weasyprint")
    
    html_content = generate_order_html(
        case_id, financial_year, comparisons, reviews, officer_name
    )
    
    # CSS for PDF styling
    css_content = """
        @page {
            size: A4;
            margin: 2.5cm 2cm 2.5cm 2cm;
            @top-center {
                content: "DRAFT GENERATED FOR REVIEW";
                font-size: 16pt;
                color: rgba(220, 38, 38, 0.12);
                font-weight: bold;
            }
            @bottom-center {
                content: "Page " counter(page) " of " counter(pages);
                font-size: 9pt;
                color: #9CA3AF;
            }
        }
        body {
            font-family: "Times New Roman", Georgia, serif;
            font-size: 11pt;
            line-height: 1.6;
            color: #1F2937;
        }
    """
    
    # Generate filename
    timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    filename = f"KSERC_TruingUp_{financial_year}_{timestamp}.pdf"
    file_path = os.path.join(OUTPUT_DIR, filename)
    
    # Generate PDF
    html = HTML(string=html_content)
    css = CSS(string=css_content)
    html.write_pdf(file_path, stylesheets=[css])
    
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
