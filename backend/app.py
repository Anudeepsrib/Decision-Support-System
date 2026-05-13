"""
KSERC Decision Support System MVP application entry point.

Documented local command:
    python -m uvicorn backend.app:app --reload --port 8000
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

try:
    from .api import compat_router, router as api_router
    from .config import get_settings, validate_required_environment
    from .database import init_db
except ImportError:  # Support `cd backend && python -m uvicorn app:app`.
    from api import compat_router, router as api_router
    from config import get_settings, validate_required_environment
    from database import init_db


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
    validate_required_environment()
    settings.ensure_directories()
    init_db()

    # Demo data seeding disabled - only uploaded documents will be processed
    print("[MVP] Demo data seeding disabled - processing uploaded documents only")

    yield


app = FastAPI(
    title="KSERC Decision Support System — MVP",
    description=(
        "Demo-ready MVP for KSERC Truing-Up Order generation. "
        "Upload ARR orders and petition PDFs, extract financial tables, "
        "compare approved vs actual values, review flagged items, "
        "and generate KSERC-style draft orders."
    ),
    version="1.0.0-mvp",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# CORS - driven by .env so local ports are not hidden in code.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)
app.include_router(compat_router)

# Serve generated PDFs as static files
settings.generated_reports_dir.mkdir(parents=True, exist_ok=True)
app.mount("/generated", StaticFiles(directory=settings.generated_reports_dir), name="generated")


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "KSERC Decision Support System",
        "version": "1.0.0-mvp",
        "mode": "demo",
        "status": "operational",
        "docs": "/docs",
        "features": [
            "pdf_upload",
            "table_extraction",
            "variance_comparison",
            "officer_review",
            "pdf_generation",
            "audit_trail",
        ],
    }


@app.get("/health", tags=["Health"])
async def health():
    return {
        "status": "healthy",
        "mode": "demo" if settings.demo_mode else "local",
        "database": "configured",
        "upload_dir": str(settings.upload_dir),
        "generated_reports_dir": str(settings.generated_reports_dir),
        "pdf_engine": settings.pdf_engine,
    }
