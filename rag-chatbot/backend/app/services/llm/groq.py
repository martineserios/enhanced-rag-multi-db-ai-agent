# filepath: backend/services/llm/groq.py
"""
Groq LLM service implementation.

This module implements the LLM service interface for Groq-hosted models
using the Groq API.
"""
import time
import asyncio
from typing import Dict, List, Any, Optional, Union
import json
import logging
import aiohttp

from groq import AsyncGroq, APIError
import tiktoken

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings
from app.services.llm.base import LLMService, ModelType


logger = get_logger(__name__)

class GroqService(LLMService):
    """
    Groq implementation of the LLM service.
    
    This class provides access to Groq-hosted models through the Groq API.
    
    Attributes:
        client: Groq API client
        model: Currently configured model
        tokenizer: Tokenizer for counting tokens
        session: aiohttp client session for making HTTP requests
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Groq LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If Groq API key is missing or invalid
        """
        super().__init__(settings)
        
        # Configure retry settings
        self.retry_attempts = getattr(settings, 'llm_retry_attempts', 3)
        self.retry_delay = getattr(settings, 'llm_retry_delay', 1.0)  # seconds
        
        # Initialize aiohttp session
        self.session = aiohttp.ClientSession()
        
        # Validate provider settings
        self._validate_provider_settings()
        
        # Initialize client
        try:
            self.client = AsyncGroq(api_key=self.settings.groq_api_key)
            
            # Model settings
            self.model = self.settings.groq_model
            
            # Use tiktoken for approximately counting tokens
            try:
                self.tokenizer = tiktoken.encoding_for_model("cl100k_base")
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(
                f"Initialized Groq service with model: {self.model}, "
                f"retry_attempts={self.retry_attempts}, retry_delay={self.retry_delay}s"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize Groq client")
            raise LLMProviderError(f"Groq client initialization failed: {str(e)}")
    
    def _validate_provider_settings(self) -> None:
        """
        Validate Groq provider settings.
        
        Raises:
            LLMProviderError: If required settings are missing or invalid
        """
        if not self.settings.groq_api_key:
            raise LLMProviderError("Groq API key is required")
        if not self.settings.groq_model:
            raise LLMProviderError("Groq model is required")
    
    async def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get information about available Groq models.
        
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
                        m for m in models if m.id.startswith("llama")
                    ]
                }
            elif model_type == ModelType.TEXT:
                return {
                    "models": [
                        m for m in models if m.id.startswith("llama")
                    ]
                }
            elif model_type == ModelType.EMBEDDING:
                return {"models": []}  # Groq doesn't support embeddings yet
            
            return {"models": []}
            
        except Exception as e:
            self.logger.exception("Failed to get model information")
            raise LLMProviderError(f"Failed to get model information: {str(e)}")
        
        # Check for API key
        if not settings.groq_api_key:
            raise LLMProviderError("Groq API key is required")
        
        # Initialize client
        try:
            self.client = AsyncGroq(api_key=settings.groq_api_key)
            
            # Model settings
            self.model = settings.groq_model
            
            # Use tiktoken for approximately counting tokens
            try:
                self.tokenizer = tiktoken.encoding_for_model("cl100k_base")
            except KeyError:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            
            self.logger.info(f"Initialized Groq service with model: {self.model}")
            
        except Exception as e:
            self.logger.exception("Failed to initialize Groq client")
            raise LLMProviderError(f"Groq client initialization failed: {str(e)}")
    
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
        Generate text from a prompt using Groq's completions API.
        
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
            
            # Create messages from prompt for compatibility with chat models
            messages = [{"role": "user", "content": prompt}]
            
            # Generate response using the chat API
            return await self.generate_chat_response(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
        except Exception as e:
            if not isinstance(e, (LLMRequestError, LLMRateLimitError)):
                self.logger.exception("Unexpected error generating text")
                raise LLMRequestError(f"Failed to generate text with Groq: {str(e)}")
            raise
    
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
        Generate a chat response using Groq's chat completion API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the Groq API
            
        Returns:
            The generated response text
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
            # Use provided model or default
            model_name = model or self.model
            
            # Make the API request using the client
            response = await self.client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Extract the response text
            if not response.choices:
                raise LLMRequestError("No response generated from Groq")
            
            return response.choices[0].message.content
                
        except APIError as e:
            if "rate_limit" in str(e).lower():
                raise LLMRateLimitError("Rate limit exceeded for Groq API")
            self.logger.error(f"Groq API request failed: {str(e)}")
            raise LLMRequestError(f"Failed to generate response: {str(e)}")
        except asyncio.TimeoutError:
            self.logger.error("Groq API request timed out")
            raise LLMRequestError("Request timed out")
        except Exception as e:
            self.logger.exception("Unexpected error in Groq chat completion")
            raise LLMRequestError(f"Failed to generate response: {str(e)}")
    
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
        Get an embedding vector for a text.
        
        Note: Groq doesn't support embeddings yet, so this method raises
        an error.
        Groq doesn't currently provide an embeddings API, so this method
        raises an error.
        
        Args:
            text: The text to get an embedding for
            
        Raises:
            LLMRequestError: Always, as embeddings are not supported
        """
        raise LLMRequestError("Groq does not provide an embeddings API")
    
    async def health_check(self) -> bool:
        """
        Check if the Groq service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        try:
            # Try a simple request with minimal tokens
            await self.client.chat.completions.create(
                model=self.model,
                max_tokens=1,
                messages=[
                    {"role": "user", "content": "Hi"}
                ]
            )
            return True
        except Exception as e:
            self.logger.error(f"Groq health check failed: {str(e)}")
            return False

    async def close(self) -> None:
        """Close the aiohttp session."""
        if hasattr(self, 'session'):
            await self.session.close()
            self.logger.info("Closed Groq service session")