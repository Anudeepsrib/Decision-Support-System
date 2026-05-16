# KSERC Decision Support System — Security and Auditability (Current Posture)

**Honest assessment for an MVP:** Security is "local-demo appropriate," not "production enterprise grade."

---

## What Is Currently Implemented

### 1. Deterministic Value Chain (Strong)

- Every number in the final PDF originates from `pdfplumber` extraction of the uploaded source PDFs.
- The canonical registry is a pure-Python, version-controlled, reviewable file (`canonical_registry.py`).
- The comparison engine (`comparison.py`) contains only arithmetic and fixed thresholds.
- No generative model can alter a value. This is the strongest security property of the system today.

### 2. Provenance & Traceability (Good)

- `extracted_rows` table stores `page_number`, `table_index`, `table_name`, `row_label`, `raw_text`, `confidence`.
- `comparisons` table stores six provenance columns (document_id + page + table for approved, actual, and claimed).
- The generated PDF appendix "Extraction Coverage & Provenance" exposes this data.
- SHA-256 hash of the final PDF is stored in `generated_orders.file_hash`.

An auditor can, in principle, take any number in the PDF, look up its canonical_id, find the comparison row, and open the exact page in the source PDFs to verify.

### 3. File Handling (Basic but Functional)

- Uploads are written to `mvp_uploads/<uuid>.pdf` with UUID filenames (no user-controlled paths).
- Generated PDFs go to `output/` and are served read-only via FastAPI `StaticFiles`.
- File size limit (75 MB) and content-type check (`.pdf`) exist in the upload endpoints.

### 4. Audit Trail (Rudimentary)

- `/api/audit` endpoint returns a list of major events (uploads, extractions, comparisons, reviews, generations).
- `reviews` table captures `officer_name`, `officer_comment`, `action`, `reviewed_at`, and any `edited_value`.
- Every generated order records `generated_by`, `generated_at`, and the snapshot counts (`total_items`, `review_required`).

### 5. Environment & Secrets

- All configuration via `.env` (never committed).
- `JWT_SECRET_KEY` is required but the full JWT authentication flow is not yet enforced in demo mode.
- No hardcoded credentials in source.

---

## What Is Missing / Weak (Known Gaps)

| Area | Current State | Risk Level | Phase Target |
|------|---------------|------------|--------------|
| Authentication / RBAC | Demo mode bypasses; skeleton JWT code exists | High (for production) | Phase 3 |
| Role-based permissions | No "Officer" vs "Senior Officer" vs "Admin" enforcement | High | Phase 3 |
| Input sanitization for LLM (future) | N/A today (no LLM) | Critical when Phase 2 added | Phase 2 |
| Tamper-evident audit log | Basic table; no hash chaining or Merkle tree | Medium | Phase 3 |
| Upload virus/malware scanning | None | Medium | Phase 3 |
| Rate limiting / DoS protection | None (local only) | Low for MVP | Phase 3 |
| Encrypted at-rest storage | SQLite file is plaintext | Low (local dev) | Phase 3 (or OS-level disk encryption) |
| Dependency vulnerability scanning | Not automated | Medium | Phase 3 CI |
| Secrets management (for production) | `.env` file | High | Phase 3 (Vault / AWS Secrets / etc.) |

---

## Data Flow Security Properties

- **Uploaded PDFs** never leave the local machine in the default configuration.
- **No external API calls** are made during normal operation (except optional Playwright browser or future LLM).
- **Generated PDFs** contain only data that passed through the canonical registry and comparison engine.
- **Officer comments** are stored verbatim and will appear in the PDF appendix — this is intentional for accountability.

---

## Recommendations for Phase 3 Production Hardening

1. Implement proper user model + JWT login + role checks before any non-demo deployment.
2. Add cryptographic audit log (append-only table with previous-hash pointer + root hash published periodically).
3. Integrate a document management system (S3 + versioning or on-prem DMS) instead of local `mvp_uploads/`.
4. Add Content Security Policy, strict CORS, and request size limits in production reverse proxy.
5. Run `pip-audit` / `safety` and `npm audit` in CI and block on high-severity findings.
6. For LLM phase: implement the full validator stack described in [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md) before the first real LLM call.
7. Consider running the entire stack inside a locked-down container or VM for air-gapped regulatory environments.

---

## Auditability Statement (For Regulators)

"The current MVP guarantees that every numeric value in a generated draft order can be traced, via database records, to an exact page and table in one of the two source PDFs uploaded by the user. No value is synthesized, inferred by a model, or altered after extraction except by an explicit officer edit action that is itself logged with a mandatory justification comment."

This property holds **only** because the system is currently LLM-free and deterministic. Adding any generative capability without the guardrails in the Phase 2 plan would invalidate this statement.

---

**Treat this document as a living security posture statement.** It must be updated before any production pilot.
