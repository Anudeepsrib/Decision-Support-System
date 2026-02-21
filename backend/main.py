"""
DEVELOPMENT ENTRY POINT — main.py
=====================================
⚠️  This is the minimal development server. Swagger is always-on and there is
    no authentication, rate-limiting, or security middleware.

For any real usage (demo, staging, production), use main_secure.py instead:
    uvicorn backend.main_secure:app --reload --port 8000

main_secure.py adds: JWT auth, RBAC, rate-limiting, security headers,
                     environment-gated Swagger, and lifespan hooks.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.extraction import router as extraction_router
from backend.api.mapping import router as mapping_router
from backend.api.reports import router as reports_router

app = FastAPI(
    title="ARR Truing-Up Decision Support System",
    description=(
        "Production-grade AI-augmented engine for Annual Revenue Requirement "
        "Truing-Up under the KSERC MYT 2022-27 Framework. "
        "Designed for 100% mathematical fidelity and full regulatory traceability."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register API routes
app.include_router(extraction_router)
app.include_router(mapping_router)
app.include_router(reports_router)


@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "ARR Truing-Up DSS",
        "version": "1.0.0",
        "framework": "KSERC MYT 2022-27",
        "status": "operational"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "engine": "KSERC-MYT-2022-27-v1.0"}
