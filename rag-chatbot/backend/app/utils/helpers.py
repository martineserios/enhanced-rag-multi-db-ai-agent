# filepath: backend/utils/helpers.py
"""
Input validation utilities.

This module provides reusable validation functions for different types of input,
ensuring consistency in validation across the application.
"""
import re
import uuid
from typing import Dict, List, Any, Optional, Union, Callable
from datetime import datetime
import json
import logging
from pathlib import Path

from pydantic import BaseModel, ValidationError, validator
from fastapi import UploadFile, HTTPException

from app.core.logging import get_logger
from app.core.exceptions import ValidationError as AppValidationError


logger = get_logger(__name__)


def validate_memory_type(memory_type: str) -> bool:
    """
    Validate that a memory type is supported.
    
    Args:
        memory_type: The memory type to validate
        
    Returns:
        True if the memory type is valid
        
    Raises:
        AppValidationError: If the memory type is invalid
    """
    valid_types = ["short_term", "semantic", "episodic", "procedural"]
    
    if memory_type not in valid_types:
        valid_types_str = ", ".join(valid_types)
        raise AppValidationError(
            f"Invalid memory type: {memory_type}. Valid types are: {valid_types_str}"
        )
    
    return True


def validate_llm_provider(provider: str) -> bool:
    """
    Validate that an LLM provider is supported.
    
    Args:
        provider: The provider name to validate
        
    Returns:
        True if the provider is valid
        
    Raises:
        AppValidationError: If the provider is invalid
    """
    valid_providers = ["openai", "anthropic", "groq"]
    
    if provider not in valid_providers:
        valid_providers_str = ", ".join(valid_providers)
        raise AppValidationError(
            f"Invalid LLM provider: {provider}. Valid providers are: {valid_providers_str}"
        )
    
    return True


def validate_conversation_id(conversation_id: str) -> bool:
    """
    Validate a conversation ID format.
    
    Args:
        conversation_id: The conversation ID to validate
        
    Returns:
        True if the conversation ID is valid
        
    Raises:
        AppValidationError: If the conversation ID is invalid
    """
    # Check if the conversation ID is a valid UUID
    try:
        uuid_obj = uuid.UUID(conversation_id)
        return True
    except ValueError:
        # If not a UUID, check if it matches our custom format
        pattern = r'^conversation:[a-f0-9-]+$'
        if re.match(pattern, conversation_id):
            return True
        
        raise AppValidationError(
            "Invalid conversation ID format. Must be a UUID or start with 'conversation:'"
        )


def validate_document_file(file: UploadFile) -> bool:
    """
    Validate that a document file is of an accepted type.
    
    Args:
        file: The uploaded file to validate
        
    Returns:
        True if the file is valid
        
    Raises:
        AppValidationError: If the file is invalid
    """
    if not file or not file.filename:
        raise AppValidationError("No file provided")
    
    # Get file extension
    file_extension = Path(file.filename).suffix.lower()
    
    # Define accepted file types
    accepted_extensions = [
        '.txt', '.pdf', '.doc', '.docx', 
        '.xls', '.xlsx', '.ppt', '.pptx',
        '.csv', '.json', '.html', '.htm',
        '.md', '.markdown'
    ]
    
    if file_extension not in accepted_extensions:
        accepted_str = ", ".join(accepted_extensions)
        raise AppValidationError(
            f"Invalid file type: {file_extension}. Accepted types are: {accepted_str}"
        )
    
    # Optional: Check file size
    # We're using the file.file.seek() and tell() methods to get the file size
    # without reading the entire file into memory
    try:
        file.file.seek(0, 2)  # Seek to the end of the file
        file_size = file.file.tell()  # Get current position (file size)
        file.file.seek(0)  # Reset to the beginning
        
        # 100 MB max file size
        max_size = 100 * 1024 * 1024
        if file_size > max_size:
            raise AppValidationError(
                f"File too large. Maximum file size is 100 MB, got {file_size / (1024 * 1024):.2f} MB"
            )
    except Exception as e:
        logger.warning(f"Could not check file size: {str(e)}")
    
    return True


def validate_memory_weights(weights: Dict[str, float]) -> bool:
    """
    Validate memory weights dictionary.
    
    Args:
        weights: Dictionary mapping memory types to weights
        
    Returns:
        True if the weights are valid
        
    Raises:
        AppValidationError: If the weights are invalid
    """
    valid_types = ["short_term", "semantic", "episodic", "procedural"]
    
    # Check that all keys are valid memory types
    for memory_type in weights.keys():
        if memory_type not in valid_types:
            valid_types_str = ", ".join(valid_types)
            raise AppValidationError(
                f"Invalid memory type in weights: {memory_type}. Valid types are: {valid_types_str}"
            )
    
    # Check that all weights are positive floats
    for memory_type, weight in weights.items():
        if not isinstance(weight, (int, float)):
            raise AppValidationError(
                f"Weight for {memory_type} must be a number, got {type(weight).__name__}"
            )
        
        if weight < 0:
            raise AppValidationError(
                f"Weight for {memory_type} must be positive, got {weight}"
            )
    
    return True


