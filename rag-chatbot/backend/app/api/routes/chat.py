# filepath: backend/app/api/routes/chat.py
"""
API routes for chat functionality.

This module defines the FastAPI routes for chat operations, including sending
messages, retrieving conversation history, and managing chat sessions.
"""
from typing import Dict, List, Any, Optional, Annotated
import uuid
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks, Query, Path, Body
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.exceptions import (
    LLMError, LLMProviderError, LLMRequestError, 
    MemoryError, MemoryRetrievalError
)
from app.config import Settings, get_settings, ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from app.services.database.postgres import query_postgres
from app.services.database.mongo import query_mongo

import logging
logger = logging.getLogger("uvicorn.error") 


router = APIRouter()
logger = get_logger(__name__)

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    background_tasks: BackgroundTasks,
    settings: Settings = Depends(get_settings)
):
    """
    Process a chat message using the specified LLM provider with memory-enhanced RAG.
    
    This endpoint:
    1. Validates the request
    2. Retrieves context from memory systems
    3. Generates a response using the selected LLM
    4. Stores the interaction in memory
    5. Returns the response with metadata
    
    Args:
        request: Chat request containing message and parameters
        background_tasks: FastAPI background tasks for async operations
        settings: Application settings
        
    Returns:
        ChatResponse with the generated message and metadata
        
    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    try:
        # Validate provider is available
        if hasattr(request.provider, "value"):
            provider = request.provider.value
        elif request.provider:
            provider = request.provider
        elif hasattr(settings.default_llm_provider, "value"):
            provider = settings.default_llm_provider.value
        else:
            provider = settings.default_llm_provider

        # Check if provider API key is configured
        api_key_attr = f"{provider}_api_key"
        api_key_value = getattr(settings, api_key_attr, None)
        logger.info(f"Provider: {provider}")
        logger.info(f"API key attribute: {api_key_attr}")
        logger.info(f"API key value: {api_key_value}")

        if not hasattr(settings, api_key_attr) or not api_key_value:
            raise LLMProviderError(f"{provider.capitalize()} API key is not configured")
        
        # Initialize conversation ID if not provided
        conversation_id = request.conversation_id or str(uuid.uuid4())
        
        logger.info(
            f"Processing chat request with {provider}",
            extra={
                "conversation_id": conversation_id,
                "provider": provider,
                "message_length": len(request.message),
                "use_memory": request.use_memory,
                "use_rag": request.use_rag,
                "use_sql": request.use_sql,
                "use_mongo": request.use_mongo
            }
        )
        
        # Get the LLM service
        llm_service = get_llm_service(provider, settings)
        
        # Collect context from various sources
        context = ""
        memory_sources = {
            "short_term": False,
            "semantic": False,
            "episodic": False,
            "procedural": False
        }
        
        # Use Memory Manager for context if memory is enabled
        if settings.memory_enabled and request.use_memory:
            try:
                memory_manager = get_memory_manager()
                
                # Determine which memory types to use
                memory_types = request.memory_types or settings.get_enabled_memory_types()
                
                # Get unified context from multiple memory sources
                context = await memory_manager.create_unified_context(
                    query=request.message,
                    conversation_id=conversation_id,
                    memory_types=memory_types,
                    weights=request.memory_weights
                )
                
                # Update memory sources that were used
                if context:
                    for memory_type in memory_types:
                        memory_sources[memory_type] = True
                
                logger.debug(
                    "Retrieved context from memory",
                    extra={
                        "context_length": len(context),
                        "memory_types": memory_types
                    }
                )
                
            except MemoryError as e:
                logger.error(f"Error retrieving context from memory: {str(e)}")
                # Continue without memory context
        
        # Add SQL context if requested
        if request.use_sql:
            try:
                sql_results = await query_postgres(request.message, settings)
                if sql_results:
                    context += "\n\n## SQL Database Results\n" + sql_results
            except Exception as e:
                logger.error(f"Error querying SQL database: {str(e)}")
        
        # Add MongoDB context if requested
        if request.use_mongo:
            try:
                mongo_results = await query_mongo(request.message, settings)
                if mongo_results:
                    context += "\n\n## MongoDB Results\n" + mongo_results
            except Exception as e:
                logger.error(f"Error querying MongoDB: {str(e)}")
        
        # Generate chat response using the LLM with the context
        response = await llm_service.generate_response(
            query=request.message,
            context=context
        )
        
        # Store the conversation in memory if enabled (as a background task)
        if settings.memory_enabled and request.use_memory:
            try:
                # Structure the conversation content
                content = {
                    "user_message": request.message,
                    "assistant_message": response
                }
                
                # Metadata about the conversation
                metadata = {
                    "provider": provider,
                    "timestamp": datetime.utcnow().isoformat(),
                    "memory_types_used": [
                        memory_type for memory_type, used in memory_sources.items() if used
                    ]
                }
                
                # Generate a unique key for the message
                message_key = f"conversation:{conversation_id}:message:{uuid.uuid4()}"
                
                # Store in short-term memory
                if "short_term" in memory_types:
                    background_tasks.add_task(
                        memory_manager.store_memory,
                        memory_type="short_term",
                        content=content,
                        key=message_key,
                        metadata=metadata,
                        conversation_id=conversation_id
                    )
                
                # Store in episodic memory
                if "episodic" in memory_types:
                    background_tasks.add_task(
                        memory_manager.store_memory,
                        memory_type="episodic",
                        content=content,
                        key=message_key,
                        metadata=metadata,
                        conversation_id=conversation_id
                    )
                
            except Exception as e:
                logger.error(f"Error storing conversation in memory: {str(e)}")
                # Continue without storing in memory
        
        logger.info(
            f"Chat response generated successfully",
            extra={
                "conversation_id": conversation_id,
                "provider": provider,
                "response_length": len(response)
            }
        )
        
        # Return the response
        return ChatResponse(
            message=response,
            conversation_id=conversation_id,
            provider=provider,
            memory_sources=memory_sources
        )
        
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except LLMRequestError as e:
        logger.error(f"LLM request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")


@router.get("/conversations")
async def get_conversations(
    limit: int = Query(10, ge=1, le=100),
    settings: Settings = Depends(get_settings)
):
    """
    Get a list of existing conversations from episodic memory.
    
    Args:
        limit: Maximum number of conversations to return
        settings: Application settings
        
    Returns:
        Dictionary with list of conversations
        
    Raises:
        HTTPException: If retrieving conversations fails
    """
    try:
        if not settings.memory_enabled or not settings.enable_episodic_memory:
            logger.warning("Memory system or episodic memory is disabled")
            return {"conversations": []}
        
        memory_manager = get_memory_manager()
        
        # Get unique conversation IDs from episodic memory
        mongo_db = memory_manager.memory_systems["episodic"].db
        episodic_collection = mongo_db["episodic_memory"]
        
        # Aggregate to get unique conversation IDs with latest timestamp
        pipeline = [
            {"$sort": {"timestamp": -1}},
            {"$group": {
                "_id": "$conversation_id",
                "latest_message": {"$first": "$user_message"},
                "latest_response": {"$first": "$assistant_message"},
                "latest_time": {"$first": "$timestamp"},
                "count": {"$sum": 1}
            }},
            {"$sort": {"latest_time": -1}},
            {"$limit": limit}
        ]
        
        cursor = episodic_collection.aggregate(pipeline)
        conversations = await cursor.to_list(length=limit)
        
        # Format timestamps and truncate long messages
        for conv in conversations:
            if "latest_time" in conv:
                conv["latest_time"] = conv["latest_time"].isoformat()
            
            # Truncate long messages
            if "latest_message" in conv and len(conv["latest_message"]) > 100:
                conv["latest_message"] = conv["latest_message"][:100] + "..."
            
            if "latest_response" in conv and len(conv["latest_response"]) > 100:
                conv["latest_response"] = conv["latest_response"][:100] + "..."
        
        return {
            "conversations": [
                {
                    "conversation_id": conv["_id"],
                    "latest_message": conv.get("latest_message", ""),
                    "latest_response": conv.get("latest_response", ""),
                    "latest_time": conv.get("latest_time", ""),
                    "message_count": conv.get("count", 0)
                }
                for conv in conversations
            ]
        }
        
    except Exception as e:
        logger.exception(f"Error retrieving conversations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversations: {str(e)}")


@router.get("/conversation/{conversation_id}")
async def get_conversation_history(
    conversation_id: str = Path(..., description="ID of the conversation to retrieve"),
    limit: int = Query(20, ge=1, le=100),
    settings: Settings = Depends(get_settings)
):
    """
    Get the message history for a specific conversation.
    
    Args:
        conversation_id: ID of the conversation to retrieve
        limit: Maximum number of messages to return
        settings: Application settings
        
    Returns:
        Dictionary with conversation details and messages
        
    Raises:
        HTTPException: If retrieving the conversation fails
    """
    try:
        if not settings.memory_enabled or not settings.enable_episodic_memory:
            logger.warning("Memory system or episodic memory is disabled")
            raise HTTPException(status_code=400, detail="Conversation history is not available")
        
        memory_manager = get_memory_manager()
        
        # Retrieve conversation messages from episodic memory
        results = await memory_manager.search_memory(
            memory_type="episodic",
            query="",  # Empty query to get all messages
            limit=limit,
            conversation_id=conversation_id
        )
        
        if not results:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        # Sort messages by timestamp
        messages = sorted(
            results,
            key=lambda x: x.get("timestamp", ""),
            reverse=True  # Newest first
        )
        
        # Format the response
        return {
            "conversation_id": conversation_id,
            "message_count": len(messages),
            "messages": messages
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(
    conversation_id: str = Path(..., description="ID of the conversation to delete"),
    settings: Settings = Depends(get_settings)
):
    """
    Delete a conversation and all its messages from memory.
    
    Args:
        conversation_id: ID of the conversation to delete
        settings: Application settings
        
    Returns:
        Status message indicating success
        
    Raises:
        HTTPException: If deleting the conversation fails
    """
    try:
        if not settings.memory_enabled:
            logger.warning("Memory system is disabled")
            raise HTTPException(status_code=400, detail="Conversation management is not available")
        
        memory_manager = get_memory_manager()
        deleted = False
        
        # Delete from short-term memory if enabled
        if settings.enable_short_term_memory and "short_term" in memory_manager.memory_systems:
            try:
                await memory_manager.memory_systems["short_term"].clear(conversation_id=conversation_id)
                deleted = True
            except Exception as e:
                logger.error(f"Error clearing short-term memory: {str(e)}")
        
        # Delete from episodic memory if enabled
        if settings.enable_episodic_memory and "episodic" in memory_manager.memory_systems:
            try:
                mongo_db = memory_manager.memory_systems["episodic"].db
                episodic_collection = mongo_db["episodic_memory"]
                
                result = await episodic_collection.delete_many({"conversation_id": conversation_id})
                if result.deleted_count > 0:
                    deleted = True
                    
            except Exception as e:
                logger.error(f"Error clearing episodic memory: {str(e)}")
        
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Conversation {conversation_id} not found")
        
        return {
            "status": "success",
            "message": f"Conversation {conversation_id} deleted successfully"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.get("/providers")
def get_providers(settings: Settings = Depends(get_settings)):
    """
    Return a list of all available LLM providers.
    """
    # Adjust the attribute name as needed
    providers = getattr(settings, "llm_providers", ["openai"])
    return {"providers": providers}