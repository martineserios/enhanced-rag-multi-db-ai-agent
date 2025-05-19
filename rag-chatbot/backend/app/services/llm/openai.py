# filepath: backend/services/llm/openai.py
"""
OpenAI LLM service implementation.

This module implements the LLM service interface for OpenAI models like GPT-4
and GPT-3.5-Turbo using the OpenAI API.
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
import json
import logging

from openai import AsyncOpenAI, APIError, RateLimitError
import tiktoken

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings
from app.services.llm.base import LLMService, ModelType


logger = get_logger(__name__)

class OpenAIService(LLMService):
    """
    OpenAI implementation of the LLM service.
    
    This class provides access to OpenAI's GPT models through the OpenAI API.
    
    Attributes:
        client: OpenAI API client
        model: Currently configured model
        embedding_model: Model used for embeddings
        tokenizer: Tokenizer for counting tokens
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the OpenAI LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If OpenAI API key is missing or invalid
        """
        super().__init__(settings)
        
        # Configure retry settings
        self.retry_attempts = getattr(settings, 'llm_retry_attempts', 3)
        self.retry_delay = getattr(settings, 'llm_retry_delay', 1.0)  # seconds
        
        # Validate provider settings
        self._validate_provider_settings()
        
        # Initialize client
        try:
            self.client = AsyncOpenAI(api_key=self.settings.openai_api_key)
            
            # Model settings
            self.model = self.settings.openai_model
            self.embedding_model = "text-embedding-3-small"
            
            # Get tokenizer for the model
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fall back to cl100k_base for newer models
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(
                f"Initialized OpenAI service with model: {self.model}, "
                f"retry_attempts={self.retry_attempts}, retry_delay={self.retry_delay}s"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize OpenAI client")
            raise LLMProviderError(f"OpenAI client initialization failed: {str(e)}")
    
    def _validate_provider_settings(self) -> None:
        """
        Validate OpenAI provider settings.
        
        Raises:
            LLMProviderError: If required settings are missing or invalid
        """
        if not self.settings.openai_api_key:
            raise LLMProviderError("OpenAI API key is required")
        if not self.settings.openai_model:
            raise LLMProviderError("OpenAI model is required")
    
    async def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get information about available OpenAI models.
        
        Args:
            model_type: Type of model to get info for
            
        Returns:
            Dictionary containing model information
            
        Raises:
            LLMProviderError: If model information cannot be retrieved
        """
        try:
            # Get model list from API
            models = await self.client.models.list()
            
            # Filter by model type
            if model_type == ModelType.CHAT:
                return {
                    "models": [
                        m for m in models.data if m.id.startswith("gpt")
                    ]
                }
            elif model_type == ModelType.TEXT:
                return {
                    "models": [
                        m for m in models.data if m.id.startswith("text")
                    ]
                }
            elif model_type == ModelType.EMBEDDING:
                return {
                    "models": [
                        m for m in models.data if m.id.startswith("text-embedding")
                    ]
                }
            
            return {"models": []}
            
        except Exception as e:
            self.logger.exception("Failed to get model information")
            raise LLMProviderError(f"Failed to get model information: {str(e)}")
        
        # Check for API key
        if not settings.openai_api_key:
            raise LLMProviderError("OpenAI API key is required")
        
        # Initialize client
        try:
            self.client = AsyncOpenAI(api_key=settings.openai_api_key)
            
            # Model settings
            self.model = settings.openai_model
            self.embedding_model = "text-embedding-3-small"
            
            # Get tokenizer for the model
            try:
                self.tokenizer = tiktoken.encoding_for_model(self.model)
            except KeyError:
                # Fall back to cl100k_base for newer models
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(f"Initialized OpenAI service with model: {self.model}")
            
        except Exception as e:
            self.logger.exception("Failed to initialize OpenAI client")
            raise LLMProviderError(f"OpenAI client initialization failed: {str(e)}")
    
    @log_execution_time(logger)
    async def generate_text(
        self, 
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt using OpenAI's completions API.
        
        Args:
            prompt: The prompt to generate text from
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 to 1.0)
            **kwargs: Additional parameters for the API
            
        Returns:
            The generated text
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
            # Use provided model or default
            model = model or self.model
            
            # Create a timeout
            timeout = kwargs.pop("timeout", self.request_timeout)
            
            # Make the API call
            response = await self._execute_with_retry(
                self.client.completions.create(
                    model=model,
                    prompt=prompt,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    timeout=timeout,
                    **kwargs
                ),
                error_type=APIError,
                error_message="Failed to generate text with OpenAI"
            )
            
            # Extract the generated text
            generated_text = response.choices[0].text.strip()
            
            # Track token usage
            tokens = await self.count_tokens(prompt + generated_text)
            self._update_usage_stats(tokens)
            
            return generated_text
            
        except RateLimitError as e:
            self.logger.warning(f"OpenAI rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise LLMRequestError(f"OpenAI API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"OpenAI request timed out after {timeout} seconds")
            raise LLMRequestError(f"OpenAI request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating text")
            raise LLMRequestError(f"Failed to generate text with OpenAI: {str(e)}")
    
    @log_execution_time(logger)
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation using OpenAI's chat API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Controls randomness (0.0 to 1.0)
            **kwargs: Additional parameters for the API
            
        Returns:
            The generated response
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        # Use provided model or default
        model = model or self.model
        
        # Filter out any unexpected keys in messages
        filtered_messages = []
        for message in messages:
            filtered_message = {
                "role": message["role"],
                "content": message["content"]
            }
            filtered_messages.append(filtered_message)
        
        # Create a timeout
        timeout = kwargs.pop("timeout", self.request_timeout)
        
        try:
            # Make the API call with retry logic
            response = await self._execute_with_retry(
                self.client.chat.completions.create,
                error_type=APIError,
                error_message="Failed to generate chat response with OpenAI",
                model=model,
                messages=filtered_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.choices[0].message.content.strip()
            
            # Track token usage
            tokens = await self.count_tokens(generated_text)
            self._update_usage_stats(tokens)
            
            self.logger.debug(
                "Generated chat response",
                extra={
                    "model": self.model,
                    "message_count": len(messages),
                    "response_length": len(generated_text)
                }
            )
            
            return generated_text
            
        except RateLimitError as e:
            self.logger.warning(f"OpenAI rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise LLMRequestError(f"OpenAI API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"OpenAI request timed out after {timeout} seconds")
            raise LLMRequestError(f"OpenAI request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating chat response")
            raise LLMRequestError(f"Failed to generate chat response with OpenAI: {str(e)}")
    
    async def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text using tiktoken.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
            
        Raises:
            LLMRequestError: If token counting fails
        """
        try:
            return len(self.tokenizer.encode(text))
        except Exception as e:
            self.logger.warning(f"Failed to count tokens: {str(e)}")
            raise LLMRequestError(f"Failed to count tokens: {str(e)}")
    
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding vector for a text using OpenAI's embedding API.
        
        Args:
            text: The text to get embedding for
            
        Returns:
            List of float values representing the embedding
            
        Raises:
            LLMRequestError: If embedding generation fails
        """
        try:
            # Create a timeout
            timeout = self.request_timeout
            
            # Make the API call
            response = await self._execute_with_retry(
                self.client.embeddings.create(
                    model=self.embedding_model,
                    input=text,
                    timeout=timeout
                ),
                error_type=APIError,
                error_message="Failed to generate embedding with OpenAI"
            )
            
            # Extract the embedding
            embedding = response.data[0].embedding
            
            # Track token usage
            tokens = await self.count_tokens(text)
            self._update_usage_stats(tokens)
            
            return embedding
            
        except RateLimitError as e:
            self.logger.warning(f"OpenAI rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise LLMRequestError(f"OpenAI API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"OpenAI request timed out after {timeout} seconds")
            raise LLMRequestError(f"OpenAI request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating embedding")
            raise LLMRequestError(f"Failed to generate embedding with OpenAI: {str(e)}")
    
    @log_execution_time(logger)
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding vector for a text using OpenAI's embeddings API.
        
        Args:
            text: The text to get an embedding for
            
        Returns:
            The embedding vector
            
        Raises:
            LLMRequestError: If getting the embedding fails
        """
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            
            # Extract the embedding
            embedding = response.data[0].embedding
            
            return embedding
            
        except Exception as e:
            self.logger.exception("Error getting embedding")
            raise LLMRequestError(f"Failed to get embedding with OpenAI: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if the OpenAI service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Try a simple model list request
            await self.client.models.list()
            return True
        except Exception as e:
            self.logger.error(f"OpenAI health check failed: {str(e)}")
            return False