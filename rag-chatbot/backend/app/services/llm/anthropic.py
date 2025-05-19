# filepath: backend/services/llm/anthropic.py
"""
Anthropic LLM service implementation.

This module implements the LLM service interface for Anthropic Claude models
using the Anthropic API.
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
import json
import re
import logging

import anthropic
from anthropic import Anthropic, AsyncAnthropic, APIError, RateLimitError
import tiktoken

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings
from app.services.llm.base import LLMService, ModelType


logger = get_logger(__name__)

class AnthropicService(LLMService):
    """
    Anthropic implementation of the LLM service.
    
    This class provides access to Anthropic Claude models through the Anthropic API.
    
    Attributes:
        client: Anthropic API client
        model: Currently configured model
        tokenizer: Tokenizer for counting tokens
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Anthropic LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If Anthropic API key is missing or invalid
        """
        super().__init__(settings)
        
        # Configure retry settings
        self.retry_attempts = getattr(settings, 'llm_retry_attempts', 3)
        self.retry_delay = getattr(settings, 'llm_retry_delay', 1.0)  # seconds
        
        # Validate provider settings
        self._validate_provider_settings()
        
        # Initialize client
        try:
            self.client = AsyncAnthropic(api_key=self.settings.anthropic_api_key)
            
            # Model settings
            self.model = self.settings.anthropic_model
            
            # Use tiktoken for approximately counting tokens
            try:
                self.tokenizer = tiktoken.encoding_for_model("cl100k_base")
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(
                f"Initialized Anthropic service with model: {self.model}, "
                f"retry_attempts={self.retry_attempts}, retry_delay={self.retry_delay}s"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize Anthropic client")
            raise LLMProviderError(f"Anthropic client initialization failed: {str(e)}")
    
    def _validate_provider_settings(self) -> None:
        """
        Validate Anthropic provider settings.
        
        Raises:
            LLMProviderError: If required settings are missing or invalid
        """
        if not self.settings.anthropic_api_key:
            raise LLMProviderError("Anthropic API key is required")
        if not self.settings.anthropic_model:
            raise LLMProviderError("Anthropic model is required")
    
    async def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get information about available Anthropic models.
        
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
                        m for m in models if m.id.startswith("claude")
                    ]
                }
            elif model_type == ModelType.TEXT:
                return {
                    "models": [
                        m for m in models if m.id.startswith("claude")
                    ]
                }
            elif model_type == ModelType.EMBEDDING:
                return {"models": []}  # Anthropic doesn't support embeddings yet
            
            return {"models": []}
            
        except Exception as e:
            self.logger.exception("Failed to get model information")
            raise LLMProviderError(f"Failed to get model information: {str(e)}")
        
        # Check for API key
        if not settings.anthropic_api_key:
            raise LLMProviderError("Anthropic API key is required")
        
        # Initialize client
        try:
            self.client = AsyncAnthropic(api_key=settings.anthropic_api_key)
            
            # Model settings
            self.model = settings.anthropic_model
            
            # Use tiktoken for approximately counting tokens
            # Claude uses a different tokenizer, but this is a reasonable approximation
            try:
                self.tokenizer = tiktoken.encoding_for_model("cl100k_base")
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(f"Initialized Anthropic service with model: {self.model}")
            
        except Exception as e:
            self.logger.exception("Failed to initialize Anthropic client")
            raise LLMProviderError(f"Anthropic client initialization failed: {str(e)}")
    
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
        Generate text from a prompt using Anthropic's completions API.
        
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
            
            # Format prompt as expected by Anthropic
            formatted_prompt = f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}"
            
            # Create a timeout
            timeout = kwargs.pop("timeout", self.request_timeout)
            
            # Make the API call
            response = await self._execute_with_retry(
                self.client.completions.create(
                    model=model,
                    prompt=formatted_prompt,
                    temperature=temperature,
                    max_tokens_to_sample=max_tokens,
                    timeout=timeout,
                    **kwargs
                ),
                error_type=APIError,
                error_message="Failed to generate text with Anthropic"
            )
            
            # Extract the generated text
            generated_text = response.completion.strip()
            
            # Track token usage
            tokens = await self.count_tokens(prompt + generated_text)
            self._update_usage_stats(tokens)
            
            return generated_text
            
        except RateLimitError as e:
            self.logger.warning(f"Anthropic rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            raise LLMRequestError(f"Anthropic API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"Anthropic request timed out after {timeout} seconds")
            raise LLMRequestError(f"Anthropic request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating text")
            raise LLMRequestError(f"Failed to generate text with Anthropic: {str(e)}")
    
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
        Generate a response in a chat conversation using Anthropic's messages API.
        
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
        
        # Convert OpenAI-style messages to Anthropic format
        formatted_messages = []
        
        system_content = None
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                system_content = content
            elif role == "user":
                formatted_messages.append({
                    "role": "user",
                    "content": content
                })
            elif role == "assistant":
                formatted_messages.append({
                    "role": "assistant",
                    "content": content
                })
            # Ignore any other roles
        
        # Create a timeout
        timeout = kwargs.pop("timeout", self.request_timeout)
        
        try:
            # Make the API call with retry logic
            response = await self._execute_with_retry(
                self.client.messages.create,
                error_type=APIError,
                error_message="Failed to generate chat response with Anthropic",
                model=model,
                messages=formatted_messages,
                system=system_content,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.content[0].text
            
            # Track token usage
            tokens = await self.count_tokens(generated_text)
            self._update_usage_stats(tokens)
            
            return generated_text
            
        except RateLimitError as e:
            self.logger.warning(f"Anthropic rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            raise LLMRequestError(f"Anthropic API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"Anthropic request timed out after {timeout} seconds")
            raise LLMRequestError(f"Anthropic request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating chat response")
            raise LLMRequestError(f"Failed to generate chat response with Anthropic: {str(e)}")
            
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
            self.logger.warning(f"Anthropic rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"Anthropic rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"Anthropic API error: {str(e)}")
            raise LLMRequestError(f"Anthropic API error: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error(f"Anthropic request timed out after {timeout} seconds")
            raise LLMRequestError(f"Anthropic request timed out after {timeout} seconds")
        except Exception as e:
            self.logger.exception("Unexpected error generating chat response")
            raise LLMRequestError(f"Failed to generate chat response with Anthropic: {str(e)}")
    
    async def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text using tiktoken.
        
        Note: This is an approximation since Anthropic uses a different tokenizer,
        but it's a reasonable estimate for rate limiting purposes.
        
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
        Get an embedding vector for a text.
        
        Note: Anthropic doesn't support embeddings yet, so this method raises
        an error.
        Anthropic doesn't currently provide an embeddings API, so this method
        raises an error.
        
        Args:
            text: The text to get an embedding for
            
        Raises:
            LLMRequestError: Always, as embeddings are not supported
        """
        raise LLMRequestError("Anthropic does not provide an embeddings API")
    
    async def health_check(self) -> bool:
        """
        Check if the Anthropic service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Try a simple request with minimal tokens
            await self.client.messages.create(
                model=self.model,
                max_tokens=1,
                messages=[
                    {"role": "user", "content": "Hi"}
                ]
            )
            return True
        except Exception as e:
            self.logger.error(f"Anthropic health check failed: {str(e)}")
            return False