"""
Integration Tests for T1.1.3: Basic Conversation API + Context Management

End-to-end integration tests for the conversation system with real components.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app


client = TestClient(app)


@pytest.mark.integration
class TestConversationIntegration:
    """Integration tests for complete conversation workflow."""
    
    def test_complete_conversation_flow(self):
        """Test complete conversation flow from start to context preservation."""
        # Mock the LLM providers to avoid real API calls
        with patch('app.services.medical_chat.MedicalChatService.get_medical_response') as mock_get_medical_response:
            mock_get_medical_response.return_value = {
                'content': 'Respuesta médica sobre Ozempic. Consulte con su médico.',
                'context_preserved': True,
                'session_id': 'mock_session_id'
            }
            
            # First conversation message
            response1 = client.post("/api/v1/chat", json={
                "message": "¿Qué es Ozempic?",
                "language": "es"
            })
            
            assert response1.status_code == 200
            data1 = response1.json()
            session_id = data1["session_id"]
            
            # Second message with context
            response2 = client.post("/api/v1/chat", json={
                "message": "¿Cómo se inyecta?",
                "language": "es",
                "session_id": session_id
            })
            
            assert response2.status_code == 200
            data2 = response2.json()
            assert data2["session_id"] == session_id
            assert data2["context_preserved"] is True
    
    def test_health_endpoints_integration(self):
        """Test that all health endpoints work together."""
        # Test main health endpoint
        health_response = client.get("/health")
        assert health_response.status_code in [200, 503]  # Degraded is OK without real API keys
        
        # Test chat service health
        chat_health_response = client.get("/api/v1/chat/health")
        assert chat_health_response.status_code in [200, 503]  # Degraded is OK
    
    def test_session_context_retrieval_integration(self):
        """Test session context retrieval after conversation."""
        with patch('app.services.medical_chat.MedicalChatService.get_session_context') as mock_context:
            mock_context.return_value = {
                "session_id": "integration-test",
                "language": "es",
                "messages": [{"role": "user", "content": "Test"}],
                "created_at": "2025-01-01T00:00:00",
                "last_activity": "2025-01-01T00:00:00",
                "patient_id": None
            }
            
            response = client.get("/api/v1/chat/sessions/integration-test/context")
            assert response.status_code == 200
            
            data = response.json()
            assert data["session_id"] == "integration-test"
            assert data["message_count"] == 1
            assert data["language"] == "es"


@pytest.mark.integration 
@pytest.mark.medical
class TestMedicalConversationIntegration:
    """Integration tests for medical-specific conversation features."""
    
    def test_medical_disclaimer_always_present(self):
        """Test that medical disclaimer is always included."""
        with patch('app.core.llm_factory.get_provider_manager'):
            response = client.post("/api/v1/chat", json={
                "message": "¿Es seguro Ozempic?",
                "language": "es"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "medical_disclaimer" in data
            assert len(data["medical_disclaimer"]) > 0
    
    def test_bilingual_conversation_switching(self):
        """Test switching languages within same session.""" 
        session_id = "bilingual-test-session"
        
        with patch('app.core.llm_factory.get_provider_manager') as mock_manager:
            mock_provider_manager = mock_manager.return_value
            mock_provider_manager.generate_medical_response.return_value = type('MockResponse', (), {
                'content': 'Medical response',
                'provider': type('MockProvider', (), {'value': 'openai'})(),
                'model': 'gpt-4',
                'medical_validated': True
            })()
            
            # Spanish message
            response1 = client.post("/api/v1/chat", json={
                "message": "¿Qué es Ozempic?",
                "language": "es",
                "session_id": session_id
            })
            assert response1.status_code == 200
            assert response1.json()["language"] == "es"
            
            # English message in same session
            response2 = client.post("/api/v1/chat", json={
                "message": "What are the side effects?", 
                "language": "en",
                "session_id": session_id
            })
            assert response2.status_code == 200
            assert response2.json()["language"] == "en"
            assert response2.json()["session_id"] == session_id


@pytest.mark.integration
class TestErrorHandlingIntegration:
    """Integration tests for error handling scenarios."""
    
    def test_service_unavailable_graceful_degradation(self):
        """Test graceful degradation when services are unavailable."""
        with patch('app.services.medical_chat.MedicalChatService.get_medical_response') as mock_service:
            mock_service.side_effect = Exception("Service temporarily unavailable")
            
            response = client.post("/api/v1/chat", json={
                "message": "Test message",
                "language": "es"
            })
            
            assert response.status_code == 500
            data = response.json()
            assert "error" in data["detail"]
            assert "timestamp" in data["detail"]
    
    def test_invalid_request_validation(self):
        """Test various invalid request scenarios."""
        # Empty message
        response1 = client.post("/api/v1/chat", json={
            "message": "",
            "language": "es"
        })
        assert response1.status_code == 422
        
        # Invalid language
        response2 = client.post("/api/v1/chat", json={
            "message": "Test",
            "language": "invalid"
        })
        assert response2.status_code == 422
        
        # Message too long
        response3 = client.post("/api/v1/chat", json={
            "message": "x" * 1001,  # Exceeds 1000 char limit
            "language": "es"
        })
        assert response3.status_code == 422


@pytest.mark.integration
class TestPerformanceIntegration:
    """Integration tests for performance characteristics."""
    
    def test_response_time_tracking(self):
        """Test that response times are tracked and reasonable."""
        with patch('app.core.llm_factory.get_provider_manager') as mock_manager:
            mock_provider_manager = mock_manager.return_value
            mock_provider_manager.generate_medical_response.return_value = type('MockResponse', (), {
                'content': 'Quick response',
                'provider': type('MockProvider', (), {'value': 'openai'})(),
                'model': 'gpt-4',
                'medical_validated': True
            })()
            
            response = client.post("/api/v1/chat", json={
                "message": "Quick test",
                "language": "es"
            })
            
            assert response.status_code == 200
            data = response.json()
            assert "response_time_ms" in data
            assert isinstance(data["response_time_ms"], int)
            assert data["response_time_ms"] > 0
            # Response should be fast in test environment
            assert data["response_time_ms"] < 5000  # Less than 5 seconds


@pytest.mark.integration
class TestAuditLoggingIntegration:
    """Integration tests for audit logging functionality."""
    
    def test_medical_interaction_logging(self):
        """Test that medical interactions are properly logged."""
        with patch('app.api.endpoints.chat.log_medical_interaction') as mock_log:
            with patch('app.core.llm_factory.get_provider_manager'):
                response = client.post("/api/v1/chat", json={
                    "message": "Medical question",
                    "language": "es",
                    "patient_id": "test-patient-123"
                })
                
                assert response.status_code == 200
                
                # Should log both request and response
                assert mock_log.call_count >= 2
                
                # Verify request log
                request_call = mock_log.call_args_list[0]
                assert request_call[1]["patient_id"] == "test-patient-123"
                assert request_call[1]["interaction_type"] == "chat_request"
                
                # Verify response log
                response_call = mock_log.call_args_list[1]
                assert response_call[1]["interaction_type"] == "chat_response"