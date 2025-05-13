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
from app.services.llm.base import LLMService


logger = get_logger(__name__)

class AnthropicService(LLMService):
    """
    Anthropic implementation of the LLM service.
    
    This class:
    1. Connects to Anthropic's API
    2. Manages API key authentication
    3. Handles token counting and rate limiting
    4. Provides access to Claude models
    """
    
    def __init__(self, settings: Settings):
        """
        Initialize the Anthropic LLM service.
        
        Args:
            settings: Application configuration settings
            
        Raises:
            LLMProviderError: If Anthropic API key is missing or invalid
        """
        super().__init__("anthropic", settings)
        
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
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate text from a prompt using Anthropic's completions API.
        
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
            # Format prompt as expected by Anthropic
            formatted_prompt = f"{anthropic.HUMAN_PROMPT} {prompt}{anthropic.AI_PROMPT}"
            
            # Create a timeout
            timeout = kwargs.pop("timeout", self.request_timeout)
            
            # Make the API call
            response = await self.client.completions.create(
                model=self.model,
                prompt=formatted_prompt,
                temperature=temperature,
                max_tokens_to_sample=max_tokens,
                timeout=timeout,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.completion.strip()
            
            # Approximately track token usage
            self.token_count += await self.count_tokens(prompt + generated_text)
            
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
        temperature: float = 0.7,
        max_tokens: int = 1000,
        **kwargs
    ) -> str:
        """
        Generate a response in a chat conversation using Anthropic's messages API.
        
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
            
            # Make the API call
            response = await self.client.messages.create(
                model=self.model,
                messages=formatted_messages,
                system=system_content,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=timeout,
                **kwargs
            )
            
            # Extract the generated text
            generated_text = response.content[0].text
            
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
        Approximately count the number of tokens in a text using cl100k_base.
        
        Note that this is an approximation since Claude uses a different tokenizer,
        but it's close enough for most purposes.
        
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