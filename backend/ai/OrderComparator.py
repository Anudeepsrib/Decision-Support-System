"""
OrderComparator.py
Fully deterministic Order vs Reference Document Comparison Engine.
Uses regex extraction, difflib string similarity, and rule-based comparison.
NO LLM calls in the comparison pipeline — LLM is optional for report generation only.
"""

import os
import re
import json
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Tuple
from difflib import SequenceMatcher
from dateutil import parser as dateutil_parser


# ═══════════════════════════════════════════════════════════════
# STEP 1 — REGEX FIELD EXTRACTION
# ═══════════════════════════════════════════════════════════════

# Order-level regex patterns
_ORDER_NUMBER_PATTERNS = [
    r"(?:Order\s*(?:Number|No\.?|#|ID))\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
    r"(?:PO\s*(?:Number|No\.?|#))\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
    r"(?:Invoice\s*(?:Number|No\.?|#))\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
    r"(?:Ref(?:erence)?\s*(?:Number|No\.?|#))\s*[:\-]?\s*([A-Za-z0-9\-\/]+)",
]

_CUSTOMER_PATTERNS = [
    r"(?:Customer|Client|Bill\s*To|Buyer|Sold\s*To)\s*[:\-]?\s*(.+?)(?:\n|$)",
    r"(?:Company|Organization|Firm)\s*[:\-]?\s*(.+?)(?:\n|$)",
]

_ADDRESS_PATTERNS = [
    r"(?:Ship(?:ping)?\s*(?:Address|To)|Deliver(?:y)?\s*(?:Address|To))\s*[:\-]?\s*(.+?)(?:\n\n|\n(?=[A-Z]))",
    r"(?:Address)\s*[:\-]?\s*(.+?)(?:\n\n|\n(?=[A-Z]))",
]

_DATE_PATTERNS = [
    r"(?:Order\s*Date|Date\s*of\s*Order|Date\s*Ordered)\s*[:\-]?\s*(\d{1,4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,4})",
    r"(?:Delivery\s*Date|Ship\s*Date|Expected\s*Delivery|Due\s*Date)\s*[:\-]?\s*(\d{1,4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,4})",
]

_CURRENCY_PATTERNS = [
    r"(?:Currency)\s*[:\-]?\s*([A-Z]{3})",
    r"(\$|USD|EUR|GBP|INR|₹|€|£)",
]

# Generic date finder
_GENERIC_DATE = re.compile(r"\b(\d{1,4}[\-\/\.]\d{1,2}[\-\/\.]\d{1,4})\b")

# Price patterns
_PRICE_PATTERN = re.compile(
    r"[\$€£₹]?\s*(\d{1,3}(?:[,\s]\d{3})*(?:\.\d{1,2})?)"
)

# Quantity patterns
_QTY_PATTERN = re.compile(
    r"(?:Qty|Quantity|Units|Ordered\s*Units|Count)\s*[:\-]?\s*(\d+)", re.IGNORECASE
)


def _first_match(text: str, patterns: List[str], flags=re.IGNORECASE | re.DOTALL) -> str:
    """Return the first captured group from the first matching pattern, or NOT_FOUND."""
    for pattern in patterns:
        m = re.search(pattern, text, flags)
        if m:
            return m.group(1).strip()
    return "NOT_FOUND"


def _extract_all_dates(text: str) -> List[str]:
    """Find all date strings in text."""
    return _GENERIC_DATE.findall(text)