def validate_json_string(json_str: str) -> Dict[str, Any]:
    """
    Validate and parse a JSON string.
    
    Args:
        json_str: The JSON string to validate
        
    Returns:
        Parsed JSON dictionary
        
    Raises:
        AppValidationError: If the JSON is invalid
    """
    try:
        return json.loads(json_str)
    except json.JSONDecodeError as e:
        raise AppValidationError(f"Invalid JSON: {str(e)}")


def sanitize_text_input(text: str) -> str:
    """
    Sanitize text input to prevent injection attacks.
    
    This function:
    1. Removes or escapes potentially harmful characters
    2. Limits the length of the input
    
    Args:
        text: The input text to sanitize
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Limit length (100,000 characters max)
    if len(text) > 100000:
        logger.warning(f"Input text truncated from {len(text)} to 100,000 characters")
        text = text[:100000]
    
    # Remove control characters except for newlines and tabs
    text = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', text)
    
    return text


def validate_with_model(data: Dict[str, Any], model_class: type) -> Dict[str, Any]:
    """
    Validate data using a Pydantic model.
    
    Args:
        data: The data to validate
        model_class: The Pydantic model class to use for validation
        
    Returns:
        Validated data (model.dict())
        
    Raises:
        AppValidationError: If validation fails
    """
    try:
        model = model_class(**data)
        return model.dict()
    except ValidationError as e:
        # Convert Pydantic validation error to our custom error
        errors = []
        for error in e.errors():
            errors.append({
                "loc": error.get("loc", []),
                "msg": error.get("msg", ""),
                "type": error.get("type", "")
            })
        
        raise AppValidationError(detail="Validation error", errors=errors)


def ensure_limit_offset(limit: int, offset: int) -> tuple[int, int]:
    """
    Ensure limit and offset parameters are within acceptable ranges.
    
    Args:
        limit: Maximum number of items to return
        offset: Number of items to skip
        
    Returns:
        Tuple of (validated_limit, validated_offset)
    """
    # Set maximum values
    max_limit = 1000
    max_offset = 10000
    
    # Ensure limit is positive and not too large
    if limit <= 0:
        limit = 10  # Default
    elif limit > max_limit:
        limit = max_limit
    
    # Ensure offset is non-negative and not too large
    if offset < 0:
        offset = 0
    elif offset > max_offset:
        offset = max_offset
    
    return limit, offset


def validate_iso_datetime(datetime_str: str) -> Optional[datetime]:
    """
    Validate an ISO format datetime string.
    
    Args:
        datetime_str: The datetime string to validate
        
    Returns:
        Parsed datetime object, or None if invalid
        
    Raises:
        AppValidationError: If the datetime string is invalid
    """
    if not datetime_str:
        return None
    
    try:
        return datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
    except ValueError:
        raise AppValidationError(f"Invalid ISO datetime format: {datetime_str}")


def validate_tags(tags_str: str) -> List[str]:
    """
    Validate and parse a comma-separated list of tags.
    
    Args:
        tags_str: Comma-separated tags
        
    Returns:
        List of validated tags
    """
    if not tags_str:
        return []
    
    # Split by comma and strip whitespace
    tags = [tag.strip() for tag in tags_str.split(',')]
    
    # Remove empty tags
    tags = [tag for tag in tags if tag]
    
    # Validate each tag - allowed: alphanumeric, hyphen, underscore, space
    for tag in tags:
        if not re.match(r'^[a-zA-Z0-9\-_\s]+$', tag):
            raise AppValidationError(
                f"Invalid tag format: {tag}. Tags can only contain letters, "
                "numbers, hyphens, underscores, and spaces."
            )
    
    # Remove duplicates
    tags = list(set(tags))
    
    return tags


def create_validator(
    validation_fn: Callable,
    error_message: str
) -> Callable[[Any], Any]:
    """
    Create a validator function that can be used with FastAPI's Query and Path.
    
    Args:
        validation_fn: Function that validates the input
        error_message: Error message to show if validation fails
        
    Returns:
        Validator function compatible with FastAPI dependencies
    """
    def validator(value: Any) -> Any:
        try:
            if validation_fn(value):
                return value
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"{error_message}: {str(e)}")
        raise HTTPException(status_code=400, detail=error_message)
    
    return validator


# Create reusable validators for FastAPI dependencies
memory_type_validator = create_validator(
    validate_memory_type,
    "Invalid memory type"
)

llm_provider_validator = create_validator(
    validate_llm_provider,
    "Invalid LLM provider"
)

conversation_id_validator = create_validator(
    validate_conversation_id,
    "Invalid conversation ID format"
)