# KSERC Decision Support System — Troubleshooting Guide

---

## Backend Will Not Start

### Symptom: "Missing required environment variables: DATABASE_URL, ..."

**Cause:** `.env` file does not exist or is incomplete.

**Fix:**
```bash
cp .env.example .env          # macOS/Linux
Copy-Item .env.example .env   # Windows
python scripts/check_env.py
```

### Symptom: `ModuleNotFoundError: No module named 'backend'`

**Cause:** You ran `uvicorn` from inside the `backend/` directory or the venv is not activated.

**Fix:**
- Always run from the project root.
- Activate venv first:
  - Windows: `.\.venv\Scripts\Activate.ps1`
  - macOS/Linux: `source .venv/bin/activate`
- Correct command: `python -m uvicorn backend.app:app --reload --port 8000`

### Symptom: `RuntimeError: PDF_ENGINE must be either 'reportlab' or 'playwright'`

**Cause:** Typo in `.env` (e.g., `playright` or empty).

**Fix:** Set `PDF_ENGINE=reportlab` (recommended for first run).

---

## Frontend Will Not Start or Cannot Reach Backend

### Symptom: `npm start` fails with port 5173 already in use

**Fix:** Kill the other process or change port in `frontend/vite.config.ts` (then also update `CORS_ORIGINS` and `FRONTEND_URL`).

### Symptom: Browser console shows CORS error / "Failed to fetch"

**Likely cause:** `CORS_ORIGINS` in `.env` does not include the exact origin the browser is using.

**Fix:**
- Confirm backend is running at `http://127.0.0.1:8000/health`
- In `.env`:
  ```
  CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
  ```
- Restart the backend.

### Symptom: Frontend shows "API error" even though backend health is OK

**Fix:** Check `VITE_API_BASE_URL` in `frontend/.env.local`. It must end with `/api` or the code will double-prefix.

---

## Database Issues

### Symptom: "no such table: comparisons" or similar

**Fix:**
```bash
python scripts/init_db.py
```

This runs `Base.metadata.create_all` + SQLite schema guards.

### Symptom: SQLite locked / "database is locked"

**Cause:** Another process (perhaps a previous crashed uvicorn) still holds the file.

**Fix:** Kill all Python processes, delete `data/kserc_dss.db`, run `python scripts/init_db.py` again.

---

## Upload or Extraction Problems

### Symptom: Upload fails with "Only PDF files are allowed" or 400

**Fix:** The file must have `.pdf` extension and be under 75 MB. Rename if necessary.

### Symptom: Extraction job stays at "PENDING" or "PROCESSING" forever

**Cause:** Background task crashed (common with very large PDFs or missing optional libs).

**Fix:**
1. Check the terminal running the backend for the traceback.
2. Look at `/api/job/{job_id}` response — `error_message` field usually contains the root cause.
3. For scanned PDFs: set `OCR_ENABLED=true` and install Tesseract (advanced).

### Symptom: Very few rows extracted from a known-good PDF

**Cause:** Target table captions in the PDF do not match `TARGET_TABLE_CATALOG`.

**Workaround:** The legacy broad-row extraction path should still catch many items. For production PDFs, add new `TargetTable` entries (see [08_EXTRACTION_PIPELINE.md](08_EXTRACTION_PIPELINE.md)).

---

## Comparison Problems

### Symptom: "No ARR or Petition data found for comparison"

**Cause:** One of the two documents was never successfully extracted, or the `case_id` logic did not link them.

**Fix:**
- Go to Extraction tab and confirm both documents show "COMPLETED" with > 0 rows.
- Re-run comparison after both are ready.

### Symptom: Many "INCOMPLETE_DATA" rows even though numbers are visible in the PDFs

**Cause:** The row labels did not match any alias in the canonical registry, or value parsing failed.

**Fix:** 
- Check the Extraction tab for "unmapped" rows.
- Improve aliases in `canonical_registry.py` (add more regex patterns).
- Re-extract or re-run comparison.

---

## PDF Generation Problems

### Symptom: "Report generation failed" or 500

**Common causes:**
- `PDF_ENGINE=playwright` but Chromium not installed → run `python -m playwright install chromium`
- ReportLab not installed (rare — in requirements.txt)
- Banned string detected in context (should not happen in normal flow)

**Fix:** Check backend logs. The error message is usually explicit.

### Symptom: Generated PDF has broken tables or missing chapters that should be present

**Cause:** Coverage was "Missing" or "Fallback" for that chapter.

**Diagnostic:** Open the PDF and go to the "Extraction Coverage Summary" appendix. It lists exactly which target tables were attempted and why the chapter is missing.

**Fix:** Improve target table captions or add new `TargetTable` entries for the specific petition format.

### Symptom: Playwright path is extremely slow or times out

**Fix:** Stick with `PDF_ENGINE=reportlab` for local and demo use. Playwright is only needed when you want HTML-perfect output for Phase 2 narrative work.

---

## Smoke Test Failures

```bash
python scripts/smoke_test.py
```

If it fails:
1. Check that both sample PDFs (`arr_order_test.pdf`, `petition_test.pdf`) still exist in the repo root.
2. Confirm the backend is healthy.
3. Look at the detailed exception — it usually tells you which step (upload, comparison, generate) failed.

---

## Windows-Specific Issues

- PowerShell execution policy blocks `setup_backend.ps1` → `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass`
- Path issues with backslashes → the config resolver in `backend/config.py` handles most cases; use forward slashes in `.env`.
- Long file paths when generating many PDFs → keep `output/` clean.

---

## Getting More Debug Information

- Backend logs: everything prints to the uvicorn terminal.
- Database inspection: open `data/kserc_dss.db` with DB Browser for SQLite or `sqlite3` CLI.
- Extraction diagnostics: the Extraction tab in the UI shows raw row counts before/after mapping.
- PDF content check: use `pdftotext` (if installed) or the fidelity test to extract text from the generated PDF and grep for expected canonical names.

---

When in doubt, run the smoke test. If the smoke test passes, the core system is healthy; the issue is almost always environmental or data-specific.
