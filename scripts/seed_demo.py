#!/usr/bin/env python
"""Seed deterministic local demo data."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import validate_required_environment  # noqa: E402
from backend.database import init_db  # noqa: E402
from backend.seed_data import seed_demo_data  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Seed demo data for local development.")
    parser.add_argument("--reset", action="store_true", help="Clear existing MVP data before seeding.")
    args = parser.parse_args()

    validate_required_environment()
    init_db()
    case_id = seed_demo_data(clear=args.reset)
    print(f"Demo data ready. Case ID: {case_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
