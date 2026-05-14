"""
Deterministic narrative templates for the local MVP.

LLM integration is intentionally absent in this phase. The public function name
is kept for backward compatibility with the review workflow, but it returns a
fixed template and never calls OpenAI or any external model.
"""

from __future__ import annotations


def generate_variance_explanation(
    line_item: str,
    approved_value: float,
    actual_value: float,
    variance_percent: float,
    cost_head: str = "Other",
) -> str:
    """Generate a deterministic officer-review note for a variance item."""
    direction = "increase" if actual_value > approved_value else "decrease"
    article = "an" if direction == "increase" else "a"
    variance = abs(actual_value - approved_value)
    return _get_template_explanation(
        line_item=line_item,
        approved=approved_value,
        actual=actual_value,
        variance=variance,
        variance_pct=variance_percent,
        direction=direction,
        article=article,
        cost_head=cost_head,
    )


def _get_template_explanation(
    line_item: str,
    approved: float,
    actual: float,
    variance: float,
    variance_pct: float,
    direction: str,
    article: str,
    cost_head: str,
) -> str:
    """Generate a Commission-style deterministic variance explanation."""
    sbu_text = f" under {cost_head}" if cost_head and cost_head != "Other" else ""
    return (
        f"The deviation in {line_item}{sbu_text} is Rs. {variance:,.2f} Cr. "
        f"against the approved value of Rs. {approved:,.2f} Cr. and the reported value "
        f"of Rs. {actual:,.2f} Cr. The item records {article} {direction} of "
        f"{variance_pct:+.1f}% and is placed before the reviewing officer for "
        "deterministic variance-based examination."
    )
