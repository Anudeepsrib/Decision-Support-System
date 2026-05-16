"""
MVP PDF Extraction Pipeline — pdfplumber-based table extraction.

Extracts structured financial tables from KSERC ARR orders and
truing-up petition PDFs. Each extracted value carries provenance
metadata (page, table index, confidence).

No LangGraph, no complex AI agents — just deterministic extraction.
"""

import io
import logging
import re
import time
from typing import Callable, List, Dict, Optional, Sequence, Set, Tuple
from dataclasses import dataclass

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import camelot
    CAMELOT_AVAILABLE = True
except ImportError:
    CAMELOT_AVAILABLE = False

try:
    from .table_targets import (
        CHAPTER_CONSOLIDATED,
        CHAPTER_ENERGY_TD,
        CHAPTER_SBU_D,
        CHAPTER_SBU_G,
        CHAPTER_SBU_T,
        TARGET_TABLE_CATALOG,
        TargetTable,
        caption_matches,
        clean_text as clean_target_text,
        find_header_row,
        normalize_columns,
        table_has_required_shape,
        target_applies_to_document,
    )
except ImportError:  # Support direct imports from the backend directory.
    from table_targets import (
        CHAPTER_CONSOLIDATED,
        CHAPTER_ENERGY_TD,
        CHAPTER_SBU_D,
        CHAPTER_SBU_G,
        CHAPTER_SBU_T,
        TARGET_TABLE_CATALOG,
        TargetTable,
        caption_matches,
        clean_text as clean_target_text,
        find_header_row,
        normalize_columns,
        table_has_required_shape,
        target_applies_to_document,
    )


logger = logging.getLogger(__name__)


@dataclass
class ExtractedTableRow:
    """A single extracted row from a PDF table."""
    page_number: int
    table_index: int
    table_name: str
    row_label: str
    value: Optional[float]
    value_type: str = "value"
    document_type: str = "unknown"
    unit: str = "Rs. Cr."
    confidence: float = 0.0
    raw_text: str = ""
    target_id: Optional[str] = None
    chapter: Optional[str] = None
    table_caption: Optional[str] = None
    normalized_columns: Tuple[str, ...] = ()
    source_type: str = "chapter_table"


@dataclass
class ExtractedTargetTable:
    """A target table found during deterministic chapter-bound extraction."""
    target_id: str
    chapter: str
    document_type: str
    page_number: int
    table_caption: str
    raw_columns: Tuple[str, ...]
    normalized_columns: Tuple[str, ...]
    rows: List[ExtractedTableRow]
    confidence: float


# ─── Financial Value Parser ───

# Patterns for detecting financial values in table cells
_MONEY_PATTERN = re.compile(
    r'[-−]?\s*[\d,]+\.?\d*'
)

# Known table header keywords that identify KSERC financial tables
_TABLE_IDENTIFIERS = [
    "annual revenue requirement",
    "arr summary",
    "expected revenue",
    "erc summary",
    "revenue gap",
    "power purchase",
    "cost of power",
    "generation cost",
    "transmission cost",
    "distribution cost",
    "operation and maintenance",
    "o&m",
    "interest and finance",
    "depreciation",
    "return on equity",
    "employee cost",
    "repair and maintenance",
    "administration",
    "total expenditure",
    "total revenue",
    "gap / surplus",
    "sbu-g", "sbu-t", "sbu-d",
    "approved", "actual", "claimed", "petition",
    "truing up", "truing-up", "true up", "true-up",
]

_TARGET_PAGE_KEYWORDS = [
    *_TABLE_IDENTIFIERS,
    "table 1", "table-1", "table 2", "table-2",
    "summary of arr", "arr approved", "approved arr",
    "aggregate revenue requirement", "annual revenue requirement",
    "revenue surplus", "revenue deficit", "revenue requirement",
    "true up summary", "truing up summary", "sbu summary",
    "sbu-g", "sbu-t", "sbu-d", "state business unit",
]

_TOC_KEYWORDS = [
    "annual revenue requirement", "aggregate revenue requirement", "arr",
    "revenue gap", "expected revenue", "truing", "true up",
    "power purchase", "sbu", "summary",
]

_DEFAULT_MAX_TARGET_PAGES = {
    "arr_order": 70,
    "truing_up_petition": 55,
    "unknown": 60,
}

