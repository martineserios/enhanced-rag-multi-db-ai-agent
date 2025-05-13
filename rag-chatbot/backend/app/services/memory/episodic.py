# filepath: backend/services/memory/episodic.py
"""
Episodic memory implementation using MongoDB.

This module implements episodic memory for storing and retrieving conversation
history across sessions using MongoDB as a document store.
"""
import json
import uuid
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

import motor.motor_asyncio
from pymongo import DESCENDING, TEXT, IndexModel
from pymongo.errors import PyMongoError
from bson import ObjectId
from bson.json_util import dumps, loads

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    MemoryError, MemoryStorageError, MemoryRetrievalError, 
    DatabaseConnectionError
)
from app.config import Settings
from app.services.memory.base import MemorySystem, MemoryItem


logger = get_logger(__name__)

class BSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for MongoDB BSON types."""
    
    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)
        if isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)


class EpisodicMemory(MemorySystem[Dict[str, Any]]):
    """
    Episodic memory implementation using MongoDB.
    
    This class:
    1. Stores conversation history with timestamps
    2. Retrieves past conversations by ID or content
    3. Provides chronological access to interaction history
    
    It uses MongoDB for flexible document storage of conversation episodes.
    """
    
    def __init__(self, settings: Settings, collection_name: str = "episodic_memory"):
        """
        Initialize episodic memory with MongoDB connection.
        
        Args:
            settings: Application configuration settings
            collection_name: Name of the MongoDB collection to use
            
        Raises:
            DatabaseConnectionError: If MongoDB connection fails
        """
        super().__init__("episodic")
        self.settings = settings
        self.collection_name = collection_name
        
        # Initialize MongoDB connection
        try:
            # Create client
            self.client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
            
            # Get database
            self.db = self.client[settings.mongo_db_name]
            
            # Get collection
            self.collection = self.db[collection_name]
            
            self.logger.info(
                f"Initialized episodic memory with MongoDB collection: {collection_name}"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize MongoDB connection")
            raise DatabaseConnectionError(f"MongoDB connection failed: {str(e)}")
    
    async def _ensure_indexes(self):
        """Ensure all required indexes exist on the collection."""
        try:
            # Create a text index on user and assistant messages for text search
            await self.collection.create_index(
                [
                    ("user_message", TEXT),
                    ("assistant_message", TEXT)
                ],
                default_language="english",
                name="text_search"
            )
            
            # Create an index on conversation_id for faster lookups
            await self.collection.create_index("conversation_id")
            
            # Create an index on timestamp for sorting
            await self.collection.create_index([("timestamp", DESCENDING)])
            
            self.logger.debug("Ensured indexes for episodic memory collection")
            
        except PyMongoError as e:
            self.logger.warning(f"Failed to create indexes: {str(e)}")
    
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
        Store conversation in episodic memory.
        
        Args:
            key: Unique identifier for the conversation entry
            content: Conversation content with user_message and assistant_message
            metadata: Additional metadata to store
            conversation_id: ID of the conversation this entry belongs to
            **kwargs: Additional parameters
            
        Returns:
            The key used to store the conversation
            
        Raises:
            MemoryStorageError: If storing fails
        """
        try:
            # Ensure indexes exist
            await self._ensure_indexes()
            
            # Ensure metadata is a dictionary
            if metadata is None:
                metadata = {}
            
            # Determine conversation ID
            if conversation_id is None:
                # Try to extract from key
                if key.startswith("conversation:") and ":" in key:
                    conversation_id = key.split(":")[1]
                else:
                    # Generate a new conversation ID
                    conversation_id = str(uuid.uuid4())
            
            # Extract messages from content
            user_message = content.get("user_message", "")
            assistant_message = content.get("assistant_message", "")
            
            if not user_message and not assistant_message:
                raise ValueError("Either user_message or assistant_message must be provided")
            
            # Create document to store
            document = {
                "key": key,
                "conversation_id": conversation_id,
                "user_message": user_message,
                "assistant_message": assistant_message,
                "timestamp": datetime.utcnow(),
                "metadata": metadata
            }
            
            # Insert document
            result = await self.collection.insert_one(document)
            
            # Update key to include MongoDB ObjectId
            stored_key = f"{key}:{result.inserted_id}"
            
            self.logger.debug(
                f"Stored conversation in episodic memory: {stored_key}",
                extra={
                    "conversation_id": conversation_id,
                    "user_message_length": len(user_message),
                    "assistant_message_length": len(assistant_message)
                }
            )
            
            return stored_key
            
        except PyMongoError as e:
            self.logger.exception("MongoDB error storing conversation")
            raise MemoryStorageError(f"Failed to store in episodic memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error storing conversation")
            raise MemoryStorageError(f"Failed to store in episodic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def retrieve(self, key: str, **kwargs) -> Optional[Dict[str, Any]]:
        """
        Retrieve conversation from episodic memory by key.
        
        Args:
            key: The key of the conversation to retrieve
            **kwargs: Additional parameters
            
        Returns:
            The conversation content, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            # Check if key contains ObjectId
            obj_id = None
            if ":" in key and len(key.split(":")[-1]) == 24:
                try:
                    obj_id = ObjectId(key.split(":")[-1])
                except:
                    pass
            
            # Prepare query
            query = {"$or": [{"key": key}]}
            if obj_id:
                query["$or"].append({"_id": obj_id})
            
            # Retrieve document
            document = await self.collection.find_one(query)
            
            if not document:
                return None
            
            # Extract content
            content = {
                "user_message": document.get("user_message", ""),
                "assistant_message": document.get("assistant_message", ""),
                "conversation_id": document.get("conversation_id", ""),
                "timestamp": document.get("timestamp", datetime.utcnow()).isoformat()
            }
            
            return content
            
        except PyMongoError as e:
            self.logger.exception(f"MongoDB error retrieving conversation: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from episodic memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error retrieving conversation: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from episodic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        conversation_id: Optional[str] = None,
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for conversations in episodic memory.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            conversation_id: Optional ID to filter by conversation
            **kwargs: Additional parameters
            
        Returns:
            List of matching conversations
            
        Raises:
            MemoryRetrievalError: If search fails
        """
        try:
            search_criteria = {}
            
            # Filter by conversation ID if provided
            if conversation_id:
                search_criteria["conversation_id"] = conversation_id
                
                # Get recent messages for the conversation
                cursor = self.collection.find(search_criteria)\
                    .sort("timestamp", DESCENDING)\
                    .limit(limit)
            
            # Text search if query is provided
            elif query:
                # For short queries (probably not a full text search)
                if len(query.split()) <= 3:
                    # Search for partial matches in messages
                    # Using regex for partial matching
                    search_criteria["$or"] = [
                        {"user_message": {"$regex": query, "$options": "i"}},
                        {"assistant_message": {"$regex": query, "$options": "i"}}
                    ]
                    
                    cursor = self.collection.find(search_criteria)\
                        .sort("timestamp", DESCENDING)\
                        .limit(limit)
                else:
                    # Use text search for longer queries
                    cursor = self.collection.find(
                        {"$text": {"$search": query}},
                        {"score": {"$meta": "textScore"}}
                    ).sort([
                        ("score", {"$meta": "textScore"}),
                        ("timestamp", DESCENDING)
                    ]).limit(limit)
            else:
                # Get recent conversations (no filters)
                cursor = self.collection.find(search_criteria)\
                    .sort("timestamp", DESCENDING)\
                    .limit(limit)
            
            # Convert cursor to list
            results = []
            async for document in cursor:
                # Format document for response
                formatted_doc = {
                    "key": document.get("key", str(document["_id"])),
                    "conversation_id": document.get("conversation_id", ""),
                    "user_message": document.get("user_message", ""),
                    "assistant_message": document.get("assistant_message", ""),
                    "timestamp": document.get("timestamp", datetime.utcnow()).isoformat(),
                    "metadata": document.get("metadata", {})
                }
                
                # Add score if available
                if "score" in document:
                    formatted_doc["relevance_score"] = document["score"]
                
                results.append(formatted_doc)
            
            self.logger.debug(
                f"Episodic search results for query: {query[:50]}...",
                extra={"query": query, "result_count": len(results)}
            )
            
            return results
            
        except PyMongoError as e:
            self.logger.exception(f"MongoDB error searching conversations: {query[:50]}...")
            raise MemoryRetrievalError(f"Failed to search episodic memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error searching conversations: {query[:50]}...")
            raise MemoryRetrievalError(f"Failed to search episodic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete conversation from episodic memory.
        
        Args:
            key: The key of the conversation to delete
            **kwargs: Additional parameters
            
        Returns:
            True if conversation was deleted, False otherwise
            
        Raises:
            MemoryError: If deletion fails
        """
        try:
            # Check if key contains ObjectId
            obj_id = None
            if ":" in key and len(key.split(":")[-1]) == 24:
                try:
                    obj_id = ObjectId(key.split(":")[-1])
                except:
                    pass
            
            # Prepare query
            query = {"$or": [{"key": key}]}
            if obj_id:
                query["$or"].append({"_id": obj_id})
            
            # Delete document
            result = await self.collection.delete_one(query)
            
            deleted = result.deleted_count > 0
            
            if deleted:
                self.logger.debug(f"Deleted conversation from episodic memory: {key}")
            
            return deleted
            
        except PyMongoError as e:
            self.logger.exception(f"MongoDB error deleting conversation: {key}")
            raise MemoryError(f"Failed to delete from episodic memory: {str(e)}")
        except Exception as e:
            self.logger.exception(f"Unexpected error deleting conversation: {key}")
            raise MemoryError(f"Failed to delete from episodic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def clear(self, conversation_id: Optional[str] = None, **kwargs) -> None:
        """
        Clear conversations from episodic memory.
        
        Args:
            conversation_id: ID of the conversation to clear, or None to clear all
            **kwargs: Additional parameters
            
        Raises:
            MemoryError: If clearing fails
        """
        try:
            if conversation_id:
                # Clear a specific conversation
                result = await self.collection.delete_many({"conversation_id": conversation_id})
                self.logger.info(
                    f"Cleared conversation from episodic memory: {conversation_id}",
                    extra={"deleted_count": result.deleted_count}
                )
            else:
                # Clear all conversations
                result = await self.collection.delete_many({})
                self.logger.info(
                    "Cleared all episodic memory",
                    extra={"deleted_count": result.deleted_count}
                )
            
        except PyMongoError as e:
            self.logger.exception("MongoDB error clearing episodic memory")
            raise MemoryError(f"Failed to clear episodic memory: {str(e)}")
        except Exception as e:
            self.logger.exception("Unexpected error clearing episodic memory")
            raise MemoryError(f"Failed to clear episodic memory: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if MongoDB connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            # Check if we can access the server info
            server_info = await self.client.server_info()
            return True
        except Exception as e:
            self.logger.error(f"MongoDB health check failed: {str(e)}")
            return False
    
    async def close(self) -> None:
        """
        Close the MongoDB connection.
        
        This method should be called when shutting down the application
        to release resources properly.
        """
        try:
            self.client.close()
            self.logger.info("Closed episodic memory (MongoDB)")
        except Exception as e:
            self.logger.exception(f"Error closing episodic memory: {str(e)}")