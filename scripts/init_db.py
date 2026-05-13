#!/usr/bin/env python
"""Create/update the local SQLite schema for the KSERC DSS MVP."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.config import validate_required_environment  # noqa: E402
from backend.database import SessionLocal, init_db  # noqa: E402
from sqlalchemy import text  # noqa: E402


REQUIRED_TABLES = {
    "documents",
    "extraction_jobs",
    "extracted_rows",
    "normalized_line_items",
    "comparisons",
    "reviews",
    "generated_orders",
}


def main() -> int:
    validate_required_environment()
    init_db()

    db = SessionLocal()
    try:
        rows = db.execute(text("SELECT name FROM sqlite_master WHERE type='table'")).fetchall()
        tables = {row[0] for row in rows}
    finally:
        db.close()

    missing = sorted(REQUIRED_TABLES - tables)
    if missing:
        print("Database initialized, but required tables are missing:")
        for table in missing:
            print(f"  - {table}")
        return 1

    print("Database schema is ready.")
    print("Tables:", ", ".join(sorted(REQUIRED_TABLES)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
