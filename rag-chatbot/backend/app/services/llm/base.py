# filepath: backend/services/llm/base.py
"""
Base class for LLM service implementations.

This module defines the interface for all LLM services using the Strategy pattern,
allowing different LLM providers to be used interchangeably.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union
import logging
import time
import asyncio
from datetime import datetime

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings


logger = get_logger(__name__)

class LLMService(ABC):
    """
    Abstract base class for LLM services.
    
    This class defines the interface that all LLM service implementations must follow,
    regardless of the specific provider (OpenAI, Anthropic, Groq, etc.).
    """
    
    def __init__(self, provider_name: str, settings: Settings):
        """
        Initialize the LLM service.
        
        Args:
            provider_name: Name of the LLM provider
            settings: Application configuration settings
        """
        self.provider_name = provider_name
        self.settings = settings
        self.logger = get_logger(f"llm.{provider_name}")
        
        # Default settings
        self.retry_attempts = settings.retry_attempts
        self.retry_delay = settings.retry_delay
        self.request_timeout = settings.request_timeout
        
        # Track usage for rate limiting
        self.request_count = 0
        self.token_count = 0
        self.last_request_time = None
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.
        
        This is the core method that all LLM services must implement.
        
        Args:
            prompt: The prompt to generate text from
            **kwargs: Additional parameters for the specific provider
            
        Returns:
            The generated text
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        pass
    
    @abstractmethod
    async def generate_chat_response(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters for the specific provider
            
        Returns:
            The generated response
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        pass
    
    @log_execution_time(logger)
    async def generate_response(
        self,
        query: str,
        context: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Generate a response to a query, optionally with context.
        
        This is a higher-level method that combines the query and context
        before sending to the LLM.
        
        Args:
            query: The user's query
            context: Optional context information to include
            **kwargs: Additional parameters for the specific provider
            
        Returns:
            The generated response
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
            # Track request stats
            self.request_count += 1
            self.last_request_time = datetime.utcnow()
            
            # Create a system message with context if provided
            system_message = "You are a helpful assistant that provides accurate information."
            
            if context:
                system_message += (
                    "\n\nYou have access to the following information that may help answer "
                    "the user's question. Use this information if relevant, but you don't "
                    "have to use it all:\n\n"
                    f"{context}"
                )
            
            # Create the messages list
            messages = [
                {"role": "system", "content": system_message},
                {"role": "user", "content": query}
            ]
            
            # Generate the response with retries
            for attempt in range(self.retry_attempts):
                try:
                    response = await self.generate_chat_response(messages, **kwargs)
                    return response
                except LLMRateLimitError as e:
                    if attempt < self.retry_attempts - 1:
                        # Exponential backoff
                        wait_time = self.retry_delay * (2 ** attempt)
                        self.logger.warning(
                            f"Rate limit exceeded, retrying in {wait_time} seconds",
                            extra={"attempt": attempt + 1, "max_attempts": self.retry_attempts}
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise
                except Exception as e:
                    if attempt < self.retry_attempts - 1:
                        wait_time = self.retry_delay * (2 ** attempt)
                        self.logger.warning(
                            f"Request failed, retrying in {wait_time} seconds: {str(e)}",
                            extra={"attempt": attempt + 1, "max_attempts": self.retry_attempts}
                        )
                        await asyncio.sleep(wait_time)
                    else:
                        raise LLMRequestError(f"All {self.retry_attempts} attempts failed: {str(e)}")
            
            # Should not reach here, but just in case
            raise LLMRequestError("Failed to generate response after all retry attempts")
            
        except Exception as e:
            if not isinstance(e, (LLMRequestError, LLMRateLimitError)):
                self.logger.exception("Unexpected error generating response")
                raise LLMRequestError(f"Failed to generate response: {str(e)}")
            raise
    
    @abstractmethod
    async def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in a text.
        
        Args:
            text: The text to count tokens for
            
        Returns:
            The number of tokens
        """
        pass
    
    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """
        Get an embedding vector for a text.
        
        Args:
            text: The text to get an embedding for
            
        Returns:
            The embedding vector
            
        Raises:
            LLMRequestError: If getting the embedding fails
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the LLM service is healthy and available.
        
        Returns:
            True if the service is healthy, False otherwise
        """
        pass