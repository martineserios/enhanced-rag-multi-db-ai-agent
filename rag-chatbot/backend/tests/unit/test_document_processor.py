# filepath: backend/tests/unit/test_document_processor.py
"""
Unit tests for the Document Processor utility.

This module tests the document processor functions for loading, chunking,
and processing documents for RAG.
"""
import pytest
import os
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from langchain.schema import Document

from app.utils.document_processor import (
    get_document_loader, 
    load_document, 
    split_documents,
    process_document,
    process_directory
)
from app.core.exceptions import (
    DocumentProcessingError,
    UnsupportedDocumentTypeError
)


@pytest.fixture
def sample_documents():
    """Create sample documents for testing."""
    return [
        Document(
            page_content="This is the first page of content. It contains some text for testing.",
            metadata={"source": "test1.txt", "page": 1}
        ),
        Document(
            page_content="This is the second page of content. It also contains text for testing.",
            metadata={"source": "test1.txt", "page": 2}
        ),
        Document(
            page_content="This is a different document with some other content for testing purposes.",
            metadata={"source": "test2.txt", "page": 1}
        )
    ]


class TestGetDocumentLoader:
    """Tests for the get_document_loader function."""
    
    def test_get_loader_for_txt(self):
        """Test getting a loader for a text file."""
        with patch("app.utils.document_processor.Path") as mock_path:
            # Set up the mock to simulate a text file that exists
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.suffix = ".txt"
            mock_path.return_value = mock_path_instance
            
            # Mock the TextLoader
            with patch("app.utils.document_processor.TextLoader") as mock_loader:
                mock_loader_instance = MagicMock()
                mock_loader.return_value = mock_loader_instance
                
                # Call the function
                loader = get_document_loader("test.txt")
                
                # Check that the correct loader was created
                mock_loader.assert_called_once_with("test.txt")
                assert loader == mock_loader_instance
    
    def test_get_loader_for_pdf(self):
        """Test getting a loader for a PDF file."""
        with patch("app.utils.document_processor.Path") as mock_path:
            # Set up the mock to simulate a PDF file that exists
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.suffix = ".pdf"
            mock_path.return_value = mock_path_instance
            
            # Mock the PyPDFLoader
            with patch("app.utils.document_processor.PyPDFLoader") as mock_loader:
                mock_loader_instance = MagicMock()
                mock_loader.return_value = mock_loader_instance
                
                # Call the function
                loader = get_document_loader("test.pdf")
                
                # Check that the correct loader was created
                mock_loader.assert_called_once_with("test.pdf")
                assert loader == mock_loader_instance
    
    def test_get_loader_for_unsupported_type(self):
        """Test getting a loader for an unsupported file type."""
        with patch("app.utils.document_processor.Path") as mock_path:
            # Set up the mock to simulate a file with unsupported extension
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = True
            mock_path_instance.suffix = ".xyz"  # Unsupported extension
            mock_path.return_value = mock_path_instance
            
            # Call the function
            loader = get_document_loader("test.xyz")
            
            # Check that None was returned
            assert loader is None
    
    def test_get_loader_for_nonexistent_file(self):
        """Test getting a loader for a file that doesn't exist."""
        with patch("app.utils.document_processor.Path") as mock_path:
            # Set up the mock to simulate a file that doesn't exist
            mock_path_instance = MagicMock()
            mock_path_instance.exists.return_value = False
            mock_path.return_value = mock_path_instance
            
            # Check that the function raises a FileNotFoundError
            with pytest.raises(FileNotFoundError):
                get_document_loader("nonexistent.txt")


