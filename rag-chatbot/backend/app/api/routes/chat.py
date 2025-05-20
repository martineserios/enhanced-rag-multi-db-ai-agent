# filepath: backend/app/api/routes/chat.py
"""
API routes for chat functionality.

This module defines the FastAPI routes for chat operations, including sending
messages, retrieving conversation history, and managing chat sessions.
"""
from typing import Dict, List, Any, Optional, Literal
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from pydantic import BaseModel
from app.core.logging import get_logger
from app.config import Settings, get_settings
from app.api.models.chat import (
    ChatRequest, ChatResponse, 
    ConversationSummary, ConversationMessage,
    ConversationHistoryResponse, ConversationDeleteResponse,
    ConversationListResponse, AgentListResponse, AgentSettingsResponse
)
from app.services.agents.factory import AgentFactory
from app.services.agents.base import AgentError
from app.services.llm.base import LLMProviderError, LLMRequestError
from app.core.exceptions import MemoryError, MemoryRetrievalError

router = APIRouter()
logger = get_logger(__name__)

@router.post("/", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    settings: Settings = Depends(get_settings)
):
    """
    Process a chat message using the specified agent and LLM provider.
    
    Args:
        request: Chat request containing message and parameters
        settings: Application settings
        
    Returns:
        ChatResponse with the generated message and metadata
        
    Raises:
        HTTPException: If the request is invalid or processing fails
    """
    try:
        # Get the appropriate agent
        agent = AgentFactory.create_agent(
            agent_id=request.agent_id or settings.default_agent_id,
            settings=settings
        )
        
        # Process the request
        return await agent.process_chat_request(request)
        
    except AgentError as e:
        logger.error(f"Agent error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except LLMProviderError as e:
        logger.error(f"LLM provider error: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))
    except LLMRequestError as e:
        logger.error(f"LLM request error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error processing chat request: {str(e)}")
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/agents", response_model=AgentListResponse)
async def list_agents(settings: Settings = Depends(get_settings)):
    """
    List all available chat agents.
    
    Args:
        settings: Application settings
        
    Returns:
        List of available agents with their metadata
    """
    try:
        agents = AgentFactory.list_available_agents()
        return AgentListResponse(
            agents=agents["agents"],
            default_agent_id=agents["default_agent_id"]
        )
    except Exception as e:
        logger.exception(f"Error listing agents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list agents: {str(e)}")

@router.get("/agents/{agent_id}/settings", response_model=AgentSettingsResponse)
async def get_agent_settings(
    agent_id: str = Path(..., description="ID of the agent"),
    settings: Settings = Depends(get_settings)
):
    """
    Get settings for a specific agent.
    
    Args:
        agent_id: ID of the agent
        settings: Application settings
        
    Returns:
        Agent settings and schema
        
    Raises:
        HTTPException: If the agent is not found or settings cannot be retrieved
    """
    try:
        agent = AgentFactory.create_agent(agent_id, settings)
        return {
            "agent_id": agent.agent_id,
            "agent_name": agent.agent_name,
            "settings": await agent.get_available_settings(),
            "schema": agent.agent_settings_schema
        }
    except AgentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.exception(f"Error getting agent settings: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to get agent settings: {str(e)}")

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
    """
    try:
        # Use the default agent to get conversations
        agent = AgentFactory.get_default_agent(settings)
        return await agent.get_conversations(limit)
    except Exception as e:
        logger.exception(f"Error retrieving conversations: {str(e)}")
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
        # Use the default agent to get conversation history
        agent = AgentFactory.get_default_agent(settings)
        return await agent.get_conversation_history(conversation_id, limit)
    except MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MemoryRetrievalError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.exception(f"Error retrieving conversation history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve conversation history: {str(e)}")

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
        # Use the default agent to delete the conversation
        agent = AgentFactory.get_default_agent(settings)
        return await agent.delete_conversation(conversation_id)
    except MemoryError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except MemoryRetrievalError as e:
        raise HTTPException(status_code=404, detail=str(e))
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
    try:
        # Use the default agent to get providers
        agent = AgentFactory.get_default_agent(settings)
        return await agent.get_providers()
    except Exception as e:
        logger.exception(f"Error getting providers: {str(e)}")
        return {"providers": [], "default": None, "status": {}}