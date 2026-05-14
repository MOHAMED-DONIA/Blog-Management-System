import time
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.logger import app_logger as logger
from app.core.metrics import metrics
from app.core.request_context import request_context

class LoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # Set the request in context for services to access
        token = request_context.set(request)
        request.state.cache_hit = False
        
        try:
            response: Response = await call_next(request)
        except Exception as exc:
            duration = (time.time() - start_time) * 1000
            metrics.record_request(request.method, request.url.path, 500, duration)
            raise exc
        finally:
            duration_ms = (time.time() - start_time) * 1000

        is_hit = getattr(request.state, "cache_hit", False)
        cache_status = "HIT" if is_hit else "MISS"
        cache_source = "cache" if is_hit else "database"
        
        response.headers["x-cache"] = cache_status
        response.headers["x-cache-source"] = cache_source
        response.headers["x-response-time"] = f"{duration_ms:.2f}ms"
        
        logger.info(
            f"{request.method} {request.url.path} - Status: {response.status_code} "
            f"| Cache: {cache_status} | Source: {cache_source} | Duration: {duration_ms:.2f}ms"
        )
        
        metrics.record_request(request.method, request.url.path, response.status_code, duration_ms)
        
        # Cleanup context
        request_context.reset(token)
        
        return response
