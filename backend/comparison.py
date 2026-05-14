"""
Deterministic MVP comparison engine.

Compares approved ARR values against Petition actual/claimed values for only
canonical KSERC line items. No LLM or external model is used here.

Decision rules:
  - absolute deviation < 15%  -> ACCEPTABLE_VARIANCE
  - absolute deviation >= 15% -> REVIEW_REQUIRED
  - missing values            -> INCOMPLETE_DATA
  - low confidence            -> REVIEW_REQUIRED
"""

import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from .models import Comparison
except ImportError:  # Support direct imports from the backend directory.
    pass


@dataclass
class ComparisonResult:
    """Result of comparing a single line item."""
    canonical_id: str
    display_name: str
    sbu: str
    unit: str
    section: str
    canonical_name: str
    cost_head: str
    approved_value: Optional[float]
    actual_value: Optional[float]
    claimed_value: Optional[float]
    variance: Optional[float]
    variance_percent: Optional[float]
    decision_class: str
    flag_reason: Optional[str]
    approved_source_page: Optional[int] = None
    actual_source_page: Optional[int] = None


# ─── Configuration ───

VARIANCE_THRESHOLD_PERCENT = 15.0  # Items with >= 15% variance need review
CONFIDENCE_THRESHOLD = 0.6         # Items with confidence < 0.6 need review


def calculate_variance(
    approved: Optional[float],
    comparison_value: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate absolute and percentage deviation.
    
    deviation = comparison_value - approved
    deviation_percent = deviation / abs(approved) * 100

    When the approved value is zero and the comparison value is non-zero, the
    percent deviation is not mathematically meaningful for routing. The caller
    receives None and should mark the item for review.
    """
    if approved is None or comparison_value is None:
        return None, None
    
    variance = round(comparison_value - approved, 2)
    
    if approved != 0:
        variance_percent = round((comparison_value - approved) / abs(approved) * 100, 2)
    else:
        variance_percent = 0.0 if comparison_value == 0 else None
    
    return variance, variance_percent


def classify_decision(
    variance_percent: Optional[float],
    confidence: float = 1.0,
    missing_values: bool = False,
) -> Tuple[str, Optional[str]]:
    """
    Classify a line item for deterministic decision routing.
    
    Returns: (decision_status, flag_reason)
    """
    if missing_values:
        return "INCOMPLETE_DATA", "Missing approved, actual, or claimed value"

    if confidence < CONFIDENCE_THRESHOLD:
        return "REVIEW_REQUIRED", f"Low extraction confidence ({confidence:.0%})"
    
    if variance_percent is None:
        return "REVIEW_REQUIRED", "Approved value is zero; percentage deviation is not applicable"
    
    abs_variance = abs(variance_percent)
    
    if abs_variance < VARIANCE_THRESHOLD_PERCENT:
        return "ACCEPTABLE_VARIANCE", None

    direction = "increase" if variance_percent > 0 else "decrease"
    return "REVIEW_REQUIRED", f"Deviation of {variance_percent:+.1f}% ({direction}) exceeds {VARIANCE_THRESHOLD_PERCENT}% threshold"


def run_comparison(
    approved_items: List[Dict],
    actual_items: List[Dict],
    case_id: Optional[str] = None,
) -> List[ComparisonResult]:
    """
    Run comparison between approved and actual line items.
    
    Args:
        approved_items: List of normalized items from ARR Order
        actual_items: List of normalized items from Truing-Up Petition
        case_id: Optional case ID for grouping
        
    Returns:
        List of ComparisonResult with variance and classification
    """
    if case_id is None:
        case_id = str(uuid.uuid4())
    
    # Build lookup by canonical id/name.
    approved_lookup: Dict[str, Dict] = {}
    for item in approved_items:
        name = item.get("canonical_id") or item.get("canonical_name", "")
        approved_lookup[name] = item
    
    actual_lookup: Dict[str, Dict] = {}
    for item in actual_items:
        name = item.get("canonical_id") or item.get("canonical_name", "")
        actual_lookup[name] = item
    
    # Union of all canonical names
    all_names = set(approved_lookup.keys()) | set(actual_lookup.keys())
    
    results: List[ComparisonResult] = []
    
    for name in sorted(all_names):
        approved_item = approved_lookup.get(name, {})
        actual_item = actual_lookup.get(name, {})
        
        approved_val = approved_item.get("value")
        actual_val = actual_item.get("actual_value", actual_item.get("value"))
        claimed_val = actual_item.get("claimed_value", actual_val)
        comparison_val = claimed_val if claimed_val is not None else actual_val
        
        variance, variance_pct = calculate_variance(approved_val, comparison_val)
        
        # Get confidence (min of both sources)
        approved_conf = approved_item.get("mapping_confidence", 1.0)
        actual_conf = actual_item.get("mapping_confidence", 1.0)
        confidence = min(approved_conf, actual_conf)
        
        # Classify
        decision_class, flag_reason = classify_decision(
            variance_pct,
            confidence,
            missing_values=approved_val is None or comparison_val is None,
        )
        
        cost_head = (
            approved_item.get("cost_head") or 
            actual_item.get("cost_head") or 
            "Other"
        )
        display_name = (
            approved_item.get("display_name")
            or actual_item.get("display_name")
            or approved_item.get("canonical_name")
            or actual_item.get("canonical_name")
            or name
        )
        
        results.append(ComparisonResult(
            canonical_id=name,
            display_name=display_name,
            sbu=approved_item.get("sbu") or actual_item.get("sbu") or cost_head,
            unit=approved_item.get("unit") or actual_item.get("unit") or "Rs. Cr.",
            section=approved_item.get("section") or actual_item.get("section") or "consolidated",
            canonical_name=name,
            cost_head=cost_head,
            approved_value=approved_val,
            actual_value=actual_val,
            claimed_value=claimed_val,
            variance=variance,
            variance_percent=variance_pct,
            decision_class=decision_class,
            flag_reason=flag_reason,
            approved_source_page=approved_item.get("source_page"),
            actual_source_page=actual_item.get("source_page"),
        ))
    
    return results
