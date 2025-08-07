"""
Unit Tests for LLM Provider Factory

Tests provider factory, initialization, configuration management,
and health monitoring functionality.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.llm_factory import (
    create_openai_provider,
    create_anthropic_provider,
    create_groq_provider,
    initialize_provider_manager,
    get_provider_manager,
    health_check_providers,
    get_available_capabilities,
    get_provider_for_capability,
    reset_provider_manager
)
from app.core.llm_providers import (
    ProviderType,
    ModelCapability,
    LLMProviderManager
)


class TestProviderCreation:
    """Test individual provider creation functions."""
    
    @patch('app.core.llm_factory.get_settings')
    @patch('app.core.llm_factory.OpenAIProvider')
    def test_create_openai_provider_success(self, mock_openai_provider, mock_settings):
        """Test successful OpenAI provider creation."""
        # Mock settings
        settings = Mock()
        settings.OPENAI_API_KEY = "test-openai-key"
        mock_settings.return_value = settings
        
        # Mock provider instance
        mock_provider_instance = Mock()
        mock_openai_provider.return_value = mock_provider_instance
        
        provider = create_openai_provider()
        
        assert provider == mock_provider_instance
        mock_openai_provider.assert_called_once()
    
    @patch('app.core.llm_factory.get_settings')
    def test_create_openai_provider_no_key(self, mock_settings):
        """Test OpenAI provider creation without API key."""
        settings = Mock()
        settings.OPENAI_API_KEY = None
        mock_settings.return_value = settings
        
        provider = create_openai_provider()
        
        assert provider is None
    
    @patch('app.core.llm_factory.get_settings')
    @patch('app.core.llm_factory.AnthropicProvider')
    def test_create_anthropic_provider_success(self, mock_anthropic_provider, mock_settings):
        """Test successful Anthropic provider creation."""
        settings = Mock()
        settings.ANTHROPIC_API_KEY = "test-anthropic-key"
        mock_settings.return_value = settings
        
        mock_provider_instance = Mock()
        mock_anthropic_provider.return_value = mock_provider_instance
        
        provider = create_anthropic_provider()
        
        assert provider == mock_provider_instance
    
    @patch('app.core.llm_factory.get_settings')
    @patch('app.core.llm_factory.GroqProvider')
    def test_create_groq_provider_success(self, mock_groq_provider, mock_settings):
        """Test successful Groq provider creation."""
        settings = Mock()
        settings.GROQ_API_KEY = "test-groq-key"
        mock_settings.return_value = settings
        
        mock_provider_instance = Mock()
        mock_groq_provider.return_value = mock_provider_instance
        
        provider = create_groq_provider()
        
        assert provider == mock_provider_instance


class TestProviderManager:
    """Test provider manager initialization and management."""
    
    def setup_method(self):
        """Reset provider manager before each test."""
        reset_provider_manager()
    
    @patch('app.core.llm_factory.create_openai_provider')
    @patch('app.core.llm_factory.create_anthropic_provider') 
    @patch('app.core.llm_factory.create_groq_provider')
    def test_initialize_provider_manager(self, mock_groq, mock_anthropic, mock_openai):
        """Test provider manager initialization with all providers."""
        # Mock provider instances
        openai_provider = Mock()
        openai_provider.provider_type = ProviderType.OPENAI
        
        anthropic_provider = Mock()
        anthropic_provider.provider_type = ProviderType.ANTHROPIC
        
        groq_provider = Mock()
        groq_provider.provider_type = ProviderType.GROQ
        
        mock_openai.return_value = openai_provider
        mock_anthropic.return_value = anthropic_provider
        mock_groq.return_value = groq_provider
        
        manager = initialize_provider_manager()
        
        assert isinstance(manager, LLMProviderManager)
        assert len(manager.providers) == 3
        assert ProviderType.OPENAI in manager.providers
        assert ProviderType.ANTHROPIC in manager.providers
        assert ProviderType.GROQ in manager.providers
    
    @patch('app.core.llm_factory.create_openai_provider')
    @patch('app.core.llm_factory.create_anthropic_provider')
    @patch('app.core.llm_factory.create_groq_provider')
    def test_initialize_provider_manager_no_providers(self, mock_groq, mock_anthropic, mock_openai):
        """Test provider manager initialization with no available providers."""
        # All provider creation functions return None
        mock_openai.return_value = None
        mock_anthropic.return_value = None
        mock_groq.return_value = None
        
        manager = initialize_provider_manager()
        
        assert isinstance(manager, LLMProviderManager)
        assert len(manager.providers) == 0
    
    @patch('app.core.llm_factory.initialize_provider_manager')
    def test_get_provider_manager_singleton(self, mock_initialize):
        """Test provider manager singleton behavior."""
        mock_manager = Mock()
        mock_initialize.return_value = mock_manager
        
        # First call should initialize
        manager1 = get_provider_manager()
        assert manager1 == mock_manager
        mock_initialize.assert_called_once()
        
        # Second call should return same instance
        manager2 = get_provider_manager()
        assert manager2 == mock_manager
        assert mock_initialize.call_count == 1  # Should not be called again


class TestHealthCheck:
    """Test health check functionality."""
    
    def setup_method(self):
        """Reset provider manager before each test."""
        reset_provider_manager()
    
    @patch('app.core.llm_factory.get_provider_manager')
    async def test_health_check_providers_success(self, mock_get_manager):
        """Test successful health check of all providers."""
        # Mock manager with health check data
        mock_manager = Mock()
        mock_manager.health_check_all = AsyncMock(return_value={
            "providers": {
                "openai": {"status": "healthy", "client_initialized": True},
                "anthropic": {"status": "healthy", "client_initialized": True}
            },
            "total_providers": 2,
            "healthy_providers": 2
        })
        mock_get_manager.return_value = mock_manager
        
        health_data = await health_check_providers()
        
        assert "summary" in health_data
        assert health_data["summary"]["status"] == "healthy"
        assert health_data["summary"]["total_configured"] == 2
        assert health_data["summary"]["healthy_count"] == 2
        assert health_data["summary"]["health_percentage"] == 100.0
    
    @patch('app.core.llm_factory.get_provider_manager')
    async def test_health_check_providers_partial_failure(self, mock_get_manager):
        """Test health check with some providers failing."""
        mock_manager = Mock()
        mock_manager.health_check_all = AsyncMock(return_value={
            "providers": {
                "openai": {"status": "healthy", "client_initialized": True},
                "anthropic": {"status": "error", "error": "API key invalid"}
            },
            "total_providers": 2,
            "healthy_providers": 1
        })
        mock_get_manager.return_value = mock_manager
        
        health_data = await health_check_providers()
        
        assert health_data["summary"]["status"] == "healthy"  # At least one provider healthy
        assert health_data["summary"]["health_percentage"] == 50.0
    
    @patch('app.core.llm_factory.get_provider_manager')
    async def test_health_check_providers_error(self, mock_get_manager):
        """Test health check with complete failure."""
        mock_manager = Mock()
        mock_manager.health_check_all = AsyncMock(side_effect=Exception("Connection failed"))
        mock_get_manager.return_value = mock_manager
        
        health_data = await health_check_providers()
        
        assert health_data["summary"]["status"] == "error"
        assert "error" in health_data["summary"]
        assert health_data["total_providers"] == 0


class TestCapabilityManagement:
    """Test capability-based provider management."""
    
    def setup_method(self):
        """Reset provider manager before each test."""
        reset_provider_manager()
    
    @patch('app.core.llm_factory.get_provider_manager')
    def test_get_available_capabilities(self, mock_get_manager):
        """Test getting available capabilities from all providers."""
        # Mock providers with different capabilities
        openai_provider = Mock()
        openai_provider.get_supported_capabilities.return_value = [
            ModelCapability.MEDICAL_REASONING,
            ModelCapability.CLINICAL_CONVERSATION
        ]
        
        anthropic_provider = Mock()
        anthropic_provider.get_supported_capabilities.return_value = [
            ModelCapability.CLINICAL_CONVERSATION,
            ModelCapability.PATIENT_MONITORING
        ]
        
        mock_manager = Mock()
        mock_manager.providers = {
            ProviderType.OPENAI: openai_provider,
            ProviderType.ANTHROPIC: anthropic_provider
        }
        mock_get_manager.return_value = mock_manager
        
        capabilities = get_available_capabilities()
        
        # Should include all unique capabilities
        assert ModelCapability.MEDICAL_REASONING in capabilities
        assert ModelCapability.CLINICAL_CONVERSATION in capabilities
        assert ModelCapability.PATIENT_MONITORING in capabilities
        assert len(capabilities) == 3
    
    @patch('app.core.llm_factory.get_provider_manager')
    def test_get_provider_for_capability(self, mock_get_manager):
        """Test getting provider for specific capability."""
        mock_provider = Mock()
        mock_manager = Mock()
        mock_manager.get_provider_for_capability.return_value = mock_provider
        mock_get_manager.return_value = mock_manager
        
        provider = get_provider_for_capability(ModelCapability.MEDICAL_REASONING)
        
        assert provider == mock_provider
        mock_manager.get_provider_for_capability.assert_called_once_with(
            ModelCapability.MEDICAL_REASONING
        )


class TestConfiguration:
    """Test provider configuration management."""
    
    def test_openai_default_configuration(self):
        """Test OpenAI default configuration values."""
        with patch('app.core.llm_factory.get_settings') as mock_settings:
            settings = Mock()
            settings.OPENAI_API_KEY = "test-key"
            mock_settings.return_value = settings
            
            with patch('app.core.llm_factory.OpenAIProvider') as mock_provider:
                create_openai_provider()
                
                # Check that provider was called with correct configuration
                mock_provider.assert_called_once()
                args, kwargs = mock_provider.call_args
                
                assert kwargs['api_key'] == "test-key"
                config = kwargs['default_config']
                assert config.model_name == "gpt-4"
                assert config.temperature == 0.3  # Conservative for medical
                assert config.medical_validated is True
                assert config.hipaa_compliant is True
                assert ModelCapability.MEDICAL_REASONING in config.capabilities
    
    def test_anthropic_default_configuration(self):
        """Test Anthropic default configuration values."""
        with patch('app.core.llm_factory.get_settings') as mock_settings:
            settings = Mock()
            settings.ANTHROPIC_API_KEY = "test-key"
            mock_settings.return_value = settings
            
            with patch('app.core.llm_factory.AnthropicProvider') as mock_provider:
                create_anthropic_provider()
                
                mock_provider.assert_called_once()
                args, kwargs = mock_provider.call_args
                
                config = kwargs['default_config']
                assert config.model_name == "claude-3-sonnet-20240229"
                assert config.temperature == 0.3
                assert ModelCapability.CLINICAL_CONVERSATION in config.capabilities
    
    def test_groq_default_configuration(self):
        """Test Groq default configuration values."""
        with patch('app.core.llm_factory.get_settings') as mock_settings:
            settings = Mock()
            settings.GROQ_API_KEY = "test-key"
            settings.GROQ_MODEL = "llama-3.1-8b-instant"
            mock_settings.return_value = settings
            
            with patch('app.core.llm_factory.GroqProvider') as mock_provider:
                create_groq_provider()
                
                mock_provider.assert_called_once()
                args, kwargs = mock_provider.call_args
                
                config = kwargs['default_config']
                assert config.model_name == "llama-3.1-8b-instant"
                assert config.hipaa_compliant is False  # Groq may not be HIPAA compliant
                assert ModelCapability.KNOWLEDGE_RETRIEVAL in config.capabilities


@pytest.mark.integration
class TestFactoryIntegration:
    """Integration tests for the complete factory system."""
    
    async def test_complete_provider_lifecycle(self):
        """Test complete provider lifecycle from creation to health check."""
        # This would test the complete flow with real configurations
        # For now, we'll leave it as a placeholder for integration tests
        pass