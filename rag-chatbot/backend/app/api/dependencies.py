# filepath: backend/app/api/dependencies.py
"""
Dependency injection functions for FastAPI routes.

This module defines reusable dependencies that can be injected into FastAPI
route handlers, providing access to services and enforcing preconditions.
"""
from typing import Annotated, Dict, Any, Optional
import logging
from fastapi import Depends, HTTPException, Header, Query

from app.core.logging import get_logger, set_request_id
from app.config import Settings, get_settings
from app.services.memory.manager import get_memory_manager
from app.services.llm.factory import get_llm_service, check_llm_providers
from app.core.exceptions import MemoryError, LLMProviderError


logger = get_logger(__name__)

async def get_request_metadata(
    x_request_id: Optional[str] = Header(None),
    user_agent: Optional[str] = Header(None)
) -> Dict[str, Any]:
    """
    Extract and process metadata from the request.
    
    This dependency:
    1. Sets a unique request ID if not provided
    2. Captures user agent and other headers
    3. Makes this metadata available to route handlers
    
    Args:
        x_request_id: Optional request ID from header
        user_agent: User agent string from header
        
    Returns:
        Dictionary of request metadata
    """
    # Set request ID in context
    request_id = set_request_id(x_request_id)
    
    # Return metadata
    return {
        "request_id": request_id,
        "user_agent": user_agent
    }


async def verify_memory_enabled(
    settings: Settings = Depends(get_settings)
) -> bool:
    """
    Verify that the memory system is enabled.
    
    This dependency:
    1. Checks if memory is enabled in settings
    2. Throws HTTP exception if memory is disabled
    
    Args:
        settings: Application settings
        
    Returns:
        True if memory is enabled
        
    Raises:
        HTTPException: If memory is disabled
    """
    if not settings.memory_enabled:
        raise HTTPException(
            status_code=400,
            detail="Memory system is disabled"
        )
    return True


async def get_memory_manager_dependency(
    _: bool = Depends(verify_memory_enabled)
):
    """
    Get the memory manager instance.
    
    This dependency:
    1. Checks if memory is enabled
    2. Returns the memory manager instance
    
    Args:
        _: Dependency on verify_memory_enabled
        
    Returns:
        Memory manager instance
        
    Raises:
        HTTPException: If memory manager is not initialized
    """
    try:
        return get_memory_manager()
    except MemoryError as e:
        logger.error(f"Memory manager error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Memory system error: Memory manager not initialized"
        )


async def get_llm_service_dependency(
    provider: Optional[str] = Query(None, description="LLM provider to use"),
    settings: Settings = Depends(get_settings)
):
    """
    Get an LLM service for the specified provider.
    
    This dependency:
    1. Uses the specified provider or default
    2. Checks if the provider is available
    3. Returns the LLM service instance
    
    Args:
        provider: Optional provider name
        settings: Application settings
        
    Returns:
        LLM service instance
        
    Raises:
        HTTPException: If the provider is not available
    """
    try:
        # Use specified provider or default
        provider_name = provider or settings.default_llm_provider.value
        
        # Get the LLM service
        return get_llm_service(provider_name, settings)
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {str(e)}")
        raise HTTPException(
            status_code=400,
            detail=f"LLM provider error: {str(e)}"
        )