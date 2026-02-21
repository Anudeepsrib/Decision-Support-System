"""
F-21: Structured Logging & Observability Module.
Integrates structlog for JSON logging & request tracing.
"""

import structlog
import uuid
import time
from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


def configure_logging(json_format: bool = True):
    """
    Configure structlog for structured JSON logging.
    Call once at application startup (in main_secure.py lifespan).
    """
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]
    if json_format:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(0),
        cache_logger_on_first_use=True,
    )


logger = structlog.get_logger("arr-dss")


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Injects a unique trace_id into every request for cross-service debugging.
    Logs request method, path, status, and duration.
    """

    async def dispatch(self, request: Request, call_next):
        trace_id = request.headers.get("X-Trace-ID", str(uuid.uuid4()))
        request.state.trace_id = trace_id

        # Bind trace context for this request
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            trace_id=trace_id,
            method=request.method,
            path=request.url.path,
            client_ip=request.client.host if request.client else "unknown",
        )

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)

            logger.info(
                "request_completed",
                status_code=response.status_code,
                duration_ms=duration_ms,
            )

            # Propagate trace ID to response for frontend correlation
            response.headers["X-Trace-ID"] = trace_id
            return response

        except Exception as exc:
            duration_ms = round((time.perf_counter() - start_time) * 1000, 2)
            logger.error(
                "request_failed",
                error=str(exc),
                duration_ms=duration_ms,
            )
            raise
