# KSERC Decision Support System — Testing Guide

---

## Backend Tests (pytest)

All test files live in the project root and follow `test_*.py`.

### Run All Tests

```bash
# With venv activated
pytest -v
```

### Individual Test Suites (Important Ones)

| Test File | What It Validates | When to Run |
|-----------|-------------------|-------------|
| `test_extraction.py` | pdfplumber + table detection on sample PDFs | After extractor changes |
| `test_target_table_detection.py` | TARGET_TABLE_CATALOG matching logic | When adding SBU-G/T targets |
| `test_canonical_registry.py` | Alias matching, SBU ownership, no cross-SBU leaks | Before any registry edit |
| `test_variance.py` | `calculate_variance`, `classify_decision`, edge cases (zero approved, negative, missing) | Core engine changes |
| `test_sbu_g_mapping.py` / `test_sbu_t_mapping.py` | Specific SBU-G/T canonical coverage | SBU-G/T work |
| `test_report_context_sbu_coverage.py` | Full / Fallback / Missing chapter modes | Report context changes |
| `test_pdf_generation.py` | End-to-end PDF render (ReportLab) | Any template or generator change |
| `test_reference_pdf_fidelity.py` | Visual + content regression against known-good PDFs | Before releasing a new PDF version |
| `test_review_workflow.py` | Review submission, comment requirement, edit value | Review API changes |
| `test_security.py` | Path traversal, file size, banned strings, audit | Security-sensitive changes |
| `test_ai_safety.py` | Confirms no LLM calls, only template prompts | Continuous (cheap) |
| `test_traceability.py` | Every number in PDF has source page/table provenance | Audit-critical |

### Fast Safety Net (Recommended Before Every Commit)

```bash
pytest test_canonical_registry.py test_variance.py test_ai_safety.py test_security.py -q
```

---

## Frontend Build & Lint

```bash
cd frontend
npm run build     # TypeScript compile + Vite production build
npm run lint      # ESLint
```

A successful `npm run build` is required before any frontend PR.

---

## Smoke Test (End-to-End Integration)

The most important validation for the full pipeline:

```bash
# Backend running on 8000, frontend optional
python scripts/smoke_test.py
```

It performs:
1. Upload ARR (`arr_order_test.pdf`)
2. Upload Petition (`petition_test.pdf`)
3. Run comparison
4. Generate report
5. Download PDF bytes and assert size > 0

**Exit code 0 = the MVP is working for the sample data.**

This is the command you run before every stakeholder demo.

---

## Database & Environment Checks

```bash
python scripts/check_env.py     # All required vars present
python scripts/init_db.py       # Tables created / schema guards applied
```

---

## Manual Regression Checklist (Before Major Demos)

1. Fresh clone on a clean machine
2. Run setup scripts (or manual commands from 03_LOCAL_SETUP.md)
3. Start backend + frontend
4. Run `python scripts/smoke_test.py`
5. In UI:
   - Upload both sample PDFs
   - Confirm SBU-D rows appear with reasonable variances
   - Generate PDF
   - Open PDF and spot-check Chapter 5 tables + Extraction Coverage appendix
6. Verify no banned strings appear in the PDF (grep the PDF text or use the fidelity test)

---

## Adding a New Test (Pattern)

1. Write the test file following existing style (`test_*.py`)
2. Use the sample PDFs in the repo root when possible
3. Mock as little as possible — the strength of this MVP is that the real pipeline is fast enough to test end-to-end
4. Update this document and `docs/14_TESTING_GUIDE.md`

---

## Continuous Integration (Future)

Phase 3 will add:
- GitHub Actions workflow that runs the full pytest suite + smoke test on every push to `mvp-demo`
- Visual regression storage for generated PDFs
- Contract test between `report_context` schema and PDF renderer

For now, the local commands above are the standard.

---

**If the smoke test passes and the key unit tests pass, the system is in a demo-ready state.**
