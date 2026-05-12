"""
MVP PDF Extraction Pipeline — pdfplumber-based table extraction.

Extracts structured financial tables from KSERC ARR orders and
truing-up petition PDFs. Each extracted value carries provenance
metadata (page, table index, confidence).

No LangGraph, no complex AI agents — just deterministic extraction.
"""

import re
import io
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

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


# ─── Main Extraction Function ───

def extract_tables_from_pdf(pdf_bytes: bytes, filename: str) -> List[ExtractedTableRow]:
    """
    Extract financial tables from a PDF using pdfplumber.
    
    Returns list of ExtractedTableRow with full provenance.
    """
    if not PDFPLUMBER_AVAILABLE:
        raise RuntimeError("pdfplumber is not installed. Run: pip install pdfplumber")
    
    extracted_rows: List[ExtractedTableRow] = []
    
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for page_num, page in enumerate(pdf.pages, 1):
            tables = page.extract_tables()
            page_text = page.extract_text() or ""
            
            for table_idx, table in enumerate(tables):
                if not table or len(table) < 2:
                    continue
                
                # Get table text for identification
                table_text = " ".join(
                    " ".join(str(cell or "") for cell in row)
                    for row in table[:3]  # Check first 3 rows
                )
                
                is_financial, matched_keyword = _is_financial_table(table_text)
                
                # Determine table name from header row
                table_name = ""
                if table[0]:
                    header_text = " | ".join(str(c or "") for c in table[0] if c)
                    table_name = header_text[:200]
                
                if matched_keyword:
                    table_name = f"{matched_keyword.title()} — {table_name}"
                
                # Process each row
                for row_idx, row in enumerate(table):
                    if not row or row_idx == 0:  # Skip header
                        continue
                    
                    # First column is usually the label
                    row_label = str(row[0] or "").strip()
                    if not row_label or len(row_label) < 2:
                        continue
                    
                    # Try to extract value from remaining columns
                    raw_text = " | ".join(str(c or "") for c in row)
                    
                    # Try each column after the label for a financial value
                    value = None
                    for col_idx in range(1, len(row)):
                        cell = str(row[col_idx] or "").strip()
                        parsed = _parse_financial_value(cell)
                        if parsed is not None:
                            value = parsed
                            break  # Take the first valid value
                    
                    confidence = _calculate_confidence(row_label, value, table_name)
                    
                    extracted_rows.append(ExtractedTableRow(
                        page_number=page_num,
                        table_index=table_idx,
                        table_name=table_name,
                        row_label=row_label,
                        value=value,
                        confidence=confidence,
                        raw_text=raw_text,
                    ))
    
    return extracted_rows


def get_page_count(pdf_bytes: bytes) -> int:
    """Get the number of pages in a PDF."""
    if not PDFPLUMBER_AVAILABLE:
        return 0
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        return len(pdf.pages)
