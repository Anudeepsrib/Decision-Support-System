"""
Build deterministic KSERC draft-order report context.

The PDF layer consumes only this context. It never renders raw extraction rows,
debug fields, provenance columns, tariff slabs, or unmapped extraction noise.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Dict, Iterable, List, Optional

try:
    from .canonical_registry import (
        REGISTRY_BY_ID,
        SECTION_COMMON,
        SECTION_CONSOLIDATED,
        SECTION_ENERGY,
        SECTION_SBU_D,
        SECTION_SBU_G,
        SECTION_SBU_T,
    )
except ImportError:  # Support direct imports from the backend directory.
    from canonical_registry import (
        REGISTRY_BY_ID,
        SECTION_COMMON,
        SECTION_CONSOLIDATED,
        SECTION_ENERGY,
        SECTION_SBU_D,
        SECTION_SBU_G,
        SECTION_SBU_T,
    )


ARR_ORDER_DATE = "25.06.2022"
FULL_ORDER_TARGET_PAGES = 237

_REGISTRY_ORDER = {item.canonical_id: index for index, item in enumerate(REGISTRY_BY_ID.values(), 1)}

_BANNED_REPORT_PATTERNS = (
    r"\b0\s+to\s+100\s+units\b",
    r"\b0\s+to\s+200\s+units\b",
    r"\bsingle\s+phase\b",
    r"\bthree\s+phase\b",
    r"\bfixed\s+charge\b",
    r"\benergy\s+charge\b",
    r"\brs\s*/?\s*kva\b",
    r"\brs\s*/?\s*kwh\b",
    r"\braw_label\b",
    r"\bnormalized_label\b",
    r"\bsource_page\b",
    r"\bconfidence\b",
    r"\bdocument_type\b",
)

_SECTION_TOC_TITLES = {
    SECTION_SBU_G: "Chapter-2. Truing up of SBU-G of KSEB Ltd",
    SECTION_SBU_T: "Chapter-3. Truing up of SBU-T of KSEB Ltd",
    SECTION_ENERGY: "Chapter-4. Energy sales and T&D loss",
    SECTION_SBU_D: "Chapter-5. Truing up of SBU-D of KSEB Ltd",
    SECTION_COMMON: "Chapter-6. Approval of common expenses of KSEB Ltd",
    SECTION_CONSOLIDATED: "Chapter-7. Consolidated Truing up of accounts of KSEB Ltd",
}

SECTION_OWNERSHIP = {
    SECTION_SBU_G: {
        "COST_OF_GENERATION",
        "OWN_GENERATION",
        "HYDRO_GENERATION",
        "AUXILIARY_CONSUMPTION",
        "FUEL_COST_GENERATION",
        "OM_EXPENSES_GENERATION",
        "EMPLOYEE_COST_GENERATION",
        "A_G_EXPENSES_GENERATION",
        "R_M_EXPENSES_GENERATION",
        "INTEREST_FINANCE_GENERATION",
        "DEPRECIATION_GENERATION",
        "ROE_GENERATION",
        "NON_TARIFF_INCOME_GENERATION",
        "NET_ARR_GENERATION",
        "MASTER_TRUST_GENERATION",
        "AMORTIZATION_GENERATION",
    },
    SECTION_SBU_T: {
        "TRANSMISSION_OM_EXPENSES",
        "OM_EXPENSES_TRANSMISSION",
        "TRANSMISSION_EMPLOYEE_COST",
        "TRANSMISSION_A_G_EXPENSES",
        "TRANSMISSION_R_M_EXPENSES",
        "INTEREST_FINANCE_TRANSMISSION",
        "DEPRECIATION_TRANSMISSION",
        "ROE_TRANSMISSION",
        "NON_TARIFF_INCOME_TRANSMISSION",
        "NET_ARR_TRANSMISSION",
        "TRANSMISSION_AVAILABILITY",
        "TRANSMISSION_COMPENSATION",
        "MASTER_TRUST_TRANSMISSION",
        "AMORTIZATION_TRANSMISSION",
    },
    SECTION_SBU_D: {
        "PURCHASE_OF_POWER",
        "COST_OF_GENERATION_TRANSFER",
        "GENERATION_OF_POWER",
        "DISTRIBUTION_OM_COST",
        "OM_COST",
        "DISTRIBUTION_EMPLOYEE_COST",
        "DISTRIBUTION_A_G_EXPENSES",
        "DISTRIBUTION_R_M_EXPENSES",
        "INTEREST_FINANCE_CHARGES",
        "DEPRECIATION",
        "ROE",
        "OTHER_EXPENSES",
        "ADDITIONAL_CONTRIBUTION_MASTER_TRUST",
        "REPAYMENT_OF_BOND",
        "AMORTIZATION_INTANGIBLE_ASSETS",
        "AMORTIZATION_PAST_GAP",
        "EXCEPTIONAL_ITEM",
        "PAY_REVISION_EXPENSES",
        "NON_TARIFF_INCOME",
        "REVENUE_FROM_TARIFF_EXTERNAL_SALE",
        "NET_EXPENDITURE",
        "TOTAL_INCOME",
        "REVENUE_SURPLUS_GAP",
        "GAINS_TD_LOSS_REDUCTION",
    },
    SECTION_ENERGY: {
        "ENERGY_SALES",
        "ENERGY_INPUT",
        "TRANSMISSION_LOSS",
        "DISTRIBUTION_LOSS",
        "T_D_LOSS",
        "HYDRO_INFLOW",
        "NET_GENERATION",
    },
    SECTION_COMMON: {
        "COMMON_EMPLOYEE_COST",
        "COMMON_A_G_EXPENSES",
        "COMMON_R_M_EXPENSES",
        "COMMON_INTEREST",
        "COMMON_DEPRECIATION",
        "COMMON_NON_TARIFF_INCOME",
    },
}

PRIMARY_SECTION_BY_CANONICAL_ID = {
    canonical_id: section
    for section, canonical_ids in SECTION_OWNERSHIP.items()
    for canonical_id in canonical_ids
}

CHAPTER_PAGE_RANGES = {
    "introduction": (3, 18),
    SECTION_SBU_G: (19, 36),
    SECTION_SBU_T: (37, 58),
    SECTION_ENERGY: (59, 71),
    SECTION_SBU_D: (72, 147),
    SECTION_COMMON: (148, 196),
    SECTION_CONSOLIDATED: (197, 200),
}


def _as_float(value) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _clean_for_match(value: str) -> str:
    value = (value or "").lower()
    value = re.sub(r"[^a-z0-9/%.-]+", " ", value)
    return re.sub(r"\s+", " ", value).strip()


def _contains_banned_report_text(*values: str) -> bool:
    combined = _clean_for_match(" ".join(value or "" for value in values))
    return any(re.search(pattern, combined) for pattern in _BANNED_REPORT_PATTERNS)


def _status_label(status: Optional[str]) -> str:
    return (status or "INCOMPLETE_DATA").replace("_", " ").title()


def _status_phrase(status: Optional[str]) -> str:
    return _status_label(status).lower()


def _row_from_comparison(index: int, comparison: Dict) -> Optional[Dict]:
    canonical_id = comparison.get("canonical_id") or comparison.get("canonical_name") or ""
    registry_item = REGISTRY_BY_ID.get(canonical_id)

    if comparison.get("include_in_report") is False:
        return None
    if registry_item is None:
        return None

    display_name = comparison.get("display_name") or registry_item.display_name
    if _contains_banned_report_text(display_name, canonical_id, comparison.get("canonical_name") or ""):
        return None

    unit = comparison.get("unit") or registry_item.unit or "Rs. Cr."
    section = PRIMARY_SECTION_BY_CANONICAL_ID.get(canonical_id) or registry_item.section
    if canonical_id not in SECTION_OWNERSHIP.get(section, set()):
        return None
    sbu = registry_item.sbu

    return {
        "no": index,
        "comparison_id": comparison.get("id"),
        "canonical_id": canonical_id,
        "display_name": display_name,
        "sbu": sbu,
        "unit": unit,
        "section": section,
        "arr_approved_value": _as_float(comparison.get("approved_value")),
        "petition_actual_value": _as_float(comparison.get("actual_value")),
        "petition_claimed_value": _as_float(comparison.get("claimed_value")),
        "deviation_value": _as_float(comparison.get("variance")),
        "deviation_percent": _as_float(comparison.get("variance_percent")),
        "status": comparison.get("decision_class") or "INCOMPLETE_DATA",
        "is_total": bool(comparison.get("is_total") or registry_item.is_total),
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


def _summary_as_row(index: int, particular: str, summary: Dict) -> Dict:
    return {
        "no": index,
        "display_name": particular,
        "unit": "Rs. Cr.",
        "arr_approved_value": summary.get("approved"),
        "petition_actual_value": summary.get("actual"),
        "petition_claimed_value": summary.get("claimed"),
        "deviation_value": summary.get("deviation"),
        "deviation_percent": None,
        "status": None,
        "is_total": True,
    }


def _sort_rows(rows: List[Dict]) -> None:
    rows.sort(
        key=lambda row: (
            row.get("section") or "",
            _REGISTRY_ORDER.get(row.get("canonical_id"), 9999),
            row.get("display_name") or "",
        )
    )
    for index, row in enumerate(rows, 1):
        row["no"] = index


def _find_row(rows: List[Dict], canonical_ids: Iterable[str]) -> Optional[Dict]:
    wanted = set(canonical_ids)
    return next((row for row in rows if row.get("canonical_id") in wanted), None)


def _line_item_text(row: Optional[Dict], heading: str) -> str:
    if row is None:
        return (
            f"The Commission records that no mapped canonical value is available under {heading} "
            "in the current extraction set. The item may be examined separately if supporting "
            "details are placed on record."
        )

    return (
        f"The Commission has examined the claim under {row['display_name']}. For the purpose "
        f"of this draft report, the item is placed under {_status_phrase(row.get('status'))} "
        "based on the extracted values and variance threshold. The Commission may take "
        "appropriate decision after examining the details submitted by KSEB Ltd."
    )


def _numbered(no: str, text: str) -> Dict:
    return {"no": no, "text": text}


def _make_section(heading: str, paragraphs: List[Dict], table: Optional[str] = None) -> Dict:
    return {"heading": heading, "paragraphs": paragraphs, "table": table}


ISSUE_DEFINITIONS = {
    SECTION_SBU_G: [
        {
            "issue_id": "OWN_GENERATION_AND_HYDRO",
            "title": "Own generation and hydro generation",
            "items": ("COST_OF_GENERATION", "OWN_GENERATION", "HYDRO_GENERATION", "NET_GENERATION"),
        },
        {"issue_id": "FUEL_COST_GENERATION", "title": "Fuel cost", "items": ("FUEL_COST_GENERATION",)},
        {
            "issue_id": "GENERATION_OM",
            "title": "O&M expenses",
            "items": (
                "OM_EXPENSES_GENERATION",
                "EMPLOYEE_COST_GENERATION",
                "A_G_EXPENSES_GENERATION",
                "R_M_EXPENSES_GENERATION",
            ),
        },
        {"issue_id": "GENERATION_DEPRECIATION", "title": "Depreciation", "items": ("DEPRECIATION_GENERATION",)},
        {
            "issue_id": "GENERATION_INTEREST",
            "title": "Interest and finance charges",
            "items": ("INTEREST_FINANCE_GENERATION",),
        },
        {
            "issue_id": "GENERATION_NET_ARR",
            "title": "Non-tariff income and net ARR",
            "items": ("NON_TARIFF_INCOME_GENERATION", "NET_ARR_GENERATION"),
        },
    ],
    SECTION_SBU_T: [
        {
            "issue_id": "TRANSMISSION_OM",
            "title": "Transmission O&M",
            "items": (
                "TRANSMISSION_OM_EXPENSES",
                "OM_EXPENSES_TRANSMISSION",
                "TRANSMISSION_EMPLOYEE_COST",
                "TRANSMISSION_A_G_EXPENSES",
                "TRANSMISSION_R_M_EXPENSES",
            ),
        },
        {
            "issue_id": "TRANSMISSION_DEPRECIATION",
            "title": "Transmission depreciation",
            "items": ("DEPRECIATION_TRANSMISSION",),
        },
        {
            "issue_id": "TRANSMISSION_INTEREST",
            "title": "Interest and finance charges",
            "items": ("INTEREST_FINANCE_TRANSMISSION",),
        },
        {
            "issue_id": "TRANSMISSION_AVAILABILITY",
            "title": "Transmission availability / compensation",
            "items": ("TRANSMISSION_AVAILABILITY", "TRANSMISSION_COMPENSATION"),
        },
        {
            "issue_id": "TRANSMISSION_NET_ARR",
            "title": "Non-tariff income and net ARR",
            "items": ("NON_TARIFF_INCOME_TRANSMISSION", "NET_ARR_TRANSMISSION"),
        },
    ],
    SECTION_ENERGY: [
        {"issue_id": "ENERGY_SALES", "title": "Energy sales", "items": ("ENERGY_SALES",)},
        {"issue_id": "DISTRIBUTION_LOSS", "title": "Distribution loss", "items": ("DISTRIBUTION_LOSS",)},
        {"issue_id": "TRANSMISSION_LOSS", "title": "Transmission loss", "items": ("TRANSMISSION_LOSS",)},
        {"issue_id": "TD_LOSS", "title": "T&D loss", "items": ("T_D_LOSS",)},
    ],
    SECTION_SBU_D: [
        {"issue_id": "POWER_PURCHASE_COST", "title": "Purchase of power", "items": ("PURCHASE_OF_POWER",)},
        {
            "issue_id": "DISTRIBUTION_OM",
            "title": "Distribution O&M cost",
            "items": (
                "DISTRIBUTION_OM_COST",
                "OM_COST",
                "DISTRIBUTION_EMPLOYEE_COST",
                "DISTRIBUTION_A_G_EXPENSES",
                "DISTRIBUTION_R_M_EXPENSES",
            ),
        },
        {"issue_id": "DISTRIBUTION_DEPRECIATION", "title": "Depreciation", "items": ("DEPRECIATION",)},
        {
            "issue_id": "DISTRIBUTION_INTEREST",
            "title": "Interest and finance charges",
            "items": ("INTEREST_FINANCE_CHARGES",),
        },
        {
            "issue_id": "TARIFF_REVENUE",
            "title": "Revenue from tariff and external sale",
            "items": ("REVENUE_FROM_TARIFF_EXTERNAL_SALE",),
        },
        {"issue_id": "DISTRIBUTION_NTI", "title": "Non-tariff income", "items": ("NON_TARIFF_INCOME",)},
        {
            "issue_id": "REVENUE_GAP",
            "title": "Revenue gap / surplus",
            "items": ("NET_EXPENDITURE", "TOTAL_INCOME", "REVENUE_SURPLUS_GAP"),
        },
        {
            "issue_id": "MASTER_TRUST_BOND",
            "title": "Master Trust / bond repayment",
            "items": ("ADDITIONAL_CONTRIBUTION_MASTER_TRUST", "REPAYMENT_OF_BOND"),
        },
    ],
    SECTION_COMMON: [
        {
            "issue_id": "COMMON_EMPLOYEE",
            "title": "Common employee cost",
            "items": ("COMMON_EMPLOYEE_COST",),
        },
        {
            "issue_id": "COMMON_AG",
            "title": "Common A&G expenses",
            "items": ("COMMON_A_G_EXPENSES",),
        },
        {
            "issue_id": "COMMON_RM",
            "title": "Common R&M expenses",
            "items": ("COMMON_R_M_EXPENSES",),
        },
        {
            "issue_id": "COMMON_INTEREST_DEPRECIATION",
            "title": "Common interest and depreciation",
            "items": ("COMMON_INTEREST", "COMMON_DEPRECIATION"),
        },
        {
            "issue_id": "COMMON_NTI",
            "title": "Common non-tariff income",
            "items": ("COMMON_NON_TARIFF_INCOME",),
        },
    ],
}


def _rows_for_ids(rows: List[Dict], canonical_ids: Iterable[str]) -> List[Dict]:
    wanted = set(canonical_ids)
    return [row for row in rows if row.get("canonical_id") in wanted]


def _fmt_amount(value: Optional[float], unit: str = "Rs. Cr.") -> str:
    if value is None:
        return "-"
    if unit == "%":
        return f"{value:,.2f}%"
    return f"{value:,.2f} {unit}"


def _issue_value_summary(issue_rows: List[Dict]) -> Dict:
    amount_rows = [row for row in issue_rows if not row.get("is_total")]
    if not amount_rows:
        amount_rows = issue_rows
    return {
        "approved": _sum_rows(amount_rows, "arr_approved_value"),
        "actual": _sum_rows(amount_rows, "petition_actual_value"),
        "claimed": _sum_rows(amount_rows, "petition_claimed_value"),
        "deviation": _sum_rows(amount_rows, "deviation_value"),
    }


def _make_issue_block(
    definition: Dict,
    rows: List[Dict],
    chapter_label: str,
    paragraph_prefix: str,
    paragraph_start: int,
) -> Dict:
    issue_rows = _rows_for_ids(rows, definition["items"])
    summary = _issue_value_summary(issue_rows)
    primary_row = issue_rows[0] if issue_rows else None
    status = _status_phrase(primary_row.get("status")) if primary_row else "data not available"
    unit = primary_row.get("unit") if primary_row else "Rs. Cr."

    if issue_rows:
        petition_claim = (
            f"KSEB Ltd has claimed {_fmt_amount(summary['claimed'], unit)} under this issue based on "
            "the extracted petition values."
        )
        approved_position = (
            f"The corresponding value approved in the ARR&ERC Order dated 25.06.2022 is "
            f"{_fmt_amount(summary['approved'], unit)}."
        )
        deviation_summary = (
            f"The deviation from approval is {_fmt_amount(summary['deviation'], unit)} and the item "
            f"is marked as {status} for officer review in this draft."
        )
    else:
        petition_claim = (
            "No mapped canonical value is available for this issue in the extracted canonical set."
        )
        approved_position = (
            "The item has therefore not been populated with an approved or actual value in this draft."
        )
        deviation_summary = (
            "The issue is retained in the chapter hierarchy because it is a standard head of review "
            f"for {chapter_label}."
        )

    return {
        "issue_id": definition["issue_id"],
        "title": definition["title"],
        "chapter": chapter_label,
        "items": issue_rows,
        "petition_claim": petition_claim,
        "approved_position": approved_position,
        "deviation_summary": deviation_summary,
        "analysis": (
            "The Commission has examined the claim under this head vis-a-vis the approved value, "
            "actual value and amount sought for truing up. The treatment in this draft is "
            "deterministic and remains subject to officer review."
        ),
        "draft_decision": (
            "The Commission may take an appropriate decision after examining the details submitted "
            "by KSEB Ltd and the applicable provisions of the KSERC Tariff Regulations, 2021."
        ),
        "paragraphs": [
            _numbered(f"{paragraph_prefix}.{paragraph_start}", petition_claim),
            _numbered(f"{paragraph_prefix}.{paragraph_start + 1}", approved_position),
            _numbered(f"{paragraph_prefix}.{paragraph_start + 2}", deviation_summary),
            _numbered(
                f"{paragraph_prefix}.{paragraph_start + 3}",
                "The Commission may take an appropriate decision after examining the details submitted by KSEB Ltd.",
            ),
        ],
        "table_rows": issue_rows if len(issue_rows) > 1 else [],
    }


def _chapter_intro(section: str, financial_year: str) -> str:
    if section == SECTION_SBU_G:
        return (
            "In exercise of the provisions of the Electricity Act, 2003 and the Tariff Regulations, "
            "2021, the Commission has examined the truing up of accounts of the Strategic Business "
            f"Unit - Generation of KSEB Ltd for the financial year {financial_year}. The summary of "
            "ARR and ERC for SBU-G, as extracted from the petition and compared with the approved "
            "values, is given below."
        )
    if section == SECTION_SBU_T:
        return (
            "The transmission business of KSEB Ltd is responsible for the intra-State transmission "
            f"function. The Commission has examined the expenses, income and transfer cost claimed "
            f"under SBU-T for the financial year {financial_year}."
        )
    if section == SECTION_SBU_D:
        return (
            "The distribution business of KSEB Ltd includes retail supply, power purchase, "
            "distribution operation and revenue realization. The Commission has examined the "
            "truing up claim of SBU-D with reference to the approved ARR and the values extracted "
            "from the petition."
        )
    if section == SECTION_ENERGY:
        return (
            "The Commission has examined the energy sales, input energy and loss trajectory placed "
            f"on record for the financial year {financial_year}. The analysis is limited to mapped "
            "canonical energy and loss parameters."
        )
    if section == SECTION_COMMON:
        return (
            "The common expenses of KSEB Ltd are examined separately to avoid duplication across "
            "the Strategic Business Units. The values in this chapter are restricted to canonical "
            "common-expense rows, if available."
        )
    return (
        "The consolidated chapter summarizes the truing-up position across mapped canonical heads "
        "and records the draft observations for internal review."
    )


def _make_order_chapter(
    key: str,
    base_chapter: Dict,
    rows: List[Dict],
    financial_year: str,
) -> Dict:
    paragraph_prefix = str(base_chapter.get("chapter_index", 1))
    issue_blocks = [
        _make_issue_block(definition, rows, base_chapter["sbu_name"], paragraph_prefix, (index * 4) + 3)
        for index, definition in enumerate(ISSUE_DEFINITIONS.get(key, []))
    ]
    for index, issue in enumerate(issue_blocks, 2):
        issue["table_no"] = f"Table {paragraph_prefix}.{index}"
    if not rows:
        issue_blocks.insert(
            0,
            {
                "issue_id": f"{key.upper()}_DATA_UNAVAILABLE",
                "title": "Data not available in extracted canonical set",
                "chapter": base_chapter["sbu_name"],
                "items": [],
                "petition_claim": "No mapped canonical row is available for this chapter.",
                "approved_position": "The approved and actual values are therefore not populated in this draft.",
                "deviation_summary": "The chapter is retained to preserve the order structure.",
                "analysis": "The item may be populated when the relevant values are mapped from uploaded documents.",
                "draft_decision": "The Commission may examine supporting details submitted by KSEB Ltd.",
                "paragraphs": [
                    _numbered(
                        f"{paragraph_prefix}.3",
                        "No mapped canonical row is available for this chapter in the current extraction set.",
                    )
                ],
                "table_rows": [],
            },
        )

    start_page, end_page = CHAPTER_PAGE_RANGES[key]
    return {
        "key": key,
        "chapter_no": base_chapter["chapter_no"],
        "chapter_index": base_chapter["chapter_index"],
        "title": base_chapter["title"],
        "toc_title": base_chapter["toc_title"],
        "sbu_name": base_chapter["sbu_name"],
        "intro": _chapter_intro(key, financial_year),
        "summary_table": rows,
        "summary_caption": f"{base_chapter['table_no']} {base_chapter['table_caption']}",
        "unit_label": base_chapter.get("unit_label") or "Rs. Cr.",
        "issue_blocks": issue_blocks[:6],
        "stakeholder_placeholder": (
            "The stakeholder comments, if any, shall be incorporated after officer review. "
            "This draft focuses on financial comparison based on extracted ARR and petition values."
        ),
        "chapter_decision": (
            "The Commission has examined the claims in this chapter based on the mapped canonical "
            "values. Final approval, disallowance or modification shall be subject to verification "
            "of records and decision by authorized officers."
        ),
        "page_range": {"start": start_page, "end": end_page},
    }


def _make_introduction_order_chapter(base_chapter: Dict, summary_rows: List[Dict], financial_year: str) -> Dict:
    start_page, end_page = CHAPTER_PAGE_RANGES["introduction"]
    return {
        "key": "introduction",
        "chapter_no": base_chapter["chapter_no"],
        "chapter_index": 1,
        "title": base_chapter["title"],
        "toc_title": base_chapter["toc_title"],
        "intro": (
            f"KSEB Ltd filed the petition for approval of truing up of accounts for the year {financial_year}. "
            "This chapter records the background, statutory framework, documents considered and scope of this draft order."
        ),
        "background_paragraphs": [
            _numbered(
                "1.1",
                "Kerala State Electricity Board Limited filed the petition before the Commission for approval of truing up of accounts of its Strategic Business Units.",
            ),
            _numbered(
                "1.2",
                "The petition is examined with reference to the uploaded ARR Order, uploaded Truing-Up Petition and canonical comparison prepared by the deterministic registry.",
            ),
        ],
        "statutory_paragraphs": [
            _numbered(
                "1.3",
                "Sections 61, 62 and 64 of the Electricity Act, 2003 provide the statutory framework for tariff determination and related proceedings.",
            ),
            _numbered(
                "1.4",
                "The KSERC Tariff Regulations, 2021 and MYT framework provide the basis for examination of ARR, ERC and truing up for the control period.",
            ),
        ],
        "documents_paragraphs": [
            _numbered(
                "1.5",
                "The documents considered for this draft comprise the uploaded ARR Order and the uploaded Truing-Up Petition.",
            ),
            _numbered(
                "1.6",
                "The scope of this draft is limited to internal review of extracted values, computed deviations and chapter-wise observations.",
            ),
        ],
        "stakeholder_placeholder": (
            "The stakeholder comments, if any, shall be incorporated after officer review. "
            "This draft focuses on financial comparison based on extracted ARR and petition values."
        ),
        "summary_table": summary_rows,
        "summary_caption": "Table-1.1 Summary of ARR, ERC and Revenue gap claimed for Truing up petition",
        "unit_label": "Rs. Cr.",
        "issue_blocks": [],
        "chapter_decision": (
            "The Commission after examining the petition and available details has arranged the truing up of accounts in the ensuing chapters."
        ),
        "page_range": {"start": start_page, "end": end_page},
    }

def _make_intro_chapter(financial_year: str, petition_rows: List[Dict], summary_rows: List[Dict]) -> Dict:
    return {
        "chapter_no": "CHAPTER -1",
        "chapter_index": 1,
        "title": "INTRODUCTION",
        "toc_title": "Chapter-1. Introduction",
        "table_no": "Table-1.1",
        "table_caption": "Summary of ARR, ERC and Revenue gap claimed for Truing up petition",
        "rows": petition_rows,
        "summary_rows": summary_rows,
        "unit_label": "Rs. Cr.",
        "sections": [
            _make_section(
                "Background",
                [
                    _numbered(
                        "1.1",
                        (
                            "Kerala State Electricity Board Limited (hereinafter referred to as "
                            "KSEB Ltd or licensee) filed the petition before the Commission for "
                            f"approval of truing up of accounts for the year {financial_year}. "
                            "The petition relates to the Strategic Business Units of generation, "
                            "transmission and distribution and has been considered under the "
                            "applicable tariff framework."
                        ),
                    ),
                ],
            ),
            _make_section(
                "Statutory provisions",
                [
                    _numbered(
                        "1.2",
                        (
                            "Section 61 of the Electricity Act, 2003 confers power on the "
                            "Electricity Regulatory Commissions to specify the terms and "
                            "conditions for determination of tariff. Sections 62 and 64 empower "
                            "the Commission to determine tariff and prescribe the procedure for "
                            "determination of tariff."
                        ),
                    ),
                ],
            ),
            _make_section(
                "MYT framework provisions",
                [
                    _numbered(
                        "1.3",
                        (
                            "The Commission has notified the KSERC (Terms and Conditions for "
                            "Determination of Tariff) Regulations, 2021 for the MYT control "
                            "period from 2022-23 to 2026-27. The truing up is examined vis-a-vis "
                            "the audited accounts, the ARR&ERC Order dated 25.06.2022 and the "
                            "relevant provisions of the Regulations."
                        ),
                    ),
                    _numbered(
                        "1.4",
                        (
                            "As per the Second Transfer Scheme, the activities of KSEB Ltd are "
                            "carried out through Strategic Business Units for generation, "
                            "transmission and distribution. The SBU-wise details extracted from "
                            "the uploaded documents have therefore been grouped chapter-wise."
                        ),
                    ),
                    _numbered(
                        "1.5",
                        (
                            "The documents considered for this draft comprise the uploaded ARR "
                            "Order and the uploaded Truing-Up Petition. The comparison is "
                            "restricted to canonical financial line items mapped by the "
                            "deterministic registry."
                        ),
                    ),
                ],
            ),
            _make_section(
                "Summary of petition",
                [
                    _numbered(
                        "1.6",
                        (
                            f"The summary of ARR, ERC and Revenue gap claimed by KSEB Ltd for "
                            f"True up for the year {financial_year} is given below."
                        ),
                    ),
                ],
                table="primary",
            ),
            _make_section(
                "Public hearing and documents considered",
                [
                    _numbered(
                        "1.7",
                        (
                            "Public hearing details, stakeholder submissions and additional "
                            "information furnished by KSEB Ltd may be incorporated after "
                            "verification of the records available with the Commission."
                        ),
                    ),
                    _numbered(
                        "1.8",
                        (
                            "The Commission after examining the petition and the available "
                            "details has arranged the truing up of accounts in the ensuing "
                            "chapters for internal review."
                        ),
                    ),
                ],
            ),
        ],
    }


def _make_sbu_chapter(
    chapter_index: int,
    chapter_no: str,
    title: str,
    toc_title: str,
    sbu_name: str,
    table_no: str,
    table_caption: str,
    rows: List[Dict],
    line_items: List[tuple[str, tuple[str, ...]]],
) -> Dict:
    prefix = str(chapter_index)
    sections = [
        _make_section(
            "Introduction",
            [
                _numbered(
                    f"{prefix}.1",
                    (
                        f"The Commission has examined the ARR of {sbu_name} claimed by KSEB Ltd "
                        "vis-a-vis the audited accounts, ARR&ERC Order dated 25.06.2022, KSERC "
                        "Tariff Regulations, 2021, and other relevant details."
                    ),
                ),
                _numbered(
                    f"{prefix}.2",
                    (
                        f"The summary of ARR and ERC of {sbu_name} for the year under truing up "
                        "as claimed by KSEB Ltd is given below."
                    ),
                ),
            ],
            table="primary",
        ),
        _make_section(
            f"Expenses of {sbu_name}",
            [
                _numbered(
                    f"{prefix}.3",
                    (
                        f"The expenses of {sbu_name} have been grouped under the principal heads "
                        "available in the canonical comparison. The analysis below is limited to "
                        "mapped values extracted from the uploaded documents."
                    ),
                ),
            ],
        ),
        _make_section(
            "Analysis and decision of the Commission",
            [
                _numbered(
                    f"{prefix}.4",
                    (
                        "The Commission has examined the claim under these heads. For the purpose "
                        "of this draft report, each item is placed under the stated review "
                        "category based on extracted values and the variance threshold."
                    ),
                ),
            ],
        ),
    ]

    paragraph_no = 5
    for heading, canonical_ids in line_items:
        sections.append(
            _make_section(
                heading,
                [_numbered(f"{prefix}.{paragraph_no}", _line_item_text(_find_row(rows, canonical_ids), heading))],
            )
        )
        paragraph_no += 1

    return {
        "chapter_no": chapter_no,
        "chapter_index": chapter_index,
        "title": title,
        "toc_title": toc_title,
        "sbu_name": sbu_name,
        "table_no": table_no,
        "table_caption": table_caption,
        "rows": rows,
        "summary": _section_summary(rows),
        "unit_label": "Rs. Cr." if sbu_name != "Energy sales and T&D loss" else "MU / %",
        "sections": sections,
    }


def _make_consolidated_chapter(rows: List[Dict], summary: Dict, financial_year: str) -> Dict:
    summary_rows = [
        _summary_as_row(1, "Aggregate mapped ARR / expenditure items", summary),
    ]
    return {
        "chapter_no": "CHAPTER-7",
        "chapter_index": 7,
        "title": "CONSOLIDATED TRUING UP",
        "toc_title": _SECTION_TOC_TITLES[SECTION_CONSOLIDATED] + f" for the year {financial_year}",
        "sbu_name": "Consolidated Truing up",
        "table_no": "Table 7.1",
        "table_caption": "Consolidated truing-up summary",
        "rows": summary_rows,
        "all_rows": rows,
        "summary": summary,
        "unit_label": "Rs. Cr.",
        "sections": [
            _make_section(
                "Consolidated Truing up",
                [
                    _numbered(
                        "7.1",
                        (
                            "The consolidated truing-up position based on mapped canonical line "
                            "items is summarized below."
                        ),
                    ),
                ],
                table="primary",
            ),
            _make_section(
                "Analysis and decision of the Commission",
                [
                    _numbered(
                        "7.2",
                        (
                            "The consolidated summary is computed only from mapped canonical "
                            "comparison rows and excludes tariff slabs, consumer category rows "
                            "and extraction audit data."
                        ),
                    ),
                    _numbered(
                        "7.3",
                        (
                            "Items marked for review or having incomplete mapped data shall be "
                            "verified by authorized officers before any final order is issued."
                        ),
                    ),
                ],
            ),
        ],
    }


def _ordinal_day(day: int) -> str:
    if 10 <= day % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
    return f"{day}{suffix}"


def _toc_entries(chapters: Dict[str, Dict], financial_year: str) -> List[Dict]:
    return [
        {"sl_no": 1, "particulars": chapters["introduction"]["toc_title"], "pages": 3},
        {"sl_no": 2, "particulars": chapters[SECTION_SBU_G]["toc_title"], "pages": 19},
        {"sl_no": 3, "particulars": chapters[SECTION_SBU_T]["toc_title"], "pages": 37},
        {"sl_no": 4, "particulars": chapters[SECTION_ENERGY]["toc_title"], "pages": 59},
        {"sl_no": 5, "particulars": chapters[SECTION_SBU_D]["toc_title"], "pages": 72},
        {"sl_no": 6, "particulars": chapters[SECTION_COMMON]["toc_title"], "pages": 148},
        {
            "sl_no": 7,
            "particulars": (
                f"Chapter-7. Consolidated Truing up of accounts of KSEB Ltd for the year {financial_year}"
            ),
            "pages": 197,
        },
        {"sl_no": 8, "particulars": "Annexures", "pages": 201},
    ]


def build_report_context(
    case_id: str,
    financial_year: str,
    comparisons: List[Dict],
    reviews: Optional[List[Dict]] = None,
    officer_name: str = "Demo Officer",
) -> Dict:
    """Build the deterministic report_context consumed by PDF generators."""
    generated_at = datetime.now(timezone.utc).replace(tzinfo=None)

    rows: List[Dict] = []
    for comparison in comparisons:
        row = _row_from_comparison(len(rows) + 1, comparison)
        if row is not None:
            rows.append(row)

    _sort_rows(rows)

    by_section: Dict[str, List[Dict]] = {}
    for row in rows:
        by_section.setdefault(row["section"], []).append(row)

    for section_rows in by_section.values():
        _sort_rows(section_rows)

    sbu_g_rows = by_section.get(SECTION_SBU_G, [])
    sbu_t_rows = by_section.get(SECTION_SBU_T, [])
    energy_rows = by_section.get(SECTION_ENERGY, [])
    sbu_d_rows = by_section.get(SECTION_SBU_D, [])
    common_rows = by_section.get(SECTION_COMMON, [])

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

    high_level_summary_rows = [
        _summary_as_row(1, "SBU-G", _section_summary(sbu_g_rows)),
        _summary_as_row(2, "SBU-T", _section_summary(sbu_t_rows)),
        _summary_as_row(3, "Energy sales and T&D loss", _section_summary(energy_rows)),
        _summary_as_row(4, "SBU-D", _section_summary(sbu_d_rows)),
        _summary_as_row(5, "Common expenses", _section_summary(common_rows)),
        _summary_as_row(6, "Consolidated position", consolidated_summary),
    ]

    chapters = {
        "introduction": _make_intro_chapter(
            financial_year,
            high_level_summary_rows,
            high_level_summary_rows,
        ),
        SECTION_SBU_G: _make_sbu_chapter(
            2,
            "CHAPTER-2",
            "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT GENERATION (SBU-G)",
            _SECTION_TOC_TITLES[SECTION_SBU_G],
            "SBU-G",
            "Table 2.1",
            "KSEB Ltd.-Transfer Cost of SBU-G as per truing up petition",
            sbu_g_rows,
            [
                ("O&M expenses", ("OM_EXPENSES_GENERATION",)),
                ("Depreciation", ("DEPRECIATION_GENERATION",)),
                ("Interest and finance charges", ("INTEREST_FINANCE_GENERATION",)),
                ("Non-tariff income", ("NON_TARIFF_INCOME_GENERATION",)),
                ("Net ARR", ("NET_ARR_GENERATION",)),
            ],
        ),
        SECTION_SBU_T: _make_sbu_chapter(
            3,
            "CHAPTER-3",
            "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT TRANSMISSION (SBU-T)",
            _SECTION_TOC_TITLES[SECTION_SBU_T],
            "SBU-T",
            "Table 3.1",
            "Summary of ARR and ERC claimed for SBU-T",
            sbu_t_rows,
            [
                ("O&M expenses", ("OM_EXPENSES_TRANSMISSION",)),
                ("Depreciation", ("DEPRECIATION_TRANSMISSION",)),
                ("Interest and finance charges", ("INTEREST_FINANCE_TRANSMISSION",)),
                ("Non-tariff income", ("NON_TARIFF_INCOME_TRANSMISSION",)),
                ("Net ARR", ("NET_ARR_TRANSMISSION",)),
            ],
        ),
        SECTION_ENERGY: _make_sbu_chapter(
            4,
            "CHAPTER-4",
            "ENERGY SALES AND T&D LOSS",
            _SECTION_TOC_TITLES[SECTION_ENERGY],
            "Energy sales and T&D loss",
            "Table 4.1",
            "Energy sales and T&D loss as per ARR and truing up petition",
            energy_rows,
            [
                ("Energy sales", ("ENERGY_SALES",)),
                ("Transmission loss", ("TRANSMISSION_LOSS",)),
                ("Distribution loss", ("DISTRIBUTION_LOSS",)),
                ("T&D loss", ("T_D_LOSS",)),
            ],
        ),
        SECTION_SBU_D: _make_sbu_chapter(
            5,
            "CHAPTER-5",
            "TRUING UP OF ACCOUNTS OF STRATEGIC BUSINESS UNIT DISTRIBUTION (SBU-D)",
            _SECTION_TOC_TITLES[SECTION_SBU_D],
            "SBU-D",
            "Table 5.1",
            "Summary of ARR, ERC and Revenue gap claimed for SBU-D",
            sbu_d_rows,
            [
                ("Purchase of power", ("PURCHASE_OF_POWER",)),
                ("O&M expenses", ("OM_COST",)),
                ("Depreciation", ("DEPRECIATION",)),
                ("Interest and finance charges", ("INTEREST_FINANCE_CHARGES",)),
                ("Non-tariff income", ("NON_TARIFF_INCOME",)),
                ("Net ARR", ("NET_EXPENDITURE",)),
                ("Revenue gap", ("REVENUE_SURPLUS_GAP",)),
            ],
        ),
        SECTION_COMMON: _make_sbu_chapter(
            6,
            "CHAPTER-6",
            "APPROVAL OF COMMON EXPENSES OF KSEB LTD",
            _SECTION_TOC_TITLES[SECTION_COMMON],
            "Common expenses",
            "Table 6.1",
            "Common expenses claimed by KSEB Ltd",
            common_rows,
            [
                ("Common expenses", tuple(row["canonical_id"] for row in common_rows)),
            ],
        ),
    }
    chapters[SECTION_CONSOLIDATED] = _make_consolidated_chapter(rows, consolidated_summary, financial_year)

    order_chapters = {
        "introduction": _make_introduction_order_chapter(
            chapters["introduction"],
            high_level_summary_rows,
            financial_year,
        ),
        SECTION_SBU_G: _make_order_chapter(SECTION_SBU_G, chapters[SECTION_SBU_G], sbu_g_rows, financial_year),
        SECTION_SBU_T: _make_order_chapter(SECTION_SBU_T, chapters[SECTION_SBU_T], sbu_t_rows, financial_year),
        SECTION_ENERGY: _make_order_chapter(SECTION_ENERGY, chapters[SECTION_ENERGY], energy_rows, financial_year),
        SECTION_SBU_D: _make_order_chapter(SECTION_SBU_D, chapters[SECTION_SBU_D], sbu_d_rows, financial_year),
        SECTION_COMMON: _make_order_chapter(SECTION_COMMON, chapters[SECTION_COMMON], common_rows, financial_year),
        SECTION_CONSOLIDATED: {
            "key": SECTION_CONSOLIDATED,
            "chapter_no": chapters[SECTION_CONSOLIDATED]["chapter_no"],
            "chapter_index": 7,
            "title": chapters[SECTION_CONSOLIDATED]["title"],
            "toc_title": chapters[SECTION_CONSOLIDATED]["toc_title"],
            "sbu_name": "Consolidated Truing up",
            "intro": _chapter_intro(SECTION_CONSOLIDATED, financial_year),
            "summary_table": chapters[SECTION_CONSOLIDATED]["rows"],
            "summary_caption": "Table 7.1 Consolidated truing-up summary",
            "unit_label": "Rs. Cr.",
            "issue_blocks": [],
            "stakeholder_placeholder": (
                "The consolidated position is subject to verification of chapter-wise values and officer review."
            ),
            "chapter_decision": (
                "The consolidated summary is computed only from mapped canonical rows and excludes tariff slabs, consumer category rows and extraction audit data."
            ),
            "page_range": {"start": 197, "end": 200},
        },
    }

    chapter_sequence = [
        "introduction",
        SECTION_SBU_G,
        SECTION_SBU_T,
        SECTION_ENERGY,
        SECTION_SBU_D,
        SECTION_COMMON,
        SECTION_CONSOLIDATED,
    ]

    order_date = generated_at.strftime("%d.%m.%Y")
    month_name = generated_at.strftime("%B")
    dated_this = f"Dated this the {_ordinal_day(generated_at.day)} {month_name} {generated_at.year}"

    return {
        "case_metadata": {
            "case_id": case_id,
            "financial_year": financial_year,
            "petitioner": "Kerala State Electricity Board Ltd",
            "petitioner_address": ["Vydhyuthi Bhavanam,", "Pattom Thiruvananthapuram"],
            "commission": "KERALA STATE ELECTRICITY REGULATORY COMMISSION",
            "place": "THIRUVANANTHAPURAM",
            "present": ["Shri T K Jose, Chairman", "Adv. A.J Wilson, Member", "Shri B Pradeep, Member"],
            "op_number": f"OP. No {case_id}",
            "matter": f"Petition for the Truing up of accounts of M/s KSEB Ltd for the financial year {financial_year}",
            "order_type": "Draft Truing-Up Order",
            "order_date": order_date,
            "generated_date": order_date,
            "generated_at": generated_at.isoformat(),
            "generated_by": officer_name,
            "dated_this": dated_this,
            "arr_order_date": ARR_ORDER_DATE,
            "is_draft": True,
        },
        "toc_entries": _toc_entries(chapters, financial_year),
        "chapters": chapters,
        "order_chapters": order_chapters,
        "chapter_sequence": chapter_sequence,
        "comparison_tables": rows,
        "target_page_count": FULL_ORDER_TARGET_PAGES,
        "reviews": reviews or [],
        "final_summary": {
            **consolidated_summary,
            "disclaimer": (
                "This draft order is generated for internal review based on data extracted from uploaded documents. "
                "Final approval, disallowance, or modification shall remain subject to review and decision by authorized officers."
            ),
        },
    }
