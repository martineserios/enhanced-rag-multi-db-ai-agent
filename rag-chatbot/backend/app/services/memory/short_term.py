# filepath: backend/services/memory/short_term.py
"""
Short-term memory implementation using Redis.

This module implements the short-term memory system, which stores recent
conversation context using Redis as a key-value store with time-based expiration.
"""
import json
import time
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import asyncio
import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    MemoryError, MemoryStorageError, MemoryRetrievalError, 
    DatabaseConnectionError
)
from app.config import Settings
from app.services.memory.base import MemorySystem, MemoryItem

logger = get_logger(__name__)

class ShortTermMemory(MemorySystem[Dict[str, Any]]):
    """
    Short-term memory implementation using Redis.
    
    This class:
    1. Stores recent conversation context with time-based expiration
    2. Provides fast access to recent interactions
    3. Automatically expires old conversations
    
    It uses Redis sorted sets to maintain conversation history in chronological order.
    """
    
    def __init__(self, settings: Settings, ttl: int = 3600):
        """
        Initialize short-term memory with Redis connection.
        
        Args:
            settings: Application configuration settings
            ttl: Time-to-live in seconds for memory items (default: 1 hour)
            
        Raises:
            DatabaseConnectionError: If Redis connection fails
        """
        super().__init__("short_term")
        self.settings = settings
        self.ttl = ttl
        
        # Initialize Redis connection
        try:
            self.redis = redis.Redis(
                host=settings.redis_host,
                port=settings.redis_port,
                password=settings.redis_password,
                db=settings.redis_db,
                decode_responses=True
            )
        except Exception as e:
            logger.exception("Failed to initialize Redis connection")
            raise DatabaseConnectionError(f"Redis connection failed: {str(e)}")
    
    @log_execution_time(logger)
    async def store(
        self, 
        key: str, 
        content: Dict[str, Any], 
        metadata: Optional[Dict[str, Any]] = None,
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> str:
        """
        Store conversation message in short-term memory.
        
        Args:
            key: Unique identifier for the message
            content: Message content as a dictionary with 'user_message' and 'assistant_message'
            metadata: Additional metadata to store
            conversation_id: ID of the conversation this message belongs to
            **kwargs: Additional parameters
            
        Returns:
            The key used to store the content
            
        Raises:
            MemoryStorageError: If storing fails
        """
        try:
            # Prepare the data to store
            timestamp = time.time()
            
            if metadata is None:
                metadata = {}
            
            # If conversation_id is not provided, extract from key or generate a new one
            if conversation_id is None:
                # Try to extract from key format "conversation:{id}:message:{uuid}"
                if key.startswith("conversation:") and ":message:" in key:
                    conversation_id = key.split(":")[1]
                else:
                    # If not in the expected format, use the key as is
                    conversation_id = key
            
            # Create a data dictionary to store
            data = {
                "key": key,
                "timestamp": timestamp,
                "content": content,
                "metadata": metadata
            }
            
            # Convert to JSON for storage
            json_data = json.dumps(data)
            
            # Store the message data with expiration
            await self.redis.set(key, json_data, ex=self.ttl)
            
            # Add to conversation history using a sorted set
            # This allows retrieving messages by conversation in chronological order
            conversation_key = f"conversation:{conversation_id}:messages"
            await self.redis.zadd(conversation_key, {key: timestamp})
            
            # Set expiration on the conversation set
            await self.redis.expire(conversation_key, self.ttl)
            
            self.logger.debug(
                f"Stored message in short-term memory: {key}",
                extra={"conversation_id": conversation_id}
            )
            
            return key
            
        except RedisError as e:
            self.logger.exception("Redis error storing message")
            raise MemoryStorageError(f"Failed to store in short-term memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error storing message")
            raise MemoryStorageError(f"Failed to store in short-term memory: {str(e)}")
    
    @log_execution_time(logger)
    async def retrieve(self, key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve a message by key from short-term memory.
        
        Args:
            key: The key of the message to retrieve
            **kwargs: Additional parameters
            
        Returns:
            The message content, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            # Get the data from Redis
            json_data = await self.redis.get(key)
            
            if json_data is None:
                return None
            
            # Parse the JSON data
            data = json.loads(json_data)
            
            # Return the content
            return data.get("content")
            
        except RedisError as e:
            self.logger.exception(f"Redis error retrieving message: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from short-term memory: {str(e)}")
        except json.JSONDecodeError as e:
            self.logger.exception(f"Invalid JSON in Redis for key: {key}")
            raise MemoryRetrievalError(f"Failed to decode message from short-term memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error retrieving message: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from short-term memory: {str(e)}")
    
    @log_execution_time(logger)
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for messages in short-term memory.
        
        For short-term memory, this retrieves recent messages for a conversation
        since Redis doesn't support semantic search.
        
        Args:
            query: The search query (unused in this implementation)
            limit: Maximum number of messages to return
            conversation_id: ID of the conversation to get messages for
            **kwargs: Additional parameters
            
        Returns:
            List of recent messages for the conversation
            
        Raises:
            MemoryRetrievalError: If search fails
        """
        try:
            if conversation_id is None:
                self.logger.warning("No conversation_id provided for short-term memory search")
                return []
            
            # Get the conversation history from the sorted set
            conversation_key = f"conversation:{conversation_id}:messages"
            
            # Get the newest messages first (highest scores) up to the limit
            message_keys = await self.redis.zrevrange(
                conversation_key, 
                0, 
                limit - 1, 
                withscores=True
            )
            
            if not message_keys:
                return []
            
            # Retrieve each message
            results = []
            for key, score in message_keys:
                json_data = await self.redis.get(key)
                if json_data:
                    try:
                        data = json.loads(json_data)
                        
                        # Extract content and metadata
                        content = data.get("content", {})
                        metadata = data.get("metadata", {})
                        
                        # Create a result entry
                        result = {
                            "key": key,
                            "timestamp": datetime.fromtimestamp(data.get("timestamp", 0)).isoformat(),
                            **content,  # Include user_message and assistant_message
                            "metadata": metadata
                        }
                        
                        results.append(result)
                    except json.JSONDecodeError:
                        self.logger.warning(f"Invalid JSON in Redis for key: {key}")
            
            # Sort by timestamp (newest first)
            results.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
            
            return results
            
        except RedisError as e:
            self.logger.exception("Redis error searching messages")
            raise MemoryRetrievalError(f"Failed to search short-term memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error searching messages")
            raise MemoryRetrievalError(f"Failed to search short-term memory: {str(e)}")
    
    @log_execution_time(logger)
    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete a message from short-term memory.
        
        Args:
            key: The key of the message to delete
            **kwargs: Additional parameters
            
        Returns:
            True if the message was deleted, False otherwise
            
        Raises:
            MemoryError: If deletion fails
        """
        try:
            # Check if the key exists
            exists = await self.redis.exists(key)
            
            if not exists:
                return False
            
            # Extract conversation_id from key if possible
            conversation_id = None
            if key.startswith("conversation:") and ":message:" in key:
                conversation_id = key.split(":")[1]
            
            # Delete the message
            await self.redis.delete(key)
            
            # Remove from conversation history if conversation_id is available
            if conversation_id:
                conversation_key = f"conversation:{conversation_id}:messages"
                await self.redis.zrem(conversation_key, key)
            
            return True
            
        except RedisError as e:
            self.logger.exception(f"Redis error deleting message: {key}")
            raise MemoryError(f"Failed to delete from short-term memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error deleting message: {key}")
            raise MemoryError(f"Failed to delete from short-term memory: {str(e)}")
    
    @log_execution_time(logger)
    async def clear(self, conversation_id: Optional[str] = None, **kwargs) -> None:
        """
        Clear messages from short-term memory.
        
        Args:
            conversation_id: ID of the conversation to clear, or None to clear all
            **kwargs: Additional parameters
            
        Raises:
            MemoryError: If clearing fails
        """
        try:
            if conversation_id:
                # Clear a specific conversation
                conversation_key = f"conversation:{conversation_id}:messages"
                
                # Get all message keys in the conversation
                message_keys = await self.redis.zrange(conversation_key, 0, -1)
                
                # Delete each message
                if message_keys:
                    await self.redis.delete(*message_keys)
                
                # Delete the conversation set
                await self.redis.delete(conversation_key)
                
                self.logger.info(f"Cleared conversation from short-term memory: {conversation_id}")
            else:
                # Clear all short-term memory
                # This is a simplified approach - in production, use scan for large datasets
                conversation_keys = await self.redis.keys("conversation:*:messages")
                
                for conversation_key in conversation_keys:
                    # Get message keys for each conversation
                    message_keys = await self.redis.zrange(conversation_key, 0, -1)
                    
                    # Delete messages
                    if message_keys:
                        await self.redis.delete(*message_keys)
                    
                    # Delete conversation set
                    await self.redis.delete(conversation_key)
                
                self.logger.info("Cleared all short-term memory")
            
        except RedisError as e:
            self.logger.exception("Redis error clearing memory")
            raise MemoryError(f"Failed to clear short-term memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error clearing memory")
            raise MemoryError(f"Failed to clear short-term memory: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if Redis connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            # Simple ping to check if Redis is responsive
            await self.redis.ping()
            return True
        except Exception as e:
            self.logger.error(f"Redis health check failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """
        Close the Redis connection.
        
        This method should be called when shutting down the application
        to release resources properly.
        """
        try:
            await self.redis.close()
            self.logger.info("Redis connection closed")
        except Exception as e:
            self.logger.exception(f"Error closing Redis connection: {str(e)}")