# KSERC Decision Support System — Architecture

**Version:** 1.0.0-mvp (deterministic, no LLM in runtime)

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                                USER (Browser)                               │
│                    React + Vite (http://127.0.0.1:5173)                     │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ HTTP (axios)
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              FastAPI Backend                                │
│                        (python -m uvicorn backend.app:app)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │
│  │  /upload/*   │  │ /extraction  │  │ /comparison  │  │  /review     │   │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘   │
│         │                 │                 │                 │           │
│  ┌──────▼─────────────────▼─────────────────▼─────────────────▼───────┐   │
│  │                    Core Pipeline (deterministic)                   │   │
│  │  pdfplumber ──► table_targets ──► normalizer ──► canonical_registry │   │
│  │                              │                                     │   │
│  │                              ▼                                     │   │
│  │                    comparison.py (variance + 15% rules)            │   │
│  │                              │                                     │   │
│  │                              ▼                                     │   │
│  │                    report_context.py (chapter builder)             │   │
│  └────────────────────────────────────────────────────────────────────┘   │
│                                      │                                      │
│  ┌───────────────────────────────────▼──────────────────────────────────┐ │
│  │                       PDF Generator Layer                            │ │
│  │  ReportLab (default)  OR  Playwright (optional)                      │ │
│  │  Templates: backend/templates/ (title, toc, chapter, regulatory_table)│ │
│  └──────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────┬───────────────────────────────────────┘
                                      │ Writes to
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                              Filesystem                                     │
│  mvp_uploads/  (source PDFs)                                                │
│  output/       (generated KSERC draft orders + .html previews)              │
│  data/kserc_dss.db (SQLite)                                                 │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

### 1. Frontend (React + TypeScript + Vite + Tailwind)
- Location: `frontend/src/App.tsx`
- Tabs: `arr-upload` | `petition-upload` | `extraction` | `comparison` | `generate`
- Responsibilities:
  - File upload (`.pdf` only, ≤75 MB)
  - Poll job status for background extraction
  - Display comparison table with decision badges
  - Allow officer review (approve/edit/reject + mandatory comment)
  - Trigger report generation and download
- API base: `VITE_API_BASE_URL` (defaults to `http://127.0.0.1:8000/api`)
- No state persistence on client; everything lives in backend DB

### 2. Backend (FastAPI + SQLAlchemy + Uvicorn)
- Entry: `backend/app.py` (lifespan runs `validate_required_environment()` + `init_db()`)
- Primary router: `backend/api.py` (prefix `/api`)
- Compatibility router: `backend/api.py` (`compat_router`) for smoke-test paths (`/upload/arr`, `/report/generate`, etc.)
- Key modules:
  - `extractor.py` — pdfplumber + target table detection
  - `table_targets.py` — deterministic caption patterns for SBU-G/T/D/Energy/Common
  - `normalizer.py` — label cleanup
  - `canonical_registry.py` — the heart of mapping (rule-based, version-controlled)
  - `comparison.py` — pure arithmetic + classification
  - `report_context.py` — builds the exact JSON structure consumed by PDF layer
  - `pdf_generator.py` — ReportLab or Playwright renderer
  - `prompts.py` — **deterministic template strings only** (no OpenAI call)

### 3. Database (SQLite by default)
- Engine: SQLAlchemy, `data/kserc_dss.db`
- Tables (see [07_DATA_MODEL.md](07_DATA_MODEL.md) for full schema):
  - `documents`
  - `extraction_jobs`
  - `extracted_rows` (raw with provenance)
  - `normalized_line_items`
  - `comparisons` (the three-way view)
  - `reviews`
  - `generated_orders`
- Schema creation: `Base.metadata.create_all` + lightweight SQLite guards in `database.py`
- No Alembic in MVP

### 4. Storage
- Uploaded PDFs: `mvp_uploads/<uuid>.pdf`
- Generated PDFs: `output/KSERC_TruingUp_<FY>_<timestamp>.pdf`
- Static mount: `/generated/<filename>` → `output/`

---

## Data Flow (Detailed)

```mermaid
sequenceDiagram
    participant U as User (Browser)
    participant F as Frontend (Vite:5173)
    participant B as Backend (FastAPI:8000)
    participant E as Extractor + Targets
    participant C as Canonical Registry
    participant V as Comparison Engine
    participant R as Report Context
    participant P as PDF Generator
    participant DB as SQLite

    U->>F: Upload ARR PDF
    F->>B: POST /api/upload/arr (or compat /upload/arr)
    B->>DB: INSERT Document (doc_type=arr_order)
    B->>E: extract_tables_from_pdf_path()
    E->>C: map_record_to_canonical()
    B->>DB: INSERT ExtractedRow + NormalizedLineItem
    B-->>F: JobStatus (COMPLETED)

    U->>F: Upload Petition PDF
    F->>B: POST /api/upload/petition
    ... (same extraction + canonical path) ...

    U->>F: Click "Run Comparison"
    F->>B: POST /api/comparison/run?financial_year=2024-25
    B->>V: calculate_variance() + classify_decision() for every canonical pair
    B->>DB: INSERT Comparison rows
    B-->>F: ComparisonResponse (total_items, review_required, rows)

    U->>F: Review flagged items (optional)
    F->>B: POST /api/review/{comparison_id}
    B->>DB: INSERT Review (action, officer_comment, edited_value?)

    U->>F: Click "Generate PDF"
    F->>B: POST /api/generate (or compat /report/generate)
    B->>R: build_report_context(case_id, financial_year)
    R->>C: Pull registry metadata + chapter ownership
    R-->>B: ReportContext dict (chapters, coverage[], tables, totals)
    B->>P: generate_kserc_order_pdf(context)
    P->>P: Render title_page.html + toc.html + chapter.html via ReportLab
    P->>P: Write PDF to output/
    B->>DB: INSERT GeneratedOrder (file_path, file_hash, is_draft)
    B-->>F: GeneratedOrderResponse + download URL
```

---

## Key Design Constraints (Why the Architecture Looks Like This)

1. **Determinism first** — Every number that appears in the final PDF must be traceable to a `(page, table, row_label)` triple in one of the source documents. This ruled out any generative model in Phase 1.
2. **Targeted extraction over broad scraping** — The `TARGET_TABLE_CATALOG` in `table_targets.py` is deliberately small and explicit. This is why SBU-G/T coverage is currently "conditional on caption match".
3. **Canonical registry is the contract** — `canonical_registry.py` is the single source of truth for what line items the Commission cares about. Adding a new cost head is a one-line registry edit + test.
4. **Report context is a pure data contract** — `report_context.py` produces a JSON-like structure that the PDF layer consumes. The PDF generator has no knowledge of extraction or variance logic.
5. **Two PDF engines** — ReportLab is the reliable default (no browser dependency). Playwright is available for pixel-perfect HTML-to-PDF when needed.

---

## Current Limitation — SBU Coverage (Architecturally Important)

| Chapter | Registry Section | Target Tables Defined? | Current Reality in Sample PDFs | Notes |
|---------|------------------|------------------------|--------------------------------|-------|
| SBU-G | `SECTION_SBU_G` | Yes (TRANSFER_COST, GENERATION_SUMMARY, etc.) | Full or Fallback (depends on PDF) | Requires exact caption match |
| SBU-T | `SECTION_SBU_T` | Yes | Full / Fallback / Missing | Same caption sensitivity |
| Energy/T&D | `SECTION_ENERGY` | Partial | Often Missing | Less mature target catalog |
| SBU-D | `SECTION_SBU_D` | Yes (many) | Substantive / Full | Primary focus of current test PDFs |
| Common Expenses | `SECTION_COMMON` | Yes | Usually Missing or Fallback | Needs petition table alignment |
| Consolidated | `SECTION_CONSOLIDATED` | Yes | Usually present | Built from other sections |

The architecture already supports all six chapters. The gap is in the breadth of `TARGET_TABLE_CATALOG` entries and alias coverage in the canonical registry for generation/transmission line items.

See [16_CURRENT_LIMITATIONS.md](16_CURRENT_LIMITATIONS.md) and [08_EXTRACTION_PIPELINE.md](08_EXTRACTION_PIPELINE.md) for details.

---

## Phase 2 LLM Safety Architecture (Placeholder)

The planned safe insertion point is **after** `report_context` is built and **before** the PDF renderer:

```
report_context (deterministic JSON)
        │
        ▼
[LLM Narrative Draft Layer]  ← Phase 2 only
        │
        ▼
Citation / Value Validator (must reject any numeric change or invented reg)
        │
        ▼
Officer Review Queue (human sees both deterministic base + LLM polish)
        │
        ▼
PDF Renderer (still uses the validated context)
```

LLM will **never** be allowed to:
- Change any approved/actual/claimed value
- Invent regulatory citations
- Re-assign SBU ownership
- Bypass the canonical registry

See [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md) for the full guardrail specification.

---

## Technology Versions (Current)

- Python: 3.11–3.13
- FastAPI: 0.115.8
- SQLAlchemy: 2.0.38
- pdfplumber: 0.11.5
- ReportLab: 4.2.5
- React: 18.2 + Vite 8 + TypeScript 5.6
- SQLite (default) — other DBs possible via `DATABASE_URL` but not tested in MVP

---

This architecture document is intentionally stable. Changes to the pipeline must be reflected here and in the corresponding implementation docs.
