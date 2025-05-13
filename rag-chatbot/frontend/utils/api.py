# filepath: frontend/utils/api.py
"""
API client for the Streamlit UI.

This module provides a client for interacting with the backend API,
with error handling and caching.
"""
import os
import json
from typing import Dict, List, Any, Optional
import requests
import streamlit as st


class APIError(Exception):
    """Exception raised for API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response: Optional[Any] = None):
        self.message = message
        self.status_code = status_code
        self.response = response
        super().__init__(self.message)


class APIClient:
    """
    Client for interacting with the backend API.
    
    This class:
    1. Handles API requests and responses
    2. Provides error handling
    3. Caches API responses where appropriate
    """
    
    def __init__(self, base_url: str = None):
        """
        Initialize the API client.
        
        Args:
            base_url: Base URL for the API, defaults to BACKEND_URL environment variable
        """
        self.base_url = base_url or os.environ.get("BACKEND_URL", "http://localhost:8000")
        self.session = requests.Session()
        
        # Test the connection
        self._connected = False
        try:
            self.health_check()
            self._connected = True
        except Exception:
            self._connected = False
    
    def is_connected(self) -> bool:
        """Check if the API client is connected to the backend."""
        return self._connected
    
    def health_check(self) -> Dict[str, Any]:
        """
        Check the health of the backend API.
        
        Returns:
            Health status information
            
        Raises:
            APIError: If the health check fails
        """
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            self._connected = False
            raise APIError(f"Health check failed: {str(e)}")
    
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_providers(_self) -> Dict[str, Any]:
        """
        Get available LLM providers.
        
        Returns:
            Dictionary with provider information
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = _self.session.get(f"{_self.base_url}/api/providers", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get providers: {str(e)}")
    
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_memory_types(_self) -> Dict[str, Any]:
        """
        Get available memory types.
        
        Returns:
            Dictionary with memory type information
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = _self.session.get(f"{_self.base_url}/api/memory/types", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get memory types: {str(e)}")
    
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_conversations(_self) -> Dict[str, Any]:
        """
        Get a list of conversations.
        
        Returns:
            Dictionary with conversation information
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = _self.session.get(f"{_self.base_url}/api/chat/conversations", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get conversations: {str(e)}")
    
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_conversation_history(_self, conversation_id: str) -> Dict[str, Any]:
        """
        Get the message history for a conversation.
        
        Args:
            conversation_id: ID of the conversation
            
        Returns:
            Dictionary with conversation history
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = _self.session.get(
                f"{_self.base_url}/api/chat/conversation/{conversation_id}",
                timeout=5
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get conversation history: {str(e)}")
    
    def chat(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send a chat message to the backend.
        
        Args:
            request_data: Chat request data
            
        Returns:
            Chat response
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = self.session.post(
                f"{self.base_url}/api/chat/",
                json=request_data,
                timeout=30  # Longer timeout for chat
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_detail = e.response.json().get("detail", str(e))
                except ValueError:
                    error_detail = str(e)
                raise APIError(f"Chat request failed: {error_detail}", status_code, e.response)
            raise APIError(f"Chat request failed: {str(e)}")
    
    @st.cache_data(ttl=60)  # Cache for 60 seconds
    def get_documents(_self) -> Dict[str, Any]:
        """
        Get a list of documents.
        
        Returns:
            Dictionary with document information
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = _self.session.get(f"{_self.base_url}/api/documents/", timeout=5)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Failed to get documents: {str(e)}")
    
    def upload_document(
        self,
        file,
        description: Optional[str] = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        tags: str = ""
    ) -> Dict[str, Any]:
        """
        Upload a document to the backend.
        
        Args:
            file: The file to upload
            description: Optional description of the document
            chunk_size: Size of text chunks in characters
            chunk_overlap: Overlap between chunks in characters
            tags: Comma-separated list of tags
            
        Returns:
            Upload response
            
        Raises:
            APIError: If the request fails
        """
        try:
            # Prepare form data
            files = {"file": file}
            data = {
                "description": description or "",
                "chunk_size": str(chunk_size),
                "chunk_overlap": str(chunk_overlap),
                "tags": tags
            }
            
            # Send request
            response = self.session.post(
                f"{self.base_url}/api/documents/upload",
                files=files,
                data=data,
                timeout=60  # Longer timeout for uploads
            )
            response.raise_for_status()
            
            # Clear the documents cache
            self.get_documents.clear()
            
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None:
                status_code = e.response.status_code
                try:
                    error_detail = e.response.json().get("detail", str(e))
                except ValueError:
                    error_detail = str(e)
                raise APIError(f"Document upload failed: {error_detail}", status_code, e.response)
            raise APIError(f"Document upload failed: {str(e)}")
    
    def search_documents(self, query: str) -> Dict[str, Any]:
        """
        Search for documents.
        
        Args:
            query: Search query
            
        Returns:
            Search results
            
        Raises:
            APIError: If the request fails
        """
        try:
            response = self.session.get(
                f"{self.base_url}/api/documents/search",
                params={"query": query},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            raise APIError(f"Document search failed: {str(e)}")


# Singleton API client
_api_client = None

@st.cache_resource
def get_api_client() -> APIClient:
    """
    Get or create the API client singleton.
    
    Returns:
        The API client instance
    """
    global _api_client
    if _api_client is None:
        _api_client = APIClient()
    return _api_client