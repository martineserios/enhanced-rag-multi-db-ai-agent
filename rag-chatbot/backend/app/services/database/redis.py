# filepath: backend/services/database/redis.py
"""
Redis database service for short-term memory.

This module provides functions for interacting with Redis, which is used
as the backend for short-term memory in the system.
"""
from typing import Any, Dict, List, Optional, Union
import json
import asyncio
from datetime import datetime

import redis.asyncio as redis
from redis.exceptions import RedisError

from app.core.logging import get_logger
from app.core.exceptions import DatabaseConnectionError, DatabaseQueryError
from app.config import Settings


logger = get_logger(__name__)

# Global Redis client
_redis_client = None


async def init_redis(settings: Settings):
    """
    Initialize the Redis connection.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        Redis client instance
        
    Raises:
        DatabaseConnectionError: If Redis connection fails
    """
    global _redis_client
    
    try:
        # Create Redis client
        _redis_client = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True
        )
        
        # Test connection
        await _redis_client.ping()
        
        logger.info(
            f"Initialized Redis connection",
            extra={"host": settings.redis_host, "port": settings.redis_port}
        )
        
        return _redis_client
        
    except RedisError as e:
        logger.exception("Failed to connect to Redis")
        raise DatabaseConnectionError(f"Redis connection failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error connecting to Redis")
        raise DatabaseConnectionError(f"Redis connection failed: {str(e)}")


def get_redis_client():
    """
    Get the Redis client instance.
    
    Returns:
        Redis client instance
        
    Raises:
        DatabaseConnectionError: If Redis is not initialized
    """
    global _redis_client
    
    if _redis_client is None:
        raise DatabaseConnectionError("Redis client not initialized. Call init_redis first.")
    
    return _redis_client


async def set_with_json(key: str, value: Any, expire: Optional[int] = None):
    """
    Set a key with a JSON-serialized value.
    
    Args:
        key: Redis key
        value: Value to store (will be JSON serialized)
        expire: Optional TTL in seconds
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        json_value = json.dumps(value)
        
        if expire:
            await redis_client.set(key, json_value, ex=expire)
        else:
            await redis_client.set(key, json_value)
            
    except RedisError as e:
        logger.exception(f"Redis error setting key: {key}")
        raise DatabaseQueryError(f"Failed to set Redis key: {str(e)}")
    except (TypeError, ValueError) as e:
        logger.exception(f"JSON serialization error for key: {key}")
        raise DatabaseQueryError(f"Failed to serialize value for Redis: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error setting Redis key: {key}")
        raise DatabaseQueryError(f"Failed to set Redis key: {str(e)}")


async def get_with_json(key: str) -> Optional[Any]:
    """
    Get a JSON-serialized value from Redis.
    
    Args:
        key: Redis key
        
    Returns:
        Deserialized value, or None if key doesn't exist
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        value = await redis_client.get(key)
        
        if value is None:
            return None
        
        return json.loads(value)
        
    except RedisError as e:
        logger.exception(f"Redis error getting key: {key}")
        raise DatabaseQueryError(f"Failed to get Redis key: {str(e)}")
    except json.JSONDecodeError as e:
        logger.exception(f"JSON deserialization error for key: {key}")
        raise DatabaseQueryError(f"Failed to deserialize value from Redis: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting Redis key: {key}")
        raise DatabaseQueryError(f"Failed to get Redis key: {str(e)}")


async def list_push(key: str, value: Any, expire: Optional[int] = None, max_len: Optional[int] = None):
    """
    Push a value to a Redis list.
    
    Args:
        key: Redis list key
        value: Value to push (will be JSON serialized)
        expire: Optional TTL in seconds
        max_len: Optional maximum list length
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        json_value = json.dumps(value)
        
        # Use a pipeline for atomic operations
        async with redis_client.pipeline() as pipe:
            # Push to list
            await pipe.lpush(key, json_value)
            
            # Trim list if max_len is specified
            if max_len is not None:
                await pipe.ltrim(key, 0, max_len - 1)
            
            # Set expiration if specified
            if expire is not None:
                await pipe.expire(key, expire)
            
            # Execute all commands
            await pipe.execute()
            
    except RedisError as e:
        logger.exception(f"Redis error pushing to list: {key}")
        raise DatabaseQueryError(f"Failed to push to Redis list: {str(e)}")
    except (TypeError, ValueError) as e:
        logger.exception(f"JSON serialization error for list: {key}")
        raise DatabaseQueryError(f"Failed to serialize value for Redis list: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error pushing to Redis list: {key}")
        raise DatabaseQueryError(f"Failed to push to Redis list: {str(e)}")


async def list_range(key: str, start: int = 0, end: int = -1) -> List[Any]:
    """
    Get a range of values from a Redis list.
    
    Args:
        key: Redis list key
        start: Start index
        end: End index (-1 for all elements)
        
    Returns:
        List of deserialized values
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        values = await redis_client.lrange(key, start, end)
        
        # Deserialize JSON values
        result = []
        for value in values:
            try:
                result.append(json.loads(value))
            except json.JSONDecodeError:
                logger.warning(f"Failed to deserialize list item from key: {key}")
                result.append(value)  # Use raw value as fallback
        
        return result
        
    except RedisError as e:
        logger.exception(f"Redis error getting list range: {key}")
        raise DatabaseQueryError(f"Failed to get Redis list range: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting Redis list range: {key}")
        raise DatabaseQueryError(f"Failed to get Redis list range: {str(e)}")


