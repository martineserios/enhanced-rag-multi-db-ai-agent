# filepath: frontend/pages/document_manager.py
import os
import json
import requests
import streamlit as st
import pandas as pd
from datetime import datetime

# API settings
API_URL = os.environ.get("BACKEND_URL", "http://backend:8000")

# Configure page settings
st.set_page_config(
    page_title="Manage Documents - RAG Chatbot",
    page_icon="📄",
    layout="wide"
)

st.title("Manage Documents")
st.markdown(
    """
    Upload and manage documents for the RAG system. These documents will be processed, 
    chunked, and stored in the vector database for retrieval during chat.
    """
)

# Fetch documents
@st.cache_data(ttl=60)  # Cache for 60 seconds
def fetch_documents():
    try:
        response = requests.get(f"{API_URL}/api/documents")
        if response.status_code == 200:
            # The backend returns a list, not a dict
            return response.json()
        else:
            st.error(f"Failed to fetch documents: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return []

# Document upload form
st.markdown("### Upload Document")
with st.form("upload_form"):
    uploaded_file = st.file_uploader(
        "Choose a file",
        type=["pdf", "txt", "csv", "docx", "xlsx", "pptx", "html", "md"],
        help="Upload a document to be processed and added to the RAG system."
    )
    
    description = st.text_area(
        "Document Description",
        help="Add a description to help identify this document."
    )
    
    submitted = st.form_submit_button("Upload Document")
    
    if submitted and uploaded_file is not None:
        # Create a temporary file
        with st.spinner("Uploading and processing document..."):
            # Prepare the form data
            files = {"file": (uploaded_file.name, uploaded_file, uploaded_file.type)}
            form_data = {"description": description}
            
            try:
                # Call the API
                response = requests.post(
                    f"{API_URL}/api/documents/upload", 
                    files=files,
                    data=form_data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    st.success(f"Document uploaded successfully: {result.get('filename')}")
                    st.cache_data.clear()  # Clear the cache to refresh the document list
                else:
                    st.error(f"Failed to upload document: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")

# Display documents table
st.markdown("### Document Library")
documents = fetch_documents()
st.write("Fetched documents:", documents)

if documents:
    # Convert to DataFrame for display
    df = pd.DataFrame(documents)
    
    # Format timestamps if they exist
    if "upload_date" in df.columns:
        df["upload_date"] = df["upload_date"].apply(
            lambda x: datetime.fromtimestamp(x).strftime("%Y-%m-%d %H:%M:%S") if isinstance(x, (int, float)) else x
        )
    
    # Display the table
    st.dataframe(df, use_container_width=True)
    
    # Document deletion
    st.markdown("### Delete Document")
    
    # Get list of document IDs and filenames
    document_options = {doc["filename"]: doc["document_id"] for doc in documents}
    
    selected_document = st.selectbox(
        "Select document to delete",
        options=list(document_options.keys())
    )
    
    if st.button("Delete Document"):
        document_id = document_options[selected_document]
        
        with st.spinner(f"Deleting document {selected_document}..."):
            try:
                response = requests.delete(f"{API_URL}/api/documents/{document_id}")
                
                if response.status_code == 200:
                    st.success(f"Document '{selected_document}' deleted successfully.")
                    st.cache_data.clear()  # Clear the cache to refresh the document list
                    st.rerun()  # Rerun the page to update the UI
                else:
                    st.error(f"Failed to delete document: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")
else:
    st.info("No documents have been uploaded yet. Use the form above to upload documents.")

# Add info about supported document types
st.markdown("---")
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