# filepath: backend/utils/validators.py
"""
Validation utilities for the application.

This module provides validation functions for different types of inputs,
ensuring that data meets required formats and constraints before processing.
"""
import os
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Tuple
import json
import logging
from datetime import datetime

from app.core.logging import get_logger
from app.core.exceptions import ValidationError, UnsupportedDocumentTypeError

logger = get_logger(__name__)

# Supported file extensions and MIME types
SUPPORTED_DOCUMENT_EXTENSIONS = {
    '.txt', '.pdf', '.doc', '.docx', '.csv', '.xlsx', '.xls',
    '.pptx', '.ppt', '.html', '.htm', '.md', '.markdown', '.json'
}

SUPPORTED_MIME_TYPES = {
    'text/plain', 'application/pdf', 'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/csv', 'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',
    'text/html', 'text/markdown', 'application/json'
}

# Maximum content sizes
MAX_MESSAGE_LENGTH = 32000  # Maximum length of a chat message
MAX_CONTEXT_LENGTH = 128000  # Maximum length of a context string
MAX_DOCUMENT_SIZE = 10 * 1024 * 1024  # 10 MB maximum document size

def validate_chat_message(message: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a chat message for length and content.
    
    Args:
        message: The chat message to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not message or not message.strip():
        return False, "Message cannot be empty"
    
    if len(message) > MAX_MESSAGE_LENGTH:
        return False, f"Message exceeds maximum length of {MAX_MESSAGE_LENGTH} characters"
    
    # Check for potentially harmful content (this would be more extensive in a real system)
    harmful_patterns = [
        r'(?i)^\s*system:\s*',  # Attempts to inject system prompts
        r'(?i)^\s*<\|im_start\|>\s*',  # Special tokens
        r'(?i)^\s*<\|endoftext\|>\s*'  # Special tokens
    ]
    
    for pattern in harmful_patterns:
        if re.search(pattern, message):
            return False, "Message contains potentially harmful patterns"
    
    return True, None


def validate_conversation_id(conversation_id: str) -> Tuple[bool, Optional[str]]:
    """
    Validate a conversation ID format.
    
    Args:
        conversation_id: The conversation ID to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not conversation_id:
        return False, "Conversation ID cannot be empty"
    
    # Check for valid UUID format - both standard UUID and our prefixed format
    uuid_pattern = r'^[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}$'
    prefixed_pattern = r'^conversation:[0-9a-f]{8}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{4}-?[0-9a-f]{12}(:.*)?$'
    
    if not re.match(uuid_pattern, conversation_id, re.IGNORECASE) and not re.match(prefixed_pattern, conversation_id, re.IGNORECASE):
        return False, "Invalid conversation ID format"
    
    return True, None


def validate_memory_query(query: str, memory_types: Optional[List[str]] = None) -> Tuple[bool, Optional[str]]:
    """
    Validate a memory query and requested memory types.
    
    Args:
        query: The query string
        memory_types: Optional list of memory types to query
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"
    
    if len(query) > MAX_MESSAGE_LENGTH:
        return False, f"Query exceeds maximum length of {MAX_MESSAGE_LENGTH} characters"
    
    # Validate memory types if provided
    if memory_types:
        valid_types = {"short_term", "semantic", "episodic", "procedural"}
        invalid_types = set(memory_types) - valid_types
        
        if invalid_types:
            return False, f"Invalid memory types: {', '.join(invalid_types)}"
    
    return True, None


def validate_document_file(file_path: Union[str, Path], max_size: int = MAX_DOCUMENT_SIZE) -> Tuple[bool, Optional[str]]:
    """
    Validate a document file for type and size.
    
    Args:
        file_path: Path to the document file
        max_size: Maximum allowed file size in bytes
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Convert to Path object
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        return False, f"File not found: {file_path}"
    
    # Check file size
    file_size = file_path.stat().st_size
    if file_size > max_size:
        return False, f"File size ({file_size} bytes) exceeds maximum allowed size ({max_size} bytes)"
    
    # Check file extension
    file_extension = file_path.suffix.lower()
    if file_extension not in SUPPORTED_DOCUMENT_EXTENSIONS:
        return False, f"Unsupported file extension: {file_extension}"
    
    # Additional validation could be done here, such as checking file contents
    
    return True, None


def validate_json_structure(json_data: Union[str, Dict[str, Any]], required_keys: List[str]) -> Tuple[bool, Optional[str]]:
    """
    Validate a JSON structure for required keys.
    
    Args:
        json_data: JSON string or dictionary to validate
        required_keys: List of required keys
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Parse JSON if it's a string
    if isinstance(json_data, str):
        try:
            data = json.loads(json_data)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {str(e)}"
    else:
        data = json_data
    
    # Check for required keys
    missing_keys = set(required_keys) - set(data.keys())
    if missing_keys:
        return False, f"Missing required keys: {', '.join(missing_keys)}"
    
    return True, None


def validate_procedure(procedure: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
    """
    Validate a procedure definition for procedural memory.
    
    Args:
        procedure: Procedure dictionary to validate
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Check required keys
    is_valid, error = validate_json_structure(procedure, ["name", "steps"])
    if not is_valid:
        return is_valid, error
    
    # Validate name
    name = procedure.get("name", "")
    if not name or not isinstance(name, str):
        return False, "Procedure name must be a non-empty string"
    
    # Validate steps
    steps = procedure.get("steps", [])
    if not steps or not isinstance(steps, list):
        return False, "Procedure must have at least one step"
    
    # Validate each step
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            return False, f"Step {i} must be a dictionary"
        
        # Check required step fields
        if "description" not in step:
            return False, f"Step {i} is missing required field: description"
        
        # Check description is a string
        if not isinstance(step.get("description"), str):
            return False, f"Step {i} description must be a string"
    
    return True, None


def validate_embedding_query(query: str, top_k: int = 5) -> Tuple[bool, Optional[str]]:
    """
    Validate a query for semantic search.
    
    Args:
        query: The query string
        top_k: Number of results to return
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not query or not query.strip():
        return False, "Query cannot be empty"
    
    if len(query) > MAX_MESSAGE_LENGTH:
        return False, f"Query exceeds maximum length of {MAX_MESSAGE_LENGTH} characters"
    
    if top_k < 1:
        return False, "top_k must be a positive integer"
    
    if top_k > 100:
        return False, "top_k cannot exceed 100"
    
    return True, None


def sanitize_input(text: str) -> str:
    """
    Sanitize input text to remove potentially harmful patterns.
    
    Args:
        text: The input text to sanitize
        
    Returns:
        Sanitized text
    """
    # Remove control characters
    text = ''.join(char for char in text if ord(char) >= 32 or char in '\n\r\t')
    
    # Replace potentially dangerous patterns
    patterns_to_remove = [
        r'(?i)<\|im_start\|>.*?<\|im_end\|>',
        r'(?i)<\|endoftext\|>',
        r'(?i)^\s*system:\s*'
    ]
    
    for pattern in patterns_to_remove:
        text = re.sub(pattern, '', text)
    
    return text.strip()


def validate_and_sanitize_message(message: str) -> Tuple[str, Optional[str]]:
    """
    Validate and sanitize a chat message.
    
    Args:
        message: The chat message to validate and sanitize
        
    Returns:
        Tuple of (sanitized_message, error_message)
        If validation fails, error_message will be set
    """
    # Validate first
    is_valid, error = validate_chat_message(message)
    if not is_valid:
        return "", error
    
    # Then sanitize
    sanitized = sanitize_input(message)
    
    # Check if sanitization removed all content
    if not sanitized:
        return "", "Message was empty after sanitization"
    
    return sanitized, None