# ─── Backend Dockerfile ───
# Multi-stage build for minimal production image
# F-19: Production-grade containerization

FROM python:3.12-slim AS builder

# Security: Create non-root user
RUN groupadd -r dss && useradd --no-log-init -r -g dss dss

WORKDIR /app

# Install system dependencies (Ghostscript for camelot-py)
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        ghostscript \
        build-essential \
        libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ─── Production Stage ───
FROM python:3.12-slim AS production

RUN groupadd -r dss && useradd --no-log-init -r -g dss dss

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends ghostscript libpq5 && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Copy application code
COPY backend/ ./backend/
COPY config/ ./config/

# Security: Run as non-root user
USER dss

# Health check probe (F-20)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/health')" || exit 1

EXPOSE 8000

# Production entry point via main_secure
CMD ["uvicorn", "backend.main_secure:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