class TestLoadDocument:
    """Tests for the load_document function."""
    
    def test_load_document_success(self, sample_documents):
        """Test successfully loading a document."""
        with patch("app.utils.document_processor.get_document_loader") as mock_get_loader:
            # Set up the mock loader
            mock_loader = MagicMock()
            mock_loader.load.return_value = sample_documents
            mock_get_loader.return_value = mock_loader
            
            # Call the function
            documents = load_document("test.txt")
            
            # Check that the loader was used and the documents were returned
            mock_get_loader.assert_called_once_with("test.txt")
            mock_loader.load.assert_called_once()
            assert documents == sample_documents
    
    def test_load_document_unsupported_type(self):
        """Test loading a document with an unsupported type."""
        with patch("app.utils.document_processor.get_document_loader") as mock_get_loader:
            # Set up the mock to return None (unsupported type)
            mock_get_loader.return_value = None
            
            # Check that the function raises an UnsupportedDocumentTypeError
            with pytest.raises(UnsupportedDocumentTypeError):
                load_document("test.xyz")
    
    def test_load_document_processing_error(self):
        """Test a document processing error during loading."""
        with patch("app.utils.document_processor.get_document_loader") as mock_get_loader:
            # Set up the mock loader to raise an exception
            mock_loader = MagicMock()
            mock_loader.load.side_effect = Exception("Test exception")
            mock_get_loader.return_value = mock_loader
            
            # Check that the function raises a DocumentProcessingError
            with pytest.raises(DocumentProcessingError):
                load_document("test.txt")


class TestSplitDocuments:
    """Tests for the split_documents function."""
    
    def test_split_documents_success(self, sample_documents):
        """Test successfully splitting documents into chunks."""
        with patch("app.utils.document_processor.RecursiveCharacterTextSplitter") as mock_splitter_class:
            # Set up the mock splitter
            mock_splitter = MagicMock()
            mock_splitter.split_documents.return_value = [
                Document(
                    page_content="This is the first chunk.",
                    metadata={"source": "test1.txt", "page": 1, "chunk": 1}
                ),
                Document(
                    page_content="This is the second chunk.",
                    metadata={"source": "test1.txt", "page": 1, "chunk": 2}
                ),
                Document(
                    page_content="This is the third chunk.",
                    metadata={"source": "test1.txt", "page": 2, "chunk": 1}
                )
            ]
            mock_splitter_class.return_value = mock_splitter
            
            # Call the function
            chunks = split_documents(sample_documents, chunk_size=100, chunk_overlap=20)
            
            # Check that the splitter was created and used correctly
            mock_splitter_class.assert_called_once_with(
                chunk_size=100,
                chunk_overlap=20,
                length_function=len,
                add_start_index=True
            )
            mock_splitter.split_documents.assert_called_once_with(sample_documents)
            assert len(chunks) == 3
    
    def test_split_documents_error(self, sample_documents):
        """Test an error during document splitting."""
        with patch("app.utils.document_processor.RecursiveCharacterTextSplitter") as mock_splitter_class:
            # Set up the mock splitter to raise an exception
            mock_splitter = MagicMock()
            mock_splitter.split_documents.side_effect = Exception("Test exception")
            mock_splitter_class.return_value = mock_splitter
            
            # Check that the function raises a DocumentProcessingError
            with pytest.raises(DocumentProcessingError):
                split_documents(sample_documents)


class TestProcessDocument:
    """Tests for the process_document function."""
    
    def test_process_document_success(self, sample_documents):
        """Test successfully processing a document."""
        with patch("app.utils.document_processor.load_document") as mock_load_document, \
             patch("app.utils.document_processor.split_documents") as mock_split_documents:
            # Set up the mocks
            mock_load_document.return_value = sample_documents
            
            chunks = [
                Document(
                    page_content="This is the first chunk.",
                    metadata={"source": "test1.txt", "page": 1, "chunk": 1}
                ),
                Document(
                    page_content="This is the second chunk.",
                    metadata={"source": "test1.txt", "page": 1, "chunk": 2}
                )
            ]
            mock_split_documents.return_value = chunks
            
            # Call the function
            result = process_document("test.txt", metadata={"test": "metadata"})
            
            # Check that the functions were called with the right parameters
            mock_load_document.assert_called_once_with("test.txt")
            mock_split_documents.assert_called_once_with(
                sample_documents, 
                chunk_size=1000, 
                chunk_overlap=200
            )
            
            # Check that metadata was added to each chunk
            assert result == chunks
            for chunk in result:
                assert "test" in chunk.metadata
                assert chunk.metadata["test"] == "metadata"
    
    def test_process_document_unsupported_type(self):
        """Test processing a document with an unsupported type."""
        with patch("app.utils.document_processor.load_document") as mock_load_document:
            # Set up the mock to raise an UnsupportedDocumentTypeError
            mock_load_document.side_effect = UnsupportedDocumentTypeError("Unsupported file type")
            
            # Check that the function raises an UnsupportedDocumentTypeError
            with pytest.raises(UnsupportedDocumentTypeError):
                process_document("test.xyz")
    
    def test_process_document_processing_error(self):
        """Test a document processing error."""
        with patch("app.utils.document_processor.load_document") as mock_load_document:
            # Set up the mock to raise a DocumentProcessingError
            mock_load_document.side_effect = DocumentProcessingError("Test error")
            
            # Check that the function raises a DocumentProcessingError
            with pytest.raises(DocumentProcessingError):
                process_document("test.txt")


