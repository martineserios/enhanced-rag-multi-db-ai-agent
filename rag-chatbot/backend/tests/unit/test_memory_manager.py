# filepath: backend/tests/unit/test_memory_manager.py
"""
Unit tests for the Memory Manager.

This module tests the MemoryManager class and related functionality.
"""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from app.services.memory.manager import MemoryManager, init_memory_manager, get_memory_manager
from app.services.memory.base import MemorySystem
from app.core.exceptions import MemoryError, MemoryInitializationError


@pytest.mark.asyncio
async def test_memory_manager_initialization(test_settings):
    """Test memory manager initialization with various combinations of memory systems."""
    # Test with all memory systems enabled
    with patch('app.services.memory.manager.ShortTermMemory') as mock_short_term, \
         patch('app.services.memory.manager.SemanticMemory') as mock_semantic, \
         patch('app.services.memory.manager.EpisodicMemory') as mock_episodic, \
         patch('app.services.memory.manager.ProceduralMemory') as mock_procedural:
        
        # Configure mocks
        mock_instances = []
        for mock_class in [mock_short_term, mock_semantic, mock_episodic, mock_procedural]:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value=True)
            mock_class.return_value = mock_instance
            mock_instances.append(mock_instance)
        
        # Initialize the manager
        manager = MemoryManager(test_settings)
        await manager.initialize()
        
        # Verify all memory systems were initialized
        assert len(manager.memory_systems) == 4
        assert "short_term" in manager.memory_systems
        assert "semantic" in manager.memory_systems
        assert "episodic" in manager.memory_systems
        assert "procedural" in manager.memory_systems
        assert manager.initialized is True
        
        # Verify health checks were called
        for mock_instance in mock_instances:
            mock_instance.health_check.assert_called_once()
    
    # Test with some memory systems disabled
    test_settings.enable_procedural_memory = False
    test_settings.enable_episodic_memory = False
    
    with patch('app.services.memory.manager.ShortTermMemory') as mock_short_term, \
         patch('app.services.memory.manager.SemanticMemory') as mock_semantic:
        
        # Configure mocks
        for mock_class in [mock_short_term, mock_semantic]:
            mock_instance = MagicMock()
            mock_instance.health_check = AsyncMock(return_value=True)
            mock_class.return_value = mock_instance
        
        # Initialize the manager
        manager = MemoryManager(test_settings)
        await manager.initialize()
        
        # Verify only enabled memory systems were initialized
        assert len(manager.memory_systems) == 2
        assert "short_term" in manager.memory_systems
        assert "semantic" in manager.memory_systems
        assert "episodic" not in manager.memory_systems
        assert "procedural" not in manager.memory_systems
        assert manager.initialized is True
    
    # Test with all memory systems disabled
    test_settings.enable_short_term_memory = False
    test_settings.enable_semantic_memory = False
    
    manager = MemoryManager(test_settings)
    await manager.initialize()
    
    # Verify no memory systems were initialized
    assert len(manager.memory_systems) == 0
    assert manager.initialized is True


@pytest.mark.asyncio
async def test_memory_manager_initialization_failure(test_settings):
    """Test memory manager initialization with failing memory systems."""
    with patch('app.services.memory.manager.ShortTermMemory') as mock_short_term:
        # Make the initialization fail
        mock_short_term.side_effect = Exception("Test exception")
        
        # Initialize the manager
        with pytest.raises(MemoryInitializationError):
            manager = MemoryManager(test_settings)
            await manager.initialize()


@pytest.mark.asyncio
async def test_store_memory(mock_memory_manager):
    """Test storing content in a memory system."""
    # Test storing with all parameters
    key = await mock_memory_manager.store_memory(
        memory_type="short_term",
        content={"user_message": "Hello", "assistant_message": "Hi there!"},
        key="test_key",
        metadata={"test": "metadata"}
    )
    
    # Verify the store method was called with correct parameters
    mock_memory_manager.memory_systems["short_term"].store_mock.assert_called_once()
    assert mock_memory_manager.memory_systems["short_term"].store_mock.call_args[0][0] == "test_key"
    assert mock_memory_manager.memory_systems["short_term"].store_mock.call_args[0][1] == {
        "user_message": "Hello", "assistant_message": "Hi there!"
    }
    assert mock_memory_manager.memory_systems["short_term"].store_mock.call_args[0][2]["test"] == "metadata"
    assert key == "test_key"
    
    # Test storing without key (should generate one)
    mock_memory_manager.memory_systems["short_term"].store_mock.reset_mock()
    key = await mock_memory_manager.store_memory(
        memory_type="short_term",
        content={"user_message": "Hello", "assistant_message": "Hi there!"}
    )
    
    # Verify key was generated and store was called
    mock_memory_manager.memory_systems["short_term"].store_mock.assert_called_once()
    assert key == "test_key"  # mock returns "test_key"
    
    # Test storing to unavailable memory system
    with pytest.raises(MemoryError):
        await mock_memory_manager.store_memory(
            memory_type="nonexistent",
            content={"user_message": "Hello", "assistant_message": "Hi there!"}
        )


