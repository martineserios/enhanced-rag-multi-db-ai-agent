# filepath: backend/services/database/mongo.py
"""
MongoDB service for the application.

This module provides functions for interacting with MongoDB,
including initialization, querying, and natural language to query conversion.
"""
import json
import re
from typing import Dict, List, Any, Optional, Union
import asyncio
import logging

import motor.motor_asyncio
from pymongo import DESCENDING, TEXT
from pymongo.errors import PyMongoError
from bson import ObjectId, json_util

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    DatabaseError, DatabaseConnectionError, DatabaseQueryError
)
from app.config import Settings

logger = get_logger(__name__)

# Global MongoDB client instance
_client = None
_db = None

async def init_mongo(settings: Settings):
    """
    Initialize the MongoDB connection.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        MongoDB client instance
        
    Raises:
        DatabaseConnectionError: If the connection fails
    """
    global _client, _db
    
    try:
        # Create the MongoDB client
        _client = motor.motor_asyncio.AsyncIOMotorClient(settings.mongo_uri)
        
        # Get the database
        _db = _client[settings.mongo_db_name]
        
        # Simple connection test
        await _client.admin.command('ping')
        
        logger.info(
            f"MongoDB initialized successfully",
            extra={"uri": settings.mongo_uri, "db_name": settings.mongo_db_name}
        )
        
        return _client
        
    except PyMongoError as e:
        logger.exception("Failed to initialize MongoDB connection")
        raise DatabaseConnectionError(f"MongoDB connection failed: {str(e)}")
    except Exception as e:
        logger.exception("Unexpected error initializing MongoDB")
        raise DatabaseConnectionError(f"MongoDB initialization failed: {str(e)}")


def get_db():
    """
    Get the MongoDB database instance.
    
    Returns:
        MongoDB database instance
        
    Raises:
        DatabaseError: If the database is not initialized
    """
    global _db
    if _db is None:
        raise DatabaseError("MongoDB not initialized. Call init_mongo first.")
    return _db


