# filepath: backend/tests/integration/test_chat_flow.py
"""
Integration tests for the chat flow.

This module tests the complete chat flow from API request to response,
ensuring that all components work together correctly.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings, get_settings
from app.services.memory.manager import MemoryManager
from app.services.llm.factory import get_llm_service


@pytest.fixture
def test_client():
    """Create a FastAPI test client."""
    return TestClient(app)


@pytest.fixture
def mock_settings():
    """Create mock settings for tests."""
    settings = MagicMock(spec=Settings)
    settings.memory_enabled = True
    settings.enable_short_term_memory = True
    settings.enable_semantic_memory = True
    settings.enable_episodic_memory = True
    settings.enable_procedural_memory = True
    settings.default_llm_provider = "openai"
    settings.openai_api_key = "test_openai_key"
    settings.anthropic_api_key = "test_anthropic_key"
    settings.groq_api_key = "test_groq_key"
    return settings


@pytest.fixture
def mock_dependencies(mock_settings):
    """Mock dependencies for integration tests."""
    # Override get_settings
    app.dependency_overrides[get_settings] = lambda: mock_settings
    
    # Mock memory manager and LLM service
    with patch('app.api.dependencies.get_memory_manager') as mock_get_memory_manager, \
         patch('app.api.dependencies.get_llm_service') as mock_get_llm_service, \
         patch('app.api.routes.chat.get_memory_manager') as mock_chat_get_memory_manager, \
         patch('app.api.routes.chat.get_llm_service') as mock_chat_get_llm_service:
        
        # Create mock memory manager
        mock_memory_manager = MagicMock()
        mock_memory_manager.create_unified_context = AsyncMock(
            return_value="This is the unified context from memory."
        )
        mock_memory_manager.store_memory = AsyncMock(return_value="test_key")
        mock_get_memory_manager.return_value = mock_memory_manager
        mock_chat_get_memory_manager.return_value = mock_memory_manager
        
        # Create mock LLM service
        mock_llm_service = MagicMock()
        mock_llm_service.generate_response = AsyncMock(
            return_value="I'm a helpful assistant responding to your query."
        )
        mock_get_llm_service.return_value = mock_llm_service
        mock_chat_get_llm_service.return_value = mock_llm_service
        
        yield {
            "memory_manager": mock_memory_manager,
            "llm_service": mock_llm_service
        }
    
    # Clean up
    app.dependency_overrides = {}


def test_chat_endpoint(test_client, mock_dependencies):
    """Test the chat endpoint."""
    # Prepare request data
    data = {
        "message": "What is RAG?",
        "conversation_id": None,
        "provider": "openai",
        "use_rag": True,
        "use_sql": False,
        "use_mongo": False,
        "use_memory": True
    }
    
    # Send request
    response = test_client.post("/api/chat/", json=data)
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "message" in result
    assert result["message"] == "I'm a helpful assistant responding to your query."
    assert "conversation_id" in result
    assert "provider" in result
    assert result["provider"] == "openai"
    assert "memory_sources" in result
    
    # Verify that the LLM service was called
    mock_dependencies["llm_service"].generate_response.assert_called_once()
    
    # Verify that the memory manager was used
    mock_dependencies["memory_manager"].create_unified_context.assert_called_once()


def test_chat_endpoint_no_memory(test_client, mock_dependencies, mock_settings):
    """Test the chat endpoint with memory disabled."""
    # Disable memory
    mock_settings.memory_enabled = False
    
    # Prepare request data
    data = {
        "message": "What is RAG?",
        "conversation_id": None,
        "provider": "anthropic",
        "use_rag": True,
        "use_sql": False,
        "use_mongo": False,
        "use_memory": True  # This should be ignored
    }
    
    # Send request
    response = test_client.post("/api/chat/", json=data)
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "message" in result
    assert result["message"] == "I'm a helpful assistant responding to your query."
    assert "provider" in result
    assert result["provider"] == "anthropic"
    
    # Verify that the LLM service was called
    mock_dependencies["llm_service"].generate_response.assert_called_once()
    
    # Verify that the memory manager was NOT used
    mock_dependencies["memory_manager"].create_unified_context.assert_not_called()


def test_chat_endpoint_invalid_provider(test_client, mock_dependencies):
    """Test the chat endpoint with an invalid provider."""
    # Mock get_llm_service to raise an exception
    mock_dependencies["llm_service"].generate_response.side_effect = Exception("Invalid provider")
    
    # Prepare request data
    data = {
        "message": "What is RAG?",
        "conversation_id": None,
        "provider": "invalid",
        "use_rag": True,
        "use_sql": False,
        "use_mongo": False
    }
    
    # Send request
    response = test_client.post("/api/chat/", json=data)
    
    # Check response (should be an error)
    assert response.status_code == 500
    assert "detail" in response.json()


def test_get_conversations(test_client, mock_dependencies):
    """Test getting conversation history."""
    # Mock the MongoDB aggregation in the chat router
    with patch('app.api.routes.chat.get_memory_manager') as mock_get_memory_manager:
        # Create mock memory manager
        mock_memory_manager = MagicMock()
        mock_memory_manager.memory_systems = {"episodic": MagicMock()}
        
        # Mock MongoDB collection and aggregation
        mock_collection = MagicMock()
        mock_cursor = AsyncMock()
        mock_cursor.to_list = AsyncMock(return_value=[
            {
                "_id": "conv1",
                "latest_message": "What is RAG?",
                "latest_response": "RAG stands for Retrieval-Augmented Generation...",
                "latest_time": "2023-01-01T12:00:00",
                "count": 5
            },
            {
                "_id": "conv2",
                "latest_message": "How does RAG work?",
                "latest_response": "RAG works by retrieving relevant documents...",
                "latest_time": "2023-01-02T14:30:00",
                "count": 3
            }
        ])
        mock_collection.aggregate.return_value = mock_cursor
        
        # Set up the mock db and collection
        mock_memory_manager.memory_systems["episodic"].db = MagicMock()
        mock_memory_manager.memory_systems["episodic"].db["episodic_memory"] = mock_collection
        
        mock_get_memory_manager.return_value = mock_memory_manager
        
        # Send request
        response = test_client.get("/api/chat/conversations")
        
        # Check response
        assert response.status_code == 200
        result = response.json()
        assert "conversations" in result
        assert len(result["conversations"]) == 2
        assert result["conversations"][0]["conversation_id"] == "conv1"
        assert result["conversations"][1]["conversation_id"] == "conv2"


def test_health_endpoint(test_client):
    """Test the health check endpoint."""
    # Mock the check_llm_providers function
    with patch('app.main.check_llm_providers') as mock_check_providers:
        mock_check_providers.return_value = {
            "openai": True,
            "anthropic": True,
            "groq": False
        }
        
        # Send request
        response = test_client.get("/health")
        
        # Check response
        assert response.status_code == 200
        result = response.json()
        assert "status" in result
        assert result["status"] == "healthy"
        assert "llm_providers" in result
        assert result["llm_providers"]["openai"] is True
        assert result["llm_providers"]["anthropic"] is True
        assert result["llm_providers"]["groq"] is False