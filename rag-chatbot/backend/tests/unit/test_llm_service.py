# filepath: backend/tests/unit/test_llm_service.py
"""
Unit tests for the LLM Service.

This module tests the LLM service implementations and factory functions.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
import json

from app.services.llm.base import LLMService
from app.services.llm.factory import get_llm_service, check_llm_providers, close_llm_services
from app.services.llm.openai import OpenAIService
from app.services.llm.anthropic import AnthropicService
from app.services.llm.groq import GroqService
from app.core.exceptions import LLMError, LLMProviderError, LLMRequestError


@pytest.mark.asyncio
async def test_llm_factory(test_settings):
    """Test the LLM factory functions."""
    # Test getting OpenAI service
    with patch('app.services.llm.factory.OpenAIService') as MockOpenAI:
        mock_instance = MagicMock()
        MockOpenAI.return_value = mock_instance
        
        service = get_llm_service("openai", test_settings)
        
        MockOpenAI.assert_called_once_with(test_settings)
        assert service is mock_instance
    
    # Test getting Anthropic service
    with patch('app.services.llm.factory.AnthropicService') as MockAnthropic:
        mock_instance = MagicMock()
        MockAnthropic.return_value = mock_instance
        
        service = get_llm_service("anthropic", test_settings)
        
        MockAnthropic.assert_called_once_with(test_settings)
        assert service is mock_instance
    
    # Test getting Groq service
    with patch('app.services.llm.factory.GroqService') as MockGroq:
        mock_instance = MagicMock()
        MockGroq.return_value = mock_instance
        
        service = get_llm_service("groq", test_settings)
        
        MockGroq.assert_called_once_with(test_settings)
        assert service is mock_instance
    
    # Test getting an unsupported provider
    with pytest.raises(LLMProviderError):
        get_llm_service("unsupported", test_settings)
    
    # Test getting a provider without an API key
    with patch('app.services.llm.factory.GroqService') as MockGroq:
        test_settings.groq_api_key = None
        with pytest.raises(LLMProviderError):
            get_llm_service("groq", test_settings)


@pytest.mark.asyncio
async def test_check_llm_providers(test_settings):
    """Test checking LLM provider availability."""
    # Mock the get_llm_service function and health checks
    with patch('app.services.llm.factory.get_llm_service') as mock_get_service:
        # Create mock services
        openai_service = MagicMock()
        openai_service.health_check = AsyncMock(return_value=True)
        
        anthropic_service = MagicMock()
        anthropic_service.health_check = AsyncMock(return_value=True)
        
        groq_service = MagicMock()
        groq_service.health_check = AsyncMock(return_value=False)
        
        # Configure mock to return different services
        def get_service_side_effect(provider, settings):
            if provider == "openai":
                return openai_service
            elif provider == "anthropic":
                return anthropic_service
            elif provider == "groq":
                return groq_service
            
        mock_get_service.side_effect = get_service_side_effect
        
        # Check provider availability
        results = await check_llm_providers(test_settings)
        
        # Verify results
        assert results["openai"] is True
        assert results["anthropic"] is True
        assert results["groq"] is False
        
        # Verify health checks were called
        openai_service.health_check.assert_called_once()
        anthropic_service.health_check.assert_called_once()
        groq_service.health_check.assert_called_once()
        
        # Test with a provider that raises an exception
        mock_get_service.side_effect = None
        anthropic_service.health_check.side_effect = Exception("Test exception")
        mock_get_service.return_value = anthropic_service
        
        results = await check_llm_providers(test_settings)
        
        # The result should be False for the provider that raised an exception
        assert results["anthropic"] is False


@pytest.mark.asyncio
async def test_openai_service(test_settings):
    """Test the OpenAI service implementation."""
    # Mock the AsyncOpenAI client
    with patch('app.services.llm.openai.AsyncOpenAI') as MockClient, \
         patch('app.services.llm.openai.tiktoken.encoding_for_model') as mock_encoding:
        
        # Create mock objects
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_encoding.return_value = mock_tokenizer
        
        # Test initialization
        service = OpenAIService(test_settings)
        
        MockClient.assert_called_once_with(api_key=test_settings.openai_api_key)
        assert service.model == test_settings.openai_model
        
        # Test generating chat response
        mock_chat = MagicMock()
        mock_client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_client.chat.completions.create.return_value = mock_response
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        response = await service.generate_chat_response(messages)
        
        assert response == "Generated response"
        mock_client.chat.completions.create.assert_called_once()
        
        # Test token counting
        token_count = await service.count_tokens("This is a test")
        
        assert token_count == 5
        mock_tokenizer.encode.assert_called_once_with("This is a test")
        
        # Test getting embeddings
        mock_client.embeddings.create = AsyncMock()
        mock_embedding_response = MagicMock()
        mock_embedding_response.data = [MagicMock()]
        mock_embedding_response.data[0].embedding = [0.1, 0.2, 0.3]
        mock_client.embeddings.create.return_value = mock_embedding_response
        
        embedding = await service.get_embedding("This is a test")
        
        assert embedding == [0.1, 0.2, 0.3]
        mock_client.embeddings.create.assert_called_once()


@pytest.mark.asyncio
async def test_anthropic_service(test_settings):
    """Test the Anthropic service implementation."""
    # Mock the AsyncAnthropic client
    with patch('app.services.llm.anthropic.AsyncAnthropic') as MockClient, \
         patch('app.services.llm.anthropic.tiktoken.encoding_for_model') as mock_encoding:
        
        # Create mock objects
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_encoding.return_value = mock_tokenizer
        
        # Test initialization
        service = AnthropicService(test_settings)
        
        MockClient.assert_called_once_with(api_key=test_settings.anthropic_api_key)
        assert service.model == test_settings.anthropic_model
        
        # Test generating chat response
        mock_client.messages.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock()]
        mock_response.content[0].text = "Generated response"
        mock_client.messages.create.return_value = mock_response
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        response = await service.generate_chat_response(messages)
        
        assert response == "Generated response"
        mock_client.messages.create.assert_called_once()
        
        # Test token counting
        token_count = await service.count_tokens("This is a test")
        
        assert token_count == 5
        mock_tokenizer.encode.assert_called_once_with("This is a test")
        
        # Test getting embeddings (should raise an error)
        with pytest.raises(LLMRequestError):
            await service.get_embedding("This is a test")


@pytest.mark.asyncio
async def test_groq_service(test_settings):
    """Test the Groq service implementation."""
    # Mock the AsyncGroq client
    with patch('app.services.llm.groq.AsyncGroq') as MockClient, \
         patch('app.services.llm.groq.tiktoken.encoding_for_model') as mock_encoding:
        
        # Create mock objects
        mock_client = MagicMock()
        MockClient.return_value = mock_client
        
        mock_tokenizer = MagicMock()
        mock_tokenizer.encode.return_value = [1, 2, 3, 4, 5]  # 5 tokens
        mock_encoding.return_value = mock_tokenizer
        
        # Test initialization
        service = GroqService(test_settings)
        
        MockClient.assert_called_once_with(api_key=test_settings.groq_api_key)
        assert service.model == test_settings.groq_model
        
        # Test generating chat response
        mock_client.chat.completions.create = AsyncMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Generated response"
        mock_client.chat.completions.create.return_value = mock_response
        
        messages = [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": "Hello, how are you?"}
        ]
        
        # Mock asyncio.wait_for to return the response directly
        with patch('app.services.llm.groq.asyncio.wait_for', new=AsyncMock()) as mock_wait_for:
            mock_wait_for.return_value = mock_response
            
            response = await service.generate_chat_response(messages)
            
            assert response == "Generated response"
            mock_client.chat.completions.create.assert_called_once()
        
        # Test token counting
        token_count = await service.count_tokens("This is a test")
        
        assert token_count == 5
        mock_tokenizer.encode.assert_called_once_with("This is a test")
        
        # Test getting embeddings (should raise an error)
        with pytest.raises(LLMRequestError):
            await service.get_embedding("This is a test")


@pytest.mark.asyncio
async def test_llm_base_generate_response(mock_llm_service):
    """Test the generate_response method in the LLM base class."""
    # Test generating response without context
    mock_llm_service.generate_chat_response_mock.return_value = "Response without context"
    
    response = await mock_llm_service.generate_response("Hello")
    
    assert response == "Response without context"
    mock_llm_service.generate_chat_response_mock.assert_called_once()
    
    # Check that the messages include the query
    messages = mock_llm_service.generate_chat_response_mock.call_args[0][0]
    assert len(messages) == 2  # System message and user message
    assert messages[0]["role"] == "system"
    assert messages[1]["role"] == "user"
    assert messages[1]["content"] == "Hello"
    
    # Test generating response with context
    mock_llm_service.generate_chat_response_mock.reset_mock()
    mock_llm_service.generate_chat_response_mock.return_value = "Response with context"
    
    response = await mock_llm_service.generate_response(
        "Hello",
        context="This is some context information."
    )
    
    assert response == "Response with context"
    mock_llm_service.generate_chat_response_mock.assert_called_once()
    
    # Check that the system message includes the context
    messages = mock_llm_service.generate_chat_response_mock.call_args[0][0]
    assert len(messages) == 2
    assert "This is some context information." in messages[0]["content"]
    
    # Test with retries on rate limit error
    mock_llm_service.generate_chat_response_mock.reset_mock()
    mock_llm_service.generate_chat_response_mock.side_effect = [
        LLMRequestError("Rate limit exceeded"),  # First attempt fails
        "Response after retry"                   # Second attempt succeeds
    ]
    
    # Configure retry settings
    mock_llm_service.retry_attempts = 2
    mock_llm_service.retry_delay = 0.01  # Short delay for testing
    
    response = await mock_llm_service.generate_response("Hello")
    
    assert response == "Response after retry"
    assert mock_llm_service.generate_chat_response_mock.call_count == 2
    
    # Test with all retries failing
    mock_llm_service.generate_chat_response_mock.reset_mock()
    mock_llm_service.generate_chat_response_mock.side_effect = LLMRequestError("Rate limit exceeded")
    
    with pytest.raises(LLMRequestError):
        await mock_llm_service.generate_response("Hello")
    
    assert mock_llm_service.generate_chat_response_mock.call_count == mock_llm_service.retry_attempts