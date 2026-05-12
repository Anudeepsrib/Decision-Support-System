"""
MVP Comparison Engine — Variance calculation and decision classification.

Compares Approved ARR values (from ARR Order) against Actual values
(from Truing-Up Petition) and classifies each line item for review.

Decision rules:
  - variance < 15%  → AI_AUTO (auto-approved)
  - variance >= 15% → REVIEW_REQUIRED
  - low confidence  → REVIEW_REQUIRED
"""

import uuid
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from models import NormalizedLineItem, Comparison


@dataclass
class ComparisonResult:
    """Result of comparing a single line item."""
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
    actual: Optional[float]
) -> Tuple[Optional[float], Optional[float]]:
    """
    Calculate absolute and percentage variance.
    
    variance = actual - approved
    variance_percent = (actual - approved) / approved * 100
    """
    if approved is None or actual is None:
        return None, None
    
    variance = round(actual - approved, 2)
    
    if approved != 0:
        variance_percent = round((actual - approved) / abs(approved) * 100, 2)
    else:
        variance_percent = 0.0 if actual == 0 else 100.0
    
    return variance, variance_percent


def classify_decision(
    variance_percent: Optional[float],
    confidence: float = 1.0
) -> Tuple[str, Optional[str]]:
    """
    Classify a line item for decision routing.
    
    Returns: (decision_class, flag_reason)
    """
    if confidence < CONFIDENCE_THRESHOLD:
        return "REVIEW_REQUIRED", f"Low extraction confidence ({confidence:.0%})"
    
    if variance_percent is None:
        return "REVIEW_REQUIRED", "Missing value — cannot compute variance"
    
    abs_variance = abs(variance_percent)
    
    if abs_variance < VARIANCE_THRESHOLD_PERCENT:
        return "AI_AUTO", None
    else:
        direction = "increase" if variance_percent > 0 else "decrease"
        return "REVIEW_REQUIRED", f"Variance of {variance_percent:+.1f}% ({direction}) exceeds {VARIANCE_THRESHOLD_PERCENT}% threshold"


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
    
    # Build lookup by canonical_name
    approved_lookup: Dict[str, Dict] = {}
    for item in approved_items:
        name = item.get("canonical_name", "")
        approved_lookup[name] = item
    
    actual_lookup: Dict[str, Dict] = {}
    for item in actual_items:
        name = item.get("canonical_name", "")
        actual_lookup[name] = item
    
    # Union of all canonical names
    all_names = set(approved_lookup.keys()) | set(actual_lookup.keys())
    
    results: List[ComparisonResult] = []
    
    for name in sorted(all_names):
        approved_item = approved_lookup.get(name, {})
        actual_item = actual_lookup.get(name, {})
        
        approved_val = approved_item.get("value")
        actual_val = actual_item.get("value")
        
        # Calculate variance
        variance, variance_pct = calculate_variance(approved_val, actual_val)
        
        # Get confidence (min of both sources)
        approved_conf = approved_item.get("mapping_confidence", 1.0)
        actual_conf = actual_item.get("mapping_confidence", 1.0)
        confidence = min(approved_conf, actual_conf)
        
        # Classify
        decision_class, flag_reason = classify_decision(variance_pct, confidence)
        
        cost_head = (
            approved_item.get("cost_head") or 
            actual_item.get("cost_head") or 
            "Other"
        )
        
        results.append(ComparisonResult(
            canonical_name=name,
            cost_head=cost_head,
            approved_value=approved_val,
            actual_value=actual_val,
            claimed_value=actual_val,  # In MVP, claimed = actual
            variance=variance,
            variance_percent=variance_pct,
            decision_class=decision_class,
            flag_reason=flag_reason,
            approved_source_page=approved_item.get("source_page"),
            actual_source_page=actual_item.get("source_page"),
        ))
    
    return results
