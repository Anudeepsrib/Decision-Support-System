# KSERC Decision Support System — Docker Setup

**Status:** Docker support is **intentionally not provided** for this MVP.

---

## Official Position

From the root [README.md](../README.md):

> "Docker is intentionally not part of this MVP setup. Run it directly on your computer."

The project contains:
- No `Dockerfile`
- No `docker-compose.yml`
- No `.dockerignore`
- No container-related scripts in `scripts/`

This decision was made to keep the developer experience simple and deterministic:
- One supported path (native Python venv + Node)
- No "works on my machine" container layer issues during demos
- Direct access to SQLite file, output PDFs, and logs without volume mapping complexity

---

## If You Still Want Docker (Not Recommended)

You would need to create your own:

1. Multi-stage Dockerfile (Python 3.12 slim + Node 20 for build)
2. Separate containers for backend (uvicorn) and frontend (nginx or serve)
3. Volume mounts for `data/`, `mvp_uploads/`, `output/`
4. Health checks on `/health`
5. Proper `.env` injection

This is left as an exercise for Phase 3 (production deployment).

---

## Current Reality Check

| Aspect | MVP State | Docker Impact |
|--------|-----------|---------------|
| Database | SQLite file at `data/kserc_dss.db` | Would require volume + permissions |
| PDF storage | `mvp_uploads/` and `output/` | Volume mounts required |
| PDF engines | ReportLab (easy) vs Playwright (needs Chromium in container) | Playwright container is heavy |
| Demo Mode | `DEMO_MODE=true` in .env | Easy to inject but not the point |
| Smoke test | `python scripts/smoke_test.py` | Would need container exec or service mesh |

---

## Recommendation

For stakeholder demos and development:
- Use the verified native setup in [03_LOCAL_SETUP.md](03_LOCAL_SETUP.md)
- The `scripts/setup_*.sh` and `scripts/setup_*.ps1` are the only supported automation

If a future production deployment requires containers (Kubernetes, ECS, etc.), that work belongs in Phase 3 and will be documented in the production runbook, not here.

---

**Bottom line:** Do not spend time debugging Docker for this MVP. The documented native path is the one that passes the smoke test and stakeholder demos reliably.
