"""
Unit Tests for LLM Provider System

Tests the abstract base class and concrete provider implementations
with medical-specific validation and capability routing.
"""

import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.core.llm_providers import (
    LLMProvider,
    LLMProviderManager,
    OpenAIProvider,
    AnthropicProvider,
    GroqProvider,
    ProviderType,
    ModelCapability,
    ModelConfig,
    LLMRequest,
    LLMResponse
)


class TestModelConfig:
    """Test ModelConfig dataclass."""
    
    def test_model_config_creation(self):
        """Test basic model configuration creation."""
        config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name="gpt-4",
            capabilities=[ModelCapability.MEDICAL_REASONING]
        )
        
        assert config.provider == ProviderType.OPENAI
        assert config.model_name == "gpt-4"
        assert config.max_tokens == 1500  # Default value
        assert config.temperature == 0.3  # Default value
        assert ModelCapability.MEDICAL_REASONING in config.capabilities


class TestLLMRequest:
    """Test LLMRequest dataclass."""
    
    def test_llm_request_creation(self):
        """Test LLM request creation with medical context."""
        messages = [{"role": "user", "content": "Test message"}]
        medical_context = {
            "patient_safety_level": "high",
            "medical_domain": "obesity_treatment"
        }
        
        request = LLMRequest(
            messages=messages,
            patient_id="patient_123",
            medical_context=medical_context
        )
        
        assert request.messages == messages
        assert request.patient_id == "patient_123"
        assert request.medical_context["patient_safety_level"] == "high"


class TestOpenAIProvider:
    """Test OpenAI provider implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name="gpt-4",
            capabilities=[ModelCapability.MEDICAL_REASONING],
            medical_validated=True
        )
        
    @patch('openai.OpenAI')
    def test_openai_provider_initialization(self, mock_openai):
        """Test OpenAI provider initialization."""
        provider = OpenAIProvider(api_key="test-key", default_config=self.config)
        
        assert provider.provider_type == ProviderType.OPENAI
        assert provider.api_key == "test-key"
        mock_openai.assert_called_once_with(api_key="test-key")
    
    @patch('openai.OpenAI')
    def test_openai_missing_package(self, mock_openai):
        """Test OpenAI provider with missing package."""
        mock_openai.side_effect = ImportError("No module named 'openai'")
        
        with pytest.raises(ImportError, match="Please install openai package"):
            OpenAIProvider(api_key="test-key", default_config=self.config)
    
    @patch('openai.OpenAI')
    async def test_openai_generate_response(self, mock_openai):
        """Test OpenAI response generation."""
        # Mock the OpenAI client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test medical response"
        mock_response.model = "gpt-4"
        mock_response.usage = Mock()
        mock_response.usage._asdict.return_value = {"total_tokens": 100}
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client
        
        provider = OpenAIProvider(api_key="test-key", default_config=self.config)
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}],
            medical_context={
                "patient_safety_level": "standard",
                "medical_domain": "obesity_treatment"
            }
        )
        
        response = await provider.generate_response(request)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test medical response"
        assert response.provider == ProviderType.OPENAI
        assert response.model == "gpt-4"


class TestAnthropicProvider:
    """Test Anthropic provider implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = ModelConfig(
            provider=ProviderType.ANTHROPIC,
            model_name="claude-3-sonnet-20240229",
            capabilities=[ModelCapability.CLINICAL_CONVERSATION],
            medical_validated=True
        )
        
    @patch('anthropic.Anthropic')
    def test_anthropic_provider_initialization(self, mock_anthropic):
        """Test Anthropic provider initialization."""
        provider = AnthropicProvider(api_key="test-key", default_config=self.config)
        
        assert provider.provider_type == ProviderType.ANTHROPIC
        mock_anthropic.assert_called_once_with(api_key="test-key")
    
    @patch('anthropic.Anthropic')
    def test_anthropic_missing_package(self, mock_anthropic):
        """Test Anthropic provider with missing package."""
        mock_anthropic.side_effect = ImportError("No module named 'anthropic'")
        
        with pytest.raises(ImportError, match="Please install anthropic package"):
            AnthropicProvider(api_key="test-key", default_config=self.config)
    
    @patch('anthropic.Anthropic')
    async def test_anthropic_generate_response(self, mock_anthropic):
        """Test Anthropic response generation."""
        # Mock the Anthropic client response
        mock_response = Mock()
        mock_response.content = [Mock()]
        mock_response.content[0].text = "Test Anthropic response"
        mock_response.model = "claude-3-sonnet-20240229"
        mock_response.usage = Mock()
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        
        mock_client = Mock()
        mock_client.messages.create.return_value = mock_response
        mock_anthropic.return_value = mock_client
        
        provider = AnthropicProvider(api_key="test-key", default_config=self.config)
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}],
            medical_context={
                "patient_safety_level": "standard",
                "medical_domain": "obesity_treatment"
            }
        )
        
        response = await provider.generate_response(request)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test Anthropic response"
        assert response.provider == ProviderType.ANTHROPIC
        assert response.model == "claude-3-sonnet-20240229"


