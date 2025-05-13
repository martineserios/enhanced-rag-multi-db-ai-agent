# filepath: backend/utils/document_processor.py
"""
Utilities for processing documents for RAG.

This module provides utilities for loading, processing, and chunking
documents for storage in the vector database and use in RAG.
"""
import os
from pathlib import Path
from typing import Dict, List, Any, Optional, Union, Type
import logging
import mimetypes
from concurrent.futures import ThreadPoolExecutor

from langchain_community.document_loaders import (
    TextLoader,
    CSVLoader,
    UnstructuredExcelLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredPowerPointLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    PyPDFLoader,
    DirectoryLoader,
    UnstructuredFileLoader
)
from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from app.core.logging import get_logger
from app.core.exceptions import DocumentProcessingError, UnsupportedDocumentTypeError


logger = get_logger(__name__)

# Register additional MIME types
mimetypes.add_type('application/markdown', '.md')
mimetypes.add_type('application/markdown', '.markdown')

# Map of file extensions to document loaders
DOCUMENT_LOADERS: Dict[str, Type] = {
    # Text files
    '.txt': TextLoader,
    '.text': TextLoader,
    '.md': UnstructuredMarkdownLoader,
    '.markdown': UnstructuredMarkdownLoader,
    
    # Office documents
    '.doc': UnstructuredWordDocumentLoader,
    '.docx': UnstructuredWordDocumentLoader,
    '.xls': UnstructuredExcelLoader,
    '.xlsx': UnstructuredExcelLoader,
    '.ppt': UnstructuredPowerPointLoader,
    '.pptx': UnstructuredPowerPointLoader,
    
    # PDFs
    '.pdf': PyPDFLoader,
    
    # Data files
    '.csv': CSVLoader,
    '.tsv': CSVLoader,
    
    # Web files
    '.html': UnstructuredHTMLLoader,
    '.htm': UnstructuredHTMLLoader,
    '.xml': UnstructuredHTMLLoader,
    '.json': TextLoader,
}

# Default text splitter configuration
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


def get_document_loader(file_path: Union[str, Path]) -> Optional[Any]:
    """
    Get the appropriate document loader for a file.
    
    This function selects the appropriate langchain document loader
    based on the file extension.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        Document loader instance, or None if file type is not supported
        
    Raises:
        FileNotFoundError: If the file does not exist
    """
    # Convert to Path object for easier handling
    file_path = Path(file_path)
    
    # Check if file exists
    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")
    
    # Get file extension
    file_extension = file_path.suffix.lower()
    
    # Get loader class based on extension
    loader_class = DOCUMENT_LOADERS.get(file_extension)
    
    if loader_class is None:
        logger.warning(f"Unsupported file type: {file_extension}")
        return None
    
    try:
        # Create and return the loader instance
        loader = loader_class(str(file_path))
        return loader
    except Exception as e:
        logger.exception(f"Error creating document loader for {file_path}")
        raise DocumentProcessingError(f"Failed to create document loader: {str(e)}")


def load_document(file_path: Union[str, Path]) -> List[Document]:
    """
    Load a document from a file.
    
    Args:
        file_path: Path to the document file
        
    Returns:
        List of Document objects
        
    Raises:
        UnsupportedDocumentTypeError: If the file type is not supported
        DocumentProcessingError: If document loading fails
    """
    # Get document loader
    loader = get_document_loader(file_path)
    
    if loader is None:
        raise UnsupportedDocumentTypeError(f"Unsupported file type: {Path(file_path).suffix}")
    
    try:
        # Load the document
        documents = loader.load()
        
        logger.info(
            f"Loaded document: {file_path}",
            extra={"document_count": len(documents)}
        )
        
        return documents
    except Exception as e:
        logger.exception(f"Error loading document: {file_path}")
        raise DocumentProcessingError(f"Failed to load document: {str(e)}")


