# Regulatory Decision Support System

**Configurable, deterministic system for generating regulatory truing-up draft orders from uploaded ARR Order and Truing-Up Petition PDFs.**

This system performs **end-to-end deterministic processing**:
- PDF upload (ARR Order + Petition)
- pdfplumber-based table extraction with target table detection
- Canonical mapping via rule-based registry (no LLM)
- Variance comparison (15% threshold)
- Officer review workflow
- KSERC-style draft order PDF generation (ReportLab, templates, no LLM)

**This MVP currently generates deterministic KSERC-style draft orders from mapped canonical comparison rows. LLM-based narrative generation is planned for Phase 2 and is not currently wired into the system.**

KSERC remains the included reference profile. Application identity, regulator, utility,
case prefix, reporting year, and output filename can be changed through environment
variables without modifying Python or TypeScript code.

SBU-D mapping is substantive for the included sample PDFs. SBU-G, SBU-T, Energy/T&D, and Common Expenses coverage depends on whether the uploaded PDFs contain tables whose captions match the deterministic `TARGET_TABLE_CATALOG`. Missing chapters are reported transparently.

Docker is intentionally not part of this MVP setup. Run it directly on your computer.

---

## Full Documentation Suite

All technical, setup, API, architecture, testing, demo, limitations, Phase 2 LLM safety plan, and roadmap details live in the `/docs` folder.

**Start here:**
- New developers → [docs/03_LOCAL_SETUP.md](docs/03_LOCAL_SETUP.md)
- Architecture & reviewers → [docs/02_ARCHITECTURE.md](docs/02_ARCHITECTURE.md)
- Demo presenters → [docs/15_DEMO_SCRIPT.md](docs/15_DEMO_SCRIPT.md)
- Phase 2 engineers → [docs/17_PHASE_2_LLM_PLAN.md](docs/17_PHASE_2_LLM_PLAN.md)
- Complete index → [docs/README.md](docs/README.md)

---

## Prerequisites

- Python 3.11, 3.12, or 3.13
- Node.js 20 or 22 with npm 10+
- Git
- A terminal with two tabs/windows

Optional PDF tools:

- Tesseract is only needed if you later enable OCR with `OCR_ENABLED=true`.
- Camelot/Ghostscript are not required for the default workflow. The extractor uses `pdfplumber` first and only uses Camelot if you install it yourself.
- ReportLab is the default PDF report engine. Playwright is optional; if you set `PDF_ENGINE=playwright`, also run `python -m playwright install chromium`.

## Quick Start

### Windows PowerShell

```powershell
git clone <repository-url>
cd Decision-Support-System

.\scripts\setup_backend.ps1
.\scripts\setup_frontend.ps1
```

Terminal 1:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.app:app --reload --port 8000
```

Terminal 2:

```powershell
cd frontend
npm start
```

### macOS/Linux

```bash
git clone <repository-url>
cd Decision-Support-System

bash scripts/setup_backend.sh
bash scripts/setup_frontend.sh
```

Terminal 1:

```bash
source .venv/bin/activate
python -m uvicorn backend.app:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm start
```

Open:

- Frontend: http://127.0.0.1:5173
- Backend health: http://127.0.0.1:8000/health
- API docs: http://127.0.0.1:8000/docs

## Environment Variables

The backend requires a `.env` file. The setup scripts create it from `.env.example` if it is missing.

Manual copy:

```bash
cp .env.example .env
```

Windows:

```powershell
Copy-Item .env.example .env
```

Required variables:

```env
APP_NAME=Regulatory Decision Support System
REGULATOR_NAME=Kerala State Electricity Regulatory Commission
REGULATOR_SHORT_NAME=KSERC
UTILITY_NAME=Kerala State Electricity Board Limited
UTILITY_ADDRESS=Vydhyuthi Bhavanam|Pattom, Thiruvananthapuram
COMMISSION_PLACE=Thiruvananthapuram
COMMISSION_MEMBERS=Shri T K Jose, Chairman|Adv. A.J Wilson, Member|Shri B Pradeep, Member
CONDUCT_REGULATION_NAME=KSERC (Conduct of Business) Regulations, 2003
REGULATION_NAME=KSERC (Terms and Conditions for Determination of Tariff) Regulations, 2021
CASE_ID_PREFIX=regulatory
DEFAULT_FINANCIAL_YEAR=2024-25
REPORT_FILENAME_PREFIX=Regulatory_TruingUp
DATABASE_URL=sqlite:///./data/regulatory_dss.db
JWT_SECRET_KEY=local-dev-change-me-use-a-long-random-value
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
BACKEND_URL=http://127.0.0.1:8000
FRONTEND_URL=http://127.0.0.1:5173
CORS_ORIGINS=http://127.0.0.1:5173,http://localhost:5173
UPLOAD_DIR=mvp_uploads
GENERATED_REPORTS_DIR=output
DEMO_MODE=true
PDF_ENGINE=reportlab
OCR_ENABLED=false
```

Validate the file:

```bash
python scripts/check_env.py
```

## Database Setup

The MVP uses local SQLite by default. Alembic is not used in this MVP; schema creation and small additive migration guards live in `backend/database.py`.

Create or update the schema:

```bash
python scripts/init_db.py
```

Required tables created:

- `documents`
- `extraction_jobs`
- `extracted_rows`
- `normalized_line_items`
- `comparisons`
- `reviews`
- `generated_orders`

Clean reset:

```bash
rm -f data/regulatory_dss.db
python scripts/init_db.py
```

Windows:

```powershell
Remove-Item data\regulatory_dss.db -ErrorAction SilentlyContinue
python scripts\init_db.py
```

Optional deterministic demo data:

```bash
python scripts/seed_demo.py --reset
```

## Backend Setup

Install:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/check_env.py
python scripts/init_db.py
```