class TestProcessDirectory:
    """Tests for the process_directory function."""
    
    def test_process_directory_success(self, sample_documents):
        """Test successfully processing a directory of documents."""
        with patch("app.utils.document_processor.Path") as mock_path, \
             patch("app.utils.document_processor.process_document") as mock_process_document:
            # Set up the mock directory
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.glob.return_value = [
                Path("test1.txt"),
                Path("test2.pdf"),
                Path("subdir")  # This should be skipped as it's a directory
            ]
            mock_path.return_value = mock_dir
            
            # Make Path("subdir").is_dir() return True
            def mock_is_dir(path):
                return str(path) == "subdir"
            
            # Set up relative_to to return the filename
            def mock_relative_to(path, base):
                return Path(path)
            
            # Configure the Path objects returned by glob
            for path_obj in mock_dir.glob.return_value:
                path_obj.is_dir = MagicMock(side_effect=lambda: mock_is_dir(path_obj))
                path_obj.relative_to = MagicMock(side_effect=lambda base: mock_relative_to(path_obj, base))
                path_obj.suffix = ".txt" if str(path_obj) == "test1.txt" else ".pdf"
            
            # Set up the mock process_document
            chunks1 = [
                Document(
                    page_content="Chunk from test1.txt",
                    metadata={"source": "test1.txt"}
                )
            ]
            chunks2 = [
                Document(
                    page_content="Chunk from test2.pdf",
                    metadata={"source": "test2.pdf"}
                )
            ]
            
            mock_process_document.side_effect = [chunks1, chunks2]
            
            # Call the function
            result = process_directory("testdir", metadata={"test": "metadata"})
            
            # Check that process_document was called for each file
            assert mock_process_document.call_count == 2
            
            # Check that all chunks were returned
            assert len(result) == 2
            assert result[0].page_content == "Chunk from test1.txt"
            assert result[1].page_content == "Chunk from test2.pdf"
    
    def test_process_directory_not_found(self):
        """Test processing a directory that doesn't exist."""
        with patch("app.utils.document_processor.Path") as mock_path:
            # Set up the mock directory
            mock_dir = MagicMock()
            mock_dir.exists.return_value = False
            mock_path.return_value = mock_dir
            
            # Check that the function raises a FileNotFoundError
            with pytest.raises(FileNotFoundError):
                process_directory("nonexistent")
    
    def test_process_directory_processing_error(self):
        """Test a processing error in one of the files."""
        with patch("app.utils.document_processor.Path") as mock_path, \
             patch("app.utils.document_processor.process_document") as mock_process_document:
            # Set up the mock directory
            mock_dir = MagicMock()
            mock_dir.exists.return_value = True
            mock_dir.is_dir.return_value = True
            mock_dir.glob.return_value = [
                Path("test1.txt"),
                Path("test2.pdf")
            ]
            mock_path.return_value = mock_dir
            
            # Configure the Path objects returned by glob
            for path_obj in mock_dir.glob.return_value:
                path_obj.is_dir = MagicMock(return_value=False)
                path_obj.relative_to = MagicMock(return_value=path_obj)
                path_obj.suffix = ".txt" if str(path_obj) == "test1.txt" else ".pdf"
            
            # Set up the mock process_document
            chunks1 = [
                Document(
                    page_content="Chunk from test1.txt",
                    metadata={"source": "test1.txt"}
                )
            ]
            
            # Make the second file raise an exception
            mock_process_document.side_effect = [chunks1, DocumentProcessingError("Test error")]
            
            # Call the function - it should continue despite the error
            result = process_directory("testdir", metadata={"test": "metadata"})
            
            # Check that process_document was called for each file
            assert mock_process_document.call_count == 2
            
            # Check that only the successful chunks were returned
            assert len(result) == 1
            assert result[0].page_content == "Chunk from test1.txt"