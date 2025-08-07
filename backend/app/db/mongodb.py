from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import logging

from app.core.config import get_settings

logger = logging.getLogger(__name__)

class MongoDB:
    client: AsyncIOMotorClient = None

mongodb = MongoDB()

async def connect_to_mongo():
    settings = get_settings()
    if not settings.MONGO_URI:
        logger.warning("MONGO_URI not configured. MongoDB connection skipped.")
        return

    logger.info("Connecting to MongoDB...")
    try:
        mongodb.client = AsyncIOMotorClient(settings.MONGO_URI)
        # The ping command is cheap and does not require auth. It will confirm that the connection is alive.
        await mongodb.client.admin.command('ping')
        logger.info("MongoDB connected successfully!")
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {e}")
        mongodb.client = None # Ensure client is None on failure
    except Exception as e:
        logger.error(f"An unexpected error occurred during MongoDB connection: {e}")
        mongodb.client = None

async def close_mongo_connection():
    if mongodb.client:
        logger.info("Closing MongoDB connection...")
        mongodb.client.close()
        logger.info("MongoDB connection closed.")

def get_mongo_client() -> AsyncIOMotorClient:
    if not mongodb.client:
        raise ConnectionFailure("MongoDB client is not initialized. Check MONGO_URI and connection status.")
    return mongodb.client