# Known KSERC ARR line item patterns
_LINE_ITEM_PATTERNS = [
    (r"power\s*purchase\s*cost", "Power Purchase Cost"),
    (r"cost\s*of\s*power\s*purchase", "Power Purchase Cost"),
    (r"purchase\s*of\s*power", "Power Purchase Cost"),
    (r"generation\s*cost", "Generation Cost"),
    (r"interest\s*(and|&)\s*finance", "Interest & Finance Charges"),
    (r"interest\s*on\s*loan", "Interest & Finance Charges"),
    (r"depreciation", "Depreciation"),
    (r"return\s*on\s*equity", "Return on Equity"),
    (r"roe", "Return on Equity"),
    (r"employee\s*cost", "Employee Cost"),
    (r"repair\s*(and|&)\s*maintenance", "Repair & Maintenance"),
    (r"r\s*&\s*m\s*expense", "Repair & Maintenance"),
    (r"admin.*general.*expense", "A&G Expenses"),
    (r"a\s*&\s*g\s*expense", "A&G Expenses"),
    (r"operation\s*(and|&)\s*maintenance", "O&M Expenses"),
    (r"o\s*&\s*m", "O&M Expenses"),
    (r"total\s*arr", "Total ARR"),
    (r"total\s*annual\s*revenue", "Total ARR"),
    (r"total\s*expenditure", "Total Expenditure"),
    (r"expected\s*revenue", "Expected Revenue (ERC)"),
    (r"revenue\s*from\s*tariff", "Revenue from Tariff"),
    (r"non.tariff\s*income", "Non-Tariff Income"),
    (r"revenue\s*gap", "Revenue Gap / (Surplus)"),
    (r"gap.*surplus", "Revenue Gap / (Surplus)"),
    (r"surplus.*gap", "Revenue Gap / (Surplus)"),
    (r"transmission\s*charge", "Transmission Charges"),
    (r"wheeling\s*charge", "Wheeling Charges"),
    (r"statutory\s*surplus", "Statutory Surplus"),
    (r"provision\s*for\s*bad", "Provision for Bad Debts"),
    (r"terminal\s*benefit", "Terminal Benefits"),
    (r"total\s*o\s*&\s*m", "Total O&M"),
]


def _parse_financial_value(text: str) -> Optional[float]:
    """Parse a financial value from text, handling Indian number formats."""
    if not text or text.strip() in ("-", "—", "", "N/A", "NA", "nil", "Nil"):
        return None
    
    # Clean the text
    cleaned = text.strip()
    cleaned = cleaned.replace("−", "-")  # Unicode minus
    cleaned = cleaned.replace("(", "-").replace(")", "")  # Parenthetical negatives
    cleaned = cleaned.replace(",", "")  # Remove thousands separators
    cleaned = cleaned.replace(" ", "")  # Remove spaces
    
    match = _MONEY_PATTERN.search(cleaned)
    if match:
        try:
            return float(match.group())
        except ValueError:
            return None
    return None


def _is_financial_table(table_text: str) -> Tuple[bool, str]:
    """Check if a table is likely a KSERC financial table."""
    text_lower = table_text.lower()
    for keyword in _TABLE_IDENTIFIERS:
        if keyword in text_lower:
            return True, keyword
    return False, ""


def _calculate_confidence(row_label: str, value: Optional[float], table_name: str) -> float:
    """Calculate extraction confidence score (0.0 to 1.0)."""
    score = 0.5  # Base confidence
    
    # Boost for recognized line items
    for pattern, _ in _LINE_ITEM_PATTERNS:
        if re.search(pattern, row_label.lower()):
            score += 0.3
            break
    
    # Boost for having a numeric value
    if value is not None:
        score += 0.1
    
    # Boost for recognized table
    if table_name:
        score += 0.1
    
    return min(score, 1.0)


def _infer_document_type(filename: str) -> str:
    """Infer document type from filename when the caller does not provide it."""
    name = (filename or "").lower()
    if "petition" in name or "truing" in name or "true" in name:
        return "truing_up_petition"
    if "arr" in name or "order" in name or "approval" in name:
        return "arr_order"
    return "unknown"


def _column_value_type(header: str) -> Optional[str]:
    """Map a table column heading to the value type it carries."""
    h = clean_target_text(header or "")
    if re.search(r"\bkserc\s+approval\b|\bcommission\s+approval\b|\bapproved\s+by\s+commission\b", h):
        return "kserc_approval"
    if re.search(
        r"\bmyt\s+order\b|\bmyt\b|\barr\s+approval\b|\barr\s+and\s+erc\s+order\b|"
        r"\barr\s+erc\s+order\b|\bapproved\b|\bapproval\b|\ballowed\b|\barr\s+order\b",
        h,
    ):
        return "approved"
    if re.search(r"\bactuals?\b|\baudited\b|\baudit\b|\bas\s+per\s+accounts\b|\baccounts\b", h):
        return "actual"
    if re.search(
        r"\btu\s+sought\b|\bsought\s+for\s+tu\b|\bsought\b|\btruing\s+up\s+petition\b|"
        r"\btruing\s+up\s+claim\b|\btrue\s+up\s+claim\b|\bclaimed\b|\bclaim\b|"
        r"\bpetition\s+claim\b|\bpetition\b|\bproposed\b",
        h,
    ):
        return "claimed"
    if re.search(r"\bdifference\s+over\s+approval\b|\bdeviation\s+from\s+approval\b|\bdifference\b|\bvariation\b|\bdeviation\b", h):
        return "deviation"
    return None


def _default_value_type(document_type: str) -> str:
    if document_type == "arr_order":
        return "approved"
    if document_type == "truing_up_petition":
        return "actual"
    return "value"


