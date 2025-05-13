# filepath: frontend/utils/formatters.py
"""
Utility functions for formatting and text processing in the frontend.

This module provides helper functions for formatting timestamps, text truncation,
and other UI-related text processing.
"""
from datetime import datetime
from typing import Any, Optional


def format_timestamp(timestamp: Any) -> str:
    """
    Format a timestamp to a human-readable string.
    
    Args:
        timestamp: Timestamp to format (string, datetime, or other)
        
    Returns:
        Formatted timestamp string
    """
    if not timestamp:
        return ""
    
    try:
        # If it's already a datetime object
        if isinstance(timestamp, datetime):
            dt = timestamp
        # If it's a string
        elif isinstance(timestamp, str):
            # Try ISO format first
            dt = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
        # If it's something else
        else:
            return str(timestamp)
        
        # Format the datetime
        return dt.strftime("%b %d, %Y, %I:%M %p")
    except Exception:
        # Return the original if parsing fails
        return str(timestamp)


def truncate_text(text: str, max_length: int = 100) -> str:
    """
    Truncate text to a maximum length with ellipsis.
    
    Args:
        text: Text to truncate
        max_length: Maximum length before truncation
        
    Returns:
        Truncated text
    """
    if not text:
        return ""
    
    if len(text) <= max_length:
        return text
    
    return text[:max_length] + "..."


def format_memory_source(memory_type: str, used: bool) -> str:
    """
    Format a memory source for display.
    
    Args:
        memory_type: Type of memory
        used: Whether the memory was used
        
    Returns:
        Formatted memory source string
    """
    memory_names = {
        "short_term": "Short-term Memory",
        "semantic": "Semantic Memory",
        "episodic": "Episodic Memory",
        "procedural": "Procedural Memory"
    }
    
    name = memory_names.get(memory_type, memory_type)
    icon = "✅" if used else "❌"
    
    return f"{icon} {name}"


def format_file_size(size_bytes: int) -> str:
    """
    Format a file size in bytes to a human-readable string.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted file size string
    """
    if size_bytes < 1024:
        return f"{size_bytes} bytes"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.1f} GB"