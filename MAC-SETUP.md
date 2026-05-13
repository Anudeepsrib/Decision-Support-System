# macOS Local Setup

The MVP runs directly on your Mac. Use the root `README.md` for the complete guide.

## Quick Setup

```bash
git clone <repository-url>
cd Decision-Support-System
bash setup-mac.sh
bash start-mvp-mac.sh
```

## Manual Commands

```bash
cp .env.example .env
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python scripts/init_db.py
```

Terminal 1:

```bash
source .venv/bin/activate
python -m uvicorn backend.app:app --reload --port 8000
```

Terminal 2:

```bash
cd frontend
npm ci
npm start
```

## Notes

- Use Python 3.11 or newer.
- Use Node.js 20 or 22.
- ReportLab is the default PDF engine and does not require Homebrew PDF libraries.
- OCR is disabled by default. Install Tesseract only if you later set `OCR_ENABLED=true`.
