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
from app.services.llm.base import LLMService


logger = get_logger(__name__)

class OpenAIService(LLMService):
    """
    OpenAI implementation of the LLM service.
    
    This class:
    1. Connects to OpenAI's API
    2. Manages API key authentication
    3. Handles token counting and rate limiting
    4. Provides access to GPT models and embeddings
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the OpenAI LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If OpenAI API key is missing or invalid
        """
        super().__init__("openai", settings)
        
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
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt using OpenAI's completions API.
        
        Args:
            prompt: The prompt to generate text from
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            The generated text
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
            response = await self.client.completions.create(
                model=self.model,
                prompt=prompt,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.choices[0].text.strip()
            
            # Update token usage
            if hasattr(response, "usage") and hasattr(response.usage, "total_tokens"):
                self.token_count += response.usage.total_tokens
            
            return generated_text
            
        except RateLimitError as e:
            self.logger.warning(f"OpenAI rate limit exceeded: {str(e)}")
            raise LLMRateLimitError(f"OpenAI rate limit exceeded: {str(e)}")
        except APIError as e:
            self.logger.error(f"OpenAI API error: {str(e)}")
            raise LLMRequestError(f"OpenAI API error: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error generating text")
            raise LLMRequestError(f"Failed to generate text with OpenAI: {str(e)}")
    
    @log_execution_time(logger)
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation using OpenAI's chat API.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Controls randomness (0.0 to 1.0)
            max_tokens: Maximum number of tokens to generate
            **kwargs: Additional parameters for the API
            
        Returns:
            The generated response
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
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
            
            # Make the API call
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=filtered_messages,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.choices[0].message.content.strip()
            
            # Update token usage
            if hasattr(response, "usage") and hasattr(response.usage, "total_tokens"):
                self.token_count += response.usage.total_tokens
            
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
        """
        try:
            tokens = self.tokenizer.encode(text)
            return len(tokens)
        except Exception as e:
            self.logger.warning(f"Error counting tokens: {str(e)}")
            # Fall back to rough estimate
            return len(text) // 4
    
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