Windows activation:

```powershell
.\.venv\Scripts\Activate.ps1
```

Start backend from the repository root:

```bash
python -m uvicorn backend.app:app --reload --port 8000
```

Do not start with `uvicorn main:app`; there is no `main.py` entrypoint.

## Frontend Setup

Install:

```bash
cd frontend
npm ci
```

Start:

```bash
npm start
```

The frontend defaults to `http://127.0.0.1:8000/api`. To override it, create `frontend/.env.local`:

```env
VITE_API_BASE_URL=http://127.0.0.1:8000/api
VITE_APP_NAME=Regulatory Decision Support System
VITE_REGULATOR_SHORT_NAME=KSERC
VITE_DEFAULT_FINANCIAL_YEAR=2024-25
```

Build check:

```bash
cd frontend
npm run build
```

Backend test setup and run:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

## Demo Workflow

Use the sample PDFs in the repository root:

- `samples/arr_order_test.pdf`
- `samples/petition_test.pdf`

UI flow:

1. Open http://127.0.0.1:5173.
2. Upload `samples/arr_order_test.pdf` on the ARR Upload tab.
3. Wait for extraction to complete.
4. Upload `samples/petition_test.pdf` on the Petition Upload tab.
5. Wait for extraction to complete.
6. Open Extraction and click Run Comparison.
7. Review the comparison rows.
8. Click Generate PDF.
9. Preview or download the generated draft PDF.

API smoke test against a running backend:

```bash
python scripts/smoke_test.py
```

The smoke test calls:

- `GET /health`
- `POST /upload/arr`
- `POST /upload/petition`
- `POST /comparison/run`
- `GET /comparison/results`
- `POST /report/generate`
- `GET /report/{id}`

## Project Structure

```text
backend/                FastAPI app, SQLAlchemy models, extraction, comparison, PDF generation
frontend/               Vite + React + TypeScript UI
scripts/                Local setup, env check, DB init, seed, smoke test scripts
tests/                  Automated backend and report checks
samples/                Example ARR and petition PDFs
data/                   Local SQLite DB location
mvp_uploads/            Uploaded PDFs, created automatically
output/                 Generated PDF reports, created automatically
requirements.txt        Python dependencies
.env.example            Required local configuration template
```

## Troubleshooting

Backend says `.env` variables are missing:

```bash
cp .env.example .env
python scripts/check_env.py
```

Backend cannot import `backend.app`:

```bash
python -m uvicorn backend.app:app --reload --port 8000
```

Run the command from the repository root, not from inside `backend`.

Database errors or missing tables:

```bash
python scripts/init_db.py
```

Frontend cannot reach backend:

- Confirm backend is running at http://127.0.0.1:8000/health.
- Confirm `CORS_ORIGINS` includes `http://127.0.0.1:5173`.
- If you changed ports, update `BACKEND_URL`, `FRONTEND_URL`, and `frontend/.env.local`.

PDF upload fails:

- Only `.pdf` files are accepted.
- Max upload size is 75 MB.
- Scanned PDFs may need OCR; OCR is disabled by default.

Report generation fails:

- Keep `PDF_ENGINE=reportlab` for the simplest local path.
- If using Playwright, install Chromium with `python -m playwright install chromium`.

## Useful Commands

```bash
python scripts/check_env.py
python scripts/init_db.py
python scripts/seed_demo.py --reset
python -m uvicorn backend.app:app --reload --port 8000
cd frontend && npm start
python scripts/smoke_test.py
cd frontend && npm run build
```
