# filepath: frontend/components/document_manager.py
"""
Document manager component for the Streamlit UI.

This module provides a document management interface for uploading, viewing,
and managing documents in the RAG system.
"""
import os
import json
import requests
import streamlit as st
from datetime import datetime
import pandas as pd
from typing import Dict, List, Any, Optional

from utils.api import get_api_client, APIError
from utils.formatters import format_timestamp, truncate_text


def render_document_manager():
    """
    Render the document management interface.
    
    This function:
    1. Displays a list of documents in the system
    2. Provides a form for uploading new documents
    3. Allows searching and filtering documents
    4. Provides document deletion functionality
    """
    st.title("Document Manager")
    st.markdown(
        """
        Upload and manage documents for the RAG system. These documents are stored in semantic memory
        and used to provide context for answering questions.
        """
    )
    
    # Initialize API client
    api = get_api_client()
    
    # Create tabs for different functions
    tab1, tab2, tab3 = st.tabs(["📚 Document Library", "📤 Upload Document", "🔍 Search Documents"])
    
    with tab1:
        render_document_library(api)
    
    with tab2:
        render_upload_form(api)
    
    with tab3:
        render_search_interface(api)


def render_document_library(api):
    """
    Render the document library showing all documents in the system.
    
    Args:
        api: API client instance
    """
    st.markdown("### Document Library")
    
    # Add refresh button
    if st.button("Refresh Document List"):
        st.rerun()
    
    try:
        # Fetch documents from API
        result = api.get_documents()
        documents = result.get("documents", [])
        
        if not documents:
            st.info("No documents found in the system. Upload documents using the 'Upload Document' tab.")
            return
        
        # Create a DataFrame for better display
        doc_data = []
        for doc in documents:
            # Extract metadata
            metadata = doc.get("metadata", {})
            tags = metadata.get("tags", [])
            if isinstance(tags, list):
                tags_str = ", ".join(tags)
            else:
                tags_str = str(tags)
            
            # Format the data
            doc_data.append({
                "ID": doc.get("document_id", "")[:8] + "...",
                "Filename": doc.get("filename", ""),
                "Upload Date": format_timestamp(doc.get("upload_date", "")),
                "Chunks": doc.get("chunk_count", 0),
                "Tags": tags_str,
                "Description": truncate_text(metadata.get("description", ""), 50),
                "Full ID": doc.get("document_id", "")
            })
        
        # Display as a dataframe
        df = pd.DataFrame(doc_data)
        st.dataframe(
            df[["ID", "Filename", "Upload Date", "Chunks", "Tags", "Description"]],
            hide_index=True,
            use_container_width=True
        )
        
        # Document details and actions
        st.markdown("### Document Details")
        
        # Select a document to view details
        selected_doc_id = st.selectbox(
            "Select a document to view details",
            options=[doc["Full ID"] for doc in doc_data],
            format_func=lambda x: next((doc["Filename"] for doc in doc_data if doc["Full ID"] == x), x)
        )
        
        if selected_doc_id:
            # Find the selected document
            selected_doc = next((doc for doc in documents if doc.get("document_id") == selected_doc_id), None)
            
            if selected_doc:
                # Display document details
                with st.expander("Document Details", expanded=True):
                    metadata = selected_doc.get("metadata", {})
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        st.markdown(f"**Filename:** {selected_doc.get('filename', '')}")
                        st.markdown(f"**Document ID:** {selected_doc.get('document_id', '')}")
                        st.markdown(f"**Upload Date:** {format_timestamp(selected_doc.get('upload_date', ''))}")
                    
                    with col2:
                        st.markdown(f"**Chunk Count:** {selected_doc.get('chunk_count', 0)}")
                        st.markdown(f"**Tags:** {', '.join(metadata.get('tags', []))}")
                    
                    st.markdown("**Description:**")
                    st.markdown(metadata.get("description", "No description provided."))
                
                # Get document chunks
                try:
                    doc_chunks = api.get_document_chunks(selected_doc_id)
                    chunks = doc_chunks.get("chunks", [])
                    
                    if chunks:
                        with st.expander("Document Chunks", expanded=False):
                            st.markdown(f"**Total Chunks:** {len(chunks)}")
                            
                            # Display chunks with pagination
                            chunk_index = st.selectbox(
                                "Select chunk to view",
                                options=list(range(len(chunks))),
                                format_func=lambda i: f"Chunk {i+1}"
                            )
                            
                            if chunk_index is not None and chunk_index < len(chunks):
                                chunk = chunks[chunk_index]
                                st.markdown(f"**Chunk {chunk_index+1}:**")
                                st.text_area(
                                    "Content",
                                    value=chunk.get("content", ""),
                                    height=200,
                                    disabled=True
                                )
                except APIError as e:
                    st.warning(f"Could not load document chunks: {str(e)}")
                
                # Delete document button
                if st.button("Delete Document", key=f"delete_{selected_doc_id}"):
                    try:
                        # Confirm deletion
                        if st.checkbox("Confirm deletion", key=f"confirm_delete_{selected_doc_id}"):
                            # Delete document
                            api.delete_document(selected_doc_id)
                            st.success(f"Document '{selected_doc.get('filename', '')}' deleted successfully.")
                            st.rerun()
                    except APIError as e:
                        st.error(f"Error deleting document: {str(e)}")
    
    except APIError as e:
        st.error(f"Error loading documents: {str(e)}")
    except Exception as e:
        st.error(f"Unexpected error: {str(e)}")


