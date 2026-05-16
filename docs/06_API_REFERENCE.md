# KSERC Decision Support System — API Reference (MVP)

**Base URL (local):** `http://127.0.0.1:8000`

**Two router sets:**
- Primary: `router = APIRouter(prefix="/api", ...)` — preferred by the React frontend
- Compatibility: `compat_router` (no prefix) — used by `scripts/smoke_test.py` and legacy clients

All endpoints are defined in `backend/api.py`.

---

## Health & Root

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/` | Service metadata | `{ service, version, mode, features[] }` |
| GET | `/health` | Liveness + configuration | `{ status, mode, database, upload_dir, generated_reports_dir, pdf_engine }` |

---

## Document Upload & Listing

| Method | Path | Purpose | Request | Response Model |
|--------|------|---------|---------|----------------|
| POST | `/api/upload/arr` (primary)<br>`/upload/arr` (compat) | Upload ARR Order PDF. Auto-triggers extraction. | `multipart/form-data` file | `DocumentUploadResponse` |
| POST | `/api/upload/petition` (primary)<br>`/upload/petition` (compat) | Upload Truing-Up Petition PDF. Auto-triggers extraction. | `multipart/form-data` file | `DocumentUploadResponse` |
| POST | `/api/documents/upload` | Generic upload (infers type from filename or form) | `multipart/form-data` + optional `doc_type` | `DocumentUploadResponse` |
| GET | `/api/documents` | List all uploaded documents | — | `List[DocumentListItem]` |

**DocumentUploadResponse** contains `id`, `filename`, `doc_type`, `extraction_job_id`, `job_status`, `case_id`.

**Important:** Upload endpoints now auto-start extraction (background task). No separate "Extract Tables" button is required in the current UI.

---

## Extraction Jobs

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| POST | `/api/extraction/{doc_id}/run` | Manually trigger (or re-trigger) extraction for a document | `JobStatusResponse` |
| GET | `/api/extraction/{doc_id}` | Get extraction result (rows, stats, method) | `ExtractionResultResponse` |
| GET | `/api/job/{job_id}` | Poll job progress (used by frontend polling) | `JobStatusResponse` |

**JobStatusResponse** fields: `status` (PENDING/PROCESSING/COMPLETED/FAILED), `progress`, `rows_extracted`, `stage`, `error_message`.

---

## Comparison Engine

| Method | Path | Purpose | Query/Body | Response |
|--------|------|---------|------------|----------|
| POST | `/api/comparison/run` (primary)<br>`/comparison/run` (compat) | Run deterministic variance comparison for a financial year | `?financial_year=2024-25` | `ComparisonResponse` |
| GET | `/api/comparison/results` (primary)<br>`/comparison/results` (compat) | Get latest comparison for the year | `?financial_year=2024-25` | `ComparisonResponse` |
| GET | `/api/comparison/latest` | Alias for latest results | `?financial_year=...` | `ComparisonResponse` |
| GET | `/api/comparison/{case_id}` | Get specific comparison set | — | `ComparisonResponse` |
| GET | `/api/comparison` | List all comparison cases | — | `List[ComparisonResponse]` |

**ComparisonResponse** contains:
- `case_id`, `financial_year`
- `total_items`, `auto_approved`, `review_required`, `incomplete`
- `items[]`: each with `canonical_id`, `display_name`, `sbu`, `approved_value`, `actual_value`, `claimed_value`, `variance`, `variance_percent`, `decision_class`, `flag_reason`, source pages

---

## Officer Review

| Method | Path | Purpose | Body | Response |
|--------|------|---------|------|----------|
| POST | `/api/review/{comparison_id}` | Submit officer decision on one comparison row | `ReviewRequest` (`action`: "approve"\|"reject"\|"edit", `officer_comment`, optional `edited_value`) | `ReviewResponse` |
| GET | `/api/review/{case_id}/all` | Get all reviews for a case | — | `List[ReviewResponse]` |

**ReviewRequest** enforces:
- `officer_comment` is required (minimum length enforced in UI)
- When `action=edit`, `edited_value` must be provided

---

## Report Generation & Download

| Method | Path | Purpose | Body | Response |
|--------|------|---------|------|----------|
| POST | `/api/generate` (primary)<br>`/report/generate` (compat) | Generate KSERC-style draft order PDF | `GenerateOrderRequest` (`case_id`, `financial_year`, optional `title`) | `GeneratedOrderResponse` |
| GET | `/api/generate/{order_id}/download` (primary)<br>`/report/{order_id}` (compat) | Download the generated PDF (binary) | — | `FileResponse` (application/pdf) |
| GET | `/api/generate` | List all generated orders | — | `List[GeneratedOrderResponse]` |

**GeneratedOrderResponse** includes `id`, `file_path`, `file_hash` (SHA-256), `is_draft`, `total_items`, `auto_approved`, `review_required`, `watermark_text`.

The PDF is written to `GENERATED_REPORTS_DIR` (default `output/`) and served via FastAPI `StaticFiles` at `/generated/<filename>`.

---

## Audit & Diagnostics

| Method | Path | Purpose | Response |
|--------|------|---------|----------|
| GET | `/api/audit` | Full audit trail (uploads, extractions, comparisons, reviews, generations) | `List[AuditEntry]` |
| GET | `/api/normalized` | All normalized line items (debug / advanced) | `List[NormalizedItemResponse]` |

---

## Request/Response Examples (curl)

### Upload ARR
```bash
curl -X POST "http://127.0.0.1:8000/api/upload/arr" \
  -F "file=@arr_order_test.pdf"
```

### Run Comparison
```bash
curl -X POST "http://127.0.0.1:8000/api/comparison/run?financial_year=2024-25"
```

### Generate Report
```bash
curl -X POST "http://127.0.0.1:8000/api/generate" \
  -H "Content-Type: application/json" \
  -d '{"case_id": "<uuid-from-comparison>", "financial_year": "2024-25"}'
```

### Download
```bash
curl -o KSERC_Draft.pdf "http://127.0.0.1:8000/api/generate/<order_id>/download"
# or via static mount
curl -o KSERC_Draft.pdf "http://127.0.0.1:8000/generated/KSERC_TruingUp_2024-25_....pdf"
```

---

## Error Responses (Common)

- `400 Bad Request` — Invalid file type, missing required field, validation error
- `404 Not Found` — Document / case / order not found, or no ARR/Petition data for comparison
- `422 Unprocessable Entity` — Pydantic validation failure (FastAPI auto)
- `500 Internal Server Error` — Extraction failure, PDF generation failure (check `error_message` in job status)

---

## Compatibility Note for Smoke Test

`scripts/smoke_test.py` uses the **non-/api** paths (`/upload/arr`, `/comparison/run`, `/report/generate`) because it was written against an earlier router layout. Both sets of paths are fully supported and return identical behavior.

---

**This document is generated from the actual route definitions and Pydantic models in `backend/api.py` and `backend/schemas.py`.** Do not document endpoints that are not present in the source.