def _select_value_columns(
    row: List[Optional[str]],
    header_types: Dict[int, Optional[str]],
    document_type: str,
) -> List[Tuple[int, float, str]]:
    """Select the numeric columns relevant to the document type."""
    parsed_values: List[Tuple[int, float, Optional[str]]] = []
    for col_idx in range(1, len(row)):
        parsed = _parse_financial_value(str(row[col_idx] or ""))
        if parsed is not None:
            parsed_values.append((col_idx, parsed, header_types.get(col_idx)))

    if not parsed_values:
        return []

    has_typed_headers = any(value_type for _, _, value_type in parsed_values)

    if document_type == "arr_order" and has_typed_headers:
        selected = [
            (idx, value, "approved")
            for idx, value, value_type in parsed_values
            if value_type in ("approved", "kserc_approval")
        ]
        if selected:
            return selected

    if document_type == "truing_up_petition" and has_typed_headers:
        selected = [
            (idx, value, value_type or "actual")
            for idx, value, value_type in parsed_values
            if value_type in ("approved", "actual", "claimed", "deviation")
        ]
        if selected:
            return selected

    # Fallback for unlabelled financial tables: use the first numeric value.
    idx, value, value_type = parsed_values[0]
    return [(idx, value, value_type or _default_value_type(document_type))]


def _score_page_text(text: str) -> int:
    """Score a page for likely KSERC financial summary tables."""
    lower = (text or "").lower()
    score = 0
    for keyword in _TARGET_PAGE_KEYWORDS:
        if keyword in lower:
            score += 3 if keyword in _TABLE_IDENTIFIERS else 2
    for pattern, _ in _LINE_ITEM_PATTERNS:
        if re.search(pattern, lower):
            score += 4
    if re.search(r"\btable\s*[-.]?\s*\d", lower):
        score += 1
    if any(token in lower for token in ("approved", "actual", "claimed")):
        score += 2
    return score


def _toc_page_refs(text: str, total_pages: int) -> Set[int]:
    """Extract likely page references from contents/table lists."""
    refs: Set[int] = set()
    lower = (text or "").lower()
    if "contents" not in lower and "table of contents" not in lower and "list of tables" not in lower:
        return refs

    for line in text.splitlines():
        line_lower = line.lower()
        if not any(keyword in line_lower for keyword in _TOC_KEYWORDS):
            continue
        for match in re.finditer(r"\b(\d{1,3})\b", line):
            page_num = int(match.group(1))
            if 1 <= page_num <= total_pages:
                refs.add(page_num)
    return refs


def _neighbor_pages(page_numbers: Sequence[int], total_pages: int, radius: int = 1) -> Set[int]:
    pages: Set[int] = set()
    for page_num in page_numbers:
        for candidate in range(page_num - radius, page_num + radius + 1):
            if 1 <= candidate <= total_pages:
                pages.add(candidate)
    return pages


_CHAPTER_MARKERS: Dict[str, Tuple[str, ...]] = {
    CHAPTER_SBU_G: (
        "truing up of accounts of strategic business unit generation",
        "strategic business unit generation",
        "sbu-g",
        "sbu g",
        "generation",
    ),
    CHAPTER_SBU_T: (
        "truing up of accounts of strategic business unit transmission",
        "strategic business unit transmission",
        "sbu-t",
        "sbu t",
        "transmission",
    ),
    CHAPTER_ENERGY_TD: (
        "energy sales",
        "t and d loss",
        "t d loss",
        "transmission loss",
        "distribution loss",
    ),
    CHAPTER_SBU_D: (
        "arr erc and revenue gap",
        "arr and erc and revenue gap",
        "strategic business unit distribution",
        "sbu-d",
        "sbu d",
        "distribution",
    ),
    CHAPTER_CONSOLIDATED: (
        "consolidated truing up",
        "consolidated",
    ),
}


def _chapter_page_score(text: str, chapter: str) -> int:
    normalized = clean_target_text(text)
    if not normalized:
        return 0

    markers = _CHAPTER_MARKERS.get(chapter, ())
    score = 0
    for marker in markers:
        marker_text = clean_target_text(marker)
        if marker_text and marker_text in normalized:
            score += 4 if len(marker_text.split()) > 3 else 2

    if "chapter" in normalized:
        score += 3
    if "truing up of accounts" in normalized:
        score += 2
    if "table of contents" in normalized or re.search(r"\bcontents\b", normalized):
        score -= 6
    return max(score, 0)


def detect_chapter_ranges_from_text(page_texts: Sequence[str]) -> Dict[str, Tuple[int, int]]:
    """
    Detect deterministic chapter page ranges from extracted page text.

    Returns one-indexed inclusive page ranges:
    {"SBU_G": (start_page, end_page), ...}
    """
    candidates: Dict[str, int] = {}
    for chapter in (CHAPTER_SBU_G, CHAPTER_SBU_T, CHAPTER_ENERGY_TD, CHAPTER_SBU_D, CHAPTER_CONSOLIDATED):
        scored_pages: List[Tuple[int, int]] = []
        for index, text in enumerate(page_texts, 1):
            score = _chapter_page_score(text, chapter)
            if score > 0:
                scored_pages.append((index, score))
        if not scored_pages:
            continue

        # Prefer the earliest strong chapter page after front matter, while
        # avoiding TOC-only hits that merely list every chapter.
        max_score = max(score for _, score in scored_pages)
        threshold = max(3, max_score - 2)
        strong = [page for page, score in scored_pages if score >= threshold]
        non_front_matter = [page for page in strong if page > 3]
        candidates[chapter] = min(non_front_matter or strong)

    sorted_starts = sorted((start, chapter) for chapter, start in candidates.items())
    ranges: Dict[str, Tuple[int, int]] = {}
    total_pages = len(page_texts)
    for index, (start_page, chapter) in enumerate(sorted_starts):
        next_start = sorted_starts[index + 1][0] if index + 1 < len(sorted_starts) else total_pages + 1
        end_page = max(start_page, next_start - 1)
        ranges[chapter] = (start_page, min(end_page, total_pages))

    if ranges:
        logger.info("Detected chapter_ranges=%s", ranges)
    return ranges


