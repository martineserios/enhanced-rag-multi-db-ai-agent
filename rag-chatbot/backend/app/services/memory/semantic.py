# filepath: backend/app/services/memory/semantic.py
"""
Semantic memory implementation using ChromaDB vector database.

This module implements semantic memory for storing and retrieving document
knowledge using vector embeddings and similarity search.
"""
import json
import uuid
import asyncio
from typing import Dict, List, Any, Optional, Union
from datetime import datetime
import logging
import httpx

import chromadb
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from langchain_huggingface import HuggingFaceEmbeddings
from langchain.schema import Document

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import (
    MemoryError, MemoryStorageError, MemoryRetrievalError, 
    DatabaseConnectionError
)
from app.config import Settings
from app.services.memory.base import MemorySystem, MemoryItem


logger = get_logger(__name__)

class SemanticMemory(MemorySystem[str]):
    """
    Semantic memory implementation using ChromaDB.
    
    This class:
    1. Stores document content as vector embeddings
    2. Retrieves information based on semantic similarity
    3. Supports document-based knowledge retrieval for RAG
    
    It uses ChromaDB as a vector database for efficient similarity search.
    """
    
    def __init__(self, settings: Settings, collection_name: str = "semantic_memory"):
        """
        Initialize semantic memory with ChromaDB connection.
        
        Args:
            settings: Application configuration settings
            collection_name: Name of the ChromaDB collection to use
            
        Raises:
            DatabaseConnectionError: If ChromaDB connection fails
        """
        super().__init__("semantic")
        self.settings = settings
        self.collection_name = collection_name
        self.embedding_model_name = settings.embedding_model
        self.chroma_host = settings.chroma_host
        self.chroma_port = settings.chroma_port
        
        # Initialize embedding function
        try:
            # Initialize direct ChromaDB client instead of using LangChain's wrapper
            self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
                model_name=self.embedding_model_name
            )
            
            # Create direct ChromaDB client
            self.chroma_client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port
            )
            
            # Get or create collection
            self.collection = self.chroma_client.get_or_create_collection(
                name=collection_name,
                embedding_function=self.embedding_function
            )
            
            # Also create HuggingFace embeddings for LangChain compatibility
            self.embeddings = HuggingFaceEmbeddings(model_name=self.embedding_model_name)
            
            self.logger.info(
                f"Initialized semantic memory with ChromaDB at {self.chroma_host}:{self.chroma_port}"
            )
            
        except Exception as e:
            self.logger.exception("Failed to initialize ChromaDB connection")
            raise DatabaseConnectionError(f"ChromaDB connection failed: {str(e)}")
    
    @log_execution_time(logger)
    async def store(
        self, 
        key: str, 
        content: str, 
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Store content in semantic memory.
        
        Args:
            key: Unique identifier for the content
            content: Text content to store
            metadata: Additional metadata to store with the content
            **kwargs: Additional parameters
            
        Returns:
            The key used to store the content
            
        Raises:
            MemoryStorageError: If storing fails
        """
        try:
            # Ensure metadata is a dictionary
            if metadata is None:
                metadata = {}
                
            # Add key to metadata to make it easily searchable
            metadata["key"] = key
            metadata["timestamp"] = datetime.utcnow().isoformat()
            
            # Use a thread to run the blocking operation
            loop = asyncio.get_event_loop()
            
            # Generate embeddings and add to collection
            await loop.run_in_executor(
                None,
                lambda: self.collection.add(
                    ids=[key],
                    documents=[content],
                    metadatas=[metadata]
                )
            )
            
            self.logger.debug(
                f"Stored content in semantic memory: {key}",
                extra={"content_length": len(content), "metadata": metadata}
            )
            
            return key
            
        except Exception as e:
            self.logger.exception(f"Failed to store content in semantic memory: {key}")
            raise MemoryStorageError(f"Failed to store in semantic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def retrieve(self, key: str, **kwargs) -> Optional[str]:
        """
        Retrieve content from semantic memory by key.
        
        Args:
            key: The key of the content to retrieve
            **kwargs: Additional parameters
            
        Returns:
            The content, or None if not found
            
        Raises:
            MemoryRetrievalError: If retrieval fails
        """
        try:
            # Use a thread to run the blocking operation
            loop = asyncio.get_event_loop()
            
            # Try to get item by ID first
            try:
                results = await loop.run_in_executor(
                    None,
                    lambda: self.collection.get(
                        ids=[key],
                        include=["documents", "metadatas"]
                    )
                )
                
                if results and results["ids"] and len(results["ids"]) > 0:
                    return results["documents"][0]
                
            except Exception:
                # If getting by ID fails, try querying by metadata key
                try:
                    results = await loop.run_in_executor(
                        None,
                        lambda: self.collection.query(
                            query_texts=[""],  # Empty query text
                            where={"key": key},
                            n_results=1,
                            include=["documents", "metadatas"]
                        )
                    )
                    
                    if results and results["documents"] and len(results["documents"][0]) > 0:
                        return results["documents"][0][0]
                
                except Exception:
                    # Both methods failed
                    pass
            
            return None
            
        except Exception as e:
            self.logger.exception(f"Failed to retrieve content from semantic memory: {key}")
            raise MemoryRetrievalError(f"Failed to retrieve from semantic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def search(
        self, 
        query: str, 
        limit: int = 5, 
        **kwargs
    ) -> List[Dict[str, Any]]:
        """
        Search for similar content in semantic memory.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            **kwargs: Additional parameters
            
        Returns:
            List of matching content items with metadata
            
        Raises:
            MemoryRetrievalError: If search fails
        """
        try:
            # Use a thread to run the blocking operation
            loop = asyncio.get_event_loop()
            
            # Process additional filter if it's a specific query pattern
            where_filter = {}
            if query.startswith("metadata."):
                # Handle special queries like "metadata.document_id:123"
                parts = query.split(":", 1)
                if len(parts) == 2:
                    field_path = parts[0].split(".", 1)[1]  # Remove "metadata." prefix
                    value = parts[1].strip()
                    if value == "*":
                        # Wildcard query - just check if field exists
                        query = ""  # Empty query for filtering
                    else:
                        # Exact value match
                        where_filter[field_path] = value
                        query = ""  # Empty query for filtering
            
            # Add any additional filters from kwargs
            if "where" in kwargs:
                where_filter.update(kwargs["where"])
                
            # Search for similar documents
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[query] if query else [""],
                    n_results=limit,
                    where=where_filter if where_filter else None,
                    include=["documents", "metadatas", "distances"]
                )
            )
            
            # Format results
            formatted_results = []
            
            if results and results["documents"] and len(results["documents"][0]) > 0:
                for i in range(len(results["documents"][0])):
                    # Extract data
                    document = results["documents"][0][i]
                    metadata = results["metadatas"][0][i] if results["metadatas"] else {}
                    distance = results["distances"][0][i] if "distances" in results else 0.0
                    
                    # Convert distance to score (1.0 is exact match, 0.0 is completely different)
                    similarity_score = 1.0 - min(distance, 1.0)
                    
                    # Create result item
                    result = {
                        "key": metadata.get("key", str(uuid.uuid4())),
                        "content": document,
                        "relevance_score": float(similarity_score),
                        "metadata": metadata
                    }
                    
                    formatted_results.append(result)
            
            self.logger.debug(
                f"Semantic search results for query: {query[:50]}...",
                extra={"query": query, "result_count": len(formatted_results)}
            )
            
            return formatted_results
            
        except Exception as e:
            self.logger.exception(f"Failed to search semantic memory: {query[:50]}...")
            raise MemoryRetrievalError(f"Failed to search semantic memory: {str(e)}")
    
    @log_execution_time(logger)
    async def delete(self, key: str, **kwargs) -> bool:
        """
        Delete content from semantic memory.
        
        Args:
            key: The key of the content to delete
            **kwargs: Additional parameters
            
        Returns:
            True if content was deleted, False otherwise
            
        Raises:
            MemoryError: If deletion fails
        """
        try:
            loop = asyncio.get_event_loop()
            # Try to delete by ID
            try:
                await loop.run_in_executor(
                    None,
                    lambda: self.collection.delete(ids=[key])
                )
                self.logger.debug(f"Deleted content from semantic memory: {key}")
                return True
            except Exception:
                # If deleting by ID fails, try by metadata key
                try:
                    results = await loop.run_in_executor(
                        None,
                        lambda: self.collection.query(
                            query_texts=[""],
                            where={"key": key},
                            n_results=1,
                            include=["documents", "metadatas"]
                        )
                    )
                    ids_to_delete = []
                    if results and results.get("metadatas") and len(results["metadatas"][0]) > 0:
                        for meta in results["metadatas"][0]:
                            if "key" in meta:
                                ids_to_delete.append(meta["key"])
                    if ids_to_delete:
                        await loop.run_in_executor(
                            None,
                            lambda: self.collection.delete(ids=ids_to_delete)
                        )
                        self.logger.debug(f"Deleted content from semantic memory by metadata key: {key}")
                        return True
                except Exception:
                    pass
            return False
        except Exception as e:
            self.logger.exception(f"Failed to delete content from semantic memory: {key}")
            raise MemoryError(f"Failed to delete from semantic memory: {str(e)}")
    
    async def delete_where(self, filter_dict: Dict[str, Any]) -> bool:
        """
        Delete content from semantic memory based on a filter.
        
        Args:
            filter_dict: Dictionary of metadata key-value pairs to filter by
            
        Returns:
            True if content was deleted, False otherwise
            
        Raises:
            MemoryError: If deletion fails
        """
        try:
            loop = asyncio.get_event_loop()
            results = await loop.run_in_executor(
                None,
                lambda: self.collection.query(
                    query_texts=[""],
                    where=filter_dict,
                    n_results=100,
                    include=["documents", "metadatas"]
                )
            )
            ids_to_delete = []
            if results and results.get("metadatas") and len(results["metadatas"][0]) > 0:
                for meta in results["metadatas"][0]:
                    if "key" in meta:
                        ids_to_delete.append(meta["key"])
            if ids_to_delete:
                await loop.run_in_executor(
                    None,
                    lambda: self.collection.delete(ids=ids_to_delete)
                )
                self.logger.debug(f"Deleted content from semantic memory by filter: {filter_dict}")
                return True
            return False
        except Exception as e:
            self.logger.exception(f"Failed to delete content from semantic memory by filter: {filter_dict}")
            raise MemoryError(f"Failed to delete from semantic memory: {str(e)}")

    @log_execution_time(logger)
    async def clear(self, **kwargs) -> None:
        """
        Clear all content from semantic memory.
        
        Args:
            **kwargs: Additional parameters
            
        Raises:
            MemoryError: If clearing fails
        """
        try:
            # Use a thread to run the blocking operation
            loop = asyncio.get_event_loop()
            
            # Delete all documents in the collection
            try:
                # First try the clear() method if available
                await loop.run_in_executor(
                    None,
                    lambda: self.collection.delete()  # Delete all documents in the collection
                )
            except Exception:
                # If clear() is not available, try get_collection and delete/create
                try:
                    # Delete the collection
                    await loop.run_in_executor(
                        None,
                        lambda: self.chroma_client.delete_collection(self.collection_name)
                    )
                    
                    # Recreate the collection
                    self.collection = await loop.run_in_executor(
                        None,
                        lambda: self.chroma_client.create_collection(
                            name=self.collection_name,
                            embedding_function=self.embedding_function
                        )
                    )
                except Exception as inner_exc:
                    raise inner_exc
            
            self.logger.info("Cleared all content from semantic memory")
            
        except Exception as e:
            self.logger.exception("Failed to clear semantic memory")
            raise MemoryError(f"Failed to clear semantic memory: {str(e)}")
    
    async def health_check(self) -> bool:
        """
        Check if ChromaDB connection is healthy.
        
        Returns:
            True if the connection is healthy, False otherwise
        """
        try:
            self.logger.info(f"ChromaDB health check: host={self.chroma_host}, port={self.chroma_port}")
            # Updated to use v2 API endpoint
            url = f"http://{self.chroma_host}:{self.chroma_port}/api/v2/heartbeat"
            self.logger.info(f"ChromaDB health check URL: {url}")
            async with httpx.AsyncClient() as client:
                response = await client.get(url, timeout=5.0)
                self.logger.info(f"ChromaDB health check response: status={response.status_code}, body={response.text}")
                if response.status_code == 200:
                    return True
                else:
                    self.logger.error(
                        f"ChromaDB health check failed: status={response.status_code}, body={response.text}"
                    )
                    return False
                
        except Exception as e:
            self.logger.error(f"ChromaDB health check exception: {str(e)}", exc_info=True)
            return False
    
    async def close(self) -> None:
        """
        Close the ChromaDB connection.
        
        This method should be called when shutting down the application
        to release resources properly.
        """
        try:
            # Close the ChromaDB client if there's a close method
            if hasattr(self.chroma_client, 'close'):
                self.chroma_client.close()
            self.logger.info("Closed semantic memory (ChromaDB)")
        except Exception as e:
            self.logger.exception(f"Error closing semantic memory: {str(e)}")