# filepath: backend/core/logging.py
"""
Logging configuration for the application.

This module provides a centralized way to configure logging throughout the application,
ensuring consistent log formats, levels, and handling across all components.
"""
import logging
import sys
import json
from datetime import datetime
from typing import Dict, Any, Optional
import uuid
from contextvars import ContextVar
from functools import wraps

# Store the request ID in a context variable so it's available throughout a request
request_id_context: ContextVar[str] = ContextVar('request_id', default='')

class RequestContextFilter(logging.Filter):
    """
    Filter that adds request-specific context to log records.
    
    This adds request ID, timestamp, and other context information to log records,
    making it easier to trace logs for a specific request.
    """
    
    def filter(self, record):
        """Add request context to log record."""
        # Add request ID from context if available
        record.request_id = request_id_context.get() or '-'
        
        # Add ISO-format timestamp for better parsing
        record.isotime = datetime.utcnow().isoformat()
        
        return True


class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for easier parsing and analysis.
    
    JSON-formatted logs are easier to parse by log aggregation systems and
    make structured logging more effective.
    """
    
    def format(self, record):
        """Format log record as JSON."""
        log_record = {
            'timestamp': getattr(record, 'isotime', datetime.utcnow().isoformat()),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'request_id': getattr(record, 'request_id', '-'),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Include exception info if available
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': self.formatException(record.exc_info)
            }
        
        # Include any extra attributes
        for key, value in record.__dict__.items():
            if key not in {
                'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                'funcName', 'id', 'levelname', 'levelno', 'lineno', 'module', 
                'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName',
                'isotime', 'request_id'
            } and not key.startswith('_'):
                log_record[key] = value
        
        return json.dumps(log_record)


def setup_logging(level: int = logging.INFO, json_format: bool = True) -> None:
    """
    Set up application-wide logging configuration.
    
    Args:
        level: The minimum log level to record (default: INFO)
        json_format: Whether to format logs as JSON (default: True)
    """
    # Get the root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    
    # Remove existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    
    # Add our custom filter
    context_filter = RequestContextFilter()
    console_handler.addFilter(context_filter)
    
    # Set formatter based on preference
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(isotime)s [%(request_id)s] %(levelname)s %(name)s - %(message)s'
        )
    
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Set specific levels for noisy libraries
    logging.getLogger('uvicorn.access').setLevel(logging.WARNING)
    logging.getLogger('uvicorn.error').setLevel(logging.WARNING)
    logging.getLogger('httpx').setLevel(logging.WARNING)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)


def set_request_id(request_id: Optional[str] = None) -> str:
    """
    Set the current request ID in context.
    
    Args:
        request_id: The request ID to set, or None to generate a new UUID
        
    Returns:
        The request ID that was set
    """
    rid = request_id or str(uuid.uuid4())
    request_id_context.set(rid)
    return rid


def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: The logger to use, or None to create one based on the function
    
    Returns:
        Decorator function
    """
    def decorator(func):
        nonlocal logger
        if logger is None:
            logger = logging.getLogger(func.__module__)
            
        @wraps(func)
        def wrapper(*args, **kwargs):
            start_time = datetime.now()
            try:
                result = func(*args, **kwargs)
                
                # Calculate execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                
                # Log execution time
                logger.debug(
                    f"Function '{func.__name__}' executed in {execution_time:.4f} seconds",
                    extra={"execution_time": execution_time}
                )
                
                return result
            except Exception as e:
                # Log exception with execution time
                execution_time = (datetime.now() - start_time).total_seconds()
                logger.exception(
                    f"Exception in '{func.__name__}' after {execution_time:.4f} seconds: {str(e)}",
                    extra={"execution_time": execution_time}
                )
                raise
                
        return wrapper
    return decorator