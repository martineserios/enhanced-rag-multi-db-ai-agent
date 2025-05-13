# filepath: backend/services/database/chroma.py
"""
ChromaDB service for managing vector database connections.

This module provides functions for initializing and interacting with ChromaDB,
which is used as the vector database for semantic memory.
"""
import os
import asyncio
from typing import Dict, List, Any, Optional, Union
import logging
import httpx

from chromadb import Client, ClientAPI, Collection
from chromadb.config import Settings as ChromaSettings
from chromadb.utils import embedding_functions
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document

from app.core.logging import get_logger, log_execution_time
from app.core.exceptions import DatabaseConnectionError, DatabaseQueryError
from app.config import Settings


logger = get_logger(__name__)

# Global reference to ChromaDB client
_chroma_client = None
_default_collection = None


@log_execution_time(logger)
async def init_chroma(settings: Settings) -> Client:
    """
    Initialize the ChromaDB client.
    
    Args:
        settings: Application configuration settings
        
    Returns:
        Initialized ChromaDB client
        
    Raises:
        DatabaseConnectionError: If initialization fails
    """
    global _chroma_client
    
    try:
        # Create direct ChromaDB client
        client_settings = ChromaSettings(
            chroma_api_impl="rest",
            chroma_server_host=settings.chroma_host,
            chroma_server_http_port=settings.chroma_port
        )
        
        # Use a thread to run the blocking operation
        loop = asyncio.get_event_loop()
        client = await loop.run_in_executor(
            None,
            lambda: Client(client_settings)
        )
        
        # Store the client in the global variable
        _chroma_client = client
        
        logger.info(
            f"Initialized ChromaDB client",
            extra={"host": settings.chroma_host, "port": settings.chroma_port}
        )
        
        # Initialize default collection
        await init_default_collection(settings)
        
        return client
        
    except Exception as e:
        logger.exception("Failed to initialize ChromaDB client")
        raise DatabaseConnectionError(f"ChromaDB initialization failed: {str(e)}")


@log_execution_time(logger)
async def init_default_collection(
    settings: Settings,
    collection_name: str = "documents"
) -> None:
    """
    Initialize the default collection in ChromaDB.
    
    Args:
        settings: Application configuration settings
        collection_name: Name of the collection to initialize
        
    Raises:
        DatabaseConnectionError: If initialization fails
    """
    global _chroma_client, _default_collection
    
    if _chroma_client is None:
        await init_chroma(settings)
    
    try:
        # Check if collection exists
        loop = asyncio.get_event_loop()
        collections = await loop.run_in_executor(
            None,
            lambda: _chroma_client.list_collections()
        )
        
        collection_exists = any(c.name == collection_name for c in collections)
        
        # Create collection if it doesn't exist
        if not collection_exists:
            collection = await loop.run_in_executor(
                None,
                lambda: _chroma_client.create_collection(
                    name=collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=settings.embedding_model
                    )
                )
            )
            logger.info(f"Created ChromaDB collection: {collection_name}")
        else:
            # Get existing collection
            collection = await loop.run_in_executor(
                None,
                lambda: _chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=embedding_functions.SentenceTransformerEmbeddingFunction(
                        model_name=settings.embedding_model
                    )
                )
            )
            logger.info(f"Using existing ChromaDB collection: {collection_name}")
        
        # Store the collection in the global variable
        _default_collection = collection
        
    except Exception as e:
        logger.exception(f"Failed to initialize ChromaDB collection: {collection_name}")
        raise DatabaseConnectionError(f"ChromaDB collection initialization failed: {str(e)}")


def get_chroma_client() -> Client:
    """
    Get the ChromaDB client.
    
    Returns:
        ChromaDB client
        
    Raises:
        DatabaseConnectionError: If the client is not initialized
    """
    global _chroma_client
    
    if _chroma_client is None:
        raise DatabaseConnectionError("ChromaDB client is not initialized")
    
    return _chroma_client


def get_default_collection() -> Collection:
    """
    Get the default ChromaDB collection.
    
    Returns:
        ChromaDB collection
        
    Raises:
        DatabaseConnectionError: If the collection is not initialized
    """
    global _default_collection
    
    if _default_collection is None:
        raise DatabaseConnectionError("ChromaDB collection is not initialized")
    
    return _default_collection


@log_execution_time(logger)
async def add_documents(
    documents: List[Document],
    collection_name: Optional[str] = None,
    settings: Optional[Settings] = None
) -> List[str]:
    """
    Add documents to ChromaDB.
    
    Args:
        documents: List of documents to add
        collection_name: Name of the collection to add to (uses default if None)
        settings: Application settings (required if client not initialized)
        
    Returns:
        List of document IDs
        
    Raises:
        DatabaseConnectionError: If the client is not initialized
        DatabaseQueryError: If adding documents fails
    """
    global _chroma_client, _default_collection
    
    # Initialize if needed
    if _chroma_client is None and settings is not None:
        await init_chroma(settings)
    elif _chroma_client is None:
        raise DatabaseConnectionError("ChromaDB client is not initialized and no settings provided")
    
    try:
        # Get collection
        collection = _default_collection
        if collection_name is not None:
            loop = asyncio.get_event_loop()
            collection = await loop.run_in_executor(
                None,
                lambda: _chroma_client.get_or_create_collection(
                    name=collection_name,
                    embedding_function=_default_collection._embedding_function
                )
            )
        
        # Convert documents to ChromaDB format
        ids = [str(i) for i in range(len(documents))]
        documents_text = [doc.page_content for doc in documents]
        metadatas = [doc.metadata for doc in documents]
        
        # Add documents
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: collection.add(
                ids=ids,
                documents=documents_text,
                metadatas=metadatas
            )
        )
        
        logger.info(
            f"Added documents to ChromaDB",
            extra={"document_count": len(documents), "collection": collection.name}
        )
        
        return ids
        
    except Exception as e:
        logger.exception("Failed to add documents to ChromaDB")
        raise DatabaseQueryError(f"Failed to add documents to ChromaDB: {str(e)}")


