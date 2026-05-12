"""
MVP PDF Extraction Pipeline — pdfplumber-based table extraction.

Extracts structured financial tables from KSERC ARR orders and
truing-up petition PDFs. Each extracted value carries provenance
metadata (page, table index, confidence).

No LangGraph, no complex AI agents — just deterministic extraction.
"""

import re
import io
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
    h = (header or "").lower()
    if any(token in h for token in ("approved", "approval", "allowed", "arr order")):
        return "approved"
    if any(token in h for token in ("actual", "audited", "audit")):
        return "actual"
    if any(token in h for token in ("claimed", "claim", "petition", "proposed")):
        return "claimed"
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
            if value_type == "approved"
        ]
        if selected:
            return selected

    if document_type == "truing_up_petition" and has_typed_headers:
        selected = [
            (idx, value, value_type or "actual")
            for idx, value, value_type in parsed_values
            if value_type in ("actual", "claimed")
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
    target_pages, total_pages = _select_target_pages(
        pdf=pdf,
        document_type=document_type,
        max_target_pages=max_target_pages,
        timeout_at=timeout_at,
        progress_callback=progress_callback,
    )

    if progress_callback:
        progress_callback(
            f"Extracting tables from {len(target_pages)} targeted pages",
            38,
            0,
            total_pages,
        )

    extracted_rows: List[ExtractedTableRow] = []
    last_report = 0.0
    for idx, page_num in enumerate(target_pages, 1):
        if timeout_at and time.monotonic() > timeout_at and extracted_rows:
            break

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

    return extracted_rows, target_pages


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
