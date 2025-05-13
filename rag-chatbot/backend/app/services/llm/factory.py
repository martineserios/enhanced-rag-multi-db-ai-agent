# filepath: backend/services/llm/factory.py
"""
Factory for creating LLM service instances.

This module implements the Factory Method pattern for creating LLM services
based on the provider name, allowing for easy swapping of LLM providers.
"""
from typing import Dict, Optional, Type
import logging

from app.core.logging import get_logger
from app.core.exceptions import LLMProviderError
from app.config import Settings, LLMProvider
from app.services.llm.base import LLMService
from app.services.llm.openai import OpenAIService
from app.services.llm.anthropic import AnthropicService
from app.services.llm.groq import GroqService


logger = get_logger(__name__)

# Dictionary mapping provider names to service classes
LLM_SERVICES: Dict[str, Type[LLMService]] = {
    LLMProvider.OPENAI.value: OpenAIService,
    LLMProvider.ANTHROPIC.value: AnthropicService,
    LLMProvider.GROQ.value: GroqService
}

# Singleton instances of each LLM service
_llm_instances: Dict[str, LLMService] = {}

def get_llm_service(provider: str, settings: Settings) -> LLMService:
    """
    Get or create an LLM service for the specified provider.
    
    This function implements the Factory Method pattern, creating instances
    of different LLM services based on the provider name.
    
    Args:
        provider: The name of the LLM provider (e.g., "openai", "anthropic")
        settings: Application configuration settings
        
    Returns:
        An instance of the appropriate LLM service
        
    Raises:
        LLMProviderError: If the provider is not supported or properly configured
    """
    global _llm_instances
    
    # Normalize provider name
    provider = provider.lower()
    
    # Validate provider
    if provider not in LLM_SERVICES:
        supported = ", ".join(LLM_SERVICES.keys())
        raise LLMProviderError(f"Unsupported LLM provider: {provider}. Supported providers: {supported}")
    
    # Check if we already have an instance
    if provider in _llm_instances:
        return _llm_instances[provider]
    
    # Get the service class
    service_class = LLM_SERVICES[provider]
    
    # Check if the required API key is available
    api_key_attr = f"{provider}_api_key"
    if not hasattr(settings, api_key_attr) or not getattr(settings, api_key_attr):
        raise LLMProviderError(f"{provider.capitalize()} API key is not configured")
    
    try:
        # Create the service instance
        service = service_class(settings)
        
        # Store in the instances dictionary
        _llm_instances[provider] = service
        
        logger.info(f"Created {provider.capitalize()} LLM service")
        
        return service
    
    except Exception as e:
        logger.exception(f"Failed to create {provider.capitalize()} LLM service")
        raise LLMProviderError(f"Failed to initialize {provider} service: {str(e)}")

async def check_llm_providers(settings: Settings) -> Dict[str, bool]:
    """
    Check which LLM providers are available and working.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        Dictionary mapping provider names to availability status
    """
    results = {}
    
    for provider in LLM_SERVICES:
        try:
            # Check if API key is configured
            api_key_attr = f"{provider}_api_key"
            if not hasattr(settings, api_key_attr) or not getattr(settings, api_key_attr):
                results[provider] = False
                continue
            
            # Get the service
            service = get_llm_service(provider, settings)
            
            # Check health
            is_healthy = await service.health_check()
            results[provider] = is_healthy
            
        except Exception as e:
            logger.warning(f"Error checking {provider} availability: {str(e)}")
            results[provider] = False
    
    return results

def close_llm_services():
    """
    Close all LLM service instances.
    
    This function should be called when shutting down the application
    to release resources properly.
    """
    global _llm_instances
    
    for provider, service in _llm_instances.items():
        logger.info(f"Closing {provider} LLM service")
        
        # Call close method if it exists
        if hasattr(service, "close") and callable(getattr(service, "close")):
            try:
                service.close()
            except Exception as e:
                logger.warning(f"Error closing {provider} LLM service: {str(e)}")
    
    # Clear the instances dictionary
    _llm_instances = {}