"""
LLM Provider Factory

Factory for creating and configuring LLM providers with medical-specific settings.
Handles provider initialization, configuration management, and health monitoring.
"""

from typing import Dict, Optional, List
import logging
from app.core.config import get_settings
from app.core.llm_providers import (
    LLMProvider,
    LLMProviderManager,
    OpenAIProvider,
    AnthropicProvider,
    GroqProvider,
    ProviderType,
    ModelCapability,
    ModelConfig
)

logger = logging.getLogger(__name__)

# Global provider manager instance
_provider_manager: Optional[LLMProviderManager] = None


def create_openai_provider() -> Optional[OpenAIProvider]:
    """Create OpenAI provider with medical configuration."""
    settings = get_settings()
    
    if not settings.OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured")
        return None
    
    config = ModelConfig(
        provider=ProviderType.OPENAI,
        model_name="gpt-4",
        max_tokens=1500,
        temperature=0.3,  # Conservative for medical accuracy
        capabilities=[
            ModelCapability.MEDICAL_REASONING,
            ModelCapability.CLINICAL_CONVERSATION,
            ModelCapability.PATIENT_MONITORING
        ],
        medical_validated=True,
        hipaa_compliant=True
    )
    
    try:
        provider = OpenAIProvider(api_key=settings.OPENAI_API_KEY, default_config=config)
        logger.info("OpenAI provider created successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to create OpenAI provider: {str(e)}")
        return None


def create_anthropic_provider() -> Optional[AnthropicProvider]:
    """Create Anthropic provider with medical configuration."""
    settings = get_settings()
    
    if not settings.ANTHROPIC_API_KEY:
        logger.warning("Anthropic API key not configured")
        return None
    
    config = ModelConfig(
        provider=ProviderType.ANTHROPIC,
        model_name="claude-3-sonnet-20240229",
        max_tokens=1500,
        temperature=0.3,
        capabilities=[
            ModelCapability.CLINICAL_CONVERSATION,
            ModelCapability.MEDICAL_REASONING,
            ModelCapability.PATIENT_MONITORING
        ],
        medical_validated=True,
        hipaa_compliant=True
    )
    
    try:
        provider = AnthropicProvider(api_key=settings.ANTHROPIC_API_KEY, default_config=config)
        logger.info("Anthropic provider created successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to create Anthropic provider: {str(e)}")
        return None


def create_groq_provider() -> Optional[GroqProvider]:
    """Create Groq provider with medical configuration."""
    settings = get_settings()
    
    if not settings.GROQ_API_KEY:
        logger.warning("Groq API key not configured")
        return None
    
    config = ModelConfig(
        provider=ProviderType.GROQ,
        model_name="llama2-70b-4096",
        max_tokens=1500,
        temperature=0.3,
        capabilities=[
            ModelCapability.KNOWLEDGE_RETRIEVAL,
            ModelCapability.MEDICAL_REASONING
        ],
        medical_validated=True,
        hipaa_compliant=False  # Note: Groq may not be HIPAA compliant
    )
    
    try:
        provider = GroqProvider(api_key=settings.GROQ_API_KEY, default_config=config)
        logger.info("Groq provider created successfully")
        return provider
    except Exception as e:
        logger.error(f"Failed to create Groq provider: {str(e)}")
        return None


def initialize_provider_manager() -> LLMProviderManager:
    """Initialize and configure the LLM provider manager."""
    global _provider_manager
    
    if _provider_manager is not None:
        return _provider_manager
    
    logger.info("Initializing LLM Provider Manager")
    manager = LLMProviderManager()
    
    # Create and register providers
    providers_created = 0
    
    # OpenAI Provider
    openai_provider = create_openai_provider()
    if openai_provider:
        manager.register_provider(openai_provider)
        providers_created += 1
    
    # Anthropic Provider
    anthropic_provider = create_anthropic_provider()
    if anthropic_provider:
        manager.register_provider(anthropic_provider)
        providers_created += 1
    
    # Groq Provider
    groq_provider = create_groq_provider()
    if groq_provider:
        manager.register_provider(groq_provider)
        providers_created += 1
    
    logger.info(f"Provider Manager initialized with {providers_created} providers")
    
    if providers_created == 0:
        logger.error("No LLM providers could be initialized! Check API key configuration.")
    
    _provider_manager = manager
    return manager


def get_provider_manager() -> LLMProviderManager:
    """Get the global provider manager instance."""
    global _provider_manager
    
    if _provider_manager is None:
        _provider_manager = initialize_provider_manager()
    
    return _provider_manager


async def health_check_providers() -> Dict[str, any]:
    """Comprehensive health check for all providers."""
    manager = get_provider_manager()
    
    try:
        health_data = await manager.health_check_all()
        
        # Add summary information
        health_data["summary"] = {
            "total_configured": health_data["total_providers"],
            "healthy_count": health_data["healthy_providers"],
            "health_percentage": (
                health_data["healthy_providers"] / health_data["total_providers"] * 100
                if health_data["total_providers"] > 0 else 0
            ),
            "status": "healthy" if health_data["healthy_providers"] > 0 else "unhealthy"
        }
        
        return health_data
        
    except Exception as e:
        logger.error(f"Provider health check failed: {str(e)}")
        return {
            "summary": {"status": "error", "error": str(e)},
            "providers": {},
            "total_providers": 0,
            "healthy_providers": 0
        }


def get_available_capabilities() -> List[ModelCapability]:
    """Get all available medical capabilities from registered providers."""
    manager = get_provider_manager()
    capabilities = set()
    
    for provider in manager.providers.values():
        capabilities.update(provider.get_supported_capabilities())
    
    return list(capabilities)


def get_provider_for_capability(capability: ModelCapability) -> Optional[LLMProvider]:
    """Get the best provider for a specific medical capability."""
    manager = get_provider_manager()
    return manager.get_provider_for_capability(capability)


def reset_provider_manager() -> None:
    """Reset the global provider manager (useful for testing)."""
    global _provider_manager
    _provider_manager = None
    logger.info("Provider manager reset")