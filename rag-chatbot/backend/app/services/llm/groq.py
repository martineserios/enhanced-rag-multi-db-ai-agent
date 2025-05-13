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

from groq import AsyncGroq, APIError
import tiktoken

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings
from app.services.llm.base import LLMService


logger = get_logger(__name__)

class GroqService(LLMService):
    """
    Groq implementation of the LLM service.
    
    This class:
    1. Connects to Groq's API
    2. Manages API key authentication
    3. Handles token counting and rate limiting
    4. Provides access to LLM models like Llama hosted on Groq
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Groq LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If Groq API key is missing or invalid
        """
        super().__init__("groq", settings)
        
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
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt using Groq's completions API.
        
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
            # Create messages from prompt for compatibility with chat models
            messages = [{"role": "user", "content": prompt}]
            
            # Generate response using the chat API
            return await self.generate_chat_response(
                messages=messages,
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
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation using Groq's chat API.
        
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
            system_message = None
            
            for message in messages:
                role = message["role"]
                content = message["content"]
                
                if role == "system":
                    system_message = content
                else:
                    filtered_message = {
                        "role": role,
                        "content": content
                    }
                    filtered_messages.append(filtered_message)
            
            # If we have a system message, add it as the first message
            if system_message:
                filtered_messages.insert(0, {
                    "role": "system",
                    "content": system_message
                })
            
            # Create a timeout
            timeout = kwargs.pop("timeout", self.request_timeout)
            
            # Make the API call
            response = await asyncio.wait_for(
                self.client.chat.completions.create(
                    model=self.model,
                    messages=filtered_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    **kwargs
                ),
                timeout=timeout
            )
            
            # Extract the generated text
            generated_text = response.choices[0].message.content.strip()
            
            # Approximately track token usage
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
            
        except asyncio.TimeoutError:
            self.logger.error(f"Groq request timed out after {timeout} seconds")
            raise LLMRequestError(f"Groq request timed out after {timeout} seconds")
        except APIError as e:
            if "rate limit" in str(e).lower():
                self.logger.warning(f"Groq rate limit exceeded: {str(e)}")
                raise LLMRateLimitError(f"Groq rate limit exceeded: {str(e)}")
            else:
                self.logger.error(f"Groq API error: {str(e)}")
                raise LLMRequestError(f"Groq API error: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error generating chat response")
            raise LLMRequestError(f"Failed to generate chat response with Groq: {str(e)}")
    
    async def count_tokens(self, text: str) -> int:
        """
        Approximately count the number of tokens in a text using cl100k_base.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The approximate number of tokens
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
        Get an embedding vector for a text.
        
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