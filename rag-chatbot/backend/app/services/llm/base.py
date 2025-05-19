# filepath: backend/services/llm/base.py
"""
Base class for LLM service implementations.

This module defines the interface for all LLM services using the Strategy pattern,
allowing different LLM providers to be used interchangeably.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Union, Type, TypeVar, Coroutine, Callable
import logging
import time
import asyncio
from datetime import datetime, timedelta
from enum import Enum

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, LLMRateLimitError
)
from app.config import Settings

T = TypeVar('T')


logger = get_logger(__name__)

class ModelType(Enum):
    """Enum for different types of LLM models"""
    TEXT = "text"
    CHAT = "chat"
    EMBEDDING = "embedding"


class LLMService(ABC):
    """
    Abstract base class for LLM service implementations.
    
    This class provides a common interface for all LLM providers and handles
    common functionality like token counting, rate limiting, and error handling.
    
    Attributes:
        provider_name: Name of the LLM provider
        settings: Application configuration settings
        logger: Logger instance
        request_timeout: Default request timeout
        token_count: Cumulative token count
        last_request_time: Timestamp of the last request
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If required settings are missing
        """
        self.settings = settings
        self.logger = get_logger(__name__)
        self.request_timeout = settings.request_timeout
        self.token_count = 0
        self.request_count = 0  # Initialize request_count
        self.last_request_time = datetime.now()
        self._provider_name: Optional[str] = None
        
        # Rate limiting settings (default: 60 requests per minute)
        self.rate_limit_requests = getattr(settings, 'rate_limit_requests', 60)
        self.rate_limit_window = getattr(settings, 'rate_limit_window', 60)  # seconds
        
        # Validate provider settings
        self._validate_provider_settings()
    
    @property
    def provider_name(self) -> str:
        """Get the provider name."""
        if self._provider_name is None:
            raise ValueError("Provider name not set")
        return self._provider_name
    
    @provider_name.setter
    def provider_name(self, value: str) -> None:
        """Set the provider name."""
        self._provider_name = value
        self.request_count = 0
        self.token_count = 0
        self.last_request_time: Optional[datetime] = None
        
        # Validate provider-specific settings
        self._validate_provider_settings()
    
    @abstractmethod
    def _validate_provider_settings(self) -> None:
        """
        Validate provider-specific settings.
        
        This method should be implemented by subclasses to ensure all required
        provider-specific settings are configured correctly.
        
        Raises:
            LLMProviderError: If required settings are missing or invalid
        """
        pass
    
    @abstractmethod
    async def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """
        Get information about available models for the given type.
        
        Args:
            model_type: Type of model to get info for (text, chat, embedding)
            
        Returns:
            Dictionary containing model information
            
        Raises:
            LLMProviderError: If model information cannot be retrieved
        """
        pass
    
    async def _execute_with_retry(
        self,
        coroutine_func: Union[Callable[..., Coroutine[Any, Any, T]], Coroutine[Any, Any, T]],
        error_type: Type[Exception],
        error_message: str,
        *args,
        **kwargs
    ) -> T:
        """
        Execute a coroutine with retry logic.
        
        Args:
            coroutine_func: The coroutine function to execute (not yet awaited) or a coroutine object
            error_type: Type of error to catch for retries
            error_message: Error message to raise if all retries fail
            *args: Positional arguments to pass to the coroutine
            **kwargs: Keyword arguments to pass to the coroutine
            
        Returns:
            Result of the coroutine execution
            
        Raises:
            LLMRequestError: If all retry attempts fail
        """
        last_exception = None
        last_traceback = None
        
        for attempt in range(self.retry_attempts):
            try:
                # Create a new coroutine for each attempt
                if asyncio.iscoroutinefunction(coroutine_func):
                    # If it's a coroutine function, call it with args and kwargs
                    coro = coroutine_func(*args, **kwargs)
                elif asyncio.iscoroutine(coroutine_func):
                    # If it's already a coroutine
                    if args or kwargs:
                        self.logger.warning("Args and kwargs will be ignored when passing a coroutine object")
                    coro = coroutine_func
                elif callable(coroutine_func):
                    # It's a regular function, call it and wrap the result in a coroutine
                    try:
                        result = coroutine_func(*args, **kwargs)
                        if asyncio.iscoroutine(result):
                            coro = result
                        else:
                            # Convert sync function result to coroutine
                            async def wrap() -> T:
                                return result
                            coro = wrap()
                    except Exception as e:
                        raise LLMRequestError(f"Error calling callable: {str(e)}") from e
                else:
                    raise LLMRequestError("Expected coroutine function, coroutine, or callable")
                
                # Execute the coroutine with timeout
                return await asyncio.wait_for(coro, timeout=self.request_timeout)
                
            except asyncio.TimeoutError as e:
                last_exception = e
                last_traceback = e.__traceback__
                if attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Request timed out, retrying in {wait_time} seconds (attempt {attempt + 1}/{self.retry_attempts})"
                    )
                    await asyncio.sleep(wait_time)
                continue
                    
            except error_type as e:
                last_exception = e
                last_traceback = e.__traceback__
                if attempt < self.retry_attempts - 1:
                    wait_time = self.retry_delay * (2 ** attempt)
                    self.logger.warning(
                        f"Request failed, retrying in {wait_time} seconds (attempt {attempt + 1}/{self.retry_attempts}): {str(e)}"
                    )
                    await asyncio.sleep(wait_time)
                continue
                
        # If we get here, all retries have been exhausted
        if last_exception is not None:
            error_msg = str(last_exception)
            if isinstance(last_exception, asyncio.TimeoutError):
                error_msg = "Request timed out after all retry attempts"
            elif error_message:
                error_msg = f"{error_message}: {error_msg}"
                
            # Create a new exception with the combined message
            exc = LLMRequestError(error_msg)
            # Attach the original traceback if available
            if last_traceback is not None:
                exc = exc.with_traceback(last_traceback)
            raise exc from last_exception
                
        raise LLMRequestError("Failed to execute request after all retry attempts")
    
    async def _check_rate_limit(self) -> None:
        """
        Check if we should rate limit based on request frequency.
        
        Raises:
            LLMRateLimitError: If rate limit is exceeded
        """
        now = datetime.now()
        time_since_last = (now - self.last_request_time).total_seconds()
        
        # Reset request count if it's been more than rate_limit_window seconds
        if time_since_last > self.rate_limit_window:
            self.request_count = 0
        
        # Check if we've exceeded the rate limit
        if self.request_count >= self.rate_limit_requests:
            wait_time = self.rate_limit_window - time_since_last
            if wait_time > 0:
                self.logger.warning(
                    f"Rate limit exceeded. Waiting {wait_time:.2f} seconds..."
                )
                await asyncio.sleep(wait_time)
                self.request_count = 0
            else:
                self.request_count = 0
    
    def _update_usage_stats(self, tokens: int) -> None:
        """
        Update usage statistics.
        
        Args:
            tokens: Number of tokens processed
        """
        self.request_count += 1
        self.token_count += tokens
        self.last_request_time = datetime.now()
    
    @abstractmethod
    async def generate_text(
        self, 
        prompt: str, 
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt.
        
        Args:
            prompt: The prompt to generate text from
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
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
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation.
        
        Args:
            messages: List of message dictionaries with 'role' and 'content'
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
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
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        **kwargs
    ) -> str:
        """
        Generate a response to a query, optionally with context.
        
        This is a higher-level method that combines the query and context
        before sending to the LLM.
        
        Args:
            query: The user's query
            context: Optional context information to include
            model: The model to use for generation
            max_tokens: Maximum number of tokens to generate
            temperature: Sampling temperature
            **kwargs: Additional parameters for the specific provider
            
        Returns:
            The generated response
            
        Raises:
            LLMRequestError: If the generation fails
            LLMRateLimitError: If rate limits are exceeded
        """
        try:
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
            
            # Generate the response with retry logic
            response = await self._execute_with_retry(
                self.generate_chat_response,
                error_type=LLMRequestError,
                error_message="Failed to generate response after all retry attempts",
                messages=messages,
                model=model,
                max_tokens=max_tokens,
                temperature=temperature,
                **kwargs
            )
            
            # Update usage statistics
            tokens = await self.count_tokens(query + response)
            self._update_usage_stats(tokens)
            
            return response
                
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
            text: The text to get embedding for
            
        Returns:
            List of float values representing the embedding
            
        Raises:
            LLMRequestError: If embedding generation fails
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