@pytest.mark.asyncio
async def test_retrieve_memory(mock_memory_manager):
    """Test retrieving content from a memory system."""
    # Test successful retrieval
    content = await mock_memory_manager.retrieve_memory(
        memory_type="short_term",
        key="test_key"
    )
    
    # Verify retrieve was called with correct parameters
    mock_memory_manager.memory_systems["short_term"].retrieve_mock.assert_called_once_with("test_key")
    assert content == {"test": "content"}
    
    # Test retrieval from unavailable memory system
    with pytest.raises(MemoryError):
        await mock_memory_manager.retrieve_memory(
            memory_type="nonexistent",
            key="test_key"
        )
    
    # Test retrieval when memory system raises an exception
    mock_memory_manager.memory_systems["short_term"].retrieve_mock.side_effect = Exception("Test exception")
    with pytest.raises(MemoryError):
        await mock_memory_manager.retrieve_memory(
            memory_type="short_term",
            key="test_key"
        )


@pytest.mark.asyncio
async def test_search_memory(mock_memory_manager):
    """Test searching for content in a memory system."""
    # Test successful search
    results = await mock_memory_manager.search_memory(
        memory_type="semantic",
        query="test query",
        limit=10
    )
    
    # Verify search was called with correct parameters
    mock_memory_manager.memory_systems["semantic"].search_mock.assert_called_once_with("test query", 10)
    assert results == [{"key": "test_key", "content": "test content"}]
    
    # Test search with additional parameters
    mock_memory_manager.memory_systems["semantic"].search_mock.reset_mock()
    await mock_memory_manager.search_memory(
        memory_type="semantic",
        query="test query",
        limit=10,
        extra_param="test"
    )
    
    # Verify extra parameters were passed
    assert mock_memory_manager.memory_systems["semantic"].search_mock.call_args[1]["extra_param"] == "test"
    
    # Test search from unavailable memory system
    with pytest.raises(MemoryError):
        await mock_memory_manager.search_memory(
            memory_type="nonexistent",
            query="test query"
        )


@pytest.mark.asyncio
async def test_multi_context_query(mock_memory_manager):
    """Test querying multiple memory systems."""
    # Configure mock returns for different memory systems
    mock_memory_manager.memory_systems["short_term"].search_mock.return_value = [
        {"key": "st1", "content": "short term content 1"},
        {"key": "st2", "content": "short term content 2"}
    ]
    
    mock_memory_manager.memory_systems["semantic"].search_mock.return_value = [
        {"key": "sem1", "content": "semantic content 1"},
        {"key": "sem2", "content": "semantic content 2"}
    ]
    
    mock_memory_manager.memory_systems["episodic"].search_mock.return_value = [
        {"key": "ep1", "content": "episodic content 1"},
        {"key": "ep2", "content": "episodic content 2"}
    ]
    
    mock_memory_manager.memory_systems["procedural"].search_mock.return_value = [
        {"key": "proc1", "content": "procedural content 1"},
        {"key": "proc2", "content": "procedural content 2"}
    ]
    
    # Test querying all memory systems
    results = await mock_memory_manager.multi_context_query(
        query="test query",
        conversation_id="test_conversation"
    )
    
    # Verify results from all memory systems were returned
    assert set(results.keys()) == {"short_term", "semantic", "episodic", "procedural"}
    assert len(results["short_term"]) == 2
    assert len(results["semantic"]) == 2
    assert len(results["episodic"]) == 2
    assert len(results["procedural"]) == 2
    
    # Test querying specific memory systems
    results = await mock_memory_manager.multi_context_query(
        query="test query",
        conversation_id="test_conversation",
        memory_types=["short_term", "semantic"]
    )
    
    # Verify only requested memory systems were returned
    assert set(results.keys()) == {"short_term", "semantic"}
    assert len(results["short_term"]) == 2
    assert len(results["semantic"]) == 2
    assert "episodic" not in results
    assert "procedural" not in results
    
    # Test querying with one memory system failing
    mock_memory_manager.memory_systems["episodic"].search_mock.side_effect = Exception("Test exception")
    
    results = await mock_memory_manager.multi_context_query(
        query="test query",
        conversation_id="test_conversation"
    )
    
    # Verify other memory systems still returned results
    assert set(results.keys()) == {"short_term", "semantic", "episodic", "procedural"}
    assert len(results["episodic"]) == 0  # Empty due to exception


