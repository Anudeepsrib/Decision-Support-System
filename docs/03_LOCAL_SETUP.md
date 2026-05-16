# KSERC Decision Support System — Local Setup (Verified Commands)

**Target:** Fresh clone → running instance in < 10 minutes on Windows/macOS/Linux

**Important:** Docker is intentionally **not** supported in this MVP. Use the native Python + Node path below.

---

## Prerequisites (Exact Versions)

| Component | Required Version | Notes |
|-----------|------------------|-------|
| Python | 3.11, 3.12, or 3.13 | `python --version` |
| Node.js | 20.x or 22.x | `node --version` (npm 10+) |
| Git | Any recent | `git --version` |
| Terminal | 2 tabs/windows | One for backend, one for frontend |

Optional (only if you later enable features):
- Tesseract (for `OCR_ENABLED=true`)
- `python -m playwright install chromium` (only if `PDF_ENGINE=playwright`)

---

## Step 1: Clone and Enter Directory

```bash
git clone <repository-url>
cd Decision-Support-System
```

On Windows PowerShell:
```powershell
git clone <repository-url>
cd Decision-Support-System
```

---

## Step 2: Backend Setup (from project root)

### Automated (recommended)
**Windows PowerShell:**
```powershell
.\scripts\setup_backend.ps1
```

**macOS / Linux:**
```bash
bash scripts/setup_backend.sh
```

### Manual (exact commands)

```bash
# 1. Create virtual environment (from project root)
python -m venv .venv

# 2. Activate
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
# macOS/Linux:
source .venv/bin/activate

# 3. Upgrade pip and install dependencies
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

# 4. Create .env from template
# Windows:
Copy-Item .env.example .env
# macOS/Linux:
cp .env.example .env

# 5. Validate environment (critical)
python scripts/check_env.py

# 6. Initialize database (creates tables)
python scripts/init_db.py
```

**Expected output from `check_env.py`:**
```
All required environment variables are present.
```

**Expected output from `init_db.py`:**
```
[MVP] Database initialized at sqlite:///./data/kserc_dss.db
```

---

## Step 3: Frontend Setup

```bash
cd frontend
npm ci
cd ..
```

`npm ci` is preferred over `npm install` for reproducible builds in CI and demos.

---

## Step 4: Start the Services (Two Terminals)

### Terminal 1 — Backend (from project root)

```bash
# With venv activated
python -m uvicorn backend.app:app --reload --port 8000
```

**Do not run** `uvicorn main:app` — there is no `main.py`. The entrypoint is `backend.app:app`.

**Health check (in browser or curl):**
```
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs   (FastAPI Swagger UI)
```

### Terminal 2 — Frontend (from project root)

```bash
cd frontend
npm start
```

Vite will start on `http://127.0.0.1:5173` (hard-coded in `vite.config.ts`).

---

## Step 5: Verify End-to-End Smoke Test

With both services running, from a third terminal (or in the backend venv):

```bash
python scripts/smoke_test.py
```

The smoke test performs the full workflow against the sample PDFs:
- `arr_order_test.pdf`
- `petition_test.pdf`

It exercises:
1. `POST /upload/arr`
2. `POST /upload/petition`
3. `POST /comparison/run`
4. `GET /comparison/results`
5. `POST /report/generate`
6. `GET /report/{order_id}` (download)

**Expected:** "Report generated: <order_id> (<size> bytes)" with exit code 0.

---

## URLs Summary

| Service | URL | Purpose |
|---------|-----|---------|
| Frontend UI | http://127.0.0.1:5173 | Main demo interface |
| Backend Health | http://127.0.0.1:8000/health | JSON health + mode |
| API Docs (Swagger) | http://127.0.0.1:8000/docs | Interactive API explorer |
| Generated PDFs | http://127.0.0.1:8000/generated/<filename> | Static file serving |
| Smoke Test | `python scripts/smoke_test.py` | Automated end-to-end |

---

## Database Reset (if needed)

```bash
# Windows PowerShell
Remove-Item data\kserc_dss.db -ErrorAction SilentlyContinue
python scripts\init_db.py

# macOS/Linux
rm -f data/kserc_dss.db
python scripts/init_db.py
```

---

## Optional: Seed Demo Data (Disabled by Default)

The application intentionally disables auto-seeding in `app.py` lifespan. If you want deterministic demo rows:

```bash
python scripts/seed_demo.py --reset
```

Most users should upload the real sample PDFs instead.

---

## Frontend Environment Override (Advanced)

If you need to point the frontend at a different backend (e.g., different port or remote host), create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
```

The frontend code in `App.tsx` automatically strips trailing slashes and ensures the `/api` suffix.

---

## Common First-Run Issues (Quick Fixes)

| Symptom | Fix |
|---------|-----|
| `Missing required environment variables` | Run `python scripts/check_env.py` after copying `.env.example` |
| `No module named 'backend'` | Run uvicorn command from the **project root**, not inside `backend/` |
| Frontend cannot reach backend | Confirm `CORS_ORIGINS` in `.env` includes `http://127.0.0.1:5173` |
| PDF upload fails | Only `.pdf` files ≤ 75 MB are accepted |
| ReportLab PDF looks wrong | Keep `PDF_ENGINE=reportlab` (default). Do not switch to playwright without installing Chromium |

---

## Next Steps After Successful Start

1. Open http://127.0.0.1:5173
2. Upload `arr_order_test.pdf` (ARR tab)
3. Upload `petition_test.pdf` (Petition tab)
4. Go to Extraction tab → Run Comparison
5. Review the comparison table (SBU-D items should be populated)
6. Click Generate PDF
7. Download and open the draft order

For a full stakeholder demo script with honest coverage language, see [15_DEMO_SCRIPT.md](15_DEMO_SCRIPT.md).

---

**This document is the single source of truth for "how do I run the MVP locally?"** All other documents reference these exact commands.
