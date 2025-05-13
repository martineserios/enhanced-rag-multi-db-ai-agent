# filepath: backend/tests/integration/test_memory_integration.py
"""
Integration tests for the memory system API endpoints.

This module tests the memory-related API endpoints, ensuring that
the memory systems and API routes work together correctly.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient

from app.main import app
from app.config import Settings, get_settings
from app.services.memory.manager import MemoryManager


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
    settings.get_enabled_memory_types.return_value = [
        "short_term", "semantic", "episodic", "procedural"
    ]
    settings.memory_weights = {
        "short_term": 1.0,
        "semantic": 1.0,
        "episodic": 0.5,
        "procedural": 0.8
    }
    
    return settings


@pytest.fixture
def mock_memory_dependencies(mock_settings):
    """Mock memory-related dependencies for integration tests."""
    # Override get_settings
    app.dependency_overrides[get_settings] = lambda: mock_settings
    
    # Mock memory manager
    with patch('app.api.dependencies.get_memory_manager') as mock_get_memory_manager, \
         patch('app.api.dependencies.verify_memory_enabled') as mock_verify_memory:
        
        # Create mock memory manager
        mock_memory_manager = MagicMock()
        mock_memory_manager.memory_systems = {
            "short_term": MagicMock(),
            "semantic": MagicMock(),
            "episodic": MagicMock(),
            "procedural": MagicMock()
        }
        
        # Configure health check
        mock_memory_manager.memory_systems["short_term"].health_check = AsyncMock(return_value=True)
        mock_memory_manager.memory_systems["semantic"].health_check = AsyncMock(return_value=True)
        mock_memory_manager.memory_systems["episodic"].health_check = AsyncMock(return_value=True)
        mock_memory_manager.memory_systems["procedural"].health_check = AsyncMock(return_value=False)
        
        # Configure multi-context query
        mock_memory_manager.multi_context_query = AsyncMock(return_value={
            "short_term": [
                {"key": "st1", "content": "Short-term content 1", "timestamp": "2023-01-01T12:00:00Z"},
                {"key": "st2", "content": "Short-term content 2", "timestamp": "2023-01-01T12:05:00Z"}
            ],
            "semantic": [
                {"key": "sem1", "content": "Semantic content 1"},
                {"key": "sem2", "content": "Semantic content 2"}
            ],
            "episodic": [
                {"key": "ep1", "content": "Episodic content 1", "timestamp": "2023-01-01T10:00:00Z"},
                {"key": "ep2", "content": "Episodic content 2", "timestamp": "2023-01-01T11:00:00Z"}
            ],
            "procedural": [
                {"key": "proc1", "description": "Step 1", "order": 0},
                {"key": "proc2", "description": "Step 2", "order": 1}
            ]
        })
        
        # Configure create_unified_context
        mock_memory_manager.create_unified_context = AsyncMock(
            return_value="## Recent Conversation Context\nUser: What is RAG?\nAssistant: RAG stands for...\n\n## Relevant Document Information\nDocument 1: RAG is a technique...\n\n## Similar Past Conversations\nUser: How does retrieval work?\nAssistant: Retrieval works by..."
        )
        
        # Configure search_memory for short-term
        mock_memory_manager.search_memory.side_effect = lambda memory_type, **kwargs: {
            "short_term": AsyncMock(return_value=[
                {"key": "st1", "user_message": "Hello", "assistant_message": "Hi there!", "timestamp": "2023-01-01T12:00:00Z"},
                {"key": "st2", "user_message": "What is RAG?", "assistant_message": "RAG stands for...", "timestamp": "2023-01-01T12:05:00Z"}
            ]),
            "episodic": AsyncMock(return_value=[
                {"key": "ep1", "user_message": "Tell me about memory", "assistant_message": "Memory systems in AI...", "timestamp": "2023-01-01T10:00:00Z"},
                {"key": "ep2", "user_message": "How does retrieval work?", "assistant_message": "Retrieval works by...", "timestamp": "2023-01-01T11:00:00Z"}
            ]),
            "procedural": AsyncMock(return_value=[
                {"name": "document_upload", "steps": [
                    {"description": "Step 1", "order": 0},
                    {"description": "Step 2", "order": 1}
                ]}
            ])
        }[memory_type]
        
        # Configure retrieve_memory for procedural
        mock_memory_manager.retrieve_memory = AsyncMock(return_value={
            "name": "document_upload",
            "steps": [
                {"description": "Select a file", "action": "select_file", "order": 0},
                {"description": "Upload the file", "action": "upload", "order": 1},
                {"description": "Process the file", "action": "process", "order": 2}
            ]
        })
        
        # Configure store_memory for procedural
        mock_memory_manager.store_memory = AsyncMock(return_value="procedure1")
        
        # Set up the mock manager
        mock_get_memory_manager.return_value = mock_memory_manager
        mock_verify_memory.return_value = True
        
        yield mock_memory_manager
    
    # Clean up
    app.dependency_overrides = {}


def test_memory_health_check(test_client, mock_memory_dependencies):
    """Test the memory health check endpoint."""
    # Send request
    response = test_client.get("/api/memory/health")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert "short_term" in result["status"]
    assert result["status"]["short_term"] is True
    assert "semantic" in result["status"]
    assert result["status"]["semantic"] is True
    assert "episodic" in result["status"]
    assert result["status"]["episodic"] is True
    assert "procedural" in result["status"]
    assert result["status"]["procedural"] is False
    
    # Verify that health_check was called for each memory system
    for memory_system in mock_memory_dependencies.memory_systems.values():
        memory_system.health_check.assert_called_once()


def test_query_all_memory(test_client, mock_memory_dependencies):
    """Test querying all memory types."""
    # Send request
    response = test_client.get("/api/memory?query=test%20query&conversation_id=conv1&limit=5")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "query" in result
    assert result["query"] == "test query"
    assert "conversation_id" in result
    assert result["conversation_id"] == "conv1"
    assert "results" in result
    
    # Check that each memory type has results
    assert "short_term" in result["results"]
    assert len(result["results"]["short_term"]) == 2
    assert "semantic" in result["results"]
    assert len(result["results"]["semantic"]) == 2
    assert "episodic" in result["results"]
    assert len(result["results"]["episodic"]) == 2
    assert "procedural" in result["results"]
    assert len(result["results"]["procedural"]) == 2
    
    # Verify that multi_context_query was called with the right parameters
    mock_memory_dependencies.multi_context_query.assert_called_once_with(
        query="test query",
        conversation_id="conv1",
        limit_per_type=5
    )


def test_create_unified_context(test_client, mock_memory_dependencies):
    """Test creating a unified context."""
    # Send request
    response = test_client.get("/api/memory/context?query=test%20query&conversation_id=conv1")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "query" in result
    assert result["query"] == "test query"
    assert "conversation_id" in result
    assert result["conversation_id"] == "conv1"
    assert "context" in result
    assert "Recent Conversation Context" in result["context"]
    assert "Relevant Document Information" in result["context"]
    assert "Similar Past Conversations" in result["context"]
    
    # Verify that create_unified_context was called with the right parameters
    mock_memory_dependencies.create_unified_context.assert_called_once_with(
        query="test query",
        conversation_id="conv1"
    )


def test_get_memory_types(test_client, mock_settings):
    """Test getting memory type information."""
    # Send request
    response = test_client.get("/api/memory/types")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "enabled" in result
    assert result["enabled"] is True
    assert "types" in result
    
    # Check that each memory type is included
    assert "short_term" in result["types"]
    assert result["types"]["short_term"]["enabled"] is True
    assert "semantic" in result["types"]
    assert result["types"]["semantic"]["enabled"] is True
    assert "episodic" in result["types"]
    assert result["types"]["episodic"]["enabled"] is True
    assert "procedural" in result["types"]
    assert result["types"]["procedural"]["enabled"] is True
    
    # Check weights
    assert "weights" in result
    assert result["weights"]["short_term"] == 1.0
    assert result["weights"]["semantic"] == 1.0
    assert result["weights"]["episodic"] == 0.5
    assert result["weights"]["procedural"] == 0.8


def test_get_short_term_memory(test_client, mock_memory_dependencies):
    """Test getting short-term memory for a conversation."""
    # Send request
    response = test_client.get("/api/memory/short-term/conv1?limit=10")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "conversation_id" in result
    assert result["conversation_id"] == "conv1"
    assert "memory_type" in result
    assert result["memory_type"] == "short_term"
    assert "items" in result
    assert len(result["items"]) == 2
    
    # Verify that search_memory was called with the right parameters
    mock_memory_dependencies.search_memory.assert_called_with(
        memory_type="short_term",
        query="",
        conversation_id="conv1",
        limit=10
    )


def test_get_episodic_memory(test_client, mock_memory_dependencies):
    """Test searching episodic memory."""
    # Send request with conversation_id
    response = test_client.get("/api/memory/episodic?conversation_id=conv1&limit=10")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "conversation_id" in result
    assert result["conversation_id"] == "conv1"
    assert "memory_type" in result
    assert result["memory_type"] == "episodic"
    assert "items" in result
    assert len(result["items"]) == 2
    
    # Send request with keyword
    response = test_client.get("/api/memory/episodic?keyword=retrieval&limit=10")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "keyword" in result
    assert result["keyword"] == "retrieval"
    assert "memory_type" in result
    assert result["memory_type"] == "episodic"


def test_get_procedural_memory(test_client, mock_memory_dependencies):
    """Test getting a procedure from procedural memory."""
    # Send request
    response = test_client.get("/api/memory/procedural/document_upload")
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "name" in result
    assert result["name"] == "document_upload"
    assert "memory_type" in result
    assert result["memory_type"] == "procedural"
    assert "procedure" in result
    assert "steps" in result["procedure"]
    assert len(result["procedure"]["steps"]) == 3
    
    # Verify that retrieve_memory was called with the right parameters
    mock_memory_dependencies.retrieve_memory.assert_called_once_with(
        memory_type="procedural",
        key="document_upload"
    )


def test_create_procedural_memory(test_client, mock_memory_dependencies):
    """Test creating a new procedure in procedural memory."""
    # Prepare request data
    data = {
        "name": "new_procedure",
        "steps": [
            {"description": "Step 1", "action": "action1", "order": 0},
            {"description": "Step 2", "action": "action2", "order": 1},
            {"description": "Step 3", "action": "action3", "order": 2}
        ],
        "metadata": {
            "author": "Test User",
            "category": "Test"
        }
    }
    
    # Send request
    response = test_client.post("/api/memory/procedural", json=data)
    
    # Check response
    assert response.status_code == 200
    result = response.json()
    assert "status" in result
    assert result["status"] == "success"
    assert "procedure_id" in result
    assert "step_count" in result
    assert result["step_count"] == 3
    
    # Verify that store_memory was called with the right parameters
    mock_memory_dependencies.store_memory.assert_called_once_with(
        memory_type="procedural",
        key="new_procedure",
        content={"steps": data["steps"]},
        metadata=data["metadata"]
    )


def test_memory_disabled(test_client, mock_settings, mock_memory_dependencies):
    """Test memory endpoints when memory is disabled."""
    # Disable memory
    mock_settings.memory_enabled = False
    
    # Override verify_memory_enabled to raise an exception
    from app.api.dependencies import verify_memory_enabled
    with patch('app.api.dependencies.verify_memory_enabled') as mock_verify:
        from fastapi import HTTPException
        mock_verify.side_effect = HTTPException(status_code=400, detail="Memory system is disabled")
        
        # Try to access a memory endpoint
        response = test_client.get("/api/memory/health")
        
        # Check that the response is an error
        assert response.status_code == 400
        assert "detail" in response.json()
        assert response.json()["detail"] == "Memory system is disabled"