def _extract_order_level_fields(text: str) -> Dict[str, str]:
    """Extract order-level fields from document text using regex."""
    order_number = _first_match(text, _ORDER_NUMBER_PATTERNS)
    customer_name = _first_match(text, _CUSTOMER_PATTERNS)
    shipping_address = _first_match(text, _ADDRESS_PATTERNS)
    currency = _first_match(text, _CURRENCY_PATTERNS)

    # Dates — specific patterns first
    order_date = "NOT_FOUND"
    delivery_date = "NOT_FOUND"

    m_order_date = re.search(_DATE_PATTERNS[0], text, re.IGNORECASE)
    if m_order_date:
        order_date = m_order_date.group(1).strip()

    m_delivery_date = re.search(_DATE_PATTERNS[1], text, re.IGNORECASE)
    if m_delivery_date:
        delivery_date = m_delivery_date.group(1).strip()

    # If specific patterns failed, try to pick from generic dates
    if order_date == "NOT_FOUND" or delivery_date == "NOT_FOUND":
        all_dates = _extract_all_dates(text)
        if all_dates:
            if order_date == "NOT_FOUND":
                order_date = all_dates[0]
            if delivery_date == "NOT_FOUND" and len(all_dates) > 1:
                delivery_date = all_dates[1]

    return {
        "order_number": order_number,
        "customer_name": customer_name,
        "shipping_address": shipping_address,
        "order_date": order_date,
        "delivery_date": delivery_date,
        "currency": currency,
    }


def _extract_items(text: str) -> List[Dict[str, Any]]:
    """
    Extract line items from document text.
    Splits lines by multiple spaces (common in PDF tables) and finds the product name vs numbers.
    """
    items = []
    lines = text.split("\n")
    blacklist = ["order", "date", "customer", "client", "address", "deliver", "ship", "po number"]

    for i, line in enumerate(lines):
        line = line.strip()
        lower_line = line.lower()
        if not line or len(line) < 5 or any(b in lower_line for b in blacklist):
            continue

        # Split by 2 or more spaces, or tabs (common PDF text extraction layout for tables)
        parts = re.split(r'\s{2,}|\t+', line)
        if len(parts) >= 3:
            numbers = []
            words = []
            for p in parts:
                # Clean currency symbols and commas to check if pure number
                cleaned = re.sub(r'[\$€£₹,\s]', '', p)
                if cleaned.replace('.', '', 1).isdigit():
                    numbers.append(float(cleaned))
                else:
                    words.append(p.strip())

            # If we found words (product name) and at least 2 numbers (e.g. qty + price)
            if words and len(numbers) >= 2:
                product_name = " ".join(words)
                # Ignore table headers
                if "qty" in product_name.lower() or "price" in product_name.lower():
                    continue

                qty = "NOT_FOUND"
                unit_price = "NOT_FOUND"
                total_price = "NOT_FOUND"

                if len(numbers) >= 3:
                    qty = int(numbers[0]) if numbers[0] == int(numbers[0]) else numbers[0]
                    unit_price = numbers[1]
                    total_price = numbers[2]
                elif len(numbers) == 2:
                    if numbers[0] == int(numbers[0]) and numbers[0] < 1000:
                        qty = int(numbers[0])
                        unit_price = numbers[1]
                    else:
                        unit_price = numbers[0]
                        total_price = numbers[1]

                items.append({
                    "product_name": product_name,
                    "quantity": qty,
                    "unit_price": unit_price,
                    "total_price": total_price,
                })

    return items


def extract_fields(text: str) -> Dict[str, Any]:
    """Full extraction pipeline: order-level fields + items."""
    fields = _extract_order_level_fields(text)
    fields["items"] = _extract_items(text)
    return fields


# ═══════════════════════════════════════════════════════════════
# STEP 2 — DATA NORMALIZATION
# ═══════════════════════════════════════════════════════════════

def _normalize_date(date_str: str) -> str:
    """Normalize a date string to ISO YYYY-MM-DD format."""
    if date_str == "NOT_FOUND":
        return "NOT_FOUND"
    try:
        parsed = dateutil_parser.parse(date_str, dayfirst=False)
        return parsed.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return date_str


def _normalize_string(s: str) -> str:
    """Lowercase, strip whitespace and punctuation for comparison."""
    if s == "NOT_FOUND":
        return "NOT_FOUND"
    s = s.lower().strip()
    s = re.sub(r"[^\w\s]", " ", s)  # replace punctuation with space
    s = re.sub(r"\s+", " ", s)  # collapse whitespace
    return s.strip()


