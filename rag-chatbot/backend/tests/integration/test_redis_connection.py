"""
Integration tests for Redis connection and operations.

This module contains tests to verify the Redis connection and basic operations
used by the short-term memory system.
"""
import os
import pytest
import asyncio
from datetime import datetime, timezone
from typing import Dict, Any, Optional

# Import test settings first to ensure environment variables are set correctly
from tests.test_config import get_test_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

# Skip all tests in this module if Redis is not available
REDIS_AVAILABLE = True
try:
    import redis.asyncio as redis
    from redis.exceptions import ConnectionError as RedisConnectionError
    
    # Test Redis connection
    async def check_redis_connection() -> bool:
        """Check if Redis is available and return True if it is."""
        settings = get_test_settings()
        r = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            socket_connect_timeout=2,
            socket_timeout=2,
            decode_responses=True
        )
        try:
            await r.ping()
            return True
        except (RedisConnectionError, OSError):
            return False
        except Exception as e:
            logger.warning("Unexpected error checking Redis connection: %s", e)
            return False
        finally:
            await r.aclose()  # Properly close the connection
    
    # Run the check synchronously
    REDIS_AVAILABLE = False
    try:
        REDIS_AVAILABLE = asyncio.run(check_redis_connection())
    except Exception as e:
        logger.warning("Failed to check Redis connection: %s", e)
    
except ImportError:
    REDIS_AVAILABLE = False

# Skip decorator for Redis tests
skip_if_redis_unavailable = pytest.mark.skipif(
    not REDIS_AVAILABLE,
    reason="Redis server is not available"
)

@pytest.mark.asyncio
@skip_if_redis_unavailable
async def test_redis_connection():
    """Test basic Redis connection and operations."""
    settings = get_test_settings()
    
    # Skip test if Redis is not enabled
    if not settings.enable_short_term_memory:
        pytest.skip("Short-term memory (Redis) is not enabled in settings")
    
    try:
        import redis.asyncio as redis
        
        # Create Redis connection with timeout
        redis_conn = redis.Redis(
            host=settings.redis_host,
            port=settings.redis_port,
            password=settings.redis_password,
            db=settings.redis_db,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5
        )
        
        # Test connection
        is_alive = await redis_conn.ping()
        assert is_alive, "Failed to ping Redis server"
        
        # Create a test key with a timestamp
        now = datetime.now(timezone.utc)
        test_key = f"test:connection:{now.timestamp()}"
        test_data = {
            "message": "Test message",
            "timestamp": now.isoformat()
        }
        
        # Test string operations
        await redis_conn.set(test_key, "test_value", ex=60)  # 60s TTL
        value = await redis_conn.get(test_key)
        assert value == "test_value", "Failed to get/set string value"
        
        # Test hash operations
        hash_key = f"{test_key}:hash"
        await redis_conn.hset(hash_key, mapping=test_data)
        stored_data = await redis_conn.hgetall(hash_key)
        assert stored_data == test_data, "Failed to get/set hash value"
        
        # Test list operations
        list_key = f"{test_key}:list"
        await redis_conn.rpush(list_key, "item1", "item2")
        list_length = await redis_conn.llen(list_key)
        assert list_length == 2, "Failed to perform list operations"
        
        # Test expiration
        await redis_conn.expire(test_key, 1)  # Set 1s expiration
        await asyncio.sleep(1.1)  # Wait for expiration
        expired_value = await redis_conn.get(test_key)
        assert expired_value is None, "Expiration not working"
        
        # Clean up
        await redis_conn.delete(test_key)
        await redis_conn.aclose()  # Use aclose() instead of close()
        
    except Exception as e:
        pytest.fail(f"Redis test failed: {str(e)}")
    finally:
        if 'redis_conn' in locals():
            await redis_conn.aclose()

@pytest.mark.asyncio
@skip_if_redis_unavailable
async def test_short_term_memory_integration():
    """Test integration with ShortTermMemory class."""
    from app.services.memory.short_term import ShortTermMemory
    
    settings = get_test_settings()
    
    # Skip test if Redis is not enabled
    if not settings.enable_short_term_memory:
        pytest.skip("Short-term memory (Redis) is not enabled in settings")
    
    try:
        # Initialize short-term memory
        memory = ShortTermMemory(settings=settings, ttl=60)
        
        # Create test data
        now = datetime.now(timezone.utc)
        test_key = f"test:memory:{now.timestamp()}"
        test_content = {
            "user_id": "test_user",
            "message": "Test message",
            "timestamp": now.isoformat()
        }
        test_metadata = {
            "test": True,
            "source": "test_short_term_memory_integration"
        }
        
        # Test store
        stored_key = await memory.store(
            key=test_key,
            content=test_content,
            metadata=test_metadata,
            conversation_id="test_conversation"
        )
        assert stored_key == test_key, "Failed to store in short-term memory"
        
        # Test retrieve
        retrieved = await memory.retrieve(test_key)
        assert retrieved == test_content, "Retrieved content doesn't match stored content"
        
        # Test search
        search_results = await memory.search(
            query="test",
            conversation_id="test_conversation",
            limit=1
        )
        assert len(search_results) > 0, "Failed to retrieve message via search"
        
        # Test delete
        deleted = await memory.delete(test_key)
        assert deleted, "Failed to delete from short-term memory"
        
        # Verify deletion
        should_be_none = await memory.retrieve(test_key)
        assert should_be_none is None, "Item still exists after deletion"
        
    except Exception as e:
        pytest.fail(f"ShortTermMemory test failed: {str(e)}")
    finally:
        if 'memory' in locals():
            await memory.close()