@log_execution_time(logger)
async def query_documents(
    query_text: str,
    n_results: int = 5,
    where: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
    settings: Optional[Settings] = None
) -> List[Dict[str, Any]]:
    """
    Query ChromaDB for similar documents.
    
    Args:
        query_text: Text to search for
        n_results: Number of results to return
        where: Filter to apply to results
        collection_name: Name of the collection to query (uses default if None)
        settings: Application settings (required if client not initialized)
        
    Returns:
        List of document dictionaries with content and metadata
        
    Raises:
        DatabaseConnectionError: If the client is not initialized
        DatabaseQueryError: If querying fails
    """
    global _chroma_client, _default_collection
    
    # Initialize if needed
    if _chroma_client is None and settings is not None:
        await init_chroma(settings)
    elif _chroma_client is None:
        raise DatabaseConnectionError("ChromaDB client is not initialized and no settings provided")
    
    try:
        # Get collection
        collection = _default_collection
        if collection_name is not None:
            loop = asyncio.get_event_loop()
            collection = await loop.run_in_executor(
                None,
                lambda: _chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=_default_collection._embedding_function
                )
            )
        
        # Query documents
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(
            None,
            lambda: collection.query(
                query_texts=[query_text],
                n_results=n_results,
                where=where
            )
        )
        
        # Format results
        formatted_results = []
        if results["documents"] and len(results["documents"][0]) > 0:
            for i, doc in enumerate(results["documents"][0]):
                formatted_result = {
                    "id": results["ids"][0][i],
                    "content": doc,
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if "distances" in results else None
                }
                formatted_results.append(formatted_result)
        
        logger.debug(
            f"Queried ChromaDB",
            extra={
                "query": query_text[:50] + "..." if len(query_text) > 50 else query_text,
                "result_count": len(formatted_results),
                "collection": collection.name
            }
        )
        
        return formatted_results
        
    except Exception as e:
        logger.exception("Failed to query ChromaDB")
        raise DatabaseQueryError(f"Failed to query ChromaDB: {str(e)}")


@log_execution_time(logger)
async def delete_documents(
    ids: Optional[List[str]] = None,
    where: Optional[Dict[str, Any]] = None,
    collection_name: Optional[str] = None,
    settings: Optional[Settings] = None
) -> bool:
    """
    Delete documents from ChromaDB.
    
    Args:
        ids: List of document IDs to delete
        where: Filter to apply for deletion
        collection_name: Name of the collection to delete from (uses default if None)
        settings: Application settings (required if client not initialized)
        
    Returns:
        True if documents were deleted, False otherwise
        
    Raises:
        DatabaseConnectionError: If the client is not initialized
        DatabaseQueryError: If deletion fails
    """
    global _chroma_client, _default_collection
    
    # Check that at least one of ids or where is provided
    if ids is None and where is None:
        raise ValueError("Either ids or where must be provided")
    
    # Initialize if needed
    if _chroma_client is None and settings is not None:
        await init_chroma(settings)
    elif _chroma_client is None:
        raise DatabaseConnectionError("ChromaDB client is not initialized and no settings provided")
    
    try:
        # Get collection
        collection = _default_collection
        if collection_name is not None:
            loop = asyncio.get_event_loop()
            collection = await loop.run_in_executor(
                None,
                lambda: _chroma_client.get_collection(
                    name=collection_name,
                    embedding_function=_default_collection._embedding_function
                )
            )
        
        # Delete documents
        loop = asyncio.get_event_loop()
        
        if ids is not None:
            await loop.run_in_executor(
                None,
                lambda: collection.delete(ids=ids)
            )
            logger.info(
                f"Deleted documents from ChromaDB by IDs",
                extra={"id_count": len(ids), "collection": collection.name}
            )
        else:
            await loop.run_in_executor(
                None,
                lambda: collection.delete(where=where)
            )
            logger.info(
                f"Deleted documents from ChromaDB by filter",
                extra={"where": str(where), "collection": collection.name}
            )
        
        return True
        
    except Exception as e:
        logger.exception("Failed to delete documents from ChromaDB")
        raise DatabaseQueryError(f"Failed to delete documents from ChromaDB: {str(e)}")


async def health_check() -> bool:
    """
    Check if ChromaDB is healthy.
    
    Returns:
        True if ChromaDB is healthy, False otherwise
    """
    global _chroma_client
    
    if _chroma_client is None:
        return False
    
    try:
        # Make a simple API call to check health
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: _chroma_client.heartbeat()
        )
        return True
    except Exception as e:
        logger.error(f"ChromaDB health check failed: {str(e)}")
        return False


async def close():
    """
    Close the ChromaDB client.
    
    This function should be called when shutting down the application
    to properly release resources.
    """
    global _chroma_client, _default_collection
    
    try:
        # ChromaDB doesn't have a close method, but we clear the references
        _chroma_client = None
        _default_collection = None
        logger.info("Closed ChromaDB client")
    except Exception as e:
        logger.error(f"Error closing ChromaDB client: {str(e)}")