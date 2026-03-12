"""
Enterprise FastAPI Application Entry Point
Production-grade security, monitoring, and compliance
=====================================================
Refactored: Non-comparison features commented out.
Focus: Document Comparison & Anomaly Detection only.
"""

import os
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import asyncio

# ─── Active Routers (Comparison + Auth) ───
from backend.api.auth import router as auth_router
from backend.api.order_comparison import router as comparison_router

# ─── Commented Out: Non-comparison features ───
# from backend.api.extraction import router as extraction_router
# from backend.api.mapping import router as mapping_router
# from backend.api.reports import router as reports_router
# from backend.api.tariff_generator import router as tariff_router
# from backend.api.history import router as history_router
# from backend.api.efficiency import router as efficiency_router
# from backend.api.scheduler import kserc_periodic_sync_loop

from backend.security.rate_limit import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ip_filter,
)

# ─── Environment Configuration ───
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5173,https://www.erckerala.org,https://erckerala.org"
).split(",")

# ─── Lifespan Events ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # KSERC sync commented out — not needed for comparison-only mode
    # kserc_sync_task = asyncio.create_task(kserc_periodic_sync_loop(interval_seconds=86400))
    yield
    # kserc_sync_task.cancel()

# ─── Application Initialization ───
app = FastAPI(
    title="Document Comparison & Anomaly Detection System",
    description=(
        "Deterministic order vs reference document comparison engine. "
        "Uses regex extraction, difflib similarity, and rule-based anomaly detection. "
        "No LLM required for comparison — LLM is optional for report generation only."
    ),
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1,
        "displayRequestDuration": True,
        "filter": True,
    },
    lifespan=lifespan,
)

# ─── Global Exception Handlers ───
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    Sanitize HTTP 500 Internal Server Errors to prevent stack-trace leakages.
    Log the traceback securely on the backend, return a uniform payload.
    """
    if DEBUG:
        print(f"Unhandled Error: {exc}")
        traceback.print_exc()

    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal Server Error",
            "message": "An unexpected error occurred.",
            "reference_id": request.headers.get("X-Request-ID", "unknown")
        }
    )

# ─── Security Middleware ───
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type", "X-Requested-With"],
    expose_headers=["X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
    max_age=600,
)

# ─── Register API Routes (Comparison + Auth only) ───
app.include_router(auth_router)
app.include_router(comparison_router)

# Commented out: Non-comparison routers
# app.include_router(extraction_router)
# app.include_router(mapping_router)
# app.include_router(reports_router)
# app.include_router(tariff_router)
# app.include_router(history_router)
# app.include_router(efficiency_router)


# ─── Health Check Endpoints ───
@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "Document Comparison & Anomaly Detection",
        "version": "2.0.0",
        "mode": "deterministic",
        "status": "operational",
        "environment": ENVIRONMENT,
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "engine": "deterministic-comparator-v2.0"}

@app.get("/security/status", tags=["Security"])
async def security_status():
    return {
        "security_features": {
            "authentication": "JWT with RBAC",
            "rate_limiting": "enabled",
            "brute_force_protection": "enabled",
            "security_headers": "enabled"
        },
        "environment": ENVIRONMENT
    }