def split_documents(
    documents: List[Document],
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Document]:
    """
    Split documents into chunks.
    
    Args:
        documents: List of documents to split
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of chunked documents
        
    Raises:
        DocumentProcessingError: If document splitting fails
    """
    try:
        # Create text splitter
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            length_function=len,
            add_start_index=True
        )
        
        # Split documents
        chunks = text_splitter.split_documents(documents)
        
        logger.info(
            f"Split documents into chunks",
            extra={
                "original_document_count": len(documents),
                "chunk_count": len(chunks),
                "chunk_size": chunk_size,
                "chunk_overlap": chunk_overlap
            }
        )
        
        return chunks
    except Exception as e:
        logger.exception("Error splitting documents")
        raise DocumentProcessingError(f"Failed to split documents: {str(e)}")


def process_document(
    file_path: Union[str, Path],
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP
) -> List[Document]:
    """
    Process a document for RAG.
    
    This function:
    1. Loads the document from the file
    2. Splits it into chunks
    3. Adds metadata to each chunk
    
    Args:
        file_path: Path to the document file
        metadata: Additional metadata to add to each chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        
    Returns:
        List of processed document chunks
        
    Raises:
        UnsupportedDocumentTypeError: If the file type is not supported
        DocumentProcessingError: If document processing fails
    """
    try:
        # Load the document
        documents = load_document(file_path)
        
        # Split into chunks
        chunks = split_documents(documents, chunk_size, chunk_overlap)
        
        # Add metadata to each chunk
        if metadata:
            for chunk in chunks:
                if chunk.metadata is None:
                    chunk.metadata = {}
                chunk.metadata.update(metadata)
        
        return chunks
    except (UnsupportedDocumentTypeError, DocumentProcessingError):
        # Re-raise these exceptions
        raise
    except Exception as e:
        logger.exception(f"Error processing document: {file_path}")
        raise DocumentProcessingError(f"Failed to process document: {str(e)}")


def process_directory(
    directory_path: Union[str, Path],
    glob_pattern: str = "*.*",
    metadata: Optional[Dict[str, Any]] = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    max_workers: int = 4
) -> List[Document]:
    """
    Process all documents in a directory.
    
    Args:
        directory_path: Path to the directory
        glob_pattern: Pattern to match files
        metadata: Additional metadata to add to each chunk
        chunk_size: Size of each chunk in characters
        chunk_overlap: Overlap between chunks in characters
        max_workers: Maximum number of worker threads
        
    Returns:
        List of processed document chunks
        
    Raises:
        DocumentProcessingError: If document processing fails
    """
    try:
        # Convert to Path object
        directory_path = Path(directory_path)
        
        # Check if directory exists
        if not directory_path.exists() or not directory_path.is_dir():
            raise FileNotFoundError(f"Directory not found: {directory_path}")
        
        # Get list of files
        files = list(directory_path.glob(glob_pattern))
        
        if not files:
            logger.warning(f"No files found in {directory_path} matching {glob_pattern}")
            return []
        
        logger.info(
            f"Processing directory: {directory_path}",
            extra={"file_count": len(files), "glob_pattern": glob_pattern}
        )
        
        # Process files in parallel
        all_chunks = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            for file_path in files:
                try:
                    # Skip directories
                    if file_path.is_dir():
                        continue
                    
                    # Skip unsupported file types
                    if file_path.suffix.lower() not in DOCUMENT_LOADERS:
                        logger.warning(f"Skipping unsupported file: {file_path}")
                        continue
                    
                    # Create file-specific metadata
                    file_metadata = {"source": str(file_path.relative_to(directory_path))}
                    
                    # Add additional metadata
                    if metadata:
                        file_metadata.update(metadata)
                    
                    # Process file
                    chunks = process_document(
                        file_path,
                        metadata=file_metadata,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap
                    )
                    
                    all_chunks.extend(chunks)
                except Exception as e:
                    logger.error(f"Error processing file {file_path}: {str(e)}")
        
        logger.info(
            f"Processed directory",
            extra={
                "directory": str(directory_path),
                "total_chunks": len(all_chunks),
                "files_processed": len(files)
            }
        )
        
        return all_chunks
    except Exception as e:
        logger.exception(f"Error processing directory: {directory_path}")
        raise DocumentProcessingError(f"Failed to process directory: {str(e)}")