def _normalize_price(val: Any) -> Optional[float]:
    """Normalize a value to float, or None."""
    if val == "NOT_FOUND" or val is None:
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def _normalize_quantity(val: Any) -> Optional[int]:
    """Normalize a value to int, or None."""
    if val == "NOT_FOUND" or val is None:
        return None
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return None


# ═══════════════════════════════════════════════════════════════
# STEP 3 — STRING SIMILARITY
# ═══════════════════════════════════════════════════════════════

def similarity(a: str, b: str) -> float:
    """Compute similarity ratio between two strings using difflib."""
    if a == "NOT_FOUND" or b == "NOT_FOUND":
        return 0.0
    return SequenceMatcher(None, _normalize_string(a), _normalize_string(b)).ratio()


# ═══════════════════════════════════════════════════════════════
# STEP 4 — ITEM MATCHING
# ═══════════════════════════════════════════════════════════════

def _match_items(
    order_items: List[Dict], reference_items: List[Dict], threshold: float = 0.85
) -> Tuple[List[Tuple[Dict, Dict, float]], List[Dict], List[Dict]]:
    """
    Match order items to reference items by product name similarity.
    Returns: (matched_pairs, unmatched_order, unmatched_reference)
    """
    matched = []
    used_ref_indices = set()
    unmatched_order = []

    for o_item in order_items:
        best_score = 0.0
        best_idx = -1

        for r_idx, r_item in enumerate(reference_items):
            if r_idx in used_ref_indices:
                continue
            score = similarity(
                str(o_item.get("product_name", "")),
                str(r_item.get("product_name", ""))
            )
            if score > best_score:
                best_score = score
                best_idx = r_idx

        if best_score >= threshold and best_idx >= 0:
            matched.append((o_item, reference_items[best_idx], best_score))
            used_ref_indices.add(best_idx)
        else:
            unmatched_order.append(o_item)

    unmatched_reference = [
        r for i, r in enumerate(reference_items) if i not in used_ref_indices
    ]

    return matched, unmatched_order, unmatched_reference


# ═══════════════════════════════════════════════════════════════
# STEP 5 — RULE-BASED COMPARISON
# ═══════════════════════════════════════════════════════════════

def _compare_exact(order_val: str, ref_val: str) -> Dict[str, str]:
    """Exact string comparison."""
    if order_val == "NOT_FOUND" and ref_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in either document"}
    if order_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in order document"}
    if ref_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in reference document"}
    if _normalize_string(order_val) == _normalize_string(ref_val):
        return {"status": "MATCH", "reason": "Exact match"}
    return {"status": "MISMATCH", "reason": f"Values differ: '{order_val}' vs '{ref_val}'"}


def _compare_similarity(order_val: str, ref_val: str, threshold: float = 0.9) -> Dict[str, str]:
    """String similarity comparison with threshold."""
    if order_val == "NOT_FOUND" and ref_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in either document"}
    if order_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in order document"}
    if ref_val == "NOT_FOUND":
        return {"status": "NOT_FOUND", "reason": "Field not found in reference document"}

    score = similarity(order_val, ref_val)
    if score >= threshold:
        return {"status": "MATCH", "reason": f"Semantic match (similarity: {score:.2f})"}
    return {
        "status": "MISMATCH",
        "reason": f"Similarity {score:.2f} below threshold {threshold}: '{order_val}' vs '{ref_val}'"
    }


