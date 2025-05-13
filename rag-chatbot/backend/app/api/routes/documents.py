# filepath: backend/app/api/routes/documents.py
"""
API routes for document management.

This module defines the FastAPI routes for document operations, including
uploading, retrieving, and processing documents for RAG.
"""
from typing import Dict, List, Any, Optional, Union, Annotated
import uuid
import os
import shutil
from pathlib import Path
from datetime import datetime

from fastapi import (
    APIRouter, Depends, HTTPException, UploadFile, File, Form, 
    Query, Path as PathParam, BackgroundTasks, Body
)
from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.core.exceptions import (
    DocumentError, DocumentProcessingError, DocumentNotFoundError, 
    UnsupportedDocumentTypeError, MemoryError
)
from app.config import Settings, get_settings
from app.utils.document_processor import process_document, get_document_loader
from app.services.memory.manager import get_memory_manager
from app.api.dependencies import (
    verify_memory_enabled,
    get_memory_manager_dependency,
    get_request_metadata
)


router = APIRouter()
logger = get_logger(__name__)

# Ensure upload directory exists
UPLOAD_DIR = Path("/data/uploads")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


class DocumentUploadResponse(BaseModel):
    """Response model for document upload."""
    document_id: str
    filename: str
    status: str
    message: str
    chunk_count: int = 0


class DocumentResponse(BaseModel):
    """Response model for document information."""
    document_id: str
    filename: str
    upload_date: str
    metadata: Dict[str, Any] = {}
    chunk_count: int = 0


