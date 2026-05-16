"""
Deterministic KSERC target table catalog and column normalization.

The extraction pipeline uses these targets to avoid relying on broad row
matching across the whole PDF. Targets are deliberately small and explicit:
chapter, caption patterns, expected financial columns, and priority.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


CHAPTER_SBU_G = "SBU_G"
CHAPTER_SBU_T = "SBU_T"
CHAPTER_ENERGY_TD = "ENERGY_TD"
CHAPTER_SBU_D = "SBU_D"
CHAPTER_COMMON = "COMMON_EXPENSES"
CHAPTER_CONSOLIDATED = "CONSOLIDATED"

DOCUMENT_PETITION = "PETITION"
DOCUMENT_ARR_ORDER = "ARR_ORDER"
DOCUMENT_ANY = "ANY"


@dataclass(frozen=True)
class TargetTable:
    target_id: str
    chapter: str
    document_type: str
    caption_patterns: Tuple[str, ...]
    required_columns: Tuple[str, ...]
    unit: str = "Rs. Cr."
    priority: int = 1


TARGET_TABLE_CATALOG: Tuple[TargetTable, ...] = (
    TargetTable(
        target_id="SBU_G_TRANSFER_COST",
        chapter=CHAPTER_SBU_G,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "Transfer Cost of SBU-G",
            "Transfer Cost of SBU G",
            "ARR&ERC of SBU-G",
            "ARR and ERC of SBU-G",
            "SBU-G as per truing up petition",
            "Approved Transfer Cost of SBU-G",
        ),
        required_columns=("Particulars", "MYT", "Actual", "Sought", "Difference"),
        unit="Rs. Cr.",
        priority=1,
    ),
    TargetTable(
        target_id="SBU_G_GENERATION_SUMMARY",
        chapter=CHAPTER_SBU_G,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "Cost of Generation of Power",
            "Generation summary",
            "Generation Business",
            "ARR of SBU-G",
            "SBU-G summary",
        ),
        required_columns=("Particulars", "Approved", "Actual", "Claimed"),
        unit="Rs. Cr.",
        priority=2,
    ),
    TargetTable(
        target_id="SBU_T_TRANSFER_COST",
        chapter=CHAPTER_SBU_T,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "Transfer Cost of SBU-T",
            "Transfer Cost of SBU T",
            "Intra-State Transmission charges",
            "Cost of Intra-State Transmission",
            "SBU-T transfer cost",
        ),
        required_columns=("Particulars", "MYT", "Actual", "Sought", "Difference"),
        unit="Rs. Cr.",
        priority=1,
    ),
    TargetTable(
        target_id="SBU_T_ARR_SUMMARY",
        chapter=CHAPTER_SBU_T,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "ARR and ERC of SBU-T",
            "ARR&ERC of SBU-T",
            "ARR of SBU-T",
            "SBU-T summary",
            "Summary of ARR and ERC claimed for SBU-T",
            "ARR of Transmission Business Unit",
            "ARR OF TRANSMISSION BUSINESS UNIT",
            "Transmission Business Unit (SBU-T)",
        ),
        required_columns=("Particulars", "Approved", "Actual", "Claimed"),
        unit="Rs. Cr.",
        priority=2,
    ),
    TargetTable(
        target_id="ENERGY_TD_LOSS_SUMMARY",
        chapter=CHAPTER_ENERGY_TD,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "Energy sales and T&D loss",
            "Energy Sales",
            "T&D loss",
            "Transmission loss",
            "Distribution loss",
        ),
        required_columns=("Particulars", "Approved", "Actual", "Claimed"),
        unit="MU / %",
        priority=1,
    ),
    TargetTable(
        target_id="SBU_D_ARR_SUMMARY",
        chapter=CHAPTER_SBU_D,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "ARR, ERC and Revenue Gap",
            "ARR ERC and Revenue Gap",
            "Summary of ARR",
            "SBU-D ARR summary",
            "Revenue gap claimed for SBU-D",
            "Distribution business",
        ),
        required_columns=("Particulars", "Approved", "Actual", "Claimed"),
        unit="Rs. Cr.",
        priority=1,
    ),
    TargetTable(
        target_id="CONSOLIDATED_ARR_SUMMARY",
        chapter=CHAPTER_CONSOLIDATED,
        document_type=DOCUMENT_ANY,
        caption_patterns=(
            "Consolidated ARR",
            "Consolidated Truing up",
            "Consolidated summary",
            "Total KSEB Ltd",
            "KSEB Ltd summary",
        ),
        required_columns=("Particulars", "Approved", "Actual", "Claimed"),
        unit="Rs. Cr.",
        priority=1,
    ),
)


TARGETS_BY_ID: Dict[str, TargetTable] = {
    target.target_id: target for target in TARGET_TABLE_CATALOG
}


def clean_text(value: str) -> str:
    cleaned = (value or "").lower().replace("&", " and ")
    cleaned = re.sub(r"[^a-z0-9/%().+-]+", " ", cleaned)
    return re.sub(r"\s+", " ", cleaned).strip()


def caption_matches(text: str, patterns: Iterable[str]) -> Optional[str]:
    normalized_text = clean_text(text)
    for pattern in patterns:
        normalized_pattern = clean_text(pattern)
        if normalized_pattern and normalized_pattern in normalized_text:
            return pattern
    return None


def contract_document_type(document_type: str) -> str:
    if document_type == "truing_up_petition":
        return DOCUMENT_PETITION
    if document_type == "arr_order":
        return DOCUMENT_ARR_ORDER
    return (document_type or DOCUMENT_ANY).upper()


def target_applies_to_document(target: TargetTable, document_type: str) -> bool:
    contract_type = contract_document_type(document_type)
    return target.document_type in {DOCUMENT_ANY, contract_type}


_COLUMN_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "particulars",
        (
            r"\bparticulars?\b",
            r"\bdescription\b",
            r"\bitem\b",
            r"\bhead\b",
        ),
    ),
    (
        "approved",
        (
            r"\bmyt\s+order\b",
            r"\bmyt\b",
            r"\barr\s+approval\b",
            r"\barr\s+and\s+erc\s+order\b",
            r"\barr\s+erc\s+order\b",
            r"\barr\s*&\s*erc\s+order\b",
            r"\bapproved\b",
            r"\bapproval\b",
            r"\ballowed\b",
        ),
    ),
    (
        "actual",
        (
            r"\bactuals?\b",
            r"\baudited\b",
            r"\bas\s+per\s+accounts\b",
            r"\baccounts\b",
        ),
    ),
    (
        "claimed",
        (
            r"\btu\s+sought\b",
            r"\bsought\s+for\s+tu\b",
            r"\bsought\b",
            r"\btruing\s+up\s+petition\b",
            r"\btruing\s+up\b",
            r"\btrue\s+up\b",
            r"\brequirement\b",
            r"\btruing\s+up\s+claim\b",
            r"\btrue\s+up\s+claim\b",
            r"\bclaimed\b",
            r"\bclaim\b",
            r"\bpetition\s+claim\b",
            r"\bpetition\b",
        ),
    ),
    (
        "deviation",
        (
            r"\bdifference\s+over\s+approval\b",
            r"\bdeviation\s+from\s+approval\b",
            r"\bdifference\b",
            r"\bvariation\b",
            r"\bdeviation\b",
        ),
    ),
    (
        "kserc_approval",
        (
            r"\bkserc\s+approval\b",
            r"\bcommission\s+approval\b",
            r"\bapproved\s+by\s+commission\b",
        ),
    ),
)


def normalize_column_header(header: str) -> Optional[str]:
    normalized = clean_text(header)
    if not normalized:
        return None
    for column_key, patterns in _COLUMN_PATTERNS:
        if any(re.search(pattern, normalized) for pattern in patterns):
            return column_key
    return None


def normalize_columns(headers: Sequence[object]) -> List[Optional[str]]:
    return [normalize_column_header(str(header or "")) for header in headers]


def find_header_row(table: Sequence[Sequence[object]], scan_rows: int = 4) -> Tuple[int, List[Optional[str]]]:
    best_index = 0
    best_columns: List[Optional[str]] = []
    best_score = -1
    for index, row in enumerate(table[:scan_rows]):
        columns = normalize_columns(row)
        score = len({column for column in columns if column})
        if "particulars" in columns:
            score += 2
        if any(column in columns for column in ("approved", "actual", "claimed")):
            score += 2
        if score > best_score:
            best_index = index
            best_columns = columns
            best_score = score
    return best_index, best_columns


def table_has_required_shape(table: Sequence[Sequence[object]]) -> bool:
    if not table or len(table) < 2:
        return False
    _, columns = find_header_row(table)
    column_set = {column for column in columns if column}
    return "particulars" in column_set and bool(column_set & {"approved", "actual", "claimed", "deviation"})
