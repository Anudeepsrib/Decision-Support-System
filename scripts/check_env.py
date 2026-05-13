#!/usr/bin/env python
"""Validate the local .env file required by the backend."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ENV_FILE = ROOT / ".env"
ENV_EXAMPLE = ROOT / ".env.example"

REQUIRED = [
    "DATABASE_URL",
    "JWT_SECRET_KEY",
    "JWT_ALGORITHM",
    "ACCESS_TOKEN_EXPIRE_MINUTES",
    "BACKEND_URL",
    "FRONTEND_URL",
    "CORS_ORIGINS",
    "UPLOAD_DIR",
    "GENERATED_REPORTS_DIR",
    "DEMO_MODE",
    "PDF_ENGINE",
    "OCR_ENABLED",
]


def parse_env(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    if not ENV_FILE.exists():
        print("Missing .env file.")
        print("Create it with one of these commands:")
        print("  Windows PowerShell: Copy-Item .env.example .env")
        print("  macOS/Linux:        cp .env.example .env")
        return 1

    values = parse_env(ENV_FILE)
    missing = [key for key in REQUIRED if not values.get(key)]
    if missing:
        print("Missing required environment variables:")
        for key in missing:
            print(f"  - {key}")
        print(f"Use {ENV_EXAMPLE} as the source of truth.")
        return 1

    if values["PDF_ENGINE"].lower() not in {"reportlab", "playwright"}:
        print("PDF_ENGINE must be either 'reportlab' or 'playwright'.")
        return 1

    if "change-me" in values["JWT_SECRET_KEY"].lower():
        print("Warning: JWT_SECRET_KEY is using the local placeholder value.")

    print("Environment check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
