"""
Logging Middleware
Intercepts every HTTP request and response to produce structured log entries
and record metrics (timing, status, route).
"""
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logger import get_logger
from app.core.metrics import metrics

logger = get_logger("blog_api.http")


class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Logs every incoming request and outgoing response.

    Log format (INFO):
        [METHOD] /path → status_code  (duration ms) [client_ip]

    Errors (4xx/5xx) are logged at WARNING / ERROR level.
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.perf_counter()

        # ── Pre-request ───────────────────────────────────────────────────────
        client_ip = request.client.host if request.client else "unknown"
        logger.debug(
            "→ %s %s  [%s]",
            request.method,
            request.url.path,
            client_ip,
        )

        # ── Process ───────────────────────────────────────────────────────────
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration_ms = (time.perf_counter() - start) * 1000
            logger.error(
                "✗ %s %s → EXCEPTION after %.1f ms  [%s] | %s: %s",
                request.method,
                request.url.path,
                duration_ms,
                client_ip,
                type(exc).__name__,
                exc,
            )
            metrics.record_request(
                method=request.method,
                path=request.url.path,
                status_code=500,
                duration_ms=duration_ms,
            )
            raise

        # ── Post-response ─────────────────────────────────────────────────────
        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code

        log_fn = logger.info
        if status >= 500:
            log_fn = logger.error
        elif status >= 400:
            log_fn = logger.warning

        icon = "✓" if status < 400 else ("⚠" if status < 500 else "✗")
        log_fn(
            "%s %s %s → %d  (%.1f ms)  [%s]",
            icon,
            request.method,
            request.url.path,
            status,
            duration_ms,
            client_ip,
        )

        metrics.record_request(
            method=request.method,
            path=request.url.path,
            status_code=status,
            duration_ms=duration_ms,
        )

        return response