def _select_target_pages(
    pdf,
    document_type: str,
    max_target_pages: Optional[int],
    timeout_at: Optional[float],
    progress_callback: Optional[Callable[[str, float, int, int], None]],
) -> Tuple[List[int], int]:
    """Scan page text selectively and return only pages likely to contain key tables."""
    total_pages = len(pdf.pages)
    max_pages = max_target_pages or _DEFAULT_MAX_TARGET_PAGES.get(document_type, 60)
    scored: List[Tuple[int, int]] = []
    toc_refs: Set[int] = set()
    seed_pages = set(range(1, min(total_pages, 8) + 1))
    scanned_page_numbers: List[int] = []
    top_scan_limit = min(total_pages, 20)

    # Always scan front-matter pages and potential TOC pages
    scan_candidates = set(range(1, top_scan_limit + 1))
    if total_pages > 40:
        scan_candidates.update(range(21, min(total_pages, 61), 10))
    scan_page_numbers = sorted(scan_candidates)

    last_report = 0.0
    for index in scan_page_numbers:
        if timeout_at and time.monotonic() > timeout_at:
            break
        scanned_page_numbers.append(index)
        try:
            page = pdf.pages[index - 1]
            text = page.extract_text() or ""
        except Exception:
            text = ""

        score = _score_page_text(text)
        if score > 0:
            scored.append((index, score))
        toc_refs.update(_toc_page_refs(text, total_pages))

        now = time.monotonic()
        if progress_callback and (now - last_report > 0.75 or index == scan_page_numbers[-1]):
            scan_progress = 5 + (len(scanned_page_numbers) / max(len(scan_page_numbers), 1)) * 30
            progress_callback("Scanning front matter and TOC for target tables", scan_progress, index, total_pages)
            last_report = now

    scored.sort(key=lambda item: item[1], reverse=True)
    selected = set(seed_pages)
    selected.update(_neighbor_pages([page for page, _ in scored[:max_pages]], total_pages))
    selected.update(_neighbor_pages(sorted(toc_refs), total_pages))

    if len(selected) > max_pages:
        ranked = sorted(selected, key=lambda p: next((score for page, score in scored if page == p), 0), reverse=True)
        required = sorted(seed_pages | (toc_refs & selected))
        selected = set(required[:max_pages])
        for page in ranked:
            if len(selected) >= max_pages:
                break
            selected.add(page)

    if not selected:
        # Fallback: first few pages only
        selected = set(seed_pages)

    return sorted(selected), total_pages


def _extract_rows_from_table(
    table,
    page_num: int,
    table_idx: int,
    table_name: str,
    document_type: str,
) -> List[ExtractedTableRow]:
    rows: List[ExtractedTableRow] = []
    if not table or len(table) < 2:
        return rows

    table_text = " ".join(
        " ".join(str(cell or "") for cell in row)
        for row in table[:3]
    )
    _, matched_keyword = _is_financial_table(table_text)

    if table[0]:
        header_text = " | ".join(str(c or "") for c in table[0] if c)
        table_name = header_text[:200]
    header_types = {
        idx: _column_value_type(str(cell or ""))
        for idx, cell in enumerate(table[0] or [])
    }

    if matched_keyword:
        table_name = f"{matched_keyword.title()} — {table_name}"

    for row_idx, row in enumerate(table):
        if not row or row_idx == 0:
            continue

        row_label = str(row[0] or "").strip()
        if not row_label or len(row_label) < 2:
            continue

        raw_text = " | ".join(str(c or "") for c in row)
        for _, value, value_type in _select_value_columns(row, header_types, document_type):
            confidence = _calculate_confidence(row_label, value, table_name)
            rows.append(ExtractedTableRow(
                page_number=page_num,
                table_index=table_idx,
                table_name=table_name,
                row_label=row_label,
                value=value,
                value_type=value_type,
                document_type=document_type,
                confidence=confidence,
                raw_text=raw_text,
            ))
    return rows


def _cell_text(cell: object) -> str:
    return str(cell or "").strip()


def _row_is_probable_header(row: Sequence[object]) -> bool:
    normalized_columns = normalize_columns(row)
    return "particulars" in normalized_columns and bool(
        set(normalized_columns) & {"approved", "actual", "claimed", "deviation", "kserc_approval"}
    )


def _target_value_type(column_key: str, document_type: str, normalized_columns: Sequence[Optional[str]]) -> str:
    if column_key == "kserc_approval":
        if document_type == "arr_order" and "approved" not in normalized_columns:
            return "approved"
        return "kserc_approval"
    return column_key