def _compare_numeric(order_val: Any, ref_val: Any, tolerance_pct: float = 1.0) -> Dict[str, str]:
    """Numeric comparison with percentage tolerance."""
    o = _normalize_price(order_val)
    r = _normalize_price(ref_val)

    if o is None and r is None:
        return {"status": "NOT_FOUND", "reason": "Value not found in either document"}
    if o is None:
        return {"status": "NOT_FOUND", "reason": "Value not found in order document"}
    if r is None:
        return {"status": "NOT_FOUND", "reason": "Value not found in reference document"}

    if o == r:
        return {"status": "MATCH", "reason": "Exact numeric match"}

    if r != 0:
        pct_diff = abs(o - r) / abs(r) * 100
    else:
        pct_diff = 100.0

    if pct_diff <= tolerance_pct:
        return {"status": "MATCH", "reason": f"Within tolerance (diff: {pct_diff:.2f}%)"}
    return {
        "status": "MISMATCH",
        "reason": f"Difference {pct_diff:.2f}% exceeds ±{tolerance_pct}% tolerance: {o} vs {r}"
    }


def _compare_quantity(order_val: Any, ref_val: Any) -> Dict[str, str]:
    """Exact integer comparison for quantities."""
    o = _normalize_quantity(order_val)
    r = _normalize_quantity(ref_val)

    if o is None and r is None:
        return {"status": "NOT_FOUND", "reason": "Quantity not found in either document"}
    if o is None:
        return {"status": "NOT_FOUND", "reason": "Quantity not found in order document"}
    if r is None:
        return {"status": "NOT_FOUND", "reason": "Quantity not found in reference document"}

    if o == r:
        return {"status": "MATCH", "reason": "Exact quantity match"}
    return {"status": "MISMATCH", "reason": f"Quantity differs: {o} vs {r}"}


# ═══════════════════════════════════════════════════════════════
# STEP 6 — CONFIDENCE SCORING
# ═══════════════════════════════════════════════════════════════

def _compute_confidence(comparison_result: Dict) -> int:
    """
    Compute a deterministic confidence score (0-100) based on:
    - How many fields were found (vs NOT_FOUND)
    - How many items matched
    - How many mismatches exist
    """
    score = 100

    # Penalize NOT_FOUND order-level fields
    for field_data in comparison_result.get("order_level_comparison", {}).values():
        if isinstance(field_data, dict):
            if field_data.get("status") == "NOT_FOUND":
                score -= 8

    # Penalize item mismatches
    summary = comparison_result.get("summary", {})
    total = int(summary.get("total_items_order", 0) or 0)
    mismatched = int(summary.get("mismatched_items", 0) or 0)
    missing = int(summary.get("missing_items", 0) or 0)
    extra = int(summary.get("extra_items", 0) or 0)

    if total > 0:
        score -= mismatched * 10
        score -= missing * 15
        score -= extra * 5
    else:
        score -= 20  # No items found at all

    return max(0, min(100, score))


# ═══════════════════════════════════════════════════════════════
# STEP 7 — OPTIONAL LLM REPORT
# ═══════════════════════════════════════════════════════════════

