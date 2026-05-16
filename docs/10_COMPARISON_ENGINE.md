# KSERC Decision Support System — Comparison Engine

**Core file:** `backend/comparison.py`  
**Constants:**
- `VARIANCE_THRESHOLD_PERCENT = 15.0`
- `CONFIDENCE_THRESHOLD = 0.6`

---

## Deterministic Philosophy

The comparison engine performs **pure arithmetic and rule-based classification**. No model, no learned weights, no external service.

Its only job: given a set of canonical line items that have values from both the ARR Order (approved) and the Petition (actual + claimed), compute variance and decide whether the item can be auto-accepted or must be shown to an officer.

---

## Core Formula (Exact Code)

```python
def calculate_variance(
    approved: Optional[float],
    comparison_value: Optional[float],
) -> Tuple[Optional[float], Optional[float]]:
    if approved is None or comparison_value is None:
        return None, None

    variance = round(comparison_value - approved, 2)

    if approved != 0:
        variance_percent = round(
            (comparison_value - approved) / abs(approved) * 100, 2
        )
    else:
        variance_percent = 0.0 if comparison_value == 0 else None

    return variance, variance_percent
```

**Key behaviors:**
- `deviation = comparison_value − approved`
- `deviation_percent = deviation / |approved| × 100`
- Division by zero (approved == 0 and comparison_value != 0) → `variance_percent = None` → forces `REVIEW_REQUIRED`

---

## Fallback Logic

When `actual_value` is missing for a canonical item but `claimed_value` exists:

The comparison engine (and later `report_context.py`) falls back to using `claimed_value` as the comparison value. This is recorded in provenance (`actual_source_*` vs `claimed_source_*`).

This is why some comparison rows show "Claimed" as the source even though the column is labeled "Actual" in the UI.

---

## Decision Classification (Exact Rules)

```python
def classify_decision(
    variance_percent: Optional[float],
    confidence: float = 1.0,
    missing_values: bool = False,
) -> Tuple[str, Optional[str]]:
    if missing_values:
        return "INCOMPLETE_DATA", "Missing approved, actual, or claimed value"

    if confidence < CONFIDENCE_THRESHOLD:
        return "REVIEW_REQUIRED", f"Low extraction confidence ({confidence:.0%})"

    if variance_percent is None:
        return "REVIEW_REQUIRED", "Approved value is zero; percentage deviation is not applicable"

    abs_variance = abs(variance_percent)

    if abs_variance < VARIANCE_THRESHOLD_PERCENT:
        return "ACCEPTABLE_VARIANCE", None

    return "REVIEW_REQUIRED", f"Variance {variance_percent:+.1f}% exceeds ±15% threshold"
```

---

## Decision Classes Explained

| Class | Meaning | UI Badge | Can be auto-included in draft? | Officer Action Needed? |
|-------|---------|----------|--------------------------------|------------------------|
| `ACCEPTABLE_VARIANCE` | \|variance_percent\| < 15% AND confidence ≥ 60% | Green / Auto | Yes | No (but can still review) |
| `REVIEW_REQUIRED` | Variance ≥ 15% OR low confidence OR zero approved | Amber / Review | Yes (as flagged) | Yes — approve, edit, or reject |
| `INCOMPLETE_DATA` | One or more of approved/actual/claimed is NULL | Red / Incomplete | No (excluded from totals) | Must supply or acknowledge missing data |

---

## Edge Cases Handled

1. **Approved = 0, Actual/Claimed > 0** → `variance_percent = None` → `REVIEW_REQUIRED` ("Approved value is zero...")
2. **All three values missing** → `INCOMPLETE_DATA`
3. **Only approved present** (no petition data) → `INCOMPLETE_DATA`
4. **Confidence < 0.6** → `REVIEW_REQUIRED` regardless of variance
5. **Negative variance** (actual < approved) → still uses absolute value for threshold check; sign is preserved in `variance`

---

## How Comparison Results Are Stored

For every canonical item that has at least one value from ARR and one from Petition:

- One row in `comparisons` table with:
  - `approved_value`, `actual_value`, `claimed_value`
  - `variance`, `variance_percent`
  - `decision_class`, `flag_reason`
  - Full source provenance (document_id, page, table, confidence for each side)

The `case_id` groups the entire run.

---

## Relationship to Report Generation

The report context builder (`report_context.py`) consumes the comparison rows and:

- Groups them by `section` (sbu_d, sbu_g, ...)
- Applies `_chapter_mode()` (full / fallback / missing)
- Builds the exact tables that appear in Chapters 2–7 of the PDF
- Calculates chapter totals and grand totals

**Important:** Only rows with `decision_class != "INCOMPLETE_DATA"` (or handled specially) contribute to the numeric tables in the final PDF.

---

## Threshold Rationale (Why 15%?)

- KSERC historically uses materiality thresholds in the 10–20% range for automatic pass-through vs detailed scrutiny.
- 15% is a conservative, round, defensible number for an MVP.
- It is **not** a regulatory finding — it is an internal triage threshold to focus officer attention.
- The threshold is a constant at the top of `comparison.py` and can be adjusted with a one-line change + test update.

---

## No LLM Involvement

The `prompts.py` function `generate_variance_explanation()` is called to produce the deterministic template text that appears in the review panel and in the PDF appendix. It returns a fixed sentence structure with the actual numbers substituted. It does **not** call any language model.

---

## Testing the Engine

- `test_variance.py` — formula and edge cases
- `test_canonical_registry.py` — mapping correctness
- `test_comparison` flow via smoke test

Run:
```bash
pytest test_variance.py -v
```

---

This engine is the most "regulatory-grade" component of the MVP because its output is fully deterministic and every decision can be explained by looking at four numbers and two constants.