def _repair_shifted_claim_column(normalized_columns: Sequence[Optional[str]]) -> List[Optional[str]]:
    repaired = list(normalized_columns)
    if "actual" not in repaired or "claimed" not in repaired:
        return repaired
    actual_idx = repaired.index("actual")
    claimed_idx = repaired.index("claimed")
    shifted_idx = actual_idx + 1
    if claimed_idx == shifted_idx + 1 and shifted_idx < len(repaired) and repaired[shifted_idx] is None:
        repaired[shifted_idx] = "claimed"
        repaired[claimed_idx] = None
    return repaired


def _extract_rows_from_continuation_table(
    table,
    page_num: int,
    table_idx: int,
    target: TargetTable,
    table_caption: str,
    document_type: str,
) -> Optional[ExtractedTargetTable]:
    if not table or len(table) < 2:
        return None
    first_row = table[0]
    if len(first_row) < 5:
        return None
    if not re.fullmatch(r"\d+", _cell_text(first_row[0] or "")):
        return None

    normalized_tuple = ("serial", "particulars", "approved", "actual", "claimed")
    rows: List[ExtractedTableRow] = []
    for row in table:
        if len(row) < 5:
            continue
        row_label = _cell_text(row[1])
        if not row_label or len(row_label) < 2:
            continue
        raw_text = " | ".join(_cell_text(cell) for cell in row)
        for col_idx, value_type in ((2, "approved"), (3, "actual"), (4, "claimed")):
            parsed_value = _parse_financial_value(_cell_text(row[col_idx]))
            if parsed_value is None:
                continue
            contextual_table_name = (
                f"{target.target_id} | {target.chapter} | {table_caption or 'Target table continuation'}"
            )[:200]
            rows.append(
                ExtractedTableRow(
                    page_number=page_num,
                    table_index=table_idx,
                    table_name=contextual_table_name,
                    row_label=row_label,
                    value=parsed_value,
                    value_type=value_type,
                    document_type=document_type,
                    unit=target.unit,
                    confidence=0.88,
                    raw_text=(
                        f"target_id={target.target_id}; chapter={target.chapter}; "
                        f"columns={'/'.join(normalized_tuple)}; row={raw_text}"
                    ),
                    target_id=target.target_id,
                    chapter=target.chapter,
                    table_caption=table_caption,
                    normalized_columns=normalized_tuple,
                    source_type="chapter_table",
                )
            )

    if not rows:
        return None
    return ExtractedTargetTable(
        target_id=target.target_id,
        chapter=target.chapter,
        document_type=document_type,
        page_number=page_num,
        table_caption=table_caption,
        raw_columns=(),
        normalized_columns=normalized_tuple,
        rows=rows,
        confidence=0.88,
    )


def _parse_value_near_column(
    row: Sequence[object],
    col_idx: int,
    normalized_columns: Sequence[Optional[str]],
    column_key: str,
) -> Optional[float]:
    if col_idx < len(row):
        parsed = _parse_financial_value(_cell_text(row[col_idx]))
        if parsed is not None:
            return parsed

    next_indices = [
        index for index in range(col_idx + 1, len(normalized_columns))
        if normalized_columns[index]
    ]
    next_idx = next_indices[0] if next_indices else min(len(row), col_idx + 4)
    for scan_idx in range(col_idx + 1, min(next_idx, len(row))):
        parsed = _parse_financial_value(_cell_text(row[scan_idx]))
        if parsed is not None:
            return parsed

    if column_key == "deviation":
        previous_indices = [
            index for index in range(0, col_idx)
            if normalized_columns[index]
        ]
        previous_idx = previous_indices[-1] if previous_indices else max(-1, col_idx - 4)
        for scan_idx in range(col_idx - 1, max(previous_idx, -1), -1):
            parsed = _parse_financial_value(_cell_text(row[scan_idx]))
            if parsed is not None:
                return parsed
    return None


