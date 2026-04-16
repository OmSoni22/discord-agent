"""
Enhanced logging middleware with request ID tracking and performance metrics.
"""

from fastapi import Request
from app.core.logging.logger import add_to_log
import time
import uuid
from contextvars import ContextVar

# Context variable to store request ID across async operations
request_id_var: ContextVar[str] = ContextVar("request_id", default="")


def get_request_id() -> str:
    """Get the current request ID from context."""
    return request_id_var.get()


async def logging_middleware(request: Request, call_next):
    """
    Middleware that logs all incoming requests with:
    - Unique request ID
    - Request details (method, path, headers)
    - Response time
    - Status code
    """
    # Generate unique request ID
    req_id = str(uuid.uuid4())
    request_id_var.set(req_id)
    
    # Add request ID to request state for access in routes
    request.state.request_id = req_id
    
    # Start timer
    start_time = time.time()
    
    # Try to read body (be careful with large payloads)
    try:
        body_bytes = await request.body()
        payload = body_bytes.decode() if len(body_bytes) < 10000 else "<large payload>"
    except Exception:
        payload = "<could not read body>"
    
    # Log incoming request
    add_to_log(
        "info",
        f"[{req_id}] Incoming request",
        request_id=req_id,
        path=str(request.url),
        method=request.method,
        client_host=request.client.host if request.client else "unknown",
        payload=payload[:500] if payload else "", # Limit payload size in logs
        show_in_terminal=False
    )
    
    # Process request
    try:
        response = await call_next(request)
        
        # Calculate response time
        duration = time.time() - start_time
        
        # Log response
        add_to_log(
            "info",
            f"[{req_id}] Request completed",
            request_id=req_id,
            path=str(request.url),
            method=request.method,
            status_code=response.status_code,
            duration_ms=round(duration * 1000, 2),
            show_in_terminal=False
        )
        
        # Add request ID to response headers
        response.headers["X-Request-ID"] = req_id
        
        return response
        
    except Exception as e:
        duration = time.time() - start_time
        add_to_log(
            "error",
            f"[{req_id}] Request failed",
            request_id=req_id,
            path=str(request.url),
            method=request.method,
            error=str(e),
            duration_ms=round(duration * 1000, 2)
        )
        raise