@log_execution_time(logger)
async def query_collection(
    collection_name: str, 
    query: Dict[str, Any],
    projection: Optional[Dict[str, Any]] = None,
    sort: Optional[List[tuple]] = None,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Query a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to query
        query: MongoDB query document
        projection: Optional fields to include/exclude
        sort: Optional sort specification
        limit: Maximum number of results to return
        
    Returns:
        List of matching documents
        
    Raises:
        DatabaseQueryError: If the query fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Build the query
        cursor = collection.find(query, projection)
        
        # Apply sort if specified
        if sort:
            cursor = cursor.sort(sort)
        
        # Apply limit
        cursor = cursor.limit(limit)
        
        # Execute query and convert to list
        results = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        parsed_results = json.loads(json_util.dumps(results))
        
        logger.debug(
            f"MongoDB query executed",
            extra={
                "collection": collection_name,
                "query": str(query),
                "result_count": len(results)
            }
        )
        
        return parsed_results
        
    except PyMongoError as e:
        logger.exception(f"MongoDB query error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB query failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error querying MongoDB collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB query failed: {str(e)}")


@log_execution_time(logger)
async def count_documents(collection_name: str, query: Dict[str, Any]) -> int:
    """
    Count documents in a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to query
        query: MongoDB query document
        
    Returns:
        Count of matching documents
        
    Raises:
        DatabaseQueryError: If the query fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Execute count
        count = await collection.count_documents(query)
        
        logger.debug(
            f"MongoDB count executed",
            extra={
                "collection": collection_name,
                "query": str(query),
                "count": count
            }
        )
        
        return count
        
    except PyMongoError as e:
        logger.exception(f"MongoDB count error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB count failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error counting MongoDB documents in {collection_name}")
        raise DatabaseQueryError(f"MongoDB count failed: {str(e)}")


@log_execution_time(logger)
async def aggregate(
    collection_name: str,
    pipeline: List[Dict[str, Any]],
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    Execute an aggregation pipeline on a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to query
        pipeline: Aggregation pipeline stages
        limit: Maximum number of results to return
        
    Returns:
        List of documents resulting from the aggregation
        
    Raises:
        DatabaseQueryError: If the aggregation fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Execute aggregation
        cursor = collection.aggregate(pipeline)
        
        # Convert cursor to list
        results = await cursor.to_list(length=limit)
        
        # Convert ObjectId to string for JSON serialization
        parsed_results = json.loads(json_util.dumps(results))
        
        logger.debug(
            f"MongoDB aggregation executed",
            extra={
                "collection": collection_name,
                "pipeline_length": len(pipeline),
                "result_count": len(results)
            }
        )
        
        return parsed_results
        
    except PyMongoError as e:
        logger.exception(f"MongoDB aggregation error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB aggregation failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error running MongoDB aggregation on {collection_name}")
        raise DatabaseQueryError(f"MongoDB aggregation failed: {str(e)}")


@log_execution_time(logger)
async def insert_document(
    collection_name: str,
    document: Dict[str, Any]
) -> str:
    """
    Insert a document into a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to insert into
        document: Document to insert
        
    Returns:
        Inserted document ID
        
    Raises:
        DatabaseQueryError: If the insertion fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Insert document
        result = await collection.insert_one(document)
        
        logger.debug(
            f"MongoDB document inserted",
            extra={
                "collection": collection_name,
                "document_id": str(result.inserted_id)
            }
        )
        
        return str(result.inserted_id)
        
    except PyMongoError as e:
        logger.exception(f"MongoDB insert error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB insert failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error inserting into MongoDB collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB insert failed: {str(e)}")


@log_execution_time(logger)
async def update_document(
    collection_name: str,
    query: Dict[str, Any],
    update: Dict[str, Any],
    upsert: bool = False
) -> int:
    """
    Update documents in a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to update
        query: Query to select documents to update
        update: Update operations to apply
        upsert: Whether to insert a document if none match the query
        
    Returns:
        Number of documents modified
        
    Raises:
        DatabaseQueryError: If the update fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Update documents
        result = await collection.update_many(query, update, upsert=upsert)
        
        logger.debug(
            f"MongoDB documents updated",
            extra={
                "collection": collection_name,
                "matched_count": result.matched_count,
                "modified_count": result.modified_count,
                "upserted_id": str(result.upserted_id) if result.upserted_id else None
            }
        )
        
        return result.modified_count
        
    except PyMongoError as e:
        logger.exception(f"MongoDB update error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB update failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error updating MongoDB collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB update failed: {str(e)}")


@log_execution_time(logger)
async def delete_documents(
    collection_name: str,
    query: Dict[str, Any]
) -> int:
    """
    Delete documents from a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to delete from
        query: Query to select documents to delete
        
    Returns:
        Number of documents deleted
        
    Raises:
        DatabaseQueryError: If the deletion fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Delete documents
        result = await collection.delete_many(query)
        
        logger.debug(
            f"MongoDB documents deleted",
            extra={
                "collection": collection_name,
                "deleted_count": result.deleted_count
            }
        )
        
        return result.deleted_count
        
    except PyMongoError as e:
        logger.exception(f"MongoDB delete error for collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB delete failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error deleting from MongoDB collection {collection_name}")
        raise DatabaseQueryError(f"MongoDB delete failed: {str(e)}")


@log_execution_time(logger)
async def ensure_indexes(
    collection_name: str,
    indexes: List[Dict[str, Any]]
) -> List[str]:
    """
    Create indexes on a MongoDB collection.
    
    Args:
        collection_name: Name of the collection to index
        indexes: List of index specifications
        
    Returns:
        List of created index names
        
    Raises:
        DatabaseError: If index creation fails
    """
    try:
        db = get_db()
        collection = db[collection_name]
        
        # Create indexes
        created_indexes = []
        for index_spec in indexes:
            keys = index_spec.get("keys", {})
            options = {k: v for k, v in index_spec.items() if k != "keys"}
            
            index_name = await collection.create_index(keys, **options)
            created_indexes.append(index_name)
        
        logger.debug(
            f"MongoDB indexes created",
            extra={
                "collection": collection_name,
                "index_count": len(created_indexes),
                "indexes": created_indexes
            }
        )
        
        return created_indexes
        
    except PyMongoError as e:
        logger.exception(f"MongoDB index creation error for collection {collection_name}")
        raise DatabaseError(f"MongoDB index creation failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Unexpected error creating MongoDB indexes on {collection_name}")
        raise DatabaseError(f"MongoDB index creation failed: {str(e)}")


async def query_mongo(question: str, settings: Settings) -> str:
    """
    Generate a MongoDB query from a natural language question and execute it.
    
    This is a simplified implementation for the RAG chatbot. In a production system,
    you would use more sophisticated NLP or an LLM to convert questions to queries.
    
    Args:
        question: Natural language question
        settings: Application configuration settings
        
    Returns:
        JSON string of query results
        
    Raises:
        DatabaseQueryError: If the query fails
    """
    # Simple pattern matching to map questions to predefined queries
    # In a real system, you would use an LLM or more sophisticated NLP
    
    question_lower = question.lower()
    
    # Collection extraction patterns
    collections = {
        "user": "users",
        "profile": "user_profiles",
        "document": "documents",
        "setting": "settings",
        "config": "configurations"
    }
    
    # Determine which collection to query
    target_collection = None
    for keyword, collection in collections.items():
        if keyword in question_lower:
            target_collection = collection
            break
    
    if not target_collection:
        return json.dumps({"message": "No relevant MongoDB data found for this question."})
    
    try:
        # Execute a simple query on the identified collection
        query = {}
        
        # Check for specific patterns
        if "count" in question_lower:
            # Count query
            count = await count_documents(target_collection, query)
            return json.dumps({"count": count, "collection": target_collection})
        
        # Regular query
        results = await query_collection(target_collection, query, limit=5)
        
        # Format for display
        return json.dumps(results, indent=2)
        
    except DatabaseError as e:
        logger.error(f"Error querying MongoDB for question: {question}")
        return json.dumps({"error": str(e)})
    except Exception as e:
        logger.exception(f"Unexpected error in query_mongo: {str(e)}")
        return json.dumps({"error": f"Failed to query MongoDB: {str(e)}"})