def _extract_rows_from_target_table(
    table,
    page_num: int,
    table_idx: int,
    target: TargetTable,
    table_caption: str,
    document_type: str,
) -> ExtractedTargetTable:
    if not table or len(table) < 2 or not table_has_required_shape(table):
        continuation = _extract_rows_from_continuation_table(
            table,
            page_num,
            table_idx,
            target,
            table_caption,
            document_type,
        )
        if continuation is not None:
            return continuation
        return ExtractedTargetTable(
            target_id=target.target_id,
            chapter=target.chapter,
            document_type=document_type,
            page_number=page_num,
            table_caption=table_caption,
            raw_columns=(),
            normalized_columns=(),
            rows=[],
            confidence=0.0,
        )

    header_idx, normalized_columns = find_header_row(table)
    normalized_columns = _repair_shifted_claim_column(normalized_columns)
    raw_columns = tuple(_cell_text(cell) for cell in table[header_idx])
    normalized_tuple = tuple(column or "" for column in normalized_columns)
    try:
        particulars_idx = normalized_columns.index("particulars")
    except ValueError:
        particulars_idx = 0

    rows: List[ExtractedTableRow] = []
    for row in table[header_idx + 1:]:
        if not row or _row_is_probable_header(row):
            continue
        if particulars_idx >= len(row):
            continue
        row_label = _cell_text(row[particulars_idx])
        if not row_label or len(row_label) < 2:
            continue

        raw_text = " | ".join(_cell_text(cell) for cell in row)
        for col_idx, column_key in enumerate(normalized_columns):
            if not column_key or column_key == "particulars" or col_idx >= len(row):
                continue
            value_type = _target_value_type(column_key, document_type, normalized_columns)
            if value_type not in {"approved", "actual", "claimed", "deviation", "kserc_approval"}:
                continue
            parsed_value = _parse_value_near_column(row, col_idx, normalized_columns, column_key)
            if parsed_value is None:
                continue

            contextual_table_name = (
                f"{target.target_id} | {target.chapter} | {table_caption or 'Target table'}"
            )[:200]
            row_confidence = max(
                _calculate_confidence(row_label, parsed_value, contextual_table_name),
                0.9 if value_type in {"approved", "actual", "claimed"} else 0.82,
            )
            rows.append(
                ExtractedTableRow(
                    page_number=page_num,
                    table_index=table_idx,
                    table_name=contextual_table_name,
                    row_label=row_label,
                    value=parsed_value,
                    value_type=value_type,
                    document_type=document_type,
                    unit=target.unit,
                    confidence=min(row_confidence, 0.99),
                    raw_text=(
                        f"target_id={target.target_id}; chapter={target.chapter}; "
                        f"columns={'/'.join(normalized_tuple)}; row={raw_text}"
                    ),
                    target_id=target.target_id,
                    chapter=target.chapter,
                    table_caption=table_caption,
                    normalized_columns=normalized_tuple,
                    source_type="chapter_table",
                )
            )

    confidence = 0.95 if rows else 0.0
    return ExtractedTargetTable(
        target_id=target.target_id,
        chapter=target.chapter,
        document_type=document_type,
        page_number=page_num,
        table_caption=table_caption,
        raw_columns=raw_columns,
        normalized_columns=normalized_tuple,
        rows=rows,
        confidence=confidence,
    )


def _candidate_pages_for_target(
    page_texts: Sequence[str],
    target: TargetTable,
    chapter_ranges: Dict[str, Tuple[int, int]],
) -> List[Tuple[int, str]]:
    total_pages = len(page_texts)
    if target.chapter in chapter_ranges:
        start_page, end_page = chapter_ranges[target.chapter]
        page_numbers = range(max(1, start_page), min(total_pages, end_page) + 1)
    else:
        page_numbers = range(1, total_pages + 1)

    candidates: List[Tuple[int, str]] = []
    candidate_map: Dict[int, str] = {}
    for page_num in page_numbers:
        text = page_texts[page_num - 1] if page_num - 1 < len(page_texts) else ""
        matched_caption = caption_matches(text, target.caption_patterns)
        if matched_caption:
            candidate_map[page_num] = matched_caption
            if page_num + 1 <= total_pages:
                candidate_map.setdefault(page_num + 1, matched_caption)
    return sorted(candidate_map.items())


def extract_target_tables_from_open_pdf(
    pdf,
    document_type: str,
    page_texts: Sequence[str],
    chapter_ranges: Optional[Dict[str, Tuple[int, int]]] = None,
) -> List[ExtractedTargetTable]:
    """Extract target catalog tables within detected chapter ranges."""
    chapter_ranges = chapter_ranges or {}
    found_tables: List[ExtractedTargetTable] = []
    seen: Set[Tuple[str, int, int]] = set()

    for target in sorted(TARGET_TABLE_CATALOG, key=lambda item: item.priority):
        if not target_applies_to_document(target, document_type):
            continue
        candidates = _candidate_pages_for_target(page_texts, target, chapter_ranges)
        for page_num, matched_caption in candidates:
            if page_num < 1 or page_num > len(pdf.pages):
                continue
            page_has_target_rows = False
            try:
                page = pdf.pages[page_num - 1]
                tables = page.extract_tables()
            except Exception:
                tables = []

            for table_idx, table in enumerate(tables):
                dedupe_key = (target.target_id, page_num, table_idx)
                if dedupe_key in seen:
                    continue
                table_text = " ".join(
                    " ".join(_cell_text(cell) for cell in row)
                    for row in (table or [])[:5]
                )
                table_caption = caption_matches(table_text, target.caption_patterns) or matched_caption
                target_table = _extract_rows_from_target_table(
                    table=table,
                    page_num=page_num,
                    table_idx=table_idx,
                    target=target,
                    table_caption=table_caption,
                    document_type=document_type,
                )
                if target_table.rows:
                    found_tables.append(target_table)
                    seen.add(dedupe_key)
                    page_has_target_rows = True

            if not page_has_target_rows:
                text_table = _extract_rows_from_target_text(
                    page_texts[page_num - 1] if page_num - 1 < len(page_texts) else "",
                    page_num,
                    target,
                    matched_caption,
                    document_type,
                )
                if text_table.rows:
                    found_tables.append(text_table)

    return found_tables