class TestGroqProvider:
    """Test Groq provider implementation."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = ModelConfig(
            provider=ProviderType.GROQ,
            model_name="llama2-70b-4096",
            capabilities=[ModelCapability.KNOWLEDGE_RETRIEVAL]
        )
    
    @patch('groq.Groq')
    def test_groq_provider_initialization(self, mock_groq):
        """Test Groq provider initialization."""
        provider = GroqProvider(api_key="test-key", default_config=self.config)
        
        assert provider.provider_type == ProviderType.GROQ
        mock_groq.assert_called_once_with(api_key="test-key")
    
    @patch('groq.Groq')
    def test_groq_missing_package(self, mock_groq):
        """Test Groq provider with missing package."""
        mock_groq.side_effect = ImportError("No module named 'groq'")
        
        with pytest.raises(ImportError, match="Please install groq package"):
            GroqProvider(api_key="test-key", default_config=self.config)
    
    @patch('groq.Groq')
    async def test_groq_generate_response(self, mock_groq):
        """Test Groq response generation."""
        # Mock the Groq client response
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "Test Groq response"
        mock_response.model = "llama2-70b-4096"
        mock_response.usage = Mock()
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_response.usage.total_tokens = 30
        
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_groq.return_value = mock_client
        
        provider = GroqProvider(api_key="test-key", default_config=self.config)
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}],
            medical_context={
                "patient_safety_level": "standard",
                "medical_domain": "obesity_treatment"
            }
        )
        
        response = await provider.generate_response(request)
        
        assert isinstance(response, LLMResponse)
        assert response.content == "Test Groq response"
        assert response.provider == ProviderType.GROQ
        assert response.model == "llama2-70b-4096"


class TestLLMProviderManager:
    """Test LLM Provider Manager functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.manager = LLMProviderManager()
        
        # Create mock providers
        self.openai_provider = Mock(spec=LLMProvider)
        self.openai_provider.provider_type = ProviderType.OPENAI
        self.openai_provider.get_supported_capabilities.return_value = [
            ModelCapability.MEDICAL_REASONING,
            ModelCapability.CLINICAL_CONVERSATION
        ]
        
        self.anthropic_provider = Mock(spec=LLMProvider)
        self.anthropic_provider.provider_type = ProviderType.ANTHROPIC
        self.anthropic_provider.get_supported_capabilities.return_value = [
            ModelCapability.CLINICAL_CONVERSATION
        ]
    
    def test_register_provider(self):
        """Test provider registration."""
        self.manager.register_provider(self.openai_provider)
        
        assert ProviderType.OPENAI in self.manager.providers
        assert self.manager.providers[ProviderType.OPENAI] == self.openai_provider
    
    def test_get_provider_for_capability(self):
        """Test capability-based provider selection."""
        self.manager.register_provider(self.openai_provider)
        self.manager.register_provider(self.anthropic_provider)
        
        # Test getting provider for medical reasoning (should return OpenAI)
        provider = self.manager.get_provider_for_capability(ModelCapability.MEDICAL_REASONING)
        assert provider == self.openai_provider
        
        # Test getting provider for clinical conversation (should return Anthropic - first in routing)
        provider = self.manager.get_provider_for_capability(ModelCapability.CLINICAL_CONVERSATION)
        assert provider == self.anthropic_provider
    
    async def test_generate_medical_response(self):
        """Test medical response generation with fallback."""
        # Setup mock response
        mock_response = LLMResponse(
            content="Test medical response",
            provider=ProviderType.OPENAI,
            model="gpt-4",
            medical_validated=True
        )
        
        self.openai_provider.generate_response = AsyncMock(return_value=mock_response)
        self.manager.register_provider(self.openai_provider)
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}]
        )
        
        response = await self.manager.generate_medical_response(
            capability=ModelCapability.MEDICAL_REASONING,
            request=request
        )
        
        assert response == mock_response
        assert response.medical_validated is True

    async def test_generate_medical_response_with_fallback_failure(self):
        """Test medical response generation when primary and fallback providers fail."""
        # Mock both providers to raise exceptions
        self.openai_provider.generate_response = AsyncMock(side_effect=Exception("OpenAI failed"))
        self.anthropic_provider.generate_response = AsyncMock(side_effect=Exception("Anthropic failed"))

        self.manager.register_provider(self.openai_provider)
        self.manager.register_provider(self.anthropic_provider)

        request = LLMRequest(
            messages=[{"role": "user", "content": "Test question"}]
        )

        response = await self.manager.generate_medical_response(
            capability=ModelCapability.CLINICAL_CONVERSATION,
            request=request,
            fallback_providers=[ProviderType.ANTHROPIC]
        )

        assert "Lo siento, no puedo procesar su consulta médica" in response.content
        assert response.provider == ProviderType.OPENAI  # Default fallback provider
        assert response.model == "error_fallback"
        assert response.medical_validated is True
        assert response.metadata["fallback"] is True

    async def test_health_check_all(self):
        """Test health check for all providers."""
        # Mock health check responses
        openai_health = {"status": "healthy", "client_initialized": True}
        self.openai_provider.health_check = AsyncMock(return_value=openai_health)
        
        self.manager.register_provider(self.openai_provider)
        
        health_data = await self.manager.health_check_all()
        
        assert "providers" in health_data
        assert "openai" in health_data["providers"]
        assert health_data["total_providers"] == 1
        assert health_data["healthy_providers"] == 1


