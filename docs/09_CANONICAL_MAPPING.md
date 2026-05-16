# KSERC Decision Support System — Canonical Mapping

**Core file:** `backend/canonical_registry.py`  
**Functions:** `map_record_to_canonical()`, `canonicalize_records()`, `REGISTRY_BY_ID`

---

## Why Canonical Mapping Exists

ARR Orders and Truing-Up Petitions use **different wording** for the same regulatory concepts:

- ARR Order might say: "Power Purchase Cost – Approved"
- Petition might say: "Purchase of Power – Actual / Claimed"

Without a stable mapping layer, variance comparison is impossible.

The canonical registry is the **single source of truth** for every line item the system is allowed to compare and include in the draft order.

---

## CanonicalLineItem Structure

```python
@dataclass(frozen=True)
class CanonicalLineItem:
    canonical_id: str          # Stable key, e.g. "PURCHASE_OF_POWER"
    display_name: str          # "Purchase of Power"
    sbu: str                   # "SBU-D", "SBU-G", "SBU-T"
    aliases: Tuple[str, ...]   # Regex patterns (case-insensitive match)
    unit: str
    section: str               # "sbu_d", "sbu_g", ...
    include_in_report: bool = True
    is_total: bool = False
```

---

## SBU Ownership Rules (Enforced)

The registry explicitly owns each item:

```python
SECTION_SBU_G = "sbu_g"
SECTION_SBU_T = "sbu_t"
SECTION_ENERGY = "energy_sales_td_loss"
SECTION_SBU_D = "sbu_d"
SECTION_COMMON = "common_expenses"
SECTION_CONSOLIDATED = "consolidated"
```

**Forbidden cross-SBU mappings** are prevented at the registry level. "Interest and Finance Charges" has separate entries:
- `INTEREST_FINANCE_GENERATION` (SBU-G)
- `INTEREST_FINANCE_TRANSMISSION` (SBU-T)
- `INTEREST_FINANCE_DISTRIBUTION` (SBU-D)

Attempting to map a generation interest charge to SBU-D will fail the mapping.

---

## How Mapping Works (Runtime)

1. Extracted row label is normalized (`normalizer.py`)
2. `map_record_to_canonical(record, document_type, context)` is called
3. The function scores every `CanonicalLineItem` against the label using the `aliases` regexes + contextual bonuses (SBU-D gets priority when context is None)
4. Highest scoring match (above threshold) wins
5. If no match → row is dropped from comparison (logged as unmapped)

Unmapped rows are visible in the extraction results but do **not** appear in the comparison table or final PDF.

---

## Example Mappings (Real Registry)

| Raw Label (from PDF) | Canonical ID | SBU | Section |
|----------------------|--------------|-----|---------|
| "Purchase of Power" | `PURCHASE_OF_POWER` | SBU-D | sbu_d |
| "Cost of Generation of Power" | `COST_OF_GENERATION` | SBU-G | sbu_g |
| "O&M Expenses - Distribution" | `OM_EXPENSES_DISTRIBUTION` | SBU-D | sbu_d |
| "Interest and Finance Charges" (in SBU-T chapter) | `INTEREST_FINANCE_TRANSMISSION` | SBU-T | sbu_t |
| "Employee Cost" | `EMPLOYEE_COST_DISTRIBUTION` | SBU-D | sbu_d |
| "Depreciation" (context = Generation) | `DEPRECIATION_GENERATION` | SBU-G | sbu_g |

Context (the chapter or table the row came from) is used to disambiguate shared names like "Depreciation", "Interest", "O&M".

---

## Fallback Mapping

`FALLBACK_CANONICAL_IDS` in `report_context.py` contains a small set of high-level summary rows (e.g., "Total ARR", "Revenue Gap") that can be used when chapter-specific target tables are not found.

If a chapter has only fallback rows:
- Status becomes "Fallback"
- `fallback_used: true` in coverage report
- Source note: "fallback_from_sbu_d_summary"

This is better than "Missing" but less authoritative than a dedicated target table extraction.

---

## Current Registry Coverage (Approximate)

- **SBU-D**: ~25–30 items (Power Purchase, O&M sub-heads, Employee Cost, R&M, A&G, Interest, Depreciation, RoE, Gross Fixed Assets, etc.). Strong coverage.
- **SBU-G**: Cost of Generation, O&M Generation, Interest/Finance Gen, Depreciation Gen, RoE Gen, Employee Cost Gen, etc.
- **SBU-T**: Similar structure for Transmission.
- **Energy Sales & T&D Loss**: Partial (energy sold, T&D loss %, etc.)
- **Common Expenses**: Limited
- **Consolidated / Totals**: Present (used for summary tables)

The registry is intentionally **not exhaustive** in Phase 1. Adding items is a deliberate, reviewable change.

---

## How to Extend the Registry (Safe Pattern)

1. Add a new `CanonicalLineItem(...)` in `CANONICAL_REGISTRY` tuple in `canonical_registry.py`
2. Provide 4–8 high-quality aliases (regexes)
3. Assign correct `sbu` and `section`
4. Add a test in `test_canonical_registry.py`
5. If the item belongs to a chapter, consider adding a matching `TargetTable` in `table_targets.py`

Never reuse a `canonical_id`. Never map the same logical concept to two different IDs.

---

## Unmapped Rows — What Happens?

- They are stored in `extracted_rows`
- They appear in the Extraction results UI (with warning)
- They are **excluded** from:
  - Comparison table
  - Report context chapters
  - Generated PDF
- They contribute to "unmapped_rows" count in coverage diagnostics

This is the correct behavior for a deterministic system.

---

## Relationship to SBU Coverage in Reports

The report context builder (`report_context.py`) uses `SECTION_OWNERSHIP` to decide which canonical IDs belong in which chapter. If a required ID for SBU-G is never mapped because the extraction never saw a matching label, that chapter will have zero rows → "Missing" status.

This is why expanding alias quality and target table captions is the highest-leverage Phase 1.5 activity.

---

See [08_EXTRACTION_PIPELINE.md](08_EXTRACTION_PIPELINE.md) (previous step) and [10_COMPARISON_ENGINE.md](10_COMPARISON_ENGINE.md) (next step).
