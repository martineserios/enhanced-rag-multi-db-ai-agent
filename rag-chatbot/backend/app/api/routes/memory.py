# filepath: backend/app/api/routes/memory.py
"""
API routes for memory operations.

This module defines the FastAPI routes for memory-related operations, including
querying different memory types and managing memory contents.
"""
from typing import Dict, List, Any, Optional, Annotated
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.exceptions import MemoryError, MemoryRetrievalError
from app.config import Settings, get_settings
from app.services.memory.manager import get_memory_manager
from app.api.dependencies import (
    verify_memory_enabled,
    get_memory_manager_dependency,
    get_request_metadata
)


router = APIRouter()
logger = get_logger(__name__)


class MemoryQueryRequest(BaseModel):
    """Request for multi-context memory queries."""
    query: str
    conversation_id: Optional[str] = None
    memory_types: Optional[List[str]] = None
    weights: Optional[Dict[str, float]] = None
    limit_per_type: int = Field(5, ge=1, le=20)


@router.get("/health")
async def memory_health_check(
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Check the health of memory systems.
    
    Args:
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with health status of each memory system
    """
    try:
        # Check health of each memory system
        health_results = {}
        
        for name, system in memory_manager.memory_systems.items():
            try:
                health = await system.health_check()
                health_results[name] = health
            except Exception as e:
                logger.error(f"Error checking health of {name} memory: {str(e)}")
                health_results[name] = False
        
        return {"status": health_results}
        
    except Exception as e:
        logger.exception(f"Error checking memory health: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory health check failed: {str(e)}")


@router.get("")
async def query_all_memory(
    query: str = Query(..., description="Search query"),
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID"),
    limit: int = Query(5, ge=1, le=20, description="Maximum results per memory type"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency),
    request_metadata: Dict[str, Any] = Depends(get_request_metadata)
):
    """
    Query all memory types for relevant information.
    
    This endpoint demonstrates Multi-Context Processing by querying
    multiple memory systems in parallel and returning the combined results.
    
    Args:
        query: The search query
        conversation_id: Optional conversation ID to filter results
        limit: Maximum results per memory type
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        request_metadata: Request metadata from dependency
        
    Returns:
        Dictionary with query results from each memory type
        
    Raises:
        HTTPException: If the query fails
    """
    try:
        logger.info(
            f"Multi-context memory query: {query}",
            extra={
                "conversation_id": conversation_id,
                "limit": limit,
                "request_id": request_metadata.get("request_id")
            }
        )
        
        # Query all memory types
        results = await memory_manager.multi_context_query(
            query=query,
            conversation_id=conversation_id,
            limit_per_type=limit
        )
        
        # Format the results
        # Convert timestamps to ISO format
        for memory_type, items in results.items():
            for item in items:
                if isinstance(item, dict) and "timestamp" in item:
                    timestamp = item["timestamp"]
                    if hasattr(timestamp, "isoformat"):
                        item["timestamp"] = timestamp.isoformat()
        
        return {
            "query": query,
            "conversation_id": conversation_id,
            "results": results
        }
        
    except MemoryError as e:
        logger.error(f"Memory error in multi-context query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error in multi-context memory query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")


@router.post("/query")
async def query_memory_post(
    request: MemoryQueryRequest,
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency),
    request_metadata: Dict[str, Any] = Depends(get_request_metadata)
):
    """
    Query memory systems with a POST request body.
    
    This endpoint is similar to the GET endpoint but accepts a JSON body,
    allowing for more complex query parameters.
    
    Args:
        request: Memory query request
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        request_metadata: Request metadata from dependency
        
    Returns:
        Dictionary with query results from each memory type
        
    Raises:
        HTTPException: If the query fails
    """
    try:
        logger.info(
            f"Multi-context memory query (POST): {request.query}",
            extra={
                "conversation_id": request.conversation_id,
                "memory_types": request.memory_types,
                "limit": request.limit_per_type,
                "request_id": request_metadata.get("request_id")
            }
        )
        
        # Query specified memory types
        results = await memory_manager.multi_context_query(
            query=request.query,
            conversation_id=request.conversation_id,
            memory_types=request.memory_types,
            weights=request.weights,
            limit_per_type=request.limit_per_type
        )
        
        # Format results
        for memory_type, items in results.items():
            for item in items:
                if isinstance(item, dict) and "timestamp" in item:
                    timestamp = item["timestamp"]
                    if hasattr(timestamp, "isoformat"):
                        item["timestamp"] = timestamp.isoformat()
        
        return {
            "query": request.query,
            "conversation_id": request.conversation_id,
            "memory_types": request.memory_types,
            "results": results
        }
        
    except MemoryError as e:
        logger.error(f"Memory error in multi-context query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error in multi-context memory query: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory query failed: {str(e)}")


@router.get("/context")
async def create_unified_context(
    query: str = Query(..., description="Search query"),
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Create a unified context string from all memory types.
    
    This endpoint demonstrates how context is created for the LLM by combining
    information from multiple memory sources into a unified context.
    
    Args:
        query: The search query
        conversation_id: Optional conversation ID to filter results
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with the unified context
        
    Raises:
        HTTPException: If creating the context fails
    """
    try:
        # Create unified context
        context = await memory_manager.create_unified_context(
            query=query,
            conversation_id=conversation_id
        )
        
        return {
            "query": query,
            "conversation_id": conversation_id,
            "context": context,
            "context_length": len(context)
        }
        
    except MemoryError as e:
        logger.error(f"Memory error creating unified context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Context creation failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error creating unified context: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Context creation failed: {str(e)}")


@router.get("/types")
async def get_memory_types(
    settings: Settings = Depends(get_settings)
):
    """
    Get information about available memory types.
    
    Args:
        settings: Application settings
        
    Returns:
        Dictionary with memory type information
    """
    if not settings.memory_enabled:
        return {
            "enabled": False,
            "types": {}
        }
    
    memory_types = {
        "short_term": {
            "name": "Short-term Memory",
            "description": "Recent conversation context stored in Redis",
            "enabled": settings.enable_short_term_memory,
            "ttl": settings.short_term_ttl
        },
        "semantic": {
            "name": "Semantic Memory",
            "description": "Document knowledge stored in ChromaDB",
            "enabled": settings.enable_semantic_memory,
            "embedding_model": settings.embedding_model
        },
        "episodic": {
            "name": "Episodic Memory",
            "description": "Past conversation history stored in MongoDB",
            "enabled": settings.enable_episodic_memory
        },
        "procedural": {
            "name": "Procedural Memory",
            "description": "Action workflows stored in Neo4j",
            "enabled": settings.enable_procedural_memory
        }
    }
    
    return {
        "enabled": True,
        "types": memory_types,
        "weights": settings.memory_weights
    }


@router.get("/short-term/{conversation_id}")
async def get_short_term_memory(
    conversation_id: str = Path(..., description="Conversation ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Get short-term memory for a specific conversation.
    
    Args:
        conversation_id: ID of the conversation
        limit: Maximum number of results
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with short-term memory items
        
    Raises:
        HTTPException: If retrieving memory fails
    """
    try:
        # Check if short-term memory is enabled
        if "short_term" not in memory_manager.memory_systems:
            raise HTTPException(
                status_code=400,
                detail="Short-term memory is not enabled"
            )
        
        # Search short-term memory
        results = await memory_manager.search_memory(
            memory_type="short_term",
            query="",  # Empty query to get all items
            conversation_id=conversation_id,
            limit=limit
        )
        
        return {
            "conversation_id": conversation_id,
            "memory_type": "short_term",
            "items": results
        }
        
    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"Memory error retrieving short-term memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory retrieval failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error retrieving short-term memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory retrieval failed: {str(e)}")


@router.get("/episodic")
async def get_episodic_memory(
    conversation_id: Optional[str] = Query(None, description="Optional conversation ID"),
    keyword: Optional[str] = Query(None, description="Optional keyword to search for"),
    limit: int = Query(10, ge=1, le=50, description="Maximum results"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Search episodic memory for conversations.
    
    Args:
        conversation_id: Optional ID to filter by conversation
        keyword: Optional keyword to search for
        limit: Maximum number of results
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with episodic memory items
        
    Raises:
        HTTPException: If searching memory fails
    """
    try:
        # Check if episodic memory is enabled
        if "episodic" not in memory_manager.memory_systems:
            raise HTTPException(
                status_code=400,
                detail="Episodic memory is not enabled"
            )
        
        # Need at least one search parameter
        if not conversation_id and not keyword:
            raise HTTPException(
                status_code=400,
                detail="Either conversation_id or keyword must be provided"
            )
        
        # Search episodic memory
        if keyword:
            # Search by keyword
            results = await memory_manager.search_memory(
                memory_type="episodic",
                query=keyword,
                limit=limit
            )
        else:
            # Search by conversation ID
            results = await memory_manager.search_memory(
                memory_type="episodic",
                query="",  # Empty query to get all items
                conversation_id=conversation_id,
                limit=limit
            )
        
        return {
            "conversation_id": conversation_id,
            "keyword": keyword,
            "memory_type": "episodic",
            "items": results
        }
        
    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"Memory error searching episodic memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error searching episodic memory: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Memory search failed: {str(e)}")


@router.get("/procedural/{name}")
async def get_procedural_memory(
    name: str = Path(..., description="Procedure name"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Get a procedure from procedural memory.
    
    Args:
        name: Name of the procedure
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with procedure steps
        
    Raises:
        HTTPException: If retrieving the procedure fails
    """
    try:
        # Check if procedural memory is enabled
        if "procedural" not in memory_manager.memory_systems:
            raise HTTPException(
                status_code=400,
                detail="Procedural memory is not enabled"
            )
        
        # Retrieve procedure
        procedure = await memory_manager.retrieve_memory(
            memory_type="procedural",
            key=name
        )
        
        if not procedure:
            raise HTTPException(
                status_code=404,
                detail=f"Procedure '{name}' not found"
            )
        
        return {
            "name": name,
            "memory_type": "procedural",
            "procedure": procedure
        }
        
    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"Memory error retrieving procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure retrieval failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error retrieving procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure retrieval failed: {str(e)}")


class ProcedureRequest(BaseModel):
    """Request for creating or updating a procedure."""
    name: str
    steps: List[Dict[str, Any]]
    metadata: Optional[Dict[str, Any]] = None


@router.post("/procedural")
async def create_procedural_memory(
    request: ProcedureRequest,
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Create a new procedure in procedural memory.
    
    Args:
        request: Procedure creation request
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with creation status
        
    Raises:
        HTTPException: If creating the procedure fails
    """
    try:
        # Check if procedural memory is enabled
        if "procedural" not in memory_manager.memory_systems:
            raise HTTPException(
                status_code=400,
                detail="Procedural memory is not enabled"
            )
        
        # Validate steps
        if not request.steps:
            raise HTTPException(
                status_code=400,
                detail="Procedure must have at least one step"
            )
        
        # Create procedure
        procedure_id = await memory_manager.store_memory(
            memory_type="procedural",
            key=request.name,
            content={"steps": request.steps},
            metadata=request.metadata
        )
        
        return {
            "status": "success",
            "message": f"Procedure '{request.name}' created successfully",
            "procedure_id": procedure_id,
            "step_count": len(request.steps)
        }
        
    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"Memory error creating procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure creation failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error creating procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure creation failed: {str(e)}")


@router.delete("/procedural/{name}")
async def delete_procedural_memory(
    name: str = Path(..., description="Procedure name"),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Delete a procedure from procedural memory.
    
    Args:
        name: Name of the procedure to delete
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Dictionary with deletion status
        
    Raises:
        HTTPException: If deleting the procedure fails
    """
    try:
        # Check if procedural memory is enabled
        if "procedural" not in memory_manager.memory_systems:
            raise HTTPException(
                status_code=400,
                detail="Procedural memory is not enabled"
            )
        
        # Delete procedure
        deleted = await memory_manager.delete_memory(
            memory_type="procedural",
            key=name
        )
        
        if not deleted:
            raise HTTPException(
                status_code=404,
                detail=f"Procedure '{name}' not found"
            )
        
        return {
            "status": "success",
            "message": f"Procedure '{name}' deleted successfully"
        }
        
    except HTTPException:
        raise
    except MemoryError as e:
        logger.error(f"Memory error deleting procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure deletion failed: {str(e)}")
    except Exception as e:
        logger.exception(f"Error deleting procedure: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Procedure deletion failed: {str(e)}")