# KSERC Decision Support System — Extraction Pipeline

**Core file:** `backend/extractor.py`  
**Target catalog:** `backend/table_targets.py`  
**Libraries:** pdfplumber (primary), optional camelot

---

## High-Level Flow

```
PDF file (ARR or Petition)
        │
        ▼
pdfplumber.open() → pages
        │
        ▼
For each page:
  - Detect tables (pdfplumber.extract_tables)
  - Match table caption against TARGET_TABLE_CATALOG
  - If match → extract with normalized columns
  - Else → fallback broad row extraction (legacy path)
        │
        ▼
Value parsing (money patterns, unit detection)
        │
        ▼
Provenance attachment (page, table_index, table_caption, confidence)
        │
        ▼
normalize_row_label() + map_record_to_canonical() (canonical_registry)
        │
        ▼
INSERT ExtractedRow + NormalizedLineItem
```

---

## Target Table Detection (The Phase 1.5 Foundation)

`table_targets.py` defines `TARGET_TABLE_CATALOG` — a tuple of `TargetTable` dataclasses.

Each target specifies:
- `target_id` (e.g., "SBU_D_POWER_PURCHASE")
- `chapter` (SBU_G, SBU_T, SBU_D, ENERGY_TD, COMMON_EXPENSES, CONSOLIDATED)
- `document_type` (ARR_ORDER, PETITION, ANY)
- `caption_patterns` — tuple of regex-friendly strings the caption must contain
- `required_columns` — expected header row shape after normalization
- `priority`

Example (SBU-G):

```python
TargetTable(
    target_id="SBU_G_TRANSFER_COST",
    chapter=CHAPTER_SBU_G,
    caption_patterns=(
        "Transfer Cost of SBU-G",
        "ARR&ERC of SBU-G",
        "SBU-G as per truing up petition",
        ...
    ),
    required_columns=("Particulars", "MYT", "Actual", "Sought", "Difference"),
    ...
)
```

During extraction, `caption_matches()` and `target_applies_to_document()` decide whether a discovered table is a "target" table worth precise column mapping.

**Why this matters:**
- SBU-D tables are reliably detected in the sample PDFs → "Full" coverage.
- SBU-G / SBU-T tables require the exact caption strings above (or close variants). If the real KSEB petition uses slightly different wording, the chapter becomes "Missing" or "Fallback".

---

## Column Normalization

`normalize_columns()` in `table_targets.py` maps common KSERC header variants:

- "Approved", "ARR Approved", "MYT Approved" → "Approved"
- "Actual", "Audited", "Truing Up Actual" → "Actual"
- "Claimed", "Sought", "Petition", "As per Petition" → "Claimed"
- "Difference", "Variance", "Gap" → "Difference"

This allows the same downstream code to handle both ARR Order columns and Petition columns.

---

## Value Extraction & Confidence

- Money pattern: `r'[-−]?\s*[\d,]+\.?\d*'`
- Unit inference from nearby text or column header
- Confidence heuristic based on:
  - Whether the row came from a recognized target table
  - Whether the value parsed cleanly
  - Whether the row label survived normalization

Low-confidence rows (< 0.6) are automatically flagged `REVIEW_REQUIRED` by the comparison engine.

---

## Document-Type Specific Behavior

| Document Type | Expected Tables | Typical Chapters Exercised |
|---------------|-----------------|------------------------------|
| ARR Order | Approved ARR summary, SBU-wise approved costs | SBU-D (strong), SBU-G/T (if targets present) |
| Truing-Up Petition | Actual + Claimed columns, transfer costs, true-up statements | SBU-D (strong), others conditional on caption match |

The `contract_document_type()` helper in `canonical_registry.py` helps route rows correctly.

---

## Current Coverage Reality (Tested Behavior)

From `test_report_context_sbu_coverage.py` and `test_target_table_detection.py`:

- When a target table caption **is** found → chapter status = "Full", `target_table_found: true`, source = "chapter_table"
- When only fallback rows from SBU-D summary exist → status = "Fallback", `fallback_used: true`
- When neither exists → status = "Missing", `failed_extraction_reason` populated with attempted target IDs

**In the included sample PDFs (`arr_order_test.pdf` + `petition_test.pdf`):**
- SBU-D: Substantive / Full coverage
- SBU-G: Usually Full or Fallback (some targets match)
- SBU-T: Often Fallback or Missing
- Energy/T&D and Common Expenses: Frequently "Missing"

This is **not a bug** — it is the documented Phase 1 state. Expanding the catalog is Phase 1.5 work.

---

## Extraction Job Lifecycle (in DB)

1. Upload creates `ExtractionJob` with `status=PENDING`
2. Background task sets `PROCESSING`, updates `stage` and `progress`
3. On success: `COMPLETED`, `rows_extracted`, `case_id` populated
4. On failure: `FAILED`, `error_message` set (visible in UI)

Frontend polls `/api/job/{job_id}` until `COMPLETED` or `FAILED`.

---

## OCR Path (Disabled by Default)

`OCR_ENABLED=false` in `.env`.

When enabled (and Tesseract installed):
- pdfplumber first attempts text extraction
- If page text is below threshold → falls back to OCR via pytesseract
- This path is **not** exercised by the current sample PDFs (they are text PDFs)

---

## Known Extraction Limitations (Honest)

1. **Caption sensitivity** — One character difference in a table title can cause a target table to be missed.
2. **Multi-page tables** — Continuation pages without repeated captions may be partially captured.
3. **Merged cells / complex layouts** — pdfplumber sometimes returns fragmented rows.
4. **Scanned PDFs** — Require OCR (disabled). Text layer must be present for default success.
5. **No table of contents parsing** — The pipeline does not yet use the PDF TOC to jump to chapters; it scans all pages.

---

## Adding a New Target Table (for Phase 1.5)

1. Add a new `TargetTable(...)` to `TARGET_TABLE_CATALOG` in `table_targets.py`
2. Add corresponding `CanonicalLineItem` entries in `canonical_registry.py` with good aliases
3. Add test case in `test_target_table_detection.py`
4. Re-run smoke test with a PDF that contains the new table

The architecture is deliberately built to make this extension low-risk.

---

See:
- [09_CANONICAL_MAPPING.md](09_CANONICAL_MAPPING.md) for the next step after extraction
- [16_CURRENT_LIMITATIONS.md](16_CURRENT_LIMITATIONS.md) for the full list of gaps
