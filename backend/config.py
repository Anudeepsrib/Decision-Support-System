"""
Runtime configuration for the local KSERC DSS MVP.

The app is intentionally local-first: SQLite is the default database and
all file paths resolve from the repository root unless an absolute path is
provided in the environment.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ENV_FILE = PROJECT_ROOT / ".env"

# Load .env when present. Scripts/check_env.py is responsible for telling a
# developer exactly what is missing before they start the server.
load_dotenv(ENV_FILE)


REQUIRED_ENV_VARS = (
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
)


def _bool_env(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(value: str | None) -> list[str]:
    if not value:
        return []
    return [part.strip() for part in value.split(",") if part.strip()]


def _resolve_path(value: str | None, default: str) -> Path:
    raw = value or default
    path = Path(raw)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def _sqlite_url_from_path(path: Path) -> str:
    return f"sqlite:///{path.as_posix()}"


def _resolve_database_url(value: str | None) -> str:
    raw = value or "sqlite:///./data/kserc_dss.db"
    if raw == "sqlite:///:memory:":
        return raw
    if not raw.startswith("sqlite:///"):
        return raw

    sqlite_path = raw.replace("sqlite:///", "", 1)
    path = Path(sqlite_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return _sqlite_url_from_path(path.resolve())


def _configured_values() -> dict[str, str | None]:
    return {name: os.getenv(name) for name in REQUIRED_ENV_VARS}


def missing_required_env(values: dict[str, str | None] | None = None) -> list[str]:
    values = values or _configured_values()
    return [name for name, value in values.items() if value is None or value.strip() == ""]


def validate_required_environment() -> None:
    missing = missing_required_env()
    if not missing:
        return

    names = ", ".join(missing)
    raise RuntimeError(
        "Missing required environment variables: "
        f"{names}. Copy .env.example to .env, update values if needed, "
        "then run `python scripts/check_env.py`."
    )


def _normalize_pdf_engine(value: str | None) -> str:
    engine = (value or "reportlab").strip().lower()
    if engine not in {"reportlab", "playwright"}:
        raise RuntimeError("PDF_ENGINE must be either 'reportlab' or 'playwright'.")
    return engine


@dataclass(frozen=True)
class Settings:
    database_url: str
    jwt_secret_key: str
    jwt_algorithm: str
    access_token_expire_minutes: int
    backend_url: str
    frontend_url: str
    cors_origins: list[str]
    upload_dir: Path
    generated_reports_dir: Path
    demo_mode: bool
    openai_api_key: str | None
    pdf_engine: str
    ocr_enabled: bool

    def ensure_directories(self) -> None:
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.generated_reports_dir.mkdir(parents=True, exist_ok=True)


def _build_settings() -> Settings:
    frontend_url = os.getenv("FRONTEND_URL", "http://127.0.0.1:5173")
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    cors_origins = _csv(os.getenv("CORS_ORIGINS")) or [
        frontend_url,
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    return Settings(
        database_url=_resolve_database_url(os.getenv("DATABASE_URL")),
        jwt_secret_key=os.getenv("JWT_SECRET_KEY", "local-dev-change-me"),
        jwt_algorithm=os.getenv("JWT_ALGORITHM", "HS256"),
        access_token_expire_minutes=int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60")),
        backend_url=backend_url,
        frontend_url=frontend_url,
        cors_origins=cors_origins,
        upload_dir=_resolve_path(os.getenv("UPLOAD_DIR"), "mvp_uploads"),
        generated_reports_dir=_resolve_path(os.getenv("GENERATED_REPORTS_DIR"), "output"),
        demo_mode=_bool_env(os.getenv("DEMO_MODE"), default=True),
        openai_api_key=os.getenv("OPENAI_API_KEY") or None,
        pdf_engine=_normalize_pdf_engine(os.getenv("PDF_ENGINE")),
        ocr_enabled=_bool_env(os.getenv("OCR_ENABLED"), default=False),
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return _build_settings()


def describe_missing(values: dict[str, str | None] | None = None) -> Iterable[str]:
    for name in missing_required_env(values):
        yield f"{name} is required"