def render_upload_form(api):
    """
    Render the document upload form.
    
    Args:
        api: API client instance
    """
    st.markdown("### Upload Document")
    st.markdown(
        """
        Upload a document to be processed and added to the RAG system. 
        The document will be chunked and stored in semantic memory.
        """
    )
    
    # Create the upload form
    with st.form("upload_form"):
        # File uploader
        uploaded_file = st.file_uploader(
            "Choose a file",
            type=["pdf", "txt", "csv", "docx", "xlsx", "pptx", "html", "md"],
            help="Upload a document to be processed and added to the RAG system."
        )
        
        # Document metadata
        description = st.text_area(
            "Document Description",
            help="Add a description to help identify this document."
        )
        
        tags = st.text_input(
            "Tags (comma-separated)",
            help="Add tags to categorize this document."
        )
        
        # Advanced options in an expander
        with st.expander("Advanced Options", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                chunk_size = st.number_input(
                    "Chunk Size",
                    min_value=100,
                    max_value=5000,
                    value=1000,
                    help="Size of text chunks in characters."
                )
            
            with col2:
                chunk_overlap = st.number_input(
                    "Chunk Overlap",
                    min_value=0,
                    max_value=1000,
                    value=200,
                    help="Overlap between chunks in characters."
                )
        
        # Submit button
        submitted = st.form_submit_button("Upload Document")
        
        if submitted and uploaded_file is not None:
            with st.spinner("Uploading and processing document..."):
                try:
                    # Upload the document
                    result = api.upload_document(
                        file=uploaded_file,
                        description=description,
                        chunk_size=chunk_size,
                        chunk_overlap=chunk_overlap,
                        tags=tags
                    )
                    
                    st.success(f"Document uploaded successfully: {result.get('filename')}")
                    st.json(result)
                    
                    # Clear the upload form - does not work, but we'll keep this for future Streamlit versions
                    # st.rerun()
                    
                except APIError as e:
                    st.error(f"Failed to upload document: {str(e)}")
                except Exception as e:
                    st.error(f"Unexpected error: {str(e)}")
    
    # Document upload tips
    st.markdown("### Supported Document Types")
    st.markdown(
        """
        - PDF (`.pdf`)
        - Text (`.txt`)
        - Microsoft Word (`.docx`, `.doc`)
        - Microsoft Excel (`.xlsx`, `.xls`)
        - Microsoft PowerPoint (`.pptx`, `.ppt`)
        - CSV (`.csv`)
        - HTML (`.html`, `.htm`)
        - Markdown (`.md`)
        """
    )


def render_search_interface(api):
    """
    Render the document search interface.
    
    Args:
        api: API client instance
    """
    st.markdown("### Search Documents")
    st.markdown(
        """
        Search for documents and chunks in the RAG system using semantic search.
        This uses the same vector embeddings that power the chatbot's responses.
        """
    )
    
    # Search form
    query = st.text_input("Search query")
    search_button = st.button("Search Documents")
    
    if search_button and query:
        with st.spinner("Searching documents..."):
            try:
                # Search documents
                results = api.search_documents(query)
                
                documents = results.get("documents", [])
                document_count = results.get("document_count", 0)
                
                if document_count == 0:
                    st.info("No documents found matching your query.")
                else:
                    st.success(f"Found {document_count} documents matching your query.")
                    
                    # Display document results
                    for i, doc in enumerate(documents):
                        with st.expander(f"{doc.get('filename', f'Document {i+1}')} - {len(doc.get('chunks', []))} chunks", expanded=i == 0):
                            st.markdown(f"**Document ID:** {doc.get('document_id', '')}")
                            st.markdown(f"**Description:** {doc.get('description', 'No description')}")
                            
                            # Display chunks with relevance scores
                            st.markdown("**Matching Chunks:**")
                            
                            for j, chunk in enumerate(doc.get("chunks", [])):
                                score = chunk.get("relevance_score", 0)
                                score_percentage = int(score * 100) if isinstance(score, float) else "N/A"
                                
                                st.markdown(f"**Chunk {j+1}** (Relevance: {score_percentage}%):")
                                st.text_area(
                                    f"Content {j+1}",
                                    value=chunk.get("content", ""),
                                    height=150,
                                    key=f"chunk_{i}_{j}",
                                    disabled=True
                                )
            
            except APIError as e:
                st.error(f"Error searching documents: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    render_document_manager()