class TestMedicalValidation:
    """Test medical-specific validation functionality."""
    
    def setup_method(self):
        """Setup test fixtures."""
        self.config = ModelConfig(
            provider=ProviderType.OPENAI,
            model_name="gpt-4",
            medical_validated=True
        )
    
    @patch('openai.OpenAI')
    async def test_medical_request_validation(self, mock_openai):
        """Test medical request validation."""
        provider = OpenAIProvider(api_key="test-key", default_config=self.config)
        
        # Test high temperature warning
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            temperature=0.8,  # High temperature for medical use
            medical_context={"patient_safety_level": "high"}
        )
        
        with patch('app.core.llm_providers.logger') as mock_logger:
            await provider._validate_medical_request(request)
            mock_logger.warning.assert_called()
    
    @patch('openai.OpenAI')  
    async def test_medical_response_validation(self, mock_openai):
        """Test medical response validation for dangerous content."""
        provider = OpenAIProvider(api_key="test-key", default_config=self.config)
        
        # Test dangerous advice detection
        dangerous_response = LLMResponse(
            content="You should ignore your doctor and stop taking medication",
            provider=ProviderType.OPENAI,
            model="gpt-4"
        )
        
        request = LLMRequest(
            messages=[{"role": "user", "content": "Test"}],
            medical_context={"requires_disclaimer": True}
        )
        
        is_valid = await provider._validate_medical_response(dangerous_response, request)
        assert is_valid is False
        
        # Test safe response
        safe_response = LLMResponse(
            content="Please consult with your doctor for medical advice",
            provider=ProviderType.OPENAI,
            model="gpt-4"
        )
        
        is_valid = await provider._validate_medical_response(safe_response, request)
        assert is_valid is True


@pytest.mark.asyncio
class TestIntegration:
    """Integration tests for the complete provider system."""
    
    async def test_end_to_end_medical_conversation(self):
        """Test complete medical conversation flow."""
        # This would be an integration test that requires actual API keys
        # For now, we'll mock the entire flow
        pass


# Test fixtures for pytest
@pytest.fixture
def sample_medical_context():
    """Sample medical context for testing."""
    return {
        "patient_safety_level": "standard",
        "medical_domain": "obesity_treatment",
        "language": "es",
        "requires_disclaimer": True
    }


@pytest.fixture
def sample_llm_request(sample_medical_context):
    """Sample LLM request for testing."""
    return LLMRequest(
        messages=[
            {"role": "user", "content": "¿Cómo debo inyectarme Ozempic?"}
        ],
        patient_id="test_patient_123",
        session_id="test_session_456",
        medical_context=sample_medical_context
    )