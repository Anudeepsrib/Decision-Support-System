"""
Canonical KSERC line-item registry and deterministic extraction filters.

This module is intentionally model-free. It is the gate between broad PDF table
extraction and regulatory comparison/reporting, so only rows that map to one of
these known MVP line items can enter the comparison engine.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple


@dataclass(frozen=True)
class CanonicalLineItem:
    canonical_id: str
    display_name: str
    sbu: str
    aliases: Tuple[str, ...]
    unit: str
    section: str
    include_in_report: bool = True
    is_total: bool = False


SECTION_SBU_G = "sbu_g"
SECTION_SBU_T = "sbu_t"
SECTION_ENERGY = "energy_sales_td_loss"
SECTION_SBU_D = "sbu_d"
SECTION_COMMON = "common_expenses"
SECTION_CONSOLIDATED = "consolidated"


CANONICAL_REGISTRY: Tuple[CanonicalLineItem, ...] = (
    # SBU-G
    CanonicalLineItem(
        "COST_OF_GENERATION",
        "Cost of Generation",
        "SBU-G",
        (
            r"\bcost\s+of\s+generation\b",
            r"\bgeneration\s+cost\b",
            r"\bcost\s+of\s+own\s+generation\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "OM_EXPENSES_GENERATION",
        "O&M Expenses - Generation",
        "SBU-G",
        (
            r"\bo\s*&?\s*m\s+expenses?.*\bgeneration\b",
            r"\boperation\s+and\s+maintenance.*\bgeneration\b",
            r"\bgeneration.*\bo\s*&?\s*m\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "INTEREST_FINANCE_GENERATION",
        "Interest and Finance Charges - Generation",
        "SBU-G",
        (
            r"\binterest.*finance.*\bgeneration\b",
            r"\bgeneration.*interest.*finance\b",
            r"\binterest\s+on\s+loan.*\bgeneration\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "DEPRECIATION_GENERATION",
        "Depreciation - Generation",
        "SBU-G",
        (
            r"\bdepreciation.*\bgeneration\b",
            r"\bgeneration.*depreciation\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "ROE_GENERATION",
        "Return on Equity - Generation",
        "SBU-G",
        (
            r"\breturn\s+on\s+equity.*\bgeneration\b",
            r"\broe.*\bgeneration\b",
            r"\bgeneration.*\broe\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "NON_TARIFF_INCOME_GENERATION",
        "Non-Tariff Income - Generation",
        "SBU-G",
        (
            r"\bnon[-\s]?tariff\s+income.*\bgeneration\b",
            r"\bgeneration.*non[-\s]?tariff\s+income\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
    ),
    CanonicalLineItem(
        "NET_ARR_GENERATION",
        "Net ARR - Generation",
        "SBU-G",
        (
            r"\bnet\s+arr.*\bgeneration\b",
            r"\bgeneration.*\bnet\s+arr\b",
            r"\btotal\s+arr.*\bsbu[-\s]?g\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_G,
        is_total=True,
    ),
    # SBU-T
    CanonicalLineItem(
        "OM_EXPENSES_TRANSMISSION",
        "O&M Expenses - Transmission",
        "SBU-T",
        (
            r"\bo\s*&?\s*m\s+expenses?.*\btransmission\b",
            r"\boperation\s+and\s+maintenance.*\btransmission\b",
            r"\btransmission.*\bo\s*&?\s*m\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
    ),
    CanonicalLineItem(
        "INTEREST_FINANCE_TRANSMISSION",
        "Interest and Finance Charges - Transmission",
        "SBU-T",
        (
            r"\binterest.*finance.*\btransmission\b",
            r"\btransmission.*interest.*finance\b",
            r"\binterest\s+on\s+loan.*\btransmission\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
    ),
    CanonicalLineItem(
        "DEPRECIATION_TRANSMISSION",
        "Depreciation - Transmission",
        "SBU-T",
        (
            r"\bdepreciation.*\btransmission\b",
            r"\btransmission.*depreciation\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
    ),
    CanonicalLineItem(
        "ROE_TRANSMISSION",
        "Return on Equity - Transmission",
        "SBU-T",
        (
            r"\breturn\s+on\s+equity.*\btransmission\b",
            r"\broe.*\btransmission\b",
            r"\btransmission.*\broe\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
    ),
    CanonicalLineItem(
        "NON_TARIFF_INCOME_TRANSMISSION",
        "Non-Tariff Income - Transmission",
        "SBU-T",
        (
            r"\bnon[-\s]?tariff\s+income.*\btransmission\b",
            r"\btransmission.*non[-\s]?tariff\s+income\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
    ),
    CanonicalLineItem(
        "NET_ARR_TRANSMISSION",
        "Net ARR - Transmission",
        "SBU-T",
        (
            r"\bnet\s+arr.*\btransmission\b",
            r"\btransmission.*\bnet\s+arr\b",
            r"\btotal\s+arr.*\bsbu[-\s]?t\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_T,
        is_total=True,
    ),
    # Energy and loss
    CanonicalLineItem(
        "ENERGY_SALES",
        "Energy Sales",
        "ENERGY",
        (
            r"\benergy\s+sales\b",
            r"\bsale\s+of\s+energy\b",
            r"\btotal\s+sales\s+of\s+energy\b",
        ),
        "MU",
        SECTION_ENERGY,
    ),
    CanonicalLineItem(
        "DISTRIBUTION_LOSS",
        "Distribution Loss",
        "ENERGY",
        (
            r"\bdistribution\s+loss\b",
            r"\bd\s+loss\b",
        ),
        "%",
        SECTION_ENERGY,
    ),
    CanonicalLineItem(
        "TRANSMISSION_LOSS",
        "Transmission Loss",
        "ENERGY",
        (
            r"\btransmission\s+loss\b",
            r"\bt\s+loss\b",
        ),
        "%",
        SECTION_ENERGY,
    ),
    CanonicalLineItem(
        "T_D_LOSS",
        "T&D Loss",
        "ENERGY",
        (
            r"\bt\s*&\s*d\s+loss\b",
            r"\bt\s+and\s+d\s+loss\b",
            r"\btd\s+loss\b",
            r"\bt\s+d\s+loss\b",
        ),
        "%",
        SECTION_ENERGY,
    ),
    # SBU-D
    CanonicalLineItem(
        "GENERATION_OF_POWER",
        "Generation of Power",
        "SBU-D",
        (
            r"\bgeneration\s+of\s+power\b",
            r"\bown\s+generation\s+of\s+power\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "PURCHASE_OF_POWER",
        "Purchase of Power",
        "SBU-D",
        (
            r"\bpurchase\s+of\s+power\b",
            r"\bpower\s+purchase\s+cost\b",
            r"\bcost\s+of\s+power\s+purchase\b",
            r"\bcost\s+of\s+power\s+purchased\b",
            r"\bpower\s+purchase\s+expenses?\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "INTEREST_FINANCE_CHARGES",
        "Interest and Finance Charges",
        "SBU-D",
        (
            r"\binterest\s+and\s+finance\s+charges?\b",
            r"\binterest\s*&\s*finance\s+charges?\b",
            r"\bfinance\s+charges?\b",
            r"\binterest\s+charges?\b",
            r"\binterest\s+on\s+loan\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "DEPRECIATION",
        "Depreciation",
        "SBU-D",
        (r"\bdepreciation\b",),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "OM_COST",
        "O&M Cost",
        "SBU-D",
        (
            r"\bo\s*&?\s*m\s+expenses?\b",
            r"\boperation\s+and\s+maintenance\b",
            r"\bemployee\s+(cost|expenses?)\b",
            r"\bstaff\s+cost\b",
            r"\bsalary\b",
            r"\brepair\s+and\s+maintenance\b",
            r"\br\s+(and\s+)?m\s+expenses?\b",
            r"\badministration\s+and\s+general\b",
            r"\badmin.*general.*expenses?\b",
            r"\ba\s+(and\s+)?g\s+expenses?\b",
            r"\btotal\s+o\s*&?\s*m\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "OTHER_EXPENSES",
        "Other Expenses",
        "SBU-D",
        (
            r"\bother\s+expenses?\b",
            r"\bother\s+charges?\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "ADDITIONAL_CONTRIBUTION_MASTER_TRUST",
        "Additional Contribution to Master Trust",
        "SBU-D",
        (
            r"\badditional\s+contribution.*master\s+trust\b",
            r"\bmaster\s+trust\s+contribution\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "GAINS_TD_LOSS_REDUCTION",
        "Gains from T&D Loss Reduction",
        "SBU-D",
        (
            r"\bgains?.*t\s*&\s*d\s+loss\s+reduction\b",
            r"\bgains?.*td\s+loss\s+reduction\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "AMORTIZATION_INTANGIBLE_ASSETS",
        "Amortization of Intangible Assets",
        "SBU-D",
        (
            r"\bamorti[sz]ation.*intangible\s+assets?\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "AMORTIZATION_PAST_GAP",
        "Amortization of Past Gap",
        "SBU-D",
        (
            r"\bamorti[sz]ation.*past\s+gap\b",
            r"\bamorti[sz]ation.*revenue\s+gap\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "ROE",
        "Return on Equity",
        "SBU-D",
        (
            r"\breturn\s+on\s+equity\b",
            r"\broe\b",
            r"\bequity\s+return\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "EXCEPTIONAL_ITEM",
        "Exceptional Item",
        "SBU-D",
        (r"\bexceptional\s+items?\b",),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "PAY_REVISION_EXPENSES",
        "Pay Revision Expenses",
        "SBU-D",
        (
            r"\bpay\s+revision\s+expenses?\b",
            r"\bpay\s+revision\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "REPAYMENT_OF_BOND",
        "Repayment of Bond",
        "SBU-D",
        (
            r"\brepayment\s+of\s+bond\b",
            r"\bbond\s+repayment\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "NET_EXPENDITURE",
        "Net Expenditure",
        "SBU-D",
        (
            r"\bnet\s+expenditure\b",
            r"\bnet\s+arr\b",
            r"\btotal\s+arr\b",
            r"\btotal\s+annual\s+revenue\s+requirement\b",
            r"\baggregate\s+revenue\s+requirement\b",
            r"\btotal\s+expenditure\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
        is_total=True,
    ),
    CanonicalLineItem(
        "NON_TARIFF_INCOME",
        "Non-Tariff Income",
        "SBU-D",
        (
            r"\bnon[-\s]?tariff\s+income\b",
            r"\bother\s+income\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "REVENUE_FROM_TARIFF_EXTERNAL_SALE",
        "Revenue from Tariff and External Sale",
        "SBU-D",
        (
            r"\brevenue\s+from\s+tariff\b",
            r"\btariff\s+revenue\b",
            r"\brevenue\s+from\s+external\s+sale\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
    ),
    CanonicalLineItem(
        "TOTAL_INCOME",
        "Total Income",
        "SBU-D",
        (
            r"\btotal\s+income\b",
            r"\btotal\s+revenue\b",
            r"\bexpected\s+revenue\b",
            r"\berc\s+summary\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
        is_total=True,
    ),
    CanonicalLineItem(
        "REVENUE_SURPLUS_GAP",
        "Revenue Surplus / Gap",
        "SBU-D",
        (
            r"\brevenue\s+surplus\b",
            r"\brevenue\s+gap\b",
            r"\bgap\s*/\s*surplus\b",
            r"\bsurplus\s*/\s*gap\b",
            r"\bnet\s+revenue\s+gap\b",
            r"\brevenue\s+gap\s*/\s*\(surplus\)\b",
        ),
        "Rs. Cr.",
        SECTION_SBU_D,
        is_total=True,
    ),
)


REGISTRY_BY_ID: Dict[str, CanonicalLineItem] = {
    item.canonical_id: item for item in CANONICAL_REGISTRY
}


_SBU_CONTEXT_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "SBU-G",
        (
            r"\bsbu[-\s]?g\b",
            r"\bgeneration\s+business\b",
            r"\bgeneration\s+sbu\b",
            r"\bgenerating\s+stations?\b",
        ),
    ),
    (
        "SBU-T",
        (
            r"\bsbu[-\s]?t\b",
            r"\btransmission\s+business\b",
            r"\btransmission\s+sbu\b",
        ),
    ),
    (
        "SBU-D",
        (
            r"\bsbu[-\s]?d\b",
            r"\bdistribution\s+business\b",
            r"\bdistribution\s+sbu\b",
        ),
    ),
)


_CONTEXTUAL_RULES: Dict[str, Tuple[Tuple[str, str], ...]] = {
    "SBU-G": (
        (r"\b(cost\s+of\s+generation|generation\s+cost)\b", "COST_OF_GENERATION"),
        (r"\b(o\s*&?\s*m|operation\s+and\s+maintenance|employee|repair|administration|a\s+(and\s+)?g)\b", "OM_EXPENSES_GENERATION"),
        (r"\binterest|finance\s+charges?\b", "INTEREST_FINANCE_GENERATION"),
        (r"\bdepreciation\b", "DEPRECIATION_GENERATION"),
        (r"\breturn\s+on\s+equity|\broe\b", "ROE_GENERATION"),
        (r"\bnon[-\s]?tariff\s+income\b", "NON_TARIFF_INCOME_GENERATION"),
        (r"\b(net\s+arr|total\s+arr|aggregate\s+revenue\s+requirement)\b", "NET_ARR_GENERATION"),
    ),
    "SBU-T": (
        (r"\b(o\s*&?\s*m|operation\s+and\s+maintenance|employee|repair|administration|a\s+(and\s+)?g)\b", "OM_EXPENSES_TRANSMISSION"),
        (r"\binterest|finance\s+charges?\b", "INTEREST_FINANCE_TRANSMISSION"),
        (r"\bdepreciation\b", "DEPRECIATION_TRANSMISSION"),
        (r"\breturn\s+on\s+equity|\broe\b", "ROE_TRANSMISSION"),
        (r"\bnon[-\s]?tariff\s+income\b", "NON_TARIFF_INCOME_TRANSMISSION"),
        (r"\b(net\s+arr|total\s+arr|aggregate\s+revenue\s+requirement)\b", "NET_ARR_TRANSMISSION"),
    ),
}


_IRRELEVANT_LABEL_PATTERNS: Tuple[str, ...] = (
    r"\b\d+\s*(to|-)\s*\d+\s*units?\b",
    r"\b(up\s*to|above)\s*\d+\s*units?\b",
    r"\bsingle\s+phase\b",
    r"\bthree\s+phase\b",
    r"\bfixed\s+charge\b",
    r"\benergy\s+charge\b",
    r"\bfixed\s+cost\s+per\s+month\b",
    r"\bconsumer\s+categori(?:y|es)\b",
    r"\btariff\s+slabs?\b",
    r"\bslab\s+rate\b",
    r"\bper\s+unit\b",
    r"\bpaise\s*/?\s*unit\b",
    r"\brs\s*/?\s*kwh\b",
    r"\brs\s*/?\s*kva\b",
    r"\bht[-\s]?\d+\b",
    r"\blt[-\s]?\d+\b",
)


_IRRELEVANT_TABLE_PATTERNS: Tuple[str, ...] = (
    r"\bschedule\s+of\s+tariff\b",
    r"\btariff\s+schedule\b",
    r"\bretail\s+tariff\b",
    r"\btariff\s+revision\b",
    r"\bfixed\s+charge\b",
    r"\benergy\s+charge\b",
    r"\bconsumer\s+categor(?:y|ies)\b",
)


_DATE_LIKE_LABEL = re.compile(
    r"^\s*(\d{1,2}[./-]\d{1,2}[./-]\d{2,4}|\d{4}[./-]\d{1,2}[./-]\d{1,2})\s*$"
)


def clean_label(text: str) -> str:
    """Normalize a label for deterministic matching."""
    cleaned = (text or "").lower().strip()
    cleaned = cleaned.replace("&", " and ")
    cleaned = re.sub(r"^\s*(sr\.?\s*no\.?|sl\.?\s*no\.?|[ivxlcdm]+\.|\d+[\).\s-]+)", "", cleaned)
    cleaned = re.sub(r"[^a-z0-9%/().+-]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def contract_document_type(doc_type: str) -> str:
    """Map legacy internal document types to the reporting data contract."""
    if doc_type == "arr_order":
        return "ARR_ORDER"
    if doc_type == "truing_up_petition":
        return "PETITION"
    return (doc_type or "UNKNOWN").upper()


def infer_sbu(*texts: str) -> Optional[str]:
    combined = clean_label(" ".join(text or "" for text in texts))
    for sbu, patterns in _SBU_CONTEXT_PATTERNS:
        if any(re.search(pattern, combined) for pattern in patterns):
            return sbu
    return None


def is_irrelevant_extraction_row(
    raw_label: str,
    table_name: Optional[str] = None,
    raw_text: Optional[str] = None,
) -> bool:
    """Return true for tariff slabs, date rows, and other extraction noise."""
    label = clean_label(raw_label)
    table = clean_label(table_name or "")
    text = clean_label(raw_text or "")

    if not label or _DATE_LIKE_LABEL.match(raw_label or ""):
        return True

    if re.fullmatch(r"\d{1,4}", label):
        return True

    if any(re.search(pattern, label) for pattern in _IRRELEVANT_LABEL_PATTERNS):
        return True

    if any(re.search(pattern, table) for pattern in _IRRELEVANT_TABLE_PATTERNS):
        # Keep mapped revenue rows, but reject obvious slab/rate rows from tariff tables.
        if not re.search(r"\brevenue\s+from\s+tariff\b|\btariff\s+revenue\b", label):
            return True

    if "annexure" in table and not any(
        token in label
        for token in (
            "generation",
            "purchase",
            "interest",
            "depreciation",
            "income",
            "revenue",
            "loss",
            "arr",
            "expenditure",
        )
    ):
        return True

    if text and any(re.search(pattern, text) for pattern in _IRRELEVANT_LABEL_PATTERNS):
        if not any(token in label for token in ("revenue", "income", "arr", "expenditure")):
            return True

    return False


def _record_text(record: Dict) -> Tuple[str, str, str, str]:
    raw_label = record.get("raw_label") or record.get("row_label") or ""
    normalized_label = record.get("normalized_label") or record.get("canonical_name") or ""
    table_name = record.get("table_name") or record.get("source_table") or ""
    raw_text = record.get("raw_text") or ""
    return str(raw_label), str(normalized_label), str(table_name), str(raw_text)


def map_record_to_canonical(record: Dict) -> Optional[CanonicalLineItem]:
    """
    Map one extracted/normalized record to the MVP canonical registry.

    Returning None means the row is intentionally excluded from comparison and
    report generation.
    """
    raw_label, normalized_label, table_name, raw_text = _record_text(record)
    if is_irrelevant_extraction_row(raw_label, table_name, raw_text):
        return None

    context = infer_sbu(raw_label, normalized_label, table_name, raw_text)
    label_text = clean_label(" ".join([raw_label, normalized_label]))
    combined_text = clean_label(" ".join([raw_label, normalized_label, table_name, raw_text]))

    if context in _CONTEXTUAL_RULES:
        for pattern, canonical_id in _CONTEXTUAL_RULES[context]:
            if re.search(pattern, label_text):
                return REGISTRY_BY_ID[canonical_id]

    matches: List[Tuple[int, CanonicalLineItem]] = []
    for item in CANONICAL_REGISTRY:
        if not item.include_in_report:
            continue
        if context and item.sbu.startswith("SBU-") and item.sbu != context:
            continue
        for alias in item.aliases:
            if re.search(alias, combined_text):
                score = len(alias)
                if context and item.sbu == context:
                    score += 100
                if item.sbu == "SBU-D" and context is None:
                    score += 20
                matches.append((score, item))
                break

    if not matches:
        return None

    matches.sort(key=lambda entry: entry[0], reverse=True)
    return matches[0][1]


def canonicalize_records(records: Iterable[Dict]) -> List[Dict]:
    """Attach canonical registry metadata and drop non-reportable rows."""
    canonical_records: List[Dict] = []
    for record in records:
        item = map_record_to_canonical(record)
        if item is None:
            continue
        enriched = dict(record)
        enriched.update(
            {
                "canonical_id": item.canonical_id,
                "display_name": item.display_name,
                "canonical_name": item.display_name,
                "sbu": item.sbu,
                "unit": item.unit,
                "section": item.section,
                "include_in_report": item.include_in_report,
                "is_total": item.is_total,
            }
        )
        canonical_records.append(enriched)
    return canonical_records


def registry_items_for_section(section: Optional[str] = None) -> List[CanonicalLineItem]:
    """Return reportable registry items in report order."""
    items = [item for item in CANONICAL_REGISTRY if item.include_in_report]
    if section:
        items = [item for item in items if item.section == section]
    return items
