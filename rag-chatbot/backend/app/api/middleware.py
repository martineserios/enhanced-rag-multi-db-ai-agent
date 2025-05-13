# filepath: backend/app/api/middleware.py
"""
Middleware components for the FastAPI application.

This module provides middleware for request/response processing, including:
- Request ID generation and propagation
- Error handling
- Logging
- Performance monitoring
"""
import time
from typing import Callable, Dict, Any
import logging
from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.logging import set_request_id, get_logger
from app.core.exceptions import BaseAppException

logger = get_logger(__name__)

class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware to log requests and responses.
    
    This middleware:
    1. Generates a unique request ID for each request
    2. Logs the incoming request
    3. Measures request processing time
    4. Logs the outgoing response with status and timing
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request through the middleware."""
        # Generate request ID and store in context
        request_id = set_request_id()
        
        # Start timer
        start_time = time.time()
        
        # Log the request
        logger.info(
            f"Request started: {request.method} {request.url.path}",
            extra={
                "method": request.method,
                "path": request.url.path,
                "query_params": str(request.query_params),
                "client_host": request.client.host if request.client else None,
                "client_port": request.client.port if request.client else None,
                "x_forwarded_for": request.headers.get("x-forwarded-for")
            }
        )
        
        try:
            # Process the request
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Add request ID and timing headers to response
            response.headers["X-Request-ID"] = request_id
            response.headers["X-Process-Time"] = str(process_time)
            
            # Log the response
            logger.info(
                f"Request completed: {request.method} {request.url.path} - {response.status_code}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": process_time
                }
            )
            
            return response
            
        except Exception as exc:
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Log the exception
            logger.exception(
                f"Request failed: {request.method} {request.url.path}",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "exception": str(exc)
                }
            )
            
            # Handle custom exceptions
            if isinstance(exc, BaseAppException):
                return JSONResponse(
                    status_code=exc.status_code,
                    content=exc.to_dict()
                )
            
            # For unexpected exceptions, return a generic 500 error
            return JSONResponse(
                status_code=500,
                content={
                    "status_code": 500,
                    "detail": "Internal server error",
                    "request_id": request_id
                }
            )


class PerformanceMonitoringMiddleware(BaseHTTPMiddleware):
    """
    Middleware to monitor API performance.
    
    This middleware tracks request durations and can be used to identify
    performance bottlenecks.
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process a request through the middleware."""
        # Start timer
        start_time = time.time()
        
        # Process the request
        response = await call_next(request)
        
        # Calculate and log processing time
        process_time = time.time() - start_time
        
        # Log slow requests (more than 1 second)
        if process_time > 1.0:
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} took {process_time:.2f}s",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time
                }
            )
        
        return response