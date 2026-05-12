"""
MVP Normalizer — Maps raw extracted row labels to canonical names.

Uses fuzzy matching and rule-based patterns to normalize extracted
financial line items to a standard vocabulary.

Example:
  "Purchase of power" → "Power Purchase Cost"
  "Power Purchase Cost" → "Power Purchase Cost"  
  "Cost of Power Purchased" → "Power Purchase Cost"
"""

import re
from typing import Optional, Tuple, List
from dataclasses import dataclass


@dataclass
class NormalizationResult:
    """Result of normalizing a raw row label."""
    canonical_name: str
    category: str         # ARR, ERC, Revenue_Gap, O&M_Detail
    cost_head: str        # Power_Purchase, O&M, Interest, Depreciation, ROE, Other
    confidence: float     # 0.0 to 1.0
    method: str           # rule_based | fuzzy


# ─── Canonical Vocabulary ───

CANONICAL_ITEMS = {
    # ARR Components
    "Power Purchase Cost": {"category": "ARR", "cost_head": "Power_Purchase"},
    "Generation Cost": {"category": "ARR", "cost_head": "Power_Purchase"},
    "Interest & Finance Charges": {"category": "ARR", "cost_head": "Interest"},
    "Depreciation": {"category": "ARR", "cost_head": "Depreciation"},
    "Return on Equity": {"category": "ARR", "cost_head": "ROE"},
    "O&M Expenses": {"category": "ARR", "cost_head": "O&M"},
    "Employee Cost": {"category": "ARR", "cost_head": "O&M"},
    "Repair & Maintenance": {"category": "ARR", "cost_head": "O&M"},
    "A&G Expenses": {"category": "ARR", "cost_head": "O&M"},
    "Total O&M": {"category": "ARR", "cost_head": "O&M"},
    "Transmission Charges": {"category": "ARR", "cost_head": "Other"},
    "Wheeling Charges": {"category": "ARR", "cost_head": "Other"},
    "Provision for Bad Debts": {"category": "ARR", "cost_head": "Other"},
    "Terminal Benefits": {"category": "ARR", "cost_head": "O&M"},
    "Total ARR": {"category": "ARR", "cost_head": "Total"},
    "Total Expenditure": {"category": "ARR", "cost_head": "Total"},
    
    # ERC Components
    "Expected Revenue (ERC)": {"category": "ERC", "cost_head": "Revenue"},
    "Revenue from Tariff": {"category": "ERC", "cost_head": "Revenue"},
    "Non-Tariff Income": {"category": "ERC", "cost_head": "Revenue"},
    
    # Gap
    "Revenue Gap / (Surplus)": {"category": "Revenue_Gap", "cost_head": "Gap"},
    "Statutory Surplus": {"category": "Revenue_Gap", "cost_head": "Gap"},
}


# ─── Normalization Rules ───
# (regex_pattern, canonical_name)

_NORMALIZATION_RULES: List[Tuple[str, str]] = [
    # Power Purchase
    (r"power\s*purchase\s*cost", "Power Purchase Cost"),
    (r"cost\s*of\s*power\s*purchase", "Power Purchase Cost"),
    (r"purchase\s*of\s*power", "Power Purchase Cost"),
    (r"cost\s*of\s*power", "Power Purchase Cost"),
    (r"power\s*purchase\s*expense", "Power Purchase Cost"),
    
    # Generation
    (r"generation\s*cost", "Generation Cost"),
    (r"cost\s*of\s*generation", "Generation Cost"),
    
    # Interest
    (r"interest\s*(and|&)\s*finance", "Interest & Finance Charges"),
    (r"interest\s*on\s*(loan|working)", "Interest & Finance Charges"),
    (r"finance\s*charges", "Interest & Finance Charges"),
    (r"interest\s*charges", "Interest & Finance Charges"),
    
    # Depreciation
    (r"depreciation", "Depreciation"),
    
    # ROE
    (r"return\s*on\s*equity", "Return on Equity"),
    (r"\broe\b", "Return on Equity"),
    (r"equity\s*return", "Return on Equity"),
    
    # O&M
    (r"operation\s*(and|&)\s*maintenance", "O&M Expenses"),
    (r"o\s*&\s*m\s*expense", "O&M Expenses"),
    (r"total\s*o\s*(&|and)\s*m", "Total O&M"),
    
    # O&M Details
    (r"employee\s*(cost|expense)", "Employee Cost"),
    (r"staff\s*cost", "Employee Cost"),
    (r"salary", "Employee Cost"),
    (r"repair\s*(and|&)\s*maintenance", "Repair & Maintenance"),
    (r"r\s*&\s*m\s*expense", "Repair & Maintenance"),
    (r"admin.*general.*expense", "A&G Expenses"),
    (r"a\s*&\s*g\s*expense", "A&G Expenses"),
    (r"administration\s*expense", "A&G Expenses"),
    (r"terminal\s*benefit", "Terminal Benefits"),
    (r"provision\s*for\s*bad", "Provision for Bad Debts"),
    
    # Transmission/Wheeling
    (r"transmission\s*charge", "Transmission Charges"),
    (r"wheeling\s*charge", "Wheeling Charges"),
    
    # Totals
    (r"total\s*arr", "Total ARR"),
    (r"total\s*annual\s*revenue", "Total ARR"),
    (r"total\s*expenditure", "Total Expenditure"),
    (r"aggregate\s*revenue\s*requirement", "Total ARR"),
    
    # ERC
    (r"expected\s*revenue", "Expected Revenue (ERC)"),
    (r"revenue\s*from\s*tariff", "Revenue from Tariff"),
    (r"tariff\s*revenue", "Revenue from Tariff"),
    (r"non.tariff\s*income", "Non-Tariff Income"),
    (r"other\s*income", "Non-Tariff Income"),
    
    # Gap
    (r"revenue\s*gap", "Revenue Gap / (Surplus)"),
    (r"gap.*surplus", "Revenue Gap / (Surplus)"),
    (r"surplus.*gap", "Revenue Gap / (Surplus)"),
    (r"statutory\s*surplus", "Statutory Surplus"),
    (r"net\s*revenue\s*gap", "Revenue Gap / (Surplus)"),
]


def normalize_row_label(raw_label: str) -> NormalizationResult:
    """
    Normalize a raw extracted row label to a canonical name.
    
    Uses rule-based regex matching with fallback to exact match.
    """
    label_lower = raw_label.lower().strip()
    
    # Try rule-based matching
    for pattern, canonical in _NORMALIZATION_RULES:
        if re.search(pattern, label_lower):
            info = CANONICAL_ITEMS.get(canonical, {"category": "Other", "cost_head": "Other"})
            return NormalizationResult(
                canonical_name=canonical,
                category=info["category"],
                cost_head=info["cost_head"],
                confidence=0.9,
                method="rule_based",
            )
    
    # Try exact match in canonical items
    for canonical in CANONICAL_ITEMS:
        if canonical.lower() == label_lower:
            info = CANONICAL_ITEMS[canonical]
            return NormalizationResult(
                canonical_name=canonical,
                category=info["category"],
                cost_head=info["cost_head"],
                confidence=1.0,
                method="rule_based",
            )
    
    # Fallback: use the raw label as-is
    return NormalizationResult(
        canonical_name=raw_label.strip(),
        category="Other",
        cost_head="Other",
        confidence=0.3,
        method="fallback",
    )


def normalize_batch(raw_labels: List[str]) -> List[NormalizationResult]:
    """Normalize a batch of row labels."""
    return [normalize_row_label(label) for label in raw_labels]
