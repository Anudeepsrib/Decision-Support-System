"""
MVP database configuration.

SQLite is the default local database. DATABASE_URL can still point at a
SQLAlchemy-supported database, but the documented developer path uses SQLite.
"""

from sqlalchemy import text
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

try:
    from .config import get_settings
except ImportError:  # Support direct imports from the backend directory.
    from config import get_settings


settings = get_settings()
DATABASE_URL = settings.database_url

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)
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
    try:
        from .models import Base  # noqa: F811
    except ImportError:
        from models import Base  # noqa: F811

    settings.ensure_directories()
    if DATABASE_URL.startswith("sqlite"):
        db_path = DATABASE_URL.replace("sqlite:///", "", 1)
        if db_path != ":memory:":
            from pathlib import Path

            Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_schema()
    print(f"[MVP] Database initialized at {DATABASE_URL}")


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

        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_norm_canonical_doc_type "
            "ON normalized_line_items (canonical_name, source_doc_type, financial_year)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_norm_extracted_row "
            "ON normalized_line_items (extracted_row_id)"
        ))
        conn.execute(text(
            "CREATE INDEX IF NOT EXISTS ix_extracted_doc_value_type "
            "ON extracted_rows (document_id, value_type)"
        ))
