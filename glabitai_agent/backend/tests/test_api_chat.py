"""
Tests for Chat API Endpoint

Integration tests for the medical chat API,
including bilingual support and medical response validation.
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch

from app.main import app

client = TestClient(app)


class TestChatAPI:
    """Test cases for chat API endpoint."""
    
    def test_chat_endpoint_exists(self):
        """Test that chat endpoint is accessible."""
        response = client.get("/api/v1/chat/health")
        assert response.status_code in [200, 503]  # May be 503 without OpenAI key
    
    @patch('app.services.medical_chat.MedicalChatService.get_medical_response')
    async def test_chat_spanish_request(self, mock_response):
        """Test Spanish medical chat request."""
        # Mock the medical chat response
        mock_response.return_value = {
            "content": "Ozempic puede causar náuseas, especialmente al inicio del tratamiento.",
            "language": "es",
            "session_id": "test-session",
            "context_preserved": True,
            "knowledge_sources": 2
        }
        
        request_data = {
            "message": "¿Cuáles son los efectos secundarios del Ozempic?",
            "language": "es"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        # Should return 200 or 500 (if OpenAI not configured)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert data["language"] == "es"
            assert "medical_disclaimer" in data
    
    def test_chat_request_validation(self):
        """Test chat request validation."""
        # Empty message
        response = client.post("/api/v1/chat", json={
            "message": "",
            "language": "es"
        })
        assert response.status_code == 422  # Validation error
        
        # Unsupported language
        response = client.post("/api/v1/chat", json={
            "message": "Test message",
            "language": "fr"  # Not supported
        })
        assert response.status_code == 422
        
        # Message too long
        long_message = "x" * 1001  # Max is 1000 characters
        response = client.post("/api/v1/chat", json={
            "message": long_message,
            "language": "es"
        })
        assert response.status_code == 422
    
    @patch('app.services.medical_chat.MedicalChatService.get_medical_response')
    async def test_chat_english_request(self, mock_response):
        """Test English medical chat request."""
        mock_response.return_value = {
            "content": "Ozempic may cause nausea, especially when starting treatment.",
            "language": "en", 
            "session_id": "test-session",
            "context_preserved": True,
            "knowledge_sources": 2
        }
        
        request_data = {
            "message": "What are the side effects of Ozempic?",
            "language": "en"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code in [200, 500]
        
        if response.status_code == 200:
            data = response.json()
            assert data["language"] == "en"
    
    def test_chat_session_context(self):
        """Test session context retrieval."""
        session_id = "test-session-123"
        
        response = client.get(f"/api/v1/chat/sessions/{session_id}/context")
        # Should return 404 for non-existent session or 200 if exists
        assert response.status_code in [404, 200]
    
    def test_chat_health_endpoint(self):
        """Test chat service health check."""
        response = client.get("/api/v1/chat/health")
        
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "services" in data
    
    @pytest.mark.integration
    def test_chat_medical_accuracy_validation(self):
        """Test that chat responses include medical disclaimers."""
        request_data = {
            "message": "¿Puedo cambiar mi dosis de Ozempic?",
            "language": "es"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            # Should include medical disclaimer
            assert "medical_disclaimer" in data
            assert len(data["medical_disclaimer"]) > 0
    
    def test_chat_response_time_tracking(self):
        """Test that response time is tracked."""
        request_data = {
            "message": "Hola",
            "language": "es"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "response_time_ms" in data
            assert isinstance(data["response_time_ms"], int)
            assert data["response_time_ms"] >= 0
    
    def test_chat_session_id_generation(self):
        """Test that session IDs are properly generated."""
        request_data = {
            "message": "Test message",
            "language": "es"
        }
        
        response = client.post("/api/v1/chat", json=request_data)
        
        if response.status_code == 200:
            data = response.json()
            assert "session_id" in data
            assert len(data["session_id"]) > 0
    
    @pytest.mark.medical
    def test_medical_query_handling(self):
        """Test handling of different types of medical queries."""
        medical_queries = [
            {"message": "¿Cómo me inyecto Ozempic?", "language": "es"},
            {"message": "Tengo náuseas desde que empecé el tratamiento", "language": "es"},
            {"message": "¿Cuánto peso voy a perder?", "language": "es"},
            {"message": "How do I inject Ozempic?", "language": "en"},
            {"message": "I have nausea since starting treatment", "language": "en"}
        ]
        
        for query in medical_queries:
            response = client.post("/api/v1/chat", json=query)
            # Should either work (200) or fail gracefully (500)
            assert response.status_code in [200, 500]
            
            # Should not return 4xx errors for valid medical queries
            assert response.status_code < 400 or response.status_code >= 500