"""
Build deterministic KSERC draft-order report context.

The PDF layer consumes only this context. It never renders raw extraction rows,
which prevents tariff slabs, low-confidence junk, and audit/debug data from
leaking into the stakeholder-facing order.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

try:
    from .canonical_registry import REGISTRY_BY_ID
except ImportError:  # Support direct imports from the backend directory.
    from canonical_registry import REGISTRY_BY_ID


def _as_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _row_from_comparison(index: int, comparison: Dict) -> Dict:
    canonical_id = comparison.get("canonical_id") or comparison.get("canonical_name") or ""
    registry_item = REGISTRY_BY_ID.get(canonical_id)
    display_name = (
        comparison.get("display_name")
        or (registry_item.display_name if registry_item else None)
        or comparison.get("canonical_name")
        or canonical_id
    )
    unit = comparison.get("unit") or (registry_item.unit if registry_item else "Rs. Cr.")
    sbu = comparison.get("sbu") or (registry_item.sbu if registry_item else comparison.get("cost_head") or "Other")
    section = comparison.get("section") or (registry_item.section if registry_item else "consolidated")
    is_total = bool(comparison.get("is_total") or (registry_item.is_total if registry_item else False))

    approved = _as_float(comparison.get("approved_value"))
    actual = _as_float(comparison.get("actual_value"))
    claimed = _as_float(comparison.get("claimed_value"))
    deviation = _as_float(comparison.get("variance"))
    deviation_percent = _as_float(comparison.get("variance_percent"))

    confidence_values = [
        _as_float(comparison.get("approved_confidence")),
        _as_float(comparison.get("actual_confidence")),
        _as_float(comparison.get("claimed_confidence")),
    ]
    confidence_values = [value for value in confidence_values if value is not None]

    return {
        "no": index,
        "comparison_id": comparison.get("id"),
        "canonical_id": canonical_id,
        "display_name": display_name,
        "sbu": sbu,
        "unit": unit,
        "section": section,
        "arr_approved_value": approved,
        "petition_actual_value": actual,
        "petition_claimed_value": claimed,
        "deviation_value": deviation,
        "deviation_percent": deviation_percent,
        "status": comparison.get("decision_class") or "INCOMPLETE_DATA",
        "flag_reason": comparison.get("flag_reason"),
        "source_arr_page": comparison.get("approved_source_page"),
        "source_petition_page": comparison.get("actual_source_page") or comparison.get("claimed_source_page"),
        "confidence": min(confidence_values) if confidence_values else None,
        "is_total": is_total,
    }


def _sum_rows(rows: Iterable[Dict], field: str) -> float:
    total = 0.0
    for row in rows:
        value = _as_float(row.get(field))
        if value is not None:
            total += value
    return round(total, 2)


def _section_summary(rows: List[Dict]) -> Dict:
    amount_rows = [row for row in rows if row.get("unit") == "Rs. Cr." and not row.get("is_total")]
    if not amount_rows:
        amount_rows = [row for row in rows if row.get("unit") == "Rs. Cr."]
    return {
        "approved": _sum_rows(amount_rows, "arr_approved_value"),
        "actual": _sum_rows(amount_rows, "petition_actual_value"),
        "claimed": _sum_rows(amount_rows, "petition_claimed_value"),
        "deviation": _sum_rows(amount_rows, "deviation_value"),
        "review_required": sum(1 for row in rows if row.get("status") == "REVIEW_REQUIRED"),
        "incomplete": sum(1 for row in rows if row.get("status") == "INCOMPLETE_DATA"),
        "acceptable": sum(1 for row in rows if row.get("status") == "ACCEPTABLE_VARIANCE"),
    }


def _key_deviations(rows: List[Dict], limit: int = 5) -> List[Dict]:
    return sorted(
        rows,
        key=lambda row: abs(_as_float(row.get("deviation_value")) or 0.0),
        reverse=True,
    )[:limit]


def _opening_for_sbu(sbu_name: str, rows: List[Dict]) -> str:
    if not rows:
        return (
            f"No canonical comparison rows were mapped for {sbu_name} from the uploaded ARR "
            "Order and Petition in this run."
        )
    return (
        f"The summary of ARR and ERC for {sbu_name} as extracted from the petition "
        "and compared with the approved values is given below."
    )


def _observations(rows: List[Dict]) -> List[str]:
    if not rows:
        return [
            "The Commission records that no mapped canonical line item is available for this chapter in the current extraction set."
        ]

    observations: List[str] = []
    for row in _key_deviations(rows, limit=3):
        status = row.get("status") or "REVIEW_REQUIRED"
        approved = row.get("arr_approved_value")
        deviation = row.get("deviation_value")
        if approved is None or deviation is None:
            observations.append(
                f"The claim under {row['display_name']} is marked as {status} because the extracted data is incomplete."
            )
        else:
            observations.append(
                f"The deviation in {row['display_name']} is {deviation:,.2f} {row['unit']} "
                f"against the approved value of {approved:,.2f} {row['unit']}. "
                f"The item has been marked as {status} for review."
            )

    observations.append(
        "The Commission has examined the claim under these heads. For the purpose of this draft report, each item is placed under the stated status based on the variance threshold and extraction confidence."
    )
    return observations


def build_report_context(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: Optional[List[Dict]] = None,
    officer_name: str = "Demo Officer",
) -> Dict:
    """Build the deterministic report_context consumed by PDF generators."""
    generated_at = datetime.utcnow()
    rows = [_row_from_comparison(index + 1, comparison) for index, comparison in enumerate(comparisons)]

    by_section: Dict[str, List[Dict]] = {}
    for row in rows:
        by_section.setdefault(row["section"], []).append(row)

    for section_rows in by_section.values():
        section_rows.sort(key=lambda row: (row.get("is_total"), row["display_name"]))
        for index, row in enumerate(section_rows, 1):
            row["no"] = index

    sbu_g_rows = by_section.get("sbu_g", [])
    sbu_t_rows = by_section.get("sbu_t", [])
    energy_rows = by_section.get("energy_sales_td_loss", [])
    sbu_d_rows = by_section.get("sbu_d", [])
    common_rows = by_section.get("common_expenses", [])

    all_amount_rows = [row for row in rows if row.get("unit") == "Rs. Cr." and not row.get("is_total")]
    if not all_amount_rows:
        all_amount_rows = [row for row in rows if row.get("unit") == "Rs. Cr."]

    consolidated_summary = {
        "approved": _sum_rows(all_amount_rows, "arr_approved_value"),
        "actual": _sum_rows(all_amount_rows, "petition_actual_value"),
        "claimed": _sum_rows(all_amount_rows, "petition_claimed_value"),
        "deviation": _sum_rows(all_amount_rows, "deviation_value"),
        "total_items": len(rows),
        "review_required": sum(1 for row in rows if row.get("status") == "REVIEW_REQUIRED"),
        "incomplete": sum(1 for row in rows if row.get("status") == "INCOMPLETE_DATA"),
        "acceptable": sum(1 for row in rows if row.get("status") == "ACCEPTABLE_VARIANCE"),
    }

    chapters = {
        "introduction": {
            "chapter_no": "CHAPTER 1",
            "title": "INTRODUCTION",
            "paragraphs": [
                f"Kerala State Electricity Board Limited filed the petition for truing up of accounts for the financial year {financial_year}. The Commission has examined the petition, the approved ARR/ERC values, and the extracted financial information placed on record.",
                "The documents considered for this draft comprise the uploaded ARR Order and the uploaded Truing-Up Petition. The comparison is restricted to canonical financial line items mapped by the deterministic registry.",
                "The statutory provisions section is retained as a placeholder for reference to the applicable Electricity Act provisions and KSERC MYT Regulations. Final legal references shall be verified by authorized officers.",
                "This draft order is limited to internal review of extracted values, computed deviations, and chapter-wise observations. It does not record final approval, disallowance, or modification of any claim.",
            ],
        },
        "sbu_g": {
            "chapter_no": "CHAPTER 2",
            "title": "TRUING UP OF SBU-G",
            "sbu_name": "SBU-G",
            "opening": _opening_for_sbu("SBU-G", sbu_g_rows),
            "rows": sbu_g_rows,
            "summary": _section_summary(sbu_g_rows),
            "observations": _observations(sbu_g_rows),
        },
        "sbu_t": {
            "chapter_no": "CHAPTER 3",
            "title": "TRUING UP OF SBU-T",
            "sbu_name": "SBU-T",
            "opening": _opening_for_sbu("SBU-T", sbu_t_rows),
            "rows": sbu_t_rows,
            "summary": _section_summary(sbu_t_rows),
            "observations": _observations(sbu_t_rows),
        },
        "energy_sales_td_loss": {
            "chapter_no": "CHAPTER 4",
            "title": "ENERGY SALES AND T&D LOSS",
            "sbu_name": "Energy Sales and T&D Loss",
            "opening": _opening_for_sbu("Energy Sales and T&D Loss", energy_rows),
            "rows": energy_rows,
            "summary": _section_summary(energy_rows),
            "observations": _observations(energy_rows),
            "include": bool(energy_rows),
        },
        "sbu_d": {
            "chapter_no": "CHAPTER 5",
            "title": "TRUING UP OF SBU-D",
            "sbu_name": "SBU-D",
            "opening": _opening_for_sbu("SBU-D", sbu_d_rows),
            "rows": sbu_d_rows,
            "summary": _section_summary(sbu_d_rows),
            "observations": _observations(sbu_d_rows),
        },
        "common_expenses": {
            "chapter_no": "CHAPTER 6",
            "title": "COMMON EXPENSES",
            "sbu_name": "Common Expenses",
            "opening": _opening_for_sbu("Common Expenses", common_rows),
            "rows": common_rows,
            "summary": _section_summary(common_rows),
            "observations": _observations(common_rows),
            "include": bool(common_rows),
        },
        "consolidated": {
            "chapter_no": "CHAPTER 7",
            "title": "CONSOLIDATED TRUING-UP",
            "sbu_name": "Consolidated Truing-Up",
            "opening": "The consolidated truing-up position based on mapped canonical line items is summarized below.",
            "rows": rows,
            "summary": consolidated_summary,
            "observations": [
                "The consolidated summary is computed only from mapped canonical comparison rows and excludes tariff slabs, consumer category rows, and extraction audit data.",
                "Items marked as REVIEW_REQUIRED or INCOMPLETE_DATA shall be verified by authorized officers before any final order is issued.",
            ],
        },
    }

    chapter_sequence = [
        "introduction",
        "sbu_g",
        "sbu_t",
    ]
    if energy_rows:
        chapter_sequence.append("energy_sales_td_loss")
    chapter_sequence.append("sbu_d")
    if common_rows:
        chapter_sequence.append("common_expenses")
    chapter_sequence.append("consolidated")

    return {
        "case_metadata": {
            "case_id": case_id,
            "financial_year": financial_year,
            "petitioner": "Kerala State Electricity Board Ltd",
            "order_type": "Draft Truing-Up Order",
            "generated_date": generated_at.strftime("%d.%m.%Y"),
            "generated_at": generated_at.isoformat(),
            "generated_by": officer_name,
            "is_draft": True,
        },
        "chapters": chapters,
        "chapter_sequence": chapter_sequence,
        "comparison_tables": rows,
        "reviews": reviews or [],
        "final_summary": {
            **consolidated_summary,
            "disclaimer": (
                "This draft has been generated for internal review based on extracted data from uploaded documents. "
                "Final approval, disallowance, or modification shall remain subject to review by authorized officers."
            ),
        },
    }
