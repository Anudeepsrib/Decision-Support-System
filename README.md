<div align="center">
  <img src="frontend/public/compass-logo.png" alt="Compass logo" width="104" />
  <h1>Compass</h1>
  <p><strong>Open-source decision records for teams.</strong></p>
  <p>Compare options, weigh evidence, share a workspace, and preserve why a decision was made.</p>
</div>

## Why Compass

Important decisions disappear into meetings, spreadsheets, and chat threads. Compass gives product, engineering, operations, and leadership teams a durable record of the options considered, evidence reviewed, scorecard used, and final rationale.

Start locally without an account. When a team is ready, create a bearer-protected shared workspace and sync explicitly. Optional Jev review checks whether the record is ready for human judgment. It never chooses an option.

## What it does

- Configurable weighted criteria with honest 1 to 5 scoring
- Build vs. Buy, Vendor, Technology, Hiring, and Market templates
- Evidence links, final rationale, review dates, search, and mobile layouts
- Validated JSON import plus JSON and Markdown export
- Shared workspaces with hashed access tokens and conflict-safe revisions
- LangGraph persistence for review runs
- One typed Jev call for readiness, review focus, and unsupported-evidence probability
- Docker image serving the React app and Python API together

## Run locally

Requirements: Node 22 and Python 3.10 or newer.

```powershell
py -m venv .venv
.venv\Scripts\pip install -r backend\requirements.txt
.venv\Scripts\uvicorn backend.app:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL printed by Vite. Sharing works immediately. Add `TYPESAFE_API_KEY` to your environment to enable Jev readiness checks. The default model is `jev-latest` and can be changed with `TYPESAFE_DEFAULT_MODEL`.

## Docker

Copy `.env.example` to `.env`, add the TypeSafe key if wanted, then run:

```bash
docker compose up --build
```

Open `http://localhost:8000`. Workspace and LangGraph SQLite data persist in the `compass-data` volume.

## How the backend works

The FastAPI service stores workspaces in SQLite. A workspace token is returned once, stored only as a hash on the server, and required as a bearer token for reads and writes. Every update includes its last seen revision; stale writes receive HTTP 409 instead of overwriting a teammate's work.

The review graph has two deliberately small nodes:

1. Compute completion facts such as scored cells and evidence count.
2. Ask Jev typed `Score`, `Choice`, and `Noul` questions in one `system_one` call.

LangGraph checkpoints each run under a unique thread ID. The response always states that a human decision is required. Jev receives the full selected decision record, so enable it only when that data may be sent to the configured TypeSafe endpoint.

API documentation is available at `http://localhost:8000/docs` while the server is running. Configuration is documented in `.env.example`.

## Checks

```powershell
cd frontend
npm test
npm run build

cd ..
.venv\Scripts\python -m unittest backend.test_app
```

The backend check covers authenticated create, read, update, stale-write rejection, deterministic graph preparation, and the human-decision guard without spending a Jev API call.

## Deployment boundary

The included SQLite storage is a simple self-hosted setup for one application instance. Move workspaces and LangGraph checkpoints to PostgreSQL before running multiple instances or serving large organizations. Put the service behind TLS and rate limiting for public deployments.

## Project layout

- `frontend/`: React and TypeScript product UI
- `backend/app.py`: FastAPI, SQLite storage, LangGraph, and Jev integration
- `backend/test_app.py`: focused backend and workflow check
- `Dockerfile` and `compose.yaml`: one-command deployment

## Contributing

Read [CONTRIBUTING.md](CONTRIBUTING.md). Security reports belong in private GitHub advisories as described in [SECURITY.md](SECURITY.md).

Apache-2.0 licensed. If Compass helps your team make better decisions, star the repository and share the workflow you use it for.
