"""
Test Suite for Conversation API (T1.1.3)

Test-driven development for basic conversation API + context management.
Tests define expected behavior for medical conversation management.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, patch
from datetime import datetime, timedelta
import uuid

from app.main import app
from app.services.medical_chat import ConversationContext


client = TestClient(app)


class TestChatEndpoint:
    """Test basic chat endpoint functionality."""
    
    def test_chat_endpoint_basic_request(self):
        """Test basic chat request with medical message."""
        # Red: This test should fail initially
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            # Mock successful medical response
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Para inyectar Ozempic, consulte con su médico sobre la técnica correcta.",
                "session_id": "test-session-123",
                "context_preserved": True
            })
            
            response = client.post("/api/v1/chat", json={
                "message": "¿Cómo me inyecto Ozempic?",
                "language": "es"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "message" in data
            assert "session_id" in data
            assert "medical_disclaimer" in data
            assert data["language"] == "es"
            assert data["context_preserved"] is True
    
    def test_chat_endpoint_with_session_id(self):
        """Test chat request with existing session ID for context continuity."""
        session_id = "existing-session-456"
        
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Continuando nuestra conversación anterior...",
                "session_id": session_id,
                "context_preserved": True
            })
            
            response = client.post("/api/v1/chat", json={
                "message": "¿Y cuándo debo inyectarme?",
                "language": "es",
                "session_id": session_id
            })
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["context_preserved"] is True
    
    def test_chat_endpoint_validation_empty_message(self):
        """Test validation for empty messages."""
        response = client.post("/api/v1/chat", json={
            "message": "",
            "language": "es"
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_validation_invalid_language(self):
        """Test validation for unsupported language."""
        response = client.post("/api/v1/chat", json={
            "message": "How do I inject Ozempic?",
            "language": "fr"  # Unsupported language
        })
        
        assert response.status_code == 422
    
    def test_chat_endpoint_error_handling(self):
        """Test error handling when medical service fails."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_medical_response = AsyncMock(side_effect=Exception("Service error"))
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "language": "es"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"]


class TestConversationContext:
    """Test conversation context management functionality."""
    
    def test_conversation_context_creation(self):
        """Test creation of conversation context."""
        # Red: This should initially fail until we implement it
        session_id = "test-session-789"
        language = "es"
        
        context = ConversationContext(session_id, language)
        
        assert context.session_id == session_id
        assert context.language == language
        assert context.messages == []
        assert isinstance(context.created_at, datetime)
        assert isinstance(context.last_activity, datetime)
        assert context.patient_id is None
    
    def test_conversation_context_add_message(self):
        """Test adding messages to conversation context."""
        context = ConversationContext("test-session", "es")
        
        # Add user message
        context.add_message("user", "¿Cómo funciona Ozempic?")
        assert len(context.messages) == 1
        assert context.messages[0]["role"] == "user"
        assert context.messages[0]["content"] == "¿Cómo funciona Ozempic?"
        assert "timestamp" in context.messages[0]
        
        # Add assistant response
        context.add_message("assistant", "Ozempic es un medicamento GLP-1...")
        assert len(context.messages) == 2
        assert context.messages[1]["role"] == "assistant"
    
    def test_conversation_context_message_limit(self):
        """Test that context maintains only last 10 messages."""
        context = ConversationContext("test-session", "es")
        
        # Add 15 messages (exceeding limit)
        for i in range(15):
            context.add_message("user", f"Message {i}")
        
        # Should keep only last 10
        assert len(context.messages) == 10
        assert context.messages[0]["content"] == "Message 5"  # First kept message
        assert context.messages[-1]["content"] == "Message 14"  # Last message
    
    def test_conversation_context_expiry(self):
        """Test conversation context expiration."""
        context = ConversationContext("test-session", "es")
        
        # Recent context should not be expired
        assert not context.is_expired(timeout_minutes=30)
        
        # Simulate old context
        old_time = datetime.now() - timedelta(minutes=45)
        context.last_activity = old_time
        
        # Should be expired
        assert context.is_expired(timeout_minutes=30)
    
    def test_conversation_context_llm_format(self):
        """Test getting messages in LLM provider format."""
        context = ConversationContext("test-session", "es")
        context.add_message("user", "Test user message")
        context.add_message("assistant", "Test assistant response")
        
        llm_messages = context.get_llm_messages()
        
        assert len(llm_messages) == 2
        assert llm_messages[0] == {"role": "user", "content": "Test user message"}
        assert llm_messages[1] == {"role": "assistant", "content": "Test assistant response"}
        # Should not include timestamp in LLM format