def _flatten_target_tables(target_tables: Sequence[ExtractedTargetTable]) -> List[ExtractedTableRow]:
    rows: List[ExtractedTableRow] = []
    for table in target_tables:
        rows.extend(table.rows)
    return rows


def _dedupe_rows(rows: Sequence[ExtractedTableRow]) -> List[ExtractedTableRow]:
    best: Dict[Tuple[int, str, str, Optional[float]], ExtractedTableRow] = {}
    for row in rows:
        key = (
            row.page_number,
            clean_target_text(row.row_label),
            row.value_type,
            row.value,
        )
        current = best.get(key)
        if current is None or (row.confidence or 0) > (current.confidence or 0):
            best[key] = row
    return sorted(best.values(), key=lambda row: (row.page_number, row.table_index or 0, row.row_label, row.value_type))


_TARGET_TEXT_ROW_KEYWORDS = (
    "cost of generation",
    "o&m expenses",
    "o & m expenses",
    "operation and maintenance",
    "interest & finance",
    "interest and finance",
    "depreciation",
    "return on equity",
    "roe",
    "less: non-tariff",
    "non-tariff income",
    "net arr",
    "transmission charges",
    "cost of intra-state transmission",
    "edamon",
    "pugalur",
    "transmission availability",
)


def _extract_rows_from_target_text(
    page_text: str,
    page_num: int,
    target: TargetTable,
    table_caption: str,
    document_type: str,
) -> ExtractedTargetTable:
    rows: List[ExtractedTableRow] = []
    contextual_table_name = (
        f"{target.target_id} | {target.chapter} | {table_caption or 'Target text rows'}"
    )[:200]
    for line_index, line in enumerate((page_text or "").splitlines()):
        line_clean = " ".join(line.split())
        if not line_clean:
            continue
        line_lower = line_clean.lower()
        if not any(keyword in line_lower for keyword in _TARGET_TEXT_ROW_KEYWORDS):
            continue
        line_work = re.sub(r"^\s*(\d+|[ivxlcdm]+)[.)\s-]+", "", line_clean, flags=re.IGNORECASE).strip()
        values = []
        for match in _MONEY_PATTERN.finditer(line_work):
            parsed = _parse_financial_value(match.group())
            if parsed is not None:
                values.append(parsed)
        if len(values) < 3:
            continue
        first_number = _MONEY_PATTERN.search(line_work)
        if not first_number:
            continue
        label = line_work[: first_number.start()].strip()
        if not label or len(label) < 3:
            continue
        for value_type, parsed_value in zip(("approved", "actual", "claimed"), values[-3:]):
            rows.append(
                ExtractedTableRow(
                    page_number=page_num,
                    table_index=1000 + line_index,
                    table_name=contextual_table_name,
                    row_label=label,
                    value=parsed_value,
                    value_type=value_type,
                    document_type=document_type,
                    unit=target.unit,
                    confidence=0.78,
                    raw_text=(
                        f"target_id={target.target_id}; chapter={target.chapter}; "
                        f"source=text_line; row={line_clean}"
                    ),
                    target_id=target.target_id,
                    chapter=target.chapter,
                    table_caption=table_caption,
                    normalized_columns=("particulars", "approved", "actual", "claimed"),
                    source_type="chapter_table",
                )
            )

    return ExtractedTargetTable(
        target_id=target.target_id,
        chapter=target.chapter,
        document_type=document_type,
        page_number=page_num,
        table_caption=table_caption,
        raw_columns=("text_line",),
        normalized_columns=("particulars", "approved", "actual", "claimed"),
        rows=rows,
        confidence=0.78 if rows else 0.0,
    )


def _extract_with_camelot(
    pdf_path: str,
    page_numbers: Sequence[int],
    document_type: str,
) -> List[ExtractedTableRow]:
    """Optional fallback: run Camelot only on already-targeted pages."""
    if not CAMELOT_AVAILABLE or not page_numbers:
        return []

    rows: List[ExtractedTableRow] = []
    pages = ",".join(str(page_num) for page_num in page_numbers[:20])
    try:
        tables = camelot.read_pdf(pdf_path, pages=pages, flavor="stream")
    except Exception:
        return []

    for table_idx, table in enumerate(tables):
        try:
            table_rows = table.df.fillna("").values.tolist()
            page_num = int(getattr(table, "page", 0) or 0)
        except Exception:
            continue
        rows.extend(_extract_rows_from_table(
            table_rows,
            page_num,
            table_idx,
            "Camelot targeted table",
            document_type,
        ))
    return rows


# ─── Main Extraction Function ───

def extract_tables_from_pdf(
    pdf_bytes: bytes,
    filename: str,
    document_type: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float, int, int], None]] = None,
    max_target_pages: Optional[int] = None,
    timeout_seconds: Optional[int] = 90,
) -> List[ExtractedTableRow]:
    """
    Extract financial tables from a PDF using pdfplumber.
    
    Returns list of ExtractedTableRow with full provenance.
    """
    if not PDFPLUMBER_AVAILABLE:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")
    
    document_type = document_type or _infer_document_type(filename)
    timeout_at = time.monotonic() + timeout_seconds if timeout_seconds else None

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        extracted_rows, _ = _extract_from_open_pdf(
            pdf=pdf,
            document_type=document_type,
            progress_callback=progress_callback,
            max_target_pages=max_target_pages,
            timeout_at=timeout_at,
        )
    return extracted_rows