@pytest.mark.asyncio
async def test_create_unified_context(mock_memory_manager):
    """Test creating a unified context string from multiple memory sources."""
    # Configure multi_context_query mock
    mock_memory_manager.multi_context_query = AsyncMock(return_value={
        "short_term": [
            {"user_message": "What is RAG?", "assistant_message": "RAG stands for Retrieval-Augmented Generation..."},
            {"user_message": "How does it work?", "assistant_message": "It combines retrieval of documents with generation..."}
        ],
        "semantic": [
            {"content": "RAG is a technique that enhances LLMs by retrieving relevant information."},
            {"content": "The key components of RAG are the retriever and the generator."}
        ],
        "episodic": [
            {"user_message": "Tell me about vector databases", "assistant_message": "Vector databases store embeddings..."},
            {"user_message": "What's the difference between Redis and Chroma?", "assistant_message": "Redis is an in-memory data store..."}
        ],
        "procedural": [
            {"description": "Upload a document to the system", "order": 0},
            {"description": "Process the document into chunks", "order": 1},
            {"description": "Create embeddings for each chunk", "order": 2}
        ]
    })
    
    # Test creating unified context
    context = await mock_memory_manager.create_unified_context(
        query="How does RAG work?",
        conversation_id="test_conversation"
    )
    
    # Verify context contains information from all memory systems
    assert "Recent Conversation Context" in context
    assert "What is RAG?" in context
    assert "Relevant Document Information" in context
    assert "RAG is a technique" in context
    assert "Similar Past Conversations" in context
    assert "Tell me about vector databases" in context
    assert "Relevant Procedure" in context
    assert "Upload a document" in context
    
    # Test with empty results
    mock_memory_manager.multi_context_query = AsyncMock(return_value={})
    
    context = await mock_memory_manager.create_unified_context(
        query="How does RAG work?",
        conversation_id="test_conversation"
    )
    
    # Verify empty context
    assert context == ""


@pytest.mark.asyncio
async def test_close(mock_memory_manager):
    """Test closing all memory system connections."""
    # Test successful closing
    await mock_memory_manager.close()
    
    # Verify close was called on all memory systems
    for memory_system in mock_memory_manager.memory_systems.values():
        memory_system.close_mock.assert_called_once()
    
    # Test with one memory system failing to close
    for memory_system in mock_memory_manager.memory_systems.values():
        memory_system.close_mock.reset_mock()
    
    mock_memory_manager.memory_systems["short_term"].close_mock.side_effect = Exception("Test exception")
    
    # Should not raise exception even if one system fails
    await mock_memory_manager.close()
    
    # Verify close was called on all memory systems
    for memory_system in mock_memory_manager.memory_systems.values():
        memory_system.close_mock.assert_called_once()


@pytest.mark.asyncio
async def test_singleton_functions():
    """Test singleton functions for memory manager."""
    # Mock the MemoryManager class
    with patch('app.services.memory.manager.MemoryManager') as MockMemoryManagerClass, \
         patch('app.services.memory.manager._memory_manager', None):
        
        instance = MagicMock()
        instance.initialize = AsyncMock()
        MockMemoryManagerClass.return_value = instance
        
        # Test init_memory_manager
        settings = MagicMock()
        result = await init_memory_manager(settings)
        
        # Verify MemoryManager was created with settings
        MockMemoryManagerClass.assert_called_once_with(settings)
        instance.initialize.assert_called_once()
        assert result is instance
        
        # Test get_memory_manager when initialized
        with patch('app.services.memory.manager._memory_manager', instance):
            result = get_memory_manager()
            assert result is instance
        
        # Test get_memory_manager when not initialized
        with patch('app.services.memory.manager._memory_manager', None):
            with pytest.raises(MemoryError):
                get_memory_manager()