"""Middleware for request tracing and correlation IDs."""

import logging
import time
import uuid
from contextvars import ContextVar
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

# Context variable for request ID - accessible anywhere in the request lifecycle
request_id_var: ContextVar[str] = ContextVar('request_id', default='')

logger = logging.getLogger(__name__)


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """
    Middleware that adds request tracing via correlation IDs.
    
    Features:
    - Generates or forwards X-Request-ID header
    - Logs request start/end with timing
    - Makes request ID available via context var
    """

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Get or generate request ID
        request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
        
        # Set in context for use in logging
        token = request_id_var.set(request_id)
        
        # Log request start
        start_time = time.perf_counter()
        logger.info(
            f"Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            }
        )
        
        try:
            response = await call_next(request)
            
            # Calculate duration
            duration_ms = (time.perf_counter() - start_time) * 1000
            
            # Log request end
            logger.info(
                f"Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "duration_ms": round(duration_ms, 2),
                }
            )
            
            # Add request ID to response headers
            response.headers['X-Request-ID'] = request_id
            
            return response
            
        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            logger.error(
                f"Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "duration_ms": round(duration_ms, 2),
                }
            )
            raise
        finally:
            # Reset context var
            request_id_var.reset(token)


class RequestLoggingFilter(logging.Filter):
    """
    Logging filter that adds request_id to log records.
    
    Use with a formatter like:
    %(asctime)s [%(request_id)s] %(levelname)s %(name)s: %(message)s
    """
    
    def filter(self, record: logging.LogRecord) -> bool:
        record.request_id = get_request_id() or '-'
        return True
