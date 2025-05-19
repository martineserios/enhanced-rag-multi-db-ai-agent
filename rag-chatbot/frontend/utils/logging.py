"""
Logging configuration for the frontend application.

This module provides a centralized way to configure logging throughout the frontend,
ensuring consistent log formats, levels, and handling across all components.
"""
import os
import sys
import json
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from functools import wraps

class JSONFormatter(logging.Formatter):
    """
    Format log records as JSON for easier parsing and analysis.
    
    JSON-formatted logs are easier to parse by log aggregation systems and
    make structured logging more effective.
    """
    
    def format(self, record):
        """Format log record as JSON."""
        log_record = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }
        
        # Include any extra attributes
        for key, value in record.__dict__.items():
            if key not in {
                'args', 'asctime', 'created', 'exc_info', 'exc_text', 'filename',
                'funcName', 'levelname', 'levelno', 'lineno', 'module', 
                'msecs', 'message', 'msg', 'name', 'pathname', 'process',
                'processName', 'relativeCreated', 'stack_info', 'thread', 'threadName'
            } and not key.startswith('_'):
                log_record[key] = value
        
        # Handle exceptions
        if record.exc_info:
            log_record['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_record)

def setup_logging(level: str = "INFO", json_format: bool = True):
    """
    Set up application-wide logging configuration.
    
    Args:
        level: The minimum log level (default: INFO)
        json_format: Whether to format logs as JSON (default: True)
    """
    # Convert string level to logging level
    log_level = getattr(logging, level.upper(), logging.INFO)
    
    # Clear any existing handlers and loggers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Set log level for all loggers
    root_logger.setLevel(log_level)
    
    # Configure the handler
    handler = logging.StreamHandler(sys.stdout)
    
    if json_format:
        formatter = JSONFormatter()
    else:
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
    
    handler.setFormatter(formatter)
    root_logger.addHandler(handler)
    
    # Configure specific loggers
    loggers = {
        'app': log_level,  # Main application logger
        'uvicorn': logging.INFO,  # Uvicorn server logs
        'httpx': logging.WARNING,  # HTTP client library
        'httpcore': logging.WARNING,  # Lower level HTTP library
        'streamlit': logging.WARNING,  # Streamlit framework logs
    }
    
    for logger_name, logger_level in loggers.items():
        logger = logging.getLogger(logger_name)
        logger.setLevel(logger_level)
        logger.propagate = True  # Propagate to root logger
    
    # Disable overly verbose loggers
    for logger_name in ['matplotlib', 'PIL']:
        logging.getLogger(logger_name).setLevel(logging.WARNING)
    
    return root_logger
def get_logger(name: str) -> logging.Logger:
    """
    Get a logger with the specified name.
    
    Args:
        name: The name of the logger, typically __name__
        
    Returns:
        A configured logger instance
    """
    return logging.getLogger(name)

def log_execution_time(logger: Optional[logging.Logger] = None):
    """
    Decorator to log the execution time of a function.
    
    Args:
        logger: The logger to use, or None to create one based on the function
    
    Returns:
        Decorator function
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Get logger from argument or create one based on function module
            func_logger = logger or logging.getLogger(func.__module__)
            
            # Log function start
            func_logger.debug(f"Starting {func.__qualname__}")
            
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                end_time = datetime.now()
                
                # Log successful execution
                duration = (end_time - start_time).total_seconds()
                func_logger.debug(
                    f"Completed {func.__qualname__} in {duration:.3f} seconds"
                )
                
                return result
                
            except Exception as e:
                # Log the exception
                func_logger.exception(
                    f"Error in {func.__qualname__}: {str(e)}"
                )
                raise
                
        return wrapper
    return decorator
