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
from fastapi.responses import JSONResponse
from typing import List, Dict, Optional, Any
import uuid
from datetime import datetime
import asyncio

from app.core.logging import get_logger
from app.config import Settings, get_settings
from app.api.models.chat import (
    ChatRequest, ChatResponse, 
    ConversationSummary, ConversationMessage,
    ConversationHistoryResponse, ConversationDeleteResponse,
    ConversationListResponse
)
from app.services.llm.factory import get_llm_service
from app.services.llm.base import LLMProviderError, LLMRequestError
from app.services.database import query_postgres, query_mongo
from app.services.memory.manager import get_memory_manager
from app.core.exceptions import MemoryError, MemoryRetrievalError

import logging
logger = logging.getLogger("uvicorn.error") 


router = APIRouter()
logger = get_logger(__name__)

async def store_memory_in_background(memory_manager, memory_type, content, key, metadata, conversation_id):
    try:
        await memory_manager.store_memory(
            memory_type=memory_type,
            content=content,
            key=key,
            metadata=metadata,
            conversation_id=conversation_id
        )
    except Exception as e:
        logger.error(f"Error storing conversation in memory: {str(e)}")

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
                        store_memory_in_background,
                        memory_manager=memory_manager,
                        memory_type="short_term",
                        content=content,
                        key=message_key,
                        metadata=metadata,
                        conversation_id=conversation_id
                    )
                
                # Store in episodic memory
                if "episodic" in memory_types:
                    background_tasks.add_task(
                        store_memory_in_background,
                        memory_manager=memory_manager,
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


@router.get("/conversations", response_model=ConversationListResponse)
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
        List of ConversationSummary objects
        
    Raises:
        HTTPException: If retrieving conversations fails
    """
    try:
        if not settings.memory_enabled or not settings.enable_episodic_memory:
            logger.warning("Memory system or episodic memory is disabled")
            return []
        
        memory_manager = get_memory_manager()
        
        # Get unique conversation IDs from episodic memory
        try:
            if "episodic" not in memory_manager.memory_systems:
                logger.error("Episodic memory system not found in memory manager")
                return []
                
            mongo_db = memory_manager.memory_systems["episodic"].db
            if mongo_db is None:
                logger.error("MongoDB database not initialized in episodic memory system")
                return []
                
            try:
                # List all collections to verify the database is accessible
                collection_names = await mongo_db.list_collection_names()
                logger.info(f"Available collections in database: {collection_names}")
                
                # Get or create the episodic_memory collection
                episodic_collection = mongo_db["episodic_memory"]
                logger.info(f"Using MongoDB collection: {episodic_collection.name}")
                
                # Ensure indexes exist
                await episodic_collection.create_index([("conversation_id", 1)])
                await episodic_collection.create_index([("timestamp", -1)])
                
            except Exception as e:
                logger.error(f"Failed to access MongoDB collection: {str(e)}", exc_info=True)
                return []
            
            # First, check if the collection has any documents
            count = await episodic_collection.count_documents({})
            logger.info(f"Found {count} total documents in episodic_memory collection")
            
            if count == 0:
                logger.info("No conversations found in episodic memory")
                return []
            
            # Aggregate to get unique conversation IDs with latest timestamp
            pipeline = [
                {"$match": {"conversation_id": {"$exists": True, "$ne": None}}},  # Ensure conversation_id exists
                {"$sort": {"timestamp": -1}},
                {"$group": {
                    "_id": "$conversation_id",
                    "latest_message": {"$first": "$user_message"},
                    "latest_response": {"$first": "$assistant_message"},
                    "latest_time": {"$first": "$timestamp"},
                    "message_count": {"$sum": 1}
                }},
                {"$sort": {"latest_time": -1}},
                {"$limit": limit}
            ]
            
            logger.info(f"Executing aggregation pipeline: {pipeline}")
            cursor = episodic_collection.aggregate(pipeline)
            conversations = await cursor.to_list(length=limit)
            logger.info(f"Retrieved {len(conversations)} conversations from database")
            
        except Exception as db_error:
            logger.error(f"Database error in get_conversations: {str(db_error)}", exc_info=True)
            return []
        
        # Convert to ConversationSummary objects
        result = []
        
        # Ensure conversations is a list
        if not isinstance(conversations, list):
            logger.warning(f"Expected conversations to be a list, got {type(conversations)}. Converting to list.")
            conversations = [conversations] if conversations is not None else []
            
        logger.info(f"Processing {len(conversations) if conversations else 0} conversations")
        
        if not conversations:
            logger.info("No conversations to process")
            return result
            
        for idx, conv in enumerate(conversations, 1):
            try:
                logger.debug(f"Processing conversation {idx}/{len(conversations)}")
                
                # Debug log the conversation structure
                if not isinstance(conv, dict):
                    logger.warning(f"Unexpected conversation format (expected dict, got {type(conv)}): {conv}")
                    continue
                    
                # Log all available keys in the conversation
                logger.debug(f"Conversation keys: {list(conv.keys())}")
                
                # Safely get values with debug logging and type checking
                conv_id = conv.get("_id") if hasattr(conv, 'get') else None
                latest_msg = conv.get("latest_message") if hasattr(conv, 'get') else None
                latest_resp = conv.get("latest_response") if hasattr(conv, 'get') else None
                latest_time = conv.get("latest_time") if hasattr(conv, 'get') else None
                msg_count = conv.get("message_count") if hasattr(conv, 'get') else 0
                
                # Log the extracted values for debugging
                logger.debug(
                    f"Extracted values - id: {conv_id}, "
                    f"latest_msg: {latest_msg}, latest_resp: {latest_resp}, "
                    f"latest_time: {latest_time}, count: {msg_count}"
                )
                
                # Handle datetime conversion
                if isinstance(latest_time, datetime):
                    latest_time = latest_time.isoformat()
                
                # Ensure all required fields have safe defaults
                safe_conv_id = str(conv_id) if conv_id is not None else f"unknown_{idx}"
                safe_latest_msg = str(latest_msg) if latest_msg is not None else ""
                safe_latest_resp = str(latest_resp) if latest_resp is not None else ""
                safe_latest_time = str(latest_time) if latest_time is not None else ""
                safe_msg_count = int(msg_count) if msg_count is not None and str(msg_count).isdigit() else 0
                
                # Create the summary object
                summary = ConversationSummary(
                    conversation_id=safe_conv_id,
                    latest_message=safe_latest_msg,
                    latest_response=safe_latest_resp,
                    latest_time=safe_latest_time,
                    message_count=safe_msg_count
                )
                
                logger.debug(f"Created summary: {summary}")
                result.append(summary)
                
            except Exception as e:
                logger.error(
                    f"Error processing conversation at index {idx}: {str(e)}", 
                    exc_info=True, 
                    extra={"conversation_data": str(conv)[:500] if conv else "No conversation data"}
                )
                continue
        
        # Return the result using the ConversationListResponse model
        return {"conversations": result, "total_count": len(result)}
        
    except Exception as e:
        logger.exception(f"Error retrieving conversations: {str(e)}")
        # Return empty response with proper structure on error
        return {"conversations": [], "total_count": 0}


@router.get("/conversation/{conversation_id}", response_model=ConversationHistoryResponse)
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
        ConversationHistoryResponse with conversation details and messages
        
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
        
        # Convert results to ConversationMessage objects
        messages = []
        if results:
            for msg in results:
                try:
                    if not isinstance(msg, dict):
                        logger.warning(f"Unexpected message format: {msg}")
                        continue
                        
                    timestamp = msg.get("timestamp")
                    if isinstance(timestamp, datetime):
                        timestamp = timestamp.isoformat()
                    
                    messages.append(ConversationMessage(
                        message_id=msg.get("id") or str(uuid.uuid4()),
                        conversation_id=conversation_id,
                        user_message=msg.get("user_message", "") or "",
                        assistant_message=msg.get("assistant_message", "") or "",
                        timestamp=timestamp or "",
                        memory_sources=msg.get("memory_sources", {}) or {},
                        provider=msg.get("provider"),
                        metadata=msg.get("metadata", {}) or {}
                    ))
                except Exception as e:
                    logger.error(f"Error processing message: {str(e)}", exc_info=True)
                    continue
        
        # Sort messages by timestamp (newest first)
        messages.sort(key=lambda x: x.timestamp, reverse=True)
        
        return ConversationHistoryResponse(
            conversation_id=conversation_id,
            message_count=len(messages),
            messages=messages
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to retrieve conversation history: {str(e)}"
        )


@router.delete("/conversation/{conversation_id}", response_model=ConversationDeleteResponse)
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
        ConversationDeleteResponse with status and message
        
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
        
        return ConversationDeleteResponse(
            conversation_id=conversation_id,
            status="deleted",
            message=f"Conversation {conversation_id} deleted successfully"
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting conversation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete conversation: {str(e)}")

@router.get("/providers")
async def get_providers(settings: Settings = Depends(get_settings)):
    """
    Return a list of all available LLM providers and their status.
    
    Returns:
        dict: Dictionary containing:
            - providers: List of available provider names
            - default: Default provider name
            - status: Dictionary mapping provider names to their status (enabled/disabled)
    """
    from app.services.llm.factory import LLM_SERVICES
    
    # Get all configured providers
    configured_providers = getattr(settings, "llm_providers", [])
    
    # Check which providers are actually available (have API keys)
    available_providers = []
    status = {}
    
    for provider in configured_providers:
        try:
            api_key_attr = f"{provider}_api_key"
            if hasattr(settings, api_key_attr) and getattr(settings, api_key_attr):
                available_providers.append(provider)
                status[provider] = "enabled"
            else:
                status[provider] = "disabled"
        except Exception as e:
            status[provider] = f"error: {str(e)}"
    
    # Get default provider from settings or use the first available
    default_provider = getattr(settings, "default_llm_provider", None)
    if isinstance(default_provider, str):
        default_provider = default_provider.lower()
    elif hasattr(default_provider, "value"):
        default_provider = default_provider.value.lower()
    
    # If default provider is not available, use first available provider
    if not default_provider or default_provider not in available_providers:
        default_provider = available_providers[0] if available_providers else None
    
    logger.info(
        f"Available providers: {available_providers}, "
        f"Default: {default_provider}, "
        f"Status: {status}"
    )
    
    return {
        "providers": available_providers,
        "default": default_provider,
        "status": status
    }