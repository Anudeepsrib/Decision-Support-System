"""
MVP Database Configuration — SQLite for zero-config demo.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# SQLite for MVP — zero external dependencies
DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mvp_demo.db")
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
    from backend.mvp.models import Base  # noqa: F811
    Base.metadata.create_all(bind=engine)
    print(f"[MVP] Database initialized at {DB_PATH}")
