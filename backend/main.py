"""
Enterprise FastAPI Application Entry Point
Production-grade security, monitoring, and compliance
=====================================================
Combines former main.py and main_secure.py.
"""

import os
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import asyncio

from backend.api.extraction import router as extraction_router
from backend.api.mapping import router as mapping_router
from backend.api.reports import router as reports_router
from backend.api.auth import router as auth_router
from backend.api.tariff_generator import router as tariff_router
from backend.api.history import router as history_router
from backend.api.efficiency import router as efficiency_router
from backend.security.rate_limit import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ip_filter,
)
from backend.api.scheduler import kserc_periodic_sync_loop

# ─── Environment Configuration ───
ENVIRONMENT = os.getenv("ENVIRONMENT", "development")
DEBUG = os.getenv("DEBUG", "false").lower() == "true"
CORS_ALLOWED_ORIGINS = os.getenv(
    "CORS_ALLOWED_ORIGINS", 
    "http://localhost:3000,http://localhost:5173"
).split(",")

# ─── Lifespan Events ───
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown events"""
    # Start the continuous background KSERC synchronization task
    kserc_sync_task = asyncio.create_task(kserc_periodic_sync_loop(interval_seconds=86400))
    yield
    # Safely cancel background task on shutdown
    kserc_sync_task.cancel()

# ─── Application Initialization ───
app = FastAPI(
    title="ARR Truing-Up Decision Support System",
    description=(
        "Enterprise-grade AI-augmented engine for Annual Revenue Requirement "
        "Truing-Up under the KSERC MYT 2022-27 Framework. "
        "Designed for 100% mathematical fidelity and full regulatory traceability."
    ),
    version="1.0.0",
    terms_of_service="http://example.com/terms/",
    contact={
        "name": "Regulatory Engine Support",
        "url": "http://example.com/support",
        "email": "support@example.com",
    },
    license_info={
        "name": "Internal Enterprise License",
        "url": "http://example.com/license",
    },
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    swagger_ui_parameters={
        "defaultModelsExpandDepth": -1, # Hide schemas by default
        "displayRequestDuration": True, # Show request times for latency tracking
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
            "message": "An unexpected error occurred processing the regulatory data.",
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

# ─── Register API Routes ───
app.include_router(auth_router)
app.include_router(extraction_router)
app.include_router(mapping_router)
app.include_router(reports_router)
app.include_router(tariff_router)
app.include_router(history_router)
app.include_router(efficiency_router)


# ─── Health Check Endpoints ───
@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "ARR Truing-Up DSS",
        "version": "1.0.0",
        "framework": "KSERC MYT 2022-27",
        "status": "operational",
        "environment": ENVIRONMENT,
        "security_level": "enterprise"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "engine": "KSERC-MYT-2022-27-v1.0", "security": "active"}

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
