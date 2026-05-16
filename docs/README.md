# KSERC Decision Support System — Documentation Index

**MVP Version:** 1.0.0-mvp  
**Status:** Local-first deterministic MVP (no LLM in runtime path)

This index helps different roles find the right document quickly.

---

## For New Developers (First Clone)
1. [03_LOCAL_SETUP.md](03_LOCAL_SETUP.md) — Exact commands to run from fresh clone (Python + Node)
2. [05_ENVIRONMENT_VARIABLES.md](05_ENVIRONMENT_VARIABLES.md) — All required .env values
3. [04_DOCKER_SETUP.md](04_DOCKER_SETUP.md) — Docker is intentionally not supported in this MVP

## For Reviewers & Architects
- [01_PROJECT_OVERVIEW.md](01_PROJECT_OVERVIEW.md) — Business context: truing-up, ARR, Petition, why comparison matters
- [02_ARCHITECTURE.md](02_ARCHITECTURE.md) — High-level architecture + Mermaid data flow diagrams
- [07_DATA_MODEL.md](07_DATA_MODEL.md) — All SQLAlchemy tables and relationships
- [19_SECURITY_AND_AUDITABILITY.md](19_SECURITY_AND_AUDITABILITY.md) — Current security posture and traceability

## For Backend Engineers
- [06_API_REFERENCE.md](06_API_REFERENCE.md) — All FastAPI endpoints (primary `/api/*` + compatibility routes)
- [08_EXTRACTION_PIPELINE.md](08_EXTRACTION_PIPELINE.md) — pdfplumber + target table detection (SBU-G/T/D)
- [09_CANONICAL_MAPPING.md](09_CANONICAL_MAPPING.md) — Registry, aliases, SBU ownership, forbidden cross-SBU rules
- [10_COMPARISON_ENGINE.md](10_COMPARISON_ENGINE.md) — Deterministic variance formulas and 15% threshold logic

## For Report / PDF Engineers
- [11_REPORT_GENERATION.md](11_REPORT_GENERATION.md) — Chapter builders, full/fallback/missing modes
- [12_PDF_TEMPLATE_GUIDE.md](12_PDF_TEMPLATE_GUIDE.md) — ReportLab templates, CSS, what is banned from output

## For QA & Testers
- [14_TESTING_GUIDE.md](14_TESTING_GUIDE.md) — pytest commands, smoke_test.py, frontend build checks
- [16_CURRENT_LIMITATIONS.md](16_CURRENT_LIMITATIONS.md) — Honest gaps (must-read before claiming features)

## For Demo Presenters & Stakeholders
- [15_DEMO_SCRIPT.md](15_DEMO_SCRIPT.md) — Step-by-step talking points with honest coverage statements
- [13_FRONTEND_WORKFLOW.md](13_FRONTEND_WORKFLOW.md) — UI tabs and user journey

## For Phase 2 AI / LLM Engineers
- [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md) — Safe integration boundaries (what LLM can and must never do)
- [20_ROADMAP.md](20_ROADMAP.md) — Phase 1 (current) → 1.5 (SBU-G/T completion) → 2 (LLM) → 3 (production)

## Quick Reference
- **What the MVP actually does today:** Upload ARR Order PDF + Truing-Up Petition PDF → deterministic extraction (pdfplumber + target tables) → canonical mapping → 15% variance comparison → officer review → KSERC-style draft order PDF (ReportLab, no LLM).
- **SBU-D:** Substantive coverage in current sample PDFs and registry.
- **SBU-G / SBU-T / Energy / Common:** Coverage depends on whether the uploaded PDFs contain tables whose captions match the `TARGET_TABLE_CATALOG` in `backend/table_targets.py`. Missing chapters are reported transparently as "Missing" with attempted target IDs.
- **LLM:** Zero calls in the current codebase. `prompts.py` contains only deterministic string templates. Phase 2 plan exists.

## Document Conventions
- All commands are verified against the actual scripts and `package.json` / `requirements.txt`.
- No feature is documented unless the supporting code path exists.
- Limitations are stated in plain language in the dedicated limitations document.

---

**Maintained by:** Principal Technical Documentation Architect (per task requirements)  
**Last validated against:** Current `mvp-demo` branch codebase (app.py, api.py, models.py, extractor.py, canonical_registry.py, comparison.py, report_context.py, pdf_generator.py, table_targets.py, frontend/src/App.tsx, scripts/*)

Start here: [03_LOCAL_SETUP.md](03_LOCAL_SETUP.md) for a working instance in under 10 minutes.
