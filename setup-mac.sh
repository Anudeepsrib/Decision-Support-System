#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT_DIR"

bash scripts/setup_backend.sh
bash scripts/setup_frontend.sh

echo "Local setup complete. Start with bash start-mvp.sh"
