# KSERC Decision Support System — Environment Variables

**Source of truth:** `backend/config.py` (`REQUIRED_ENV_VARS` tuple + `_build_settings()`)

All variables are **required** for the application to start. The backend calls `validate_required_environment()` in the lifespan.

---

## Complete Variable Table

| Variable | Required | Default (if any) | Used By | Description |
|----------|----------|------------------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite:///./data/kserc_dss.db` | `database.py`, SQLAlchemy | Full SQLAlchemy URL. SQLite is the only tested path in MVP. Other DBs (Postgres) are possible but unvalidated. |
| `JWT_SECRET_KEY` | Yes | (no secure default) | `config.py` (auth not fully wired in MVP) | Long random string for JWT signing. Change for any non-local use. |
| `JWT_ALGORITHM` | Yes | `HS256` | JWT handling | Standard HMAC algorithm. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Yes | `60` | Token lifetime | Currently not heavily enforced in the demo UI. |
| `BACKEND_URL` | Yes | `http://127.0.0.1:8000` | `config.py`, smoke_test.py, CORS | Base URL of the FastAPI server (used in health responses and scripts). |
| `FRONTEND_URL` | Yes | `http://127.0.0.1:5173` | `config.py`, CORS | Base URL of the Vite dev server. |
| `CORS_ORIGINS` | Yes | Derived from FRONTEND_URL + localhost:5173 | FastAPI CORSMiddleware | Comma-separated list. Must include the exact origin the browser uses (including `http://127.0.0.1:5173`). |
| `UPLOAD_DIR` | Yes | `mvp_uploads` | `api.py`, `config.py` | Relative or absolute path for uploaded PDFs. Created automatically. |
| `GENERATED_REPORTS_DIR` | Yes | `output` | `pdf_generator.py`, `config.py`, StaticFiles mount | Where generated KSERC draft orders are written. Served at `/generated/`. |
| `DEMO_MODE` | Yes | `true` | `app.py`, health endpoint, UI banners | When `true`, the app runs in frictionless demo mode (auto-demo user, relaxed validations). Set `false` for stricter production-like behavior. |
| `PDF_ENGINE` | Yes | `reportlab` | `pdf_generator.py` | `reportlab` (default, reliable) or `playwright`. Playwright requires `python -m playwright install chromium` first. |
| `OCR_ENABLED` | Yes | `false` | `extractor.py` (future path) | Tesseract OCR for scanned PDFs. Only enable after installing Tesseract and adding to PATH. Most sample PDFs are text-extractable. |

---

## .env.example (Exact Content)

```env
# KSERC DSS MVP local environment
# Copy to .env before starting the backend:
#   Windows PowerShell: Copy-Item .env.example .env
#   macOS/Linux:        cp .env.example .env

# Required backend settings
DATABASE_URL=sqlite:///./data/kserc_dss.db
JWT_SECRET_KEY=local-dev-change-me-use-a-long-random-value
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
BACKEND_URL=http://127.0.0.1:8000
FRONTEND_URL=http://127.0.0.1:5173
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
UPLOAD_DIR=mvp_uploads
GENERATED_REPORTS_DIR=output
DEMO_MODE=true

# PDF processing
# reportlab is the reliable local default. playwright is optional if browsers
# have been installed with: python -m playwright install chromium
PDF_ENGINE=reportlab

# OCR is not used by the MVP default path. Set true only after installing
# Tesseract locally and adding it to PATH.
OCR_ENABLED=false
```

---

## Variables That Do NOT Exist (Important for Phase 2 Planning)

| Variable | Status | Reason |
|----------|--------|--------|
| `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` | **Not present** | No LLM is wired. `prompts.py` contains only deterministic string templates. |
| `LLM_ENABLED` | **Not present** | Phase 2 placeholder only. |
| `REDIS_URL`, `CELERY_BROKER` | **Not present** | No background task queue beyond FastAPI `BackgroundTasks`. |
| `S3_BUCKET`, `AWS_*` | **Not present** | Local filesystem only. |

See [17_PHASE_2_LLM_PLAN.md](17_PHASE_2_LLM_PLAN.md) for how these will be introduced safely.

---

## Validation Script

The canonical checker is:

```bash
python scripts/check_env.py
```

It fails fast with a clear list of missing variables before the uvicorn server starts.

---

## Common .env Mistakes

1. **Forgetting to copy `.env.example`** → `validate_required_environment()` raises `RuntimeError` on startup.
2. **CORS_ORIGINS not including `http://127.0.0.1:5173`** → Browser `fetch` fails with CORS error even though backend is healthy.
3. **Changing `PDF_ENGINE=playwright` without installing Chromium** → Import or runtime error in `pdf_generator.py`.
4. **Using Windows backslashes in paths** → Always use forward slashes or let the resolver in `config.py` handle it (`_resolve_path`).

---

**Treat this document as the contract between DevOps and the application.** Any new required variable must be added here, to `REQUIRED_ENV_VARS` in `config.py`, and to `.env.example` simultaneously.
