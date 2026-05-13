.PHONY: help setup backend frontend init-db seed smoke test clean

PYTHON ?= python
VENV_PYTHON := .venv/bin/python

help:
	@echo "KSERC DSS MVP local commands"
	@echo "  make setup     Install backend/frontend dependencies and initialize DB"
	@echo "  make backend   Start FastAPI on http://127.0.0.1:8000"
	@echo "  make frontend  Start Vite on http://127.0.0.1:5173"
	@echo "  make init-db   Create/update local SQLite schema"
	@echo "  make seed      Seed deterministic demo data"
	@echo "  make smoke     Run API smoke test against a running backend"
	@echo "  make test      Run backend import checks and frontend build"
	@echo "  make clean     Remove local generated state"

setup:
	bash scripts/setup_backend.sh
	bash scripts/setup_frontend.sh

backend:
	. .venv/bin/activate && python -m uvicorn backend.app:app --reload --port 8000

frontend:
	cd frontend && npm start

init-db:
	. .venv/bin/activate && python scripts/init_db.py

seed:
	. .venv/bin/activate && python scripts/seed_demo.py --reset

smoke:
	. .venv/bin/activate && python scripts/smoke_test.py

test:
	. .venv/bin/activate && python -c "import backend.app; print('backend import ok')"
	cd frontend && npm run build

clean:
	rm -rf .venv frontend/node_modules frontend/dist data/kserc_dss.db
	rm -rf output/* mvp_uploads/*
