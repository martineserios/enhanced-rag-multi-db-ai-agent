# filepath: backend/tests/conftest.py
"""
Test fixtures and configuration.

This module provides pytest fixtures for testing the application.
"""
import os
import asyncio
from typing import Dict, Any, Optional
import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from app.config import Settings
from app.services.memory.base import MemorySystem
from app.services.memory.manager import MemoryManager
from app.services.llm.base import LLMService


@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def test_settings():
    """Create test settings for unit tests."""
    return Settings(
        app_name="Test RAG Chatbot",
        app_version="test",
        debug=True,
        
        # Memory settings
        memory_enabled=True,
        enable_short_term_memory=True,
        enable_semantic_memory=True,
        enable_episodic_memory=True,
        enable_procedural_memory=True,
        
        # Database URIs
        mongo_uri="mongodb://localhost:27017/test_db",
        postgres_uri="postgresql://postgres:postgres@localhost:5432/test_db",
        redis_host="localhost",
        redis_port=6379,
        chroma_host="localhost",
        chroma_port=8000,
        neo4j_uri="neo4j://localhost:7687",
        neo4j_user="neo4j",
        neo4j_password="password",
        
        # LLM settings
        openai_api_key="test_openai_key",
        anthropic_api_key="test_anthropic_key",
        groq_api_key="test_groq_key"
    )


class MockMemorySystem(MemorySystem):
    """Mock memory system for testing."""
    
    def __init__(self, name="mock"):
        super().__init__(name)
        self.store_mock = AsyncMock(return_value="test_key")
        self.retrieve_mock = AsyncMock(return_value={"test": "content"})
        self.search_mock = AsyncMock(return_value=[{"key": "test_key", "content": "test content"}])
        self.delete_mock = AsyncMock(return_value=True)
        self.clear_mock = AsyncMock()
        self.health_check_mock = AsyncMock(return_value=True)
        self.close_mock = AsyncMock()
    
    async def store(self, key, content, metadata=None, **kwargs):
        return await self.store_mock(key, content, metadata, **kwargs)
    
    async def retrieve(self, key, **kwargs):
        return await self.retrieve_mock(key, **kwargs)
    
    async def search(self, query, limit=5, **kwargs):
        return await self.search_mock(query, limit, **kwargs)
    
    async def delete(self, key, **kwargs):
        return await self.delete_mock(key, **kwargs)
    
    async def clear(self, **kwargs):
        return await self.clear_mock(**kwargs)
    
    async def health_check(self):
        return await self.health_check_mock()
    
    async def close(self):
        return await self.close_mock()


@pytest_asyncio.fixture
async def mock_memory_manager(test_settings):
    """Create a memory manager with mock memory systems."""
    manager = MemoryManager(test_settings)
    
    # Replace real memory systems with mocks
    manager.memory_systems = {
        "short_term": MockMemorySystem("short_term"),
        "semantic": MockMemorySystem("semantic"),
        "episodic": MockMemorySystem("episodic"),
        "procedural": MockMemorySystem("procedural")
    }
    
    # Set initialized flag
    manager.initialized = True
    
    yield manager


class MockLLMService(LLMService):
    """Mock LLM service for testing."""
    
    def __init__(self, provider_name="mock", settings=None):
        super().__init__(provider_name, settings or test_settings())
        self.generate_text_mock = AsyncMock(return_value="Generated text")
        self.generate_chat_response_mock = AsyncMock(return_value="Chat response")
        self.count_tokens_mock = AsyncMock(return_value=10)
        self.get_embedding_mock = AsyncMock(return_value=[0.1, 0.2, 0.3])
        self.health_check_mock = AsyncMock(return_value=True)
    
    async def generate_text(self, prompt, **kwargs):
        return await self.generate_text_mock(prompt, **kwargs)
    
    async def generate_chat_response(self, messages, **kwargs):
        return await self.generate_chat_response_mock(messages, **kwargs)
    
    async def count_tokens(self, text):
        return await self.count_tokens_mock(text)
    
    async def get_embedding(self, text):
        return await self.get_embedding_mock(text)
    
    async def health_check(self):
        return await self.health_check_mock()


@pytest_asyncio.fixture
async def mock_llm_service(test_settings):
    """Create a mock LLM service."""
    service = MockLLMService("test_provider", test_settings)
    yield service


@pytest.fixture
def mock_request_metadata():
    """Create mock request metadata."""
    return {
        "request_id": "test-request-id",
        "user_agent": "test-user-agent"
    }


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        {
            "document_id": "doc1",
            "filename": "test1.pdf",
            "content": "This is a test document with important information.",
            "metadata": {
                "author": "Test Author",
                "tags": ["test", "sample"]
            }
        },
        {
            "document_id": "doc2",
            "filename": "test2.txt",
            "content": "Another document with different content for testing.",
            "metadata": {
                "author": "Another Author",
                "tags": ["sample"]
            }
        }
    ]


@pytest.fixture
def sample_conversations():
    """Create sample conversations for testing."""
    return [
        {
            "conversation_id": "conv1",
            "messages": [
                {
                    "user_message": "Hello, how are you?",
                    "assistant_message": "I'm doing well, thanks for asking!",
                    "timestamp": "2023-01-01T12:00:00Z"
                },
                {
                    "user_message": "What is RAG?",
                    "assistant_message": "RAG stands for Retrieval-Augmented Generation...",
                    "timestamp": "2023-01-01T12:01:00Z"
                }
            ]
        },
        {
            "conversation_id": "conv2",
            "messages": [
                {
                    "user_message": "Tell me about memory systems in AI",
                    "assistant_message": "Memory systems in AI include short-term, semantic...",
                    "timestamp": "2023-01-02T15:30:00Z"
                }
            ]
        }
    ]