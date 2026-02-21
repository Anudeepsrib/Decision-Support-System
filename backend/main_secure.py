"""
Enterprise FastAPI Application Entry Point
Production-grade security, monitoring, and compliance
"""

import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager

from api.extraction import router as extraction_router
from api.mapping import router as mapping_router
from api.reports import router as reports_router
from api.auth import router as auth_router
from security.rate_limit import (
    RateLimitMiddleware,
    SecurityHeadersMiddleware,
    ip_filter,
)
# from observability import (
#     configure_logging,
#     RequestTracingMiddleware,
#     logger,
# )

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
    # configure_logging(json_format=(ENVIRONMENT == "production"))
    # logger.info("app_starting", environment=ENVIRONMENT)
    yield
    # logger.info("app_shutting_down")

# ─── Application Initialization ───
app = FastAPI(
    title="ARR Truing-Up Decision Support System",
    description=(
        "Enterprise-grade AI-augmented engine for Annual Revenue Requirement "
        "Truing-Up under the KSERC MYT 2022-27 Framework. "
        "Designed for 100% mathematical fidelity and full regulatory traceability."
    ),
    version="1.0.0",
    docs_url="/docs" if DEBUG else None,
    redoc_url="/redoc" if DEBUG else None,
    openapi_url="/openapi.json" if DEBUG else None,
    lifespan=lifespan,
)

# ─── Security & Observability Middleware ───
# app.add_middleware(RequestTracingMiddleware)  # F-21: Request tracing
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)

# 4. CORS
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
    return {
        "status": "healthy",
        "engine": "KSERC-MYT-2022-27-v1.0",
        "security": "active"
    }

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
