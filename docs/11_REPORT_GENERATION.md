# KSERC Decision Support System — Report Generation

**Core files:**
- `backend/report_context.py` — builds the data contract
- `backend/pdf_generator.py` — renders to PDF (ReportLab or Playwright)
- `backend/templates/` — HTML fragments + `kserc_order.css`

---

## Core Principle

**The PDF generator never sees raw extraction rows, debug fields, or unmapped data.**

It receives only a carefully curated `report_context` dict produced by `build_report_context()`. This is the contract that makes the output deterministic and safe for regulatory drafting.

---

## Report Context Structure (High Level)

```python
{
    "case_id": "...",
    "financial_year": "2024-25",
    "generated_at": "...",
    "title": "KSERC Truing-Up Order ...",
    "arr_order_date": "25.06.2022",
    "chapters": { ... },           # SBU-G, SBU-T, ENERGY, SBU-D, COMMON, CONSOLIDATED
    "extraction_coverage": [ ... ], # one entry per chapter: Full / Fallback / Missing
    "totals": { ... },
    "source_documents": [ ... ],
    "officer_reviews": [ ... ],
    "appendices": { ... }
}
```

The PDF layer (and future LLM narrative layer) consumes only this structure.

---

## Chapter Organization (KSERC Order Style)

| Chapter | Title (from `_SECTION_TOC_TITLES`) | Section Key | Typical Content |
|---------|------------------------------------|-------------|-----------------|
| 2 | Truing up of SBU-G of KSEB Ltd | `sbu_g` | Generation cost heads, transfer cost |
| 3 | Truing up of SBU-T of KSEB Ltd | `sbu_t` | Transmission ARR |
| 4 | Energy sales and T&D loss | `energy_sales_td_loss` | Sales, loss percentage |
| 5 | Truing up of SBU-D of KSEB Ltd | `sbu_d` | Distribution (largest chapter in current MVP) |
| 6 | Approval of common expenses of KSEB Ltd | `common_expenses` | Corporate / shared costs |
| 7 | Consolidated Truing up of accounts of KSEB Ltd | `consolidated` | Summary + Revenue Gap |

Each chapter table contains only rows that successfully mapped to the canonical registry for that section.

---

## Coverage Modes (Critical for Honest Demos)

`report_context.py` computes per-chapter status:

```python
def _chapter_mode(rows: List[Dict]) -> str:
    if not rows:
        return "missing"
    if any(row.get("canonical_id") not in FALLBACK_CANONICAL_IDS for row in rows):
        return "full"
    return "fallback"
```

| Mode | Meaning | PDF Appearance | UI Coverage Badge |
|------|---------|----------------|-------------------|
| **Full** | At least one dedicated target-table row mapped | Complete table with source pages | Green "Full" |
| **Fallback** | Only summary/fallback rows (e.g. from SBU-D totals) | Table with note "Fallback from consolidated summary" | Amber "Fallback" |
| **Missing** | No mapped rows for the chapter | Short "No data extracted for this chapter" block + list of attempted target IDs | Red "Missing" |

The generated PDF appendix ("Extraction Coverage Summary") explicitly lists every chapter's status, attempted targets, and reason for fallback/missing.

**This is the mechanism that prevents over-claiming coverage.**

---

## PDF Generation Pipeline

1. `POST /api/generate` (or `/report/generate`)
2. `build_report_context(case_id, financial_year)` — heavy lifting in `report_context.py`
3. `generate_kserc_order_pdf(context)` in `pdf_generator.py`
4. Choose engine:
   - `PDF_ENGINE=reportlab` (default) → `SimpleDocTemplate` + `Paragraph` + `Table` + custom styles
   - `PDF_ENGINE=playwright` → render `kserc_order.html` template via headless Chromium → PDF
5. Compute SHA-256 of the bytes
6. Write to `output/KSERC_TruingUp_<FY>_<timestamp>.pdf`
7. Store `GeneratedOrder` row with hash and metadata
8. Return download URL

---

## Template System (ReportLab Path)

Located in `backend/templates/`:

- `kserc_order.html` — master document (used by Playwright path)
- `components/`:
  - `title_page.html`
  - `toc.html`
  - `chapter.html`
  - `regulatory_table.html`
  - `signature_block.html`
- `kserc_order.css` — KSERC-like styling (serif headings, table borders, page numbers, watermark)

ReportLab path does **not** use the HTML files directly; it uses equivalent `ParagraphStyle` and `TableStyle` definitions that mimic the CSS.

**Banned strings** (enforced in both paths):
- Any `raw_label`, `confidence`, `source_page` debug fields
- Tariff slab language ("0 to 100 units", "single phase", "fixed charge")
- Placeholder text from old regulatory templates

The generator will raise or silently drop content containing banned patterns.

---

## Page Count & Fidelity Goals

- `MAX_MVP_REPORT_PAGES = 60` (soft guidance in `report_context.py`)
- Current generated PDFs from sample data are typically 15–40 pages depending on how many chapters have data.
- The system deliberately does **not** pad content to reach 237 pages (a common historical KSERC order length). Padding would be dishonest.

---

## Determinism Guarantee

Because:
- All numeric values come from the `comparisons` table
- All mapping decisions are in the canonical registry (version controlled)
- The chapter builder applies fixed ordering and formatting rules
- The PDF renderer uses fixed styles and no random layout

**The same two input PDFs + same financial year will always produce byte-identical (or functionally identical) draft orders** (minor timestamp differences in the filename and generation metadata aside).

This is the foundation for future regression testing and regulatory defensibility.

---

## What the Generated PDF Contains (Typical)

1. Title page with KSERC header, order number, financial year, "DRAFT — FOR REVIEW"
2. Table of Contents (page numbers are best-effort; exact pagination is hard in ReportLab without two-pass)
3. Chapter 2 – SBU-G (if data)
4. Chapter 3 – SBU-T (if data)
5. Chapter 4 – Energy & T&D (if data)
6. Chapter 5 – SBU-D (almost always present)
7. Chapter 6 – Common Expenses (if data)
8. Chapter 7 – Consolidated + Revenue Gap
9. Officer Review Summary appendix
10. Extraction Coverage & Provenance appendix (critical for audit)
11. Signature block placeholder

---

## Future (Phase 2) Narrative Layer Insertion Point

After `build_report_context()` returns, before PDF rendering:

- LLM can be asked to draft the "Commission's Analysis" paragraphs for each chapter
- The deterministic table data + officer review comments remain the source of truth
- A validator layer must reject any LLM output that changes numbers or invents citations

See [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md).

---

**Report generation is the crown jewel of the MVP** — it turns a set of comparison rows into a document that looks and feels like a real KSERC draft order, while remaining 100% traceable.
