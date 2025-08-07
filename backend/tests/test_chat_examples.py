

"""
Example integration tests for the Chat API endpoint.

These tests hit the actual API endpoint and require the backend services
(e.g., LLM providers) to be properly configured and accessible.
"""


import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

class TestChatExamples:
    """
    Integration test cases for the /api/v1/chat endpoint with example scenarios.
    """

    @pytest.mark.integration
    def test_spanish_chat_example(self):
        """
        Test a basic chat request in Spanish.
        """
        request_data = {
            "message": "¿Cuáles son los efectos secundarios de la semaglutida?",
            "language": "es"
        }
        response = client.post("/api/v1/chat", json=request_data)

        # Expect 200 OK if LLM service is configured, otherwise 500 if it fails
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert data["language"] == "es"
            assert "session_id" in data
            assert "medical_disclaimer" in data
            assert "response_time_ms" in data
            # Assert that the message is not a generic error message
            assert "service unavailable" not in data["message"].lower()
            assert "unable to process" not in data["message"].lower()
            print(f"\nSpanish Chat Response: {data['message']}")
            print(f"Session ID: {data['session_id']}")
        elif response.status_code == 500:
            data = response.json()
            assert "detail" in data
            assert data["detail"]["error"] == "Medical chat service unavailable"
            assert data["detail"]["message"] == "Unable to process medical query at this time"
            print(f"\nSpanish Chat Error: {data['detail']['message']}")

    @pytest.mark.integration
    def test_english_chat_example(self):
        """
        Test a basic chat request in English.
        """
        request_data = {
            "message": "How does GLP-1 medication work?",
            "language": "en"
        }
        response = client.post("/api/v1/chat", json=request_data)

        # Expect 200 OK if LLM service is configured, otherwise 500 if it fails
        assert response.status_code in [200, 500]

        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert data["language"] == "en"
            assert "session_id" in data
            assert "medical_disclaimer" in data
            assert "response_time_ms" in data
            # Assert that the message is not a generic error message
            assert "service unavailable" not in data["message"].lower()
            assert "unable to process" not in data["message"].lower()
            print(f"\nEnglish Chat Response: {data['message']}")
            print(f"Session ID: {data['session_id']}")
        elif response.status_code == 500:
            data = response.json()
            assert "detail" in data
            assert data["detail"]["error"] == "Medical chat service unavailable"
            assert data["detail"]["message"] == "Unable to process medical query at this time"
            print(f"\nEnglish Chat Error: {data['detail']['message']}")

    def test_chat_invalid_language(self):
        """
        Test chat request with an unsupported language.
        """
        request_data = {
            "message": "Hello",
            "language": "fr"  # Unsupported language
        }
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 422  # Unprocessable Entity (validation error)
        data = response.json()
        assert "detail" in data
        assert "Language must be one of: ['es', 'en']" in str(data["detail"])

    def test_chat_empty_message(self):
        """
        Test chat request with an empty message.
        """
        request_data = {
            "message": "",
            "language": "es"
        }
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 422  # Unprocessable Entity (validation error)
        data = response.json()
        assert "detail" in data
        assert "Message cannot be empty" in str(data["detail"])

    def test_chat_message_too_long(self):
        """
        Test chat request with a message exceeding the maximum length.
        """
        long_message = "x" * 1001  # Max is 1000 characters
        request_data = {
            "message": long_message,
            "language": "en"
        }
        response = client.post("/api/v1/chat", json=request_data)
        assert response.status_code == 422  # Unprocessable Entity (validation error)
        data = response.json()
        assert "detail" in data
        assert "Message too long (max 1000 characters)" in str(data["detail"])


