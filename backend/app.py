"""
KSERC Decision Support System — MVP Application Entry Point.

A clean, demo-ready FastAPI application with zero external dependencies
beyond SQLite and pdfplumber.

Run with:
    cd backend && python -m uvicorn mvp.app:app --reload --port 8000
"""

import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager

from database import init_db
from api import router as api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database on startup."""
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

# CORS — allow frontend dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://localhost:3000",
        "http://localhost:4173",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(api_router)

# Serve generated PDFs as static files
GENERATED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "output")
os.makedirs(GENERATED_DIR, exist_ok=True)
app.mount("/generated", StaticFiles(directory=GENERATED_DIR), name="generated")


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
    return {"status": "healthy", "mode": "mvp-demo"}
