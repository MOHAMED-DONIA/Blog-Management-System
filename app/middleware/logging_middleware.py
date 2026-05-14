import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import app_logger as logger
from app.core.metrics import metrics
from app.core.cache_context import cache_hit_context

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Reset context for each request
        token = cache_hit_context.set(False)
        
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration = (time.time() - start_time) * 1000
            metrics.record_request(request.method, request.url.path, 500, duration)
            raise exc
        finally:
            duration_ms = (time.time() - start_time) * 1000

        # Read cache status from context
        is_hit = cache_hit_context.get()
        cache_status = "HIT (Cache)" if is_hit else "MISS (Database)"
        
        # Add custom headers
        response.headers["X-Cache"] = cache_status
        response.headers["X-Response-Time-Ms"] = f"{duration_ms:.2f}ms"
        
        # Log the operation
        logger.info(
            f"{request.method} {request.url.path} - Status: {response.status_code} "
            f"| Source: {cache_status} | Duration: {duration_ms:.2f}ms"
        )
        
        metrics.record_request(request.method, request.url.path, response.status_code, duration_ms)
        
        # Cleanup context
        cache_hit_context.reset(token)
        
        return response
