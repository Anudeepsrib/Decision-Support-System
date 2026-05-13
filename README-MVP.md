# KSERC DSS MVP Local Setup

The MVP setup is local-only. Docker files were removed so developers have one supported path:

```bash
cp .env.example .env
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python scripts/init_db.py
python -m uvicorn backend.app:app --reload --port 8000
```

In a second terminal:

```bash
cd frontend
npm ci
npm start
```

See `README.md` for the complete setup, PDF dependency notes, troubleshooting, and smoke-test commands.