class TestSessionContextEndpoint:
    """Test session context retrieval endpoint."""
    
    def test_get_session_context_success(self):
        """Test successful retrieval of session context."""
        session_id = "test-session-context"
        
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_session_context = AsyncMock(return_value={
                "session_id": session_id,
                "language": "es", 
                "messages": [{"role": "user", "content": "Test"}],
                "created_at": datetime.now().isoformat(),
                "last_activity": datetime.now().isoformat(),
                "patient_id": "test-patient"
            })
            
            response = client.get(f"/api/v1/chat/sessions/{session_id}/context")
            
            assert response.status_code == 200
            data = response.json()
            assert data["session_id"] == session_id
            assert data["message_count"] == 1
            assert data["language"] == "es"
            assert "created_at" in data
            assert "last_activity" in data
    
    def test_get_session_context_not_found(self):
        """Test session context not found."""
        session_id = "nonexistent-session"
        
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_session_context = AsyncMock(
                side_effect=Exception("Session not found")
            )
            
            response = client.get(f"/api/v1/chat/sessions/{session_id}/context")
            
            assert response.status_code == 404


class TestHealthEndpoint:
    """Test chat service health endpoint."""
    
    def test_chat_health_success(self):
        """Test successful health check."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.health_check = AsyncMock(return_value={
                "service_status": "operational",
                "providers": {"summary": {"status": "healthy"}},
                "knowledge_base_loaded": True,
                "active_sessions": 5
            })
            
            response = client.get("/api/v1/chat/health")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] in ["healthy", "degraded"]
            assert "timestamp" in data
            assert "services" in data
            assert "version" in data
    
    def test_chat_health_failure(self):
        """Test health check failure."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.health_check = AsyncMock(side_effect=Exception("Health check failed"))
            
            response = client.get("/api/v1/chat/health")
            
            assert response.status_code == 503


class TestConversationPersistence:
    """Test conversation context persistence across requests."""
    
    def test_conversation_persistence_across_requests(self):
        """Test that conversation context persists across multiple requests."""
        session_id = str(uuid.uuid4())
        
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            # First request
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Ozempic se inyecta subcutáneamente una vez por semana.",
                "session_id": session_id,
                "context_preserved": True
            })
            
            response1 = client.post("/api/v1/chat", json={
                "message": "¿Cómo se inyecta Ozempic?",
                "language": "es",
                "session_id": session_id
            })
            
            assert response1.status_code == 200
            
            # Second request should have context
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Basándome en nuestra conversación anterior sobre Ozempic...",
                "session_id": session_id, 
                "context_preserved": True
            })
            
            response2 = client.post("/api/v1/chat", json={
                "message": "¿Y cuáles son los efectos secundarios?",
                "language": "es",
                "session_id": session_id
            })
            
            assert response2.status_code == 200
            assert response2.json()["context_preserved"] is True


class TestBilingualSupport:
    """Test bilingual conversation support."""
    
    def test_spanish_conversation(self):
        """Test conversation in Spanish."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Respuesta médica en español sobre Ozempic.",
                "session_id": "spanish-session",
                "context_preserved": True
            })
            
            response = client.post("/api/v1/chat", json={
                "message": "¿Qué es Ozempic?",
                "language": "es"
            })
            
            assert response.status_code == 200
            assert response.json()["language"] == "es"
    
    def test_english_conversation(self):
        """Test conversation in English."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Medical response in English about Ozempic.",
                "session_id": "english-session",
                "context_preserved": True
            })
            
            response = client.post("/api/v1/chat", json={
                "message": "What is Ozempic?",
                "language": "en"
            })
            
            assert response.status_code == 200
            assert response.json()["language"] == "en"


@pytest.mark.medical
class TestMedicalAccuracy:
    """Test medical accuracy and safety features."""
    
    def test_medical_disclaimer_included(self):
        """Test that medical disclaimer is always included."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            mock_service.get_medical_response = AsyncMock(return_value={
                "content": "Respuesta médica sobre GLP-1.",
                "session_id": "disclaimer-test",
                "context_preserved": True
            })
            
            response = client.post("/api/v1/chat", json={
                "message": "¿Es seguro Ozempic?",
                "language": "es"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "medical_disclaimer" in data
            assert len(data["medical_disclaimer"]) > 0
    
    def test_medical_logging_audit_trail(self):
        """Test that medical interactions are logged for audit."""
        with patch('app.api.endpoints.chat.medical_chat_service') as mock_service:
            with patch('app.api.endpoints.chat.log_medical_interaction') as mock_log:
                mock_service.get_medical_response = AsyncMock(return_value={
                    "content": "Medical response",
                    "session_id": "audit-test",
                    "context_preserved": True
                })
                
                client.post("/api/v1/chat", json={
                    "message": "Medical question",
                    "language": "es",
                    "patient_id": "patient-123"
                })
                
                # Should log both request and response
                assert mock_log.call_count >= 2
                
                # Check request logging
                request_call = mock_log.call_args_list[0]
                assert request_call[1]["patient_id"] == "patient-123"
                assert request_call[1]["interaction_type"] == "chat_request"
                
                # Check response logging  
                response_call = mock_log.call_args_list[1]
                assert response_call[1]["interaction_type"] == "chat_response"