def _generate_llm_report(comparison_json: Dict) -> str:
    """
    Generate a human-readable report using LLM — OPTIONAL.
    Only runs if OPENAI_API_KEY is available.
    Returns 'LLM_REPORT_DISABLED' if LLM is unavailable.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return "LLM_REPORT_DISABLED"

    try:
        from langchain_openai import ChatOpenAI
        from langchain_core.messages import HumanMessage, SystemMessage

        llm = ChatOpenAI(model="gpt-4o", temperature=0.0, api_key=api_key)
        prompt = (
            "Generate a concise human-readable report (under 120 words) summarizing:\n"
            "- mismatched fields\n"
            "- missing items\n"
            "- price differences\n"
            "- overall risk (LOW / MEDIUM / HIGH)\n"
            "- recommended action (Approve / Review / Reject)\n\n"
            f"Comparison data:\n{json.dumps(comparison_json, indent=2)}"
        )
        response = llm.invoke([
            SystemMessage(content="You are a document comparison analyst."),
            HumanMessage(content=prompt),
        ])
        return response.content.strip()
    except Exception as e:
        return f"LLM_REPORT_ERROR: {str(e)}"


def _generate_deterministic_report(comparison_json: Dict) -> str:
    """
    Generate a plain-text report deterministically (no LLM).
    Always available as fallback.
    """
    summary = comparison_json.get("summary", {})
    total = summary.get("total_items_order", "0")
    matched = summary.get("matched_items", "0")
    mismatched = summary.get("mismatched_items", "0")
    missing = summary.get("missing_items", "0")
    extra = summary.get("extra_items", "0")
    overall = summary.get("overall_status", "UNKNOWN")

    # Determine risk
    mis = int(mismatched or 0)
    miss = int(missing or 0)
    ext = int(extra or 0)
    if miss > 0 or ext > 0:
        risk = "HIGH"
        action = "Reject or escalate for manual review"
    elif mis > 0:
        risk = "MEDIUM"
        action = "Review discrepancies before approval"
    else:
        risk = "LOW"
        action = "Approve order"

    # Collect mismatch reasons
    mismatches = []
    for field_name, field_data in comparison_json.get("order_level_comparison", {}).items():
        if isinstance(field_data, dict) and field_data.get("status") == "MISMATCH":
            mismatches.append(f"  - {field_name}: {field_data.get('reason', '')}")
    for item in comparison_json.get("items_comparison", []):
        if isinstance(item, dict) and item.get("status") == "MISMATCH":
            mismatches.append(
                f"  - {item.get('product_name_order', 'Unknown')}: {item.get('reason', '')}"
            )

    lines = [
        "ORDER COMPARISON REPORT",
        "=" * 40,
        f"Total Items: {total}  |  Matched: {matched}  |  Mismatched: {mismatched}",
        f"Missing: {missing}  |  Extra: {extra}  |  Status: {overall}",
        "",
        f"Risk: {risk}",
        f"Action: {action}",
    ]
    if mismatches:
        lines.append("")
        lines.append("Discrepancies:")
        lines.extend(mismatches)

    return "\n".join(lines)


# ═══════════════════════════════════════════════════════════════
# MAIN COMPARATOR CLASS
# ═══════════════════════════════════════════════════════════════

class OrderComparator:
    """
    Fully deterministic Order vs Reference Document Comparator.
    No LLM calls in the comparison pipeline.
    LLM is only used optionally for report generation.
    """

    def compare(self, order_text: str, reference_text: str) -> Dict[str, Any]:
        """
        Run the full deterministic comparison pipeline.

        Returns dict with:
          - comparison_result: structured JSON comparison
          - executive_report: deterministic plain-text report
          - llm_report: LLM-generated report (or 'LLM_REPORT_DISABLED')
          - timestamp: ISO timestamp
        """
        # Step 1: Extract fields
        order_fields = extract_fields(order_text)
        reference_fields = extract_fields(reference_text)

        # Step 2: Compare order-level fields
        order_level = {}

        # Order number — exact match
        order_level["order_number"] = {
            "order_value": order_fields["order_number"],
            "reference_value": reference_fields["order_number"],
            **_compare_exact(order_fields["order_number"], reference_fields["order_number"]),
        }

        # Customer name — similarity ≥ 0.7
        order_level["customer_name"] = {
            "order_value": order_fields["customer_name"],
            "reference_value": reference_fields["customer_name"],
            **_compare_similarity(
                order_fields["customer_name"], reference_fields["customer_name"], threshold=0.7
            ),
        }

        # Shipping address — similarity ≥ 0.85
        order_level["shipping_address"] = {
            "order_value": order_fields["shipping_address"],
            "reference_value": reference_fields["shipping_address"],
            **_compare_similarity(
                order_fields["shipping_address"], reference_fields["shipping_address"], threshold=0.85
            ),
        }

        # Order date — normalize then exact
        o_date = _normalize_date(order_fields["order_date"])
        r_date = _normalize_date(reference_fields["order_date"])
        order_level["order_date"] = {
            "order_value": o_date,
            "reference_value": r_date,
            **_compare_exact(o_date, r_date),
        }

        # Delivery date — normalize then exact
        o_del = _normalize_date(order_fields["delivery_date"])
        r_del = _normalize_date(reference_fields["delivery_date"])
        order_level["delivery_date"] = {
            "order_value": o_del,
            "reference_value": r_del,
            **_compare_exact(o_del, r_del),
        }

        # Step 3: Match and compare items
        order_items = order_fields.get("items", [])
        ref_items = reference_fields.get("items", [])

        matched_pairs, unmatched_order, unmatched_ref = _match_items(
            order_items, ref_items, threshold=0.8
        )

        items_comparison = []
        match_count = 0
        mismatch_count = 0

        for o_item, r_item, sim_score in matched_pairs:
            # Compare each field for matched items
            qty_result = _compare_quantity(o_item.get("quantity"), r_item.get("quantity"))
            price_result = _compare_numeric(
                o_item.get("unit_price"), r_item.get("unit_price"), tolerance_pct=1.0
            )
            total_result = _compare_numeric(
                o_item.get("total_price"), r_item.get("total_price"), tolerance_pct=1.0
            )

            # Overall item status
            statuses = [qty_result["status"], price_result["status"], total_result["status"]]
            if "MISMATCH" in statuses:
                item_status = "MISMATCH"
                reasons = []
                if qty_result["status"] == "MISMATCH":
                    reasons.append(qty_result["reason"])
                if price_result["status"] == "MISMATCH":
                    reasons.append(price_result["reason"])
                if total_result["status"] == "MISMATCH":
                    reasons.append(total_result["reason"])
                item_reason = "; ".join(reasons)
                mismatch_count += 1
            else:
                item_status = "MATCH"
                item_reason = f"All fields match (name similarity: {sim_score:.2f})"
                match_count += 1

            items_comparison.append({
                "product_name_order": str(o_item.get("product_name", "")),
                "product_name_reference": str(r_item.get("product_name", "")),
                "quantity_order": str(o_item.get("quantity", "NOT_FOUND")),
                "quantity_reference": str(r_item.get("quantity", "NOT_FOUND")),
                "unit_price_order": str(o_item.get("unit_price", "NOT_FOUND")),
                "unit_price_reference": str(r_item.get("unit_price", "NOT_FOUND")),
                "total_price_order": str(o_item.get("total_price", "NOT_FOUND")),
                "total_price_reference": str(r_item.get("total_price", "NOT_FOUND")),
                "status": item_status,
                "reason": item_reason,
            })

        # Missing and extra items
        missing_items = [str(item.get("product_name", "Unknown")) for item in unmatched_order]
        extra_items = [str(item.get("product_name", "Unknown")) for item in unmatched_ref]

        # Determine overall status
        total_order = len(order_items)
        if mismatch_count == 0 and len(missing_items) == 0 and len(extra_items) == 0:
            overall_status = "ALL_MATCH"
        elif len(missing_items) > 0 or len(extra_items) > 0:
            overall_status = "CRITICAL_DISCREPANCY"
        else:
            overall_status = "REVIEW_REQUIRED"

        comparison_result = {
            "order_level_comparison": order_level,
            "items_comparison": items_comparison,
            "missing_items_in_reference": missing_items,
            "extra_items_in_reference": extra_items,
            "summary": {
                "total_items_order": str(total_order),
                "matched_items": str(match_count),
                "mismatched_items": str(mismatch_count),
                "missing_items": str(len(missing_items)),
                "extra_items": str(len(extra_items)),
                "overall_status": overall_status,
            },
        }

        # Confidence score
        confidence = _compute_confidence(comparison_result)
        comparison_result["confidence_score"] = str(confidence)

        # Reports
        deterministic_report = _generate_deterministic_report(comparison_result)
        llm_report = _generate_llm_report(comparison_result)

        return {
            "comparison_result": comparison_result,
            "executive_report": deterministic_report,
            "llm_report": llm_report,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
