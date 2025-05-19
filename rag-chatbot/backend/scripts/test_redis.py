"""
Test Redis connection and basic operations.
"""
import asyncio
import os
import sys
from dotenv import load_dotenv

# Add the project root to the Python path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Settings
from app.services.memory.short_term import ShortTermMemory
from app.core.logging import setup_logging

async def test_redis_connection():
    """Test Redis connection and basic operations."""
    # Load environment variables
    load_dotenv()
    
    # Set up logging
    setup_logging(level="DEBUG")
    
    # Get settings
    settings = Settings()
    
    print(f"Testing Redis connection to {settings.redis_host}:{settings.redis_port}...")
    
    # Create a short-term memory instance
    stm = ShortTermMemory(settings=settings, ttl=3600)
    
    # Initialize the connection
    print("Initializing Redis connection...")
    success = await stm.initialize()
    print(f"Initialization successful: {success}")
    
    if success:
        # Test storing and retrieving a value
        key = "test:key"
        value = {"message": "Hello, Redis!"}
        
        print(f"Storing test value: {value}")
        stored_key = await stm.store(key, value, {"test": True})
        print(f"Stored with key: {stored_key}")
        
        # Retrieve the value
        print("Retrieving stored value...")
        retrieved = await stm.retrieve(key)
        print(f"Retrieved value: {retrieved}")
        
        # Delete the test key
        print("Deleting test key...")
        deleted = await stm.delete(key)
        print(f"Key deleted: {deleted}")
    
    print("Test completed.")

if __name__ == "__main__":
    asyncio.run(test_redis_connection())
