"""
Enterprise FastAPI Application Entry Point
Production-grade AI + Human-in-the-Loop Regulatory Decision Support System
============================================================================
KSERC Truing-Up Order Generation with full auditability and compliance.
"""

import os
import traceback
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import asyncio

# ─── Active Routers ───
from backend.api.auth import router as auth_router
from backend.api.order_comparison import router as comparison_router
from backend.api.mapping import router as mapping_router
from backend.api.manual_decisions import router as manual_decisions_router
from backend.api.order_generator import router as order_generator_router
from backend.api.history import router as history_router
from backend.api.extraction import router as extraction_router
from backend.api.reports import router as reports_router
from backend.api.efficiency import router as efficiency_router
from backend.api.tariff_generator import router as tariff_router

# ─── Security Middleware ───
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
    from backend.models.database import init_db
    init_db()
    
    # Seed demo data if in demo mode
    try:
        from backend.scripts.seed_demo_data import seed_demo_data_if_needed
        seed_demo_data_if_needed()
    except Exception as e:
        print(f"Warning: Demo data seeding failed: {e}")
    
    yield

# ─── Application Initialization ───
app = FastAPI(
    title="KSERC Truing-Up Decision Support System",
    description=(
        "AI + Human-in-the-Loop regulatory decision system for KSERC Truing-Up Order generation. "
        "Features: Document comparison, AI-assisted analysis, manual officer overrides, "
        "audit logging, and KSERC-compliant order generation with embedded justifications."
    ),
    version="3.0.0",
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
    if isinstance(exc, HTTPException):
        from starlette.responses import JSONResponse
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
            headers=getattr(exc, "headers", None)
        )

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

# ─── Register API Routes ───
app.include_router(auth_router)
app.include_router(comparison_router)
app.include_router(mapping_router)
app.include_router(manual_decisions_router)
app.include_router(order_generator_router)
app.include_router(history_router)
app.include_router(extraction_router)
app.include_router(reports_router)
app.include_router(efficiency_router)
app.include_router(tariff_router)


# ─── Health Check Endpoints ───
@app.get("/", tags=["Health"])
async def root():
    return {
        "service": "KSERC Truing-Up Decision Support System",
        "version": "3.0.0",
        "mode": "ai-human-in-the-loop",
        "status": "operational",
        "environment": ENVIRONMENT,
        "features": [
            "document_comparison",
            "ai_decision_support",
            "manual_override",
            "kserc_order_generation",
            "audit_trail"
        ]
    }


@app.get("/health", tags=["Health"])
async def health_check():
    return {
        "status": "healthy",
        "engine": "rule-engine-v1.0",
        "decision_modes": ["AI_AUTO", "PENDING_MANUAL", "MANUAL_OVERRIDE"],
        "compliance": ["Electricity Act 2003", "KSERC MYT Regulations 2021"]
    }

@app.get("/security/status", tags=["Security"])
async def security_status():
    return {
        "security_features": {
            "authentication": "JWT with RBAC",
            "rate_limiting": "enabled",
            "brute_force_protection": "enabled",
            "security_headers": "enabled",
            "audit_logging": "enabled"
        },
        "environment": ENVIRONMENT
    }
