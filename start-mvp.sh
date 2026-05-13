#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

if [ ! -d ".venv" ]; then
  bash scripts/setup_backend.sh
fi

if [ ! -d "frontend/node_modules" ]; then
  bash scripts/setup_frontend.sh
fi

source .venv/bin/activate

BACKEND_PID=""
FRONTEND_PID=""

python -m uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!

cleanup() {
  if [ -n "$BACKEND_PID" ]; then kill "$BACKEND_PID" 2>/dev/null || true; fi
  if [ -n "$FRONTEND_PID" ]; then kill "$FRONTEND_PID" 2>/dev/null || true; fi
}
trap cleanup EXIT INT TERM

cd frontend
npm start &
FRONTEND_PID=$!

echo "Backend:  http://127.0.0.1:8000"
echo "Frontend: http://127.0.0.1:5173"
echo "API docs: http://127.0.0.1:8000/docs"
wait