async def get_conversation_keys(conversation_id: str) -> List[str]:
    """
    Get all Redis keys for a conversation.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        List of Redis keys
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        pattern = f"conversation:{conversation_id}:*"
        
        # Get all keys matching the pattern
        keys = await redis_client.keys(pattern)
        return keys
        
    except RedisError as e:
        logger.exception(f"Redis error getting conversation keys: {conversation_id}")
        raise DatabaseQueryError(f"Failed to get conversation keys: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting conversation keys: {conversation_id}")
        raise DatabaseQueryError(f"Failed to get conversation keys: {str(e)}")


async def delete_conversation(conversation_id: str) -> int:
    """
    Delete all Redis keys for a conversation.
    
    Args:
        conversation_id: Conversation ID
        
    Returns:
        Number of keys deleted
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        
        # Get all keys for the conversation
        keys = await get_conversation_keys(conversation_id)
        
        if not keys:
            return 0
        
        # Delete all keys
        deleted = await redis_client.delete(*keys)
        
        logger.info(
            f"Deleted conversation from Redis",
            extra={"conversation_id": conversation_id, "deleted_keys": deleted}
        )
        
        return deleted
        
    except RedisError as e:
        logger.exception(f"Redis error deleting conversation: {conversation_id}")
        raise DatabaseQueryError(f"Failed to delete conversation: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error deleting conversation: {conversation_id}")
        raise DatabaseQueryError(f"Failed to delete conversation: {str(e)}")


async def store_conversation_message(
    conversation_id: str,
    user_message: str,
    assistant_message: str,
    metadata: Optional[Dict[str, Any]] = None,
    ttl: int = 3600
) -> str:
    """
    Store a conversation message in Redis.
    
    Args:
        conversation_id: Conversation ID
        user_message: User message
        assistant_message: Assistant message
        metadata: Optional metadata
        ttl: Time-to-live in seconds
        
    Returns:
        Message key
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        
        # Generate message key
        import uuid
        message_id = str(uuid.uuid4())
        message_key = f"conversation:{conversation_id}:message:{message_id}"
        
        # Create message data
        message_data = {
            "user_message": user_message,
            "assistant_message": assistant_message,
            "timestamp": datetime.utcnow().isoformat(),
            "metadata": metadata or {}
        }
        
        # Store message
        await set_with_json(message_key, message_data, expire=ttl)
        
        # Add to conversation messages list
        messages_key = f"conversation:{conversation_id}:messages"
        await list_push(messages_key, message_key, expire=ttl)
        
        return message_key
        
    except RedisError as e:
        logger.exception(f"Redis error storing conversation message: {conversation_id}")
        raise DatabaseQueryError(f"Failed to store conversation message: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error storing conversation message: {conversation_id}")
        raise DatabaseQueryError(f"Failed to store conversation message: {str(e)}")


async def get_conversation_messages(
    conversation_id: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Get recent messages for a conversation.
    
    Args:
        conversation_id: Conversation ID
        limit: Maximum number of messages to return
        
    Returns:
        List of conversation messages, newest first
        
    Raises:
        DatabaseQueryError: If the operation fails
    """
    try:
        redis_client = get_redis_client()
        
        # Get message keys
        messages_key = f"conversation:{conversation_id}:messages"
        message_keys = await list_range(messages_key, 0, limit - 1)
        
        if not message_keys:
            return []
        
        # Get message data
        messages = []
        for key in message_keys:
            message_data = await get_with_json(key)
            if message_data:
                messages.append(message_data)
        
        return messages
        
    except RedisError as e:
        logger.exception(f"Redis error getting conversation messages: {conversation_id}")
        raise DatabaseQueryError(f"Failed to get conversation messages: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error getting conversation messages: {conversation_id}")
        raise DatabaseQueryError(f"Failed to get conversation messages: {str(e)}")


async def health_check() -> bool:
    """
    Check if Redis is healthy.
    
    Returns:
        True if Redis is healthy, False otherwise
    """
    try:
        redis_client = get_redis_client()
        await redis_client.ping()
        return True
    except Exception as e:
        logger.error(f"Redis health check failed: {str(e)}")
        return False


async def close():
    """
    Close the Redis connection.
    
    This should be called when shutting down the application
    to properly release resources.
    """
    global _redis_client
    
    if _redis_client is not None:
        try:
            await _redis_client.close()
            logger.info("Redis connection closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connection: {str(e)}")
        
        _redis_client = None