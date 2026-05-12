"""
MVP Database Configuration — SQLite for zero-config demo.
"""

import os
from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite for MVP — zero external dependencies
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kserc_dss.db")
DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency for database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables."""
    from models import Base  # noqa: F811
    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema()
    print(f"[MVP] Database initialized at {DB_PATH}")


def _ensure_sqlite_schema():
    """Apply tiny additive migrations needed by the MVP SQLite database."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    additions = {
        "extracted_rows": [
            ("value_type", "VARCHAR(20) NOT NULL DEFAULT 'value'"),
        ],
        "normalized_line_items": [
            ("value_type", "VARCHAR(20)"),
        ],
        "comparisons": [
            ("approved_source_document_id", "VARCHAR(36)"),
            ("actual_source_document_id", "VARCHAR(36)"),
            ("claimed_source_document_id", "VARCHAR(36)"),
            ("claimed_source_page", "INTEGER"),
            ("approved_source_table", "VARCHAR(200)"),
            ("actual_source_table", "VARCHAR(200)"),
            ("claimed_source_table", "VARCHAR(200)"),
            ("approved_confidence", "FLOAT"),
            ("actual_confidence", "FLOAT"),
            ("claimed_confidence", "FLOAT"),
        ],
    }

    with engine.begin() as conn:
        for table_name, columns in additions.items():
            existing = {
                row[1]
                for row in conn.execute(text(f"PRAGMA table_info({table_name})")).fetchall()
            }
            for column_name, ddl in columns:
                if column_name not in existing:
                    conn.execute(text(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {ddl}"))
