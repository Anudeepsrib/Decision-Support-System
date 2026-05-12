"""
MVP AI Prompts — OpenAI integration for explanation drafting.

Uses OpenAI ONLY for:
  1. Semantic mapping (optional fallback)
  2. Explanation drafting for variance items
  3. Narrative polishing for officer notes

LLM must NEVER fabricate numbers — all numeric values come from
the extraction and comparison pipelines.
"""

import os
from typing import Optional

try:
    from openai import OpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False


def _get_client() -> Optional[object]:
    """Get OpenAI client if API key is available."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    if not api_key or api_key.startswith("sk-your"):
        return None
    if not OPENAI_AVAILABLE:
        return None
    return OpenAI(api_key=api_key)


def generate_variance_explanation(
    line_item: str,
    approved_value: float,
    actual_value: float,
    variance_percent: float,
    cost_head: str = "Other",
) -> str:
    """
    Generate a short explanation paragraph for a variance item.
    
    Falls back to a template-based explanation if OpenAI is unavailable.
    
    IMPORTANT: The LLM is instructed to NEVER fabricate numbers.
    All numbers are injected from the comparison pipeline.
    """
    # Template-based fallback (always available)
    direction = "increase" if actual_value > approved_value else "decrease"
    variance = abs(actual_value - approved_value)
    
    template = _get_template_explanation(
        line_item, approved_value, actual_value, variance, variance_percent, direction, cost_head
    )
    
    # Try OpenAI if available
    client = _get_client()
    if client is None:
        return template
    
    try:
        prompt = f"""You are a regulatory analyst for the Kerala State Electricity Regulatory Commission (KSERC).
Write a brief (2-3 sentence) analytical explanation for the following variance in a Truing-Up Order:

Line Item: {line_item}
Cost Head: {cost_head}
Approved Value: ₹{approved_value:,.2f} Cr.
Actual Value: ₹{actual_value:,.2f} Cr.
Variance: ₹{variance:,.2f} Cr. ({variance_percent:+.1f}%)
Direction: {direction}

STRICT RULES:
- Do NOT invent or fabricate any numbers. Only use the values provided above.
- Write in formal regulatory language suitable for a KSERC order.
- Suggest a plausible regulatory reason for the {direction}.
- Keep it under 3 sentences.
- Reference applicable KSERC MYT 2021 regulations if relevant."""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            max_tokens=200,
            temperature=0.3,
        )
        
        ai_text = response.choices[0].message.content.strip()
        return ai_text if ai_text else template
        
    except Exception:
        return template


def _get_template_explanation(
    line_item: str,
    approved: float,
    actual: float,
    variance: float,
    variance_pct: float,
    direction: str,
    cost_head: str,
) -> str:
    """Generate template-based explanation when OpenAI is unavailable."""
    
    # Cost-head-specific templates
    templates = {
        "Power_Purchase": (
            f"The {line_item} shows an {direction} of ₹{variance:,.2f} Cr. ({variance_pct:+.1f}%) "
            f"from the Approved value of ₹{approved:,.2f} Cr. to Actual of ₹{actual:,.2f} Cr. "
            f"This may be attributed to changes in power purchase mix, hydrology conditions, "
            f"or variations in energy demand during the period."
        ),
        "O&M": (
            f"The {line_item} shows an {direction} of ₹{variance:,.2f} Cr. ({variance_pct:+.1f}%) "
            f"from Approved ₹{approved:,.2f} Cr. to Actual ₹{actual:,.2f} Cr. "
            f"This variance may be due to changes in employee strength, escalation in input costs, "
            f"or variations in repair and maintenance requirements."
        ),
        "Interest": (
            f"The {line_item} shows an {direction} of ₹{variance:,.2f} Cr. ({variance_pct:+.1f}%) "
            f"from Approved ₹{approved:,.2f} Cr. to Actual ₹{actual:,.2f} Cr. "
            f"This may be due to changes in outstanding loan balances, interest rate fluctuations, "
            f"or variations in the borrowing pattern."
        ),
        "Depreciation": (
            f"The {line_item} shows an {direction} of ₹{variance:,.2f} Cr. ({variance_pct:+.1f}%) "
            f"from Approved ₹{approved:,.2f} Cr. to Actual ₹{actual:,.2f} Cr. "
            f"This is likely due to changes in the gross fixed asset base arising from "
            f"capitalization of new assets or disposal of old assets."
        ),
    }
    
    return templates.get(cost_head, (
        f"The {line_item} shows an {direction} of ₹{variance:,.2f} Cr. ({variance_pct:+.1f}%) "
        f"from the Approved value of ₹{approved:,.2f} Cr. to Actual of ₹{actual:,.2f} Cr. "
        f"The Commission notes this variance and directs the utility to provide "
        f"detailed justification for the deviation."
    ))