@router.post("/upload", response_model=DocumentUploadResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    description: str = Form(None),
    chunk_size: int = Form(1000),
    chunk_overlap: int = Form(200),
    tags: str = Form(""),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency),
    request_metadata: Dict[str, Any] = Depends(get_request_metadata)
):
    """
    Upload and process a document for the RAG system.
    
    This endpoint:
    1. Validates and saves the uploaded file
    2. Processes the document into chunks
    3. Stores the chunks in semantic memory
    
    Args:
        background_tasks: FastAPI background tasks for async operations
        file: The uploaded file
        description: Optional description of the document
        chunk_size: Size of text chunks in characters
        chunk_overlap: Overlap between chunks in characters
        tags: Comma-separated list of tags
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        request_metadata: Request metadata from dependency
        
    Returns:
        DocumentUploadResponse with upload status
        
    Raises:
        HTTPException: If the upload or processing fails
    """
    try:
        if not file.filename:
            raise HTTPException(status_code=400, detail="No file selected")
        
        # Generate a unique document ID
        document_id = str(uuid.uuid4())
        
        # Extract file extension
        file_extension = os.path.splitext(file.filename)[1].lower()
        
        # Save the uploaded file
        saved_file_path = UPLOAD_DIR / f"{document_id}{file_extension}"
        
        try:
            with open(saved_file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
        except Exception as e:
            logger.exception(f"Failed to save file: {file.filename}")
            raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
        finally:
            file.file.close()
        
        # Check if file type is supported (after saving, use saved path)
        if not get_document_loader(str(saved_file_path)):
            raise UnsupportedDocumentTypeError(f"Unsupported file type: {file_extension}")

        
        # Parse tags
        tag_list = [tag.strip() for tag in tags.split(",")] if tags else []
        
        # Prepare metadata
        metadata = {
            "document_id": document_id,
            "filename": file.filename,
            "description": description or "",
            "upload_date": datetime.utcnow().isoformat(),
            "tags": tag_list,
            "uploader_id": request_metadata.get("request_id", "")
        }
        
        # Process the document in a background task
        chunk_count = [0]  # Use list for mutable reference in background task
        
        async def process_and_store_document():
            """Background task to process and store the document."""
            try:
                # Check if semantic memory is enabled
                if "semantic" not in memory_manager.memory_systems:
                    logger.error("Semantic memory is not enabled")
                    return
                
                # Process the document
                chunks = process_document(
                    str(saved_file_path),
                    metadata=metadata,
                    chunk_size=chunk_size,
                    chunk_overlap=chunk_overlap
                )
                
                # Store chunks in semantic memory
                def sanitize_metadata(metadata):
                    allowed_types = (str, int, float, bool, type(None))
                    return {
                        k: (v if isinstance(v, allowed_types) else str(v))
                        for k, v in metadata.items()
                    }

                for i, chunk in enumerate(chunks):
                    # Add chunk-specific metadata
                    chunk_metadata = chunk.metadata.copy()
                    chunk_metadata["chunk_id"] = i
                    chunk_metadata["chunk_index"] = i
                    chunk_metadata["total_chunks"] = len(chunks)
                    # Sanitize metadata before storing
                    sanitized_metadata = sanitize_metadata(chunk_metadata)
                    # Store in semantic memory
                    logger.info(f"Storing chunk in semantic memory:", extra={"metadata": sanitized_metadata})
                    await memory_manager.store_memory(
                        memory_type="semantic",
                        content=chunk.page_content,
                        key=f"{document_id}_chunk_{i}",
                        metadata=sanitized_metadata
                    )
                
                chunk_count[0] = len(chunks)
                
                logger.info(
                    f"Document processed and stored in semantic memory: {file.filename}",
                    extra={
                        "document_id": document_id,
                        "chunk_count": len(chunks),
                        "request_id": request_metadata.get("request_id")
                    }
                )
            except Exception as e:
                logger.exception(f"Failed to process document: {file.filename}")
                # We don't raise here since this is a background task
        
        # Add the background task
        background_tasks.add_task(process_and_store_document)
        
        logger.info(
            f"Document uploaded: {file.filename}",
            extra={
                "document_id": document_id,
                "size": file.size,
                "content_type": file.content_type,
                "request_id": request_metadata.get("request_id")
            }
        )
        
        return DocumentUploadResponse(
            document_id=document_id,
            filename=file.filename,
            status="success",
            message="Document uploaded and being processed",
            chunk_count=chunk_count[0]
        )
        
    except UnsupportedDocumentTypeError as e:
        logger.error(f"Unsupported document type: {file.filename}")
        raise HTTPException(status_code=400, detail=str(e))
    except DocumentProcessingError as e:
        logger.exception(f"Failed to process document: {file.filename}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.exception(f"Unexpected error uploading document: {file.filename}")
        raise HTTPException(status_code=500, detail=f"Document upload failed: {str(e)}")


@router.get("/", response_model=List[DocumentResponse])
async def list_documents(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    tag: Optional[str] = Query(None),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    List documents in the RAG system.
    
    Args:
        limit: Maximum number of documents to return
        offset: Number of documents to skip
        tag: Optional tag to filter by
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        List of documents
        
    Raises:
        HTTPException: If retrieving the document list fails
    """
    try:
        # Check if semantic memory is enabled
        if "semantic" not in memory_manager.memory_systems:
            logger.error("Semantic memory is not enabled")
            raise HTTPException(status_code=400, detail="Semantic memory is not enabled")
        
        # Get a list of uploaded files
        documents = []
        document_ids = set()
        
        # Use semantic memory to get document metadata
        query = "metadata.document_id:*"
        if tag:
            query += f" AND metadata.tags:{tag}"
        
        # Search semantic memory
        results = await memory_manager.search_memory(
            memory_type="semantic",
            query=query,
            limit=limit * 10  # Get more results to account for chunks
        )
        
        logger.info(f"Results from semantic memory search:", extra={"results": results})
        # Process results to get unique documents
        for result in results:
            if isinstance(result, dict) and "metadata" in result:
                metadata = result.get("metadata", {})
                document_id = metadata.get("document_id")
                
                if document_id and document_id not in document_ids:
                    document_ids.add(document_id)
                    
                    documents.append({
                        "document_id": document_id,
                        "filename": metadata.get("filename", ""),
                        "upload_date": metadata.get("upload_date", ""),
                        "metadata": metadata,
                        "chunk_count": metadata.get("total_chunks", 0)
                    })
        
        # Apply offset and limit
        documents = documents[offset:offset + limit]
        
        return documents
        
    except MemoryError as e:
        logger.error(f"Memory error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")
    except Exception as e:
        logger.exception(f"Error listing documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {str(e)}")


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: str = PathParam(..., description="Document ID"),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Get information about a specific document.
    
    Args:
        document_id: ID of the document to retrieve
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Document information
        
    Raises:
        HTTPException: If retrieving the document fails
    """
    try:
        # Check if semantic memory is enabled
        if "semantic" not in memory_manager.memory_systems:
            logger.error("Semantic memory is not enabled")
            raise HTTPException(status_code=400, detail="Semantic memory is not enabled")
        
        # Search for documents with this ID
        results = await memory_manager.search_memory(
            memory_type="semantic",
            query=f"metadata.document_id:{document_id}",
            limit=1
        )
        
        if not results:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        
        # Extract metadata from the first chunk
        metadata = results[0].get("metadata", {})
        
        return DocumentResponse(
            document_id=document_id,
            filename=metadata.get("filename", ""),
            upload_date=metadata.get("upload_date", ""),
            metadata=metadata,
            chunk_count=metadata.get("total_chunks", 0)
        )
        
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    except MemoryError as e:
        logger.error(f"Memory error retrieving document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")
    except Exception as e:
        logger.exception(f"Error retrieving document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document: {str(e)}")


@router.delete("/{document_id}")
async def delete_document(
    document_id: str = PathParam(..., description="Document ID"),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Delete a document from the RAG system.
    
    Args:
        document_id: ID of the document to delete
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Status message
        
    Raises:
        HTTPException: If deleting the document fails
    """
    try:
        # Check if semantic memory is enabled
        if "semantic" not in memory_manager.memory_systems:
            logger.error("Semantic memory is not enabled")
            raise HTTPException(status_code=400, detail="Semantic memory is not enabled")
        
        # Search for documents with this ID
        results = await memory_manager.search_memory(
            memory_type="semantic",
            query=f"metadata.document_id:{document_id}",
            limit=1
        )
        
        if not results:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        
        # Delete from semantic memory
        semantic_memory = memory_manager.memory_systems["semantic"]
        deleted = await semantic_memory.delete_where({"document_id": document_id})
        
        if not deleted:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to delete document {document_id} from semantic memory"
            )
        
        # Try to delete the file if it exists
        file_deleted = False
        for file_path in UPLOAD_DIR.glob(f"{document_id}*"):
            if file_path.is_file():
                file_path.unlink()
                file_deleted = True
        
        logger.info(
            f"Document deleted: {document_id}",
            extra={"file_deleted": file_deleted}
        )
        
        return {
            "status": "success",
            "message": f"Document {document_id} deleted successfully",
            "file_deleted": file_deleted
        }
        
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    except MemoryError as e:
        logger.error(f"Memory error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")
    except Exception as e:
        logger.exception(f"Error deleting document: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to delete document: {str(e)}")


@router.get("/{document_id}/chunks")
async def get_document_chunks(
    document_id: str = PathParam(..., description="Document ID"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Get chunks of a document.
    
    Args:
        document_id: ID of the document
        limit: Maximum number of chunks to return
        offset: Number of chunks to skip
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        List of document chunks
        
    Raises:
        HTTPException: If retrieving the chunks fails
    """
    try:
        # Check if semantic memory is enabled
        if "semantic" not in memory_manager.memory_systems:
            logger.error("Semantic memory is not enabled")
            raise HTTPException(status_code=400, detail="Semantic memory is not enabled")
        
        # Search for documents with this ID
        results = await memory_manager.search_memory(
            memory_type="semantic",
            query=f"metadata.document_id:{document_id}",
            limit=limit,
            offset=offset
        )
        
        if not results:
            raise DocumentNotFoundError(f"Document {document_id} not found")
        
        # Format chunks
        chunks = []
        for result in results:
            if isinstance(result, dict):
                chunks.append({
                    "content": result.get("content", ""),
                    "metadata": result.get("metadata", {}),
                    "chunk_id": result.get("metadata", {}).get("chunk_id", 0)
                })
        
        # Sort by chunk_id
        chunks.sort(key=lambda x: x.get("chunk_id", 0))
        
        return {
            "document_id": document_id,
            "chunk_count": len(chunks),
            "chunks": chunks
        }
        
    except DocumentNotFoundError:
        raise HTTPException(status_code=404, detail=f"Document {document_id} not found")
    except MemoryError as e:
        logger.error(f"Memory error retrieving document chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document chunks: {str(e)}")
    except Exception as e:
        logger.exception(f"Error retrieving document chunks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to retrieve document chunks: {str(e)}")


@router.get("/search")
async def search_documents(
    query: str = Query(..., description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    settings: Settings = Depends(get_settings),
    _: bool = Depends(verify_memory_enabled),
    memory_manager = Depends(get_memory_manager_dependency)
):
    """
    Search for documents and chunks.
    
    Args:
        query: Search query
        limit: Maximum number of results to return
        settings: Application settings
        _: Dependency to verify memory is enabled
        memory_manager: Memory manager instance
        
    Returns:
        Search results
        
    Raises:
        HTTPException: If the search fails
    """
    try:
        # Check if semantic memory is enabled
        if "semantic" not in memory_manager.memory_systems:
            logger.error("Semantic memory is not enabled")
            raise HTTPException(status_code=400, detail="Semantic memory is not enabled")
        
        # Search semantic memory
        results = await memory_manager.search_memory(
            memory_type="semantic",
            query=query,
            limit=limit
        )
        
        # Group results by document
        documents = {}
        for result in results:
            if isinstance(result, dict) and "metadata" in result:
                metadata = result.get("metadata", {})
                document_id = metadata.get("document_id")
                
                if document_id:
                    if document_id not in documents:
                        documents[document_id] = {
                            "document_id": document_id,
                            "filename": metadata.get("filename", ""),
                            "description": metadata.get("description", ""),
                            "chunks": []
                        }
                    
                    # Add chunk to document
                    documents[document_id]["chunks"].append({
                        "content": result.get("content", ""),
                        "chunk_id": metadata.get("chunk_id", 0),
                        "relevance_score": result.get("relevance_score", 0)
                    })
        
        return {
            "query": query,
            "document_count": len(documents),
            "documents": list(documents.values())
        }
        
    except MemoryError as e:
        logger.error(f"Memory error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")
    except Exception as e:
        logger.exception(f"Error searching documents: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to search documents: {str(e)}")