def extract_tables_from_pdf_path(
    pdf_path: str,
    filename: str,
    document_type: Optional[str] = None,
    progress_callback: Optional[Callable[[str, float, int, int], None]] = None,
    max_target_pages: Optional[int] = None,
    timeout_seconds: Optional[int] = 90,
) -> Tuple[List[ExtractedTableRow], int, List[int]]:
    """Extract targeted financial tables from a PDF path without loading it into memory."""
    if not PDFPLUMBER_AVAILABLE:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")

    document_type = document_type or _infer_document_type(filename)
    timeout_at = time.monotonic() + timeout_seconds if timeout_seconds else None

    with pdfplumber.open(pdf_path) as pdf:
        rows, target_pages = _extract_from_open_pdf(
            pdf=pdf,
            document_type=document_type,
            progress_callback=progress_callback,
            max_target_pages=max_target_pages,
            timeout_at=timeout_at,
        )
        total_pages = len(pdf.pages)

    if not rows:
        rows = _extract_with_camelot(pdf_path, target_pages, document_type)

    return rows, total_pages, target_pages


def _extract_from_open_pdf(
    pdf,
    document_type: str,
    progress_callback: Optional[Callable[[str, float, int, int], None]],
    max_target_pages: Optional[int],
    timeout_at: Optional[float],
) -> Tuple[List[ExtractedTableRow], List[int]]:
    total_pages = len(pdf.pages)
    page_texts: List[str] = []
    last_text_report = 0.0
    for index, page in enumerate(pdf.pages, 1):
        if timeout_at and time.monotonic() > timeout_at and page_texts:
            break
        try:
            page_texts.append(page.extract_text() or "")
        except Exception:
            page_texts.append("")

        now = time.monotonic()
        if progress_callback and (now - last_text_report > 0.75 or index == total_pages):
            progress_callback(
                "Detecting chapter ranges for targeted extraction",
                5 + (index / max(total_pages, 1)) * 18,
                index,
                total_pages,
            )
            last_text_report = now

    chapter_ranges = detect_chapter_ranges_from_text(page_texts)
    target_tables = extract_target_tables_from_open_pdf(
        pdf=pdf,
        document_type=document_type,
        page_texts=page_texts,
        chapter_ranges=chapter_ranges,
    )
    target_rows = _flatten_target_tables(target_tables)
    catalog_pages = sorted({table.page_number for table in target_tables})

    fallback_pages, _ = _select_target_pages(
        pdf=pdf,
        document_type=document_type,
        max_target_pages=max_target_pages,
        timeout_at=timeout_at,
        progress_callback=progress_callback,
    )
    target_pages = sorted(set(catalog_pages) | set(fallback_pages)) if catalog_pages else fallback_pages

    if progress_callback:
        progress_callback(
            f"Extracting tables from {len(target_pages)} targeted pages",
            38,
            0,
            total_pages,
        )

    extracted_rows: List[ExtractedTableRow] = list(target_rows)
    last_report = 0.0
    for idx, page_num in enumerate(target_pages, 1):
        if timeout_at and time.monotonic() > timeout_at and extracted_rows:
            break

        if catalog_pages and page_num in catalog_pages:
            # Target tables on these pages have already been extracted with
            # normalized columns and chapter context. Avoid re-adding broad
            # duplicate rows from the same financial tables.
            now = time.monotonic()
            if progress_callback and (now - last_report > 0.75 or idx == len(target_pages)):
                progress = 38 + (idx / max(len(target_pages), 1)) * 42
                progress_callback(
                    f"Extracting catalog target tables ({idx}/{len(target_pages)} target pages)",
                    progress,
                    page_num,
                    total_pages,
                )
                last_report = now
            continue

        page = pdf.pages[page_num - 1]
        try:
            tables = page.extract_tables()
        except Exception:
            tables = []

        for table_idx, table in enumerate(tables):
            extracted_rows.extend(_extract_rows_from_table(
                table=table,
                page_num=page_num,
                table_idx=table_idx,
                table_name="",
                document_type=document_type,
            ))

        now = time.monotonic()
        if progress_callback and (now - last_report > 0.75 or idx == len(target_pages)):
            progress = 38 + (idx / max(len(target_pages), 1)) * 42
            progress_callback(
                f"Extracting key financial tables ({idx}/{len(target_pages)} target pages)",
                progress,
                page_num,
                total_pages,
            )
            last_report = now

    return _dedupe_rows(extracted_rows), target_pages


def get_page_count(pdf_bytes: bytes) -> int:
    """Get the number of pages in a PDF."""
    if not PDFPLUMBER_AVAILABLE:
        return 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)


def get_page_count_from_path(pdf_path: str) -> int:
    """Get the number of pages in a PDF without loading it into memory first."""
    if not PDFPLUMBER_AVAILABLE:
        return 0
    with pdfplumber.open(pdf_path) as pdf:
        return len(pdf.pages)
