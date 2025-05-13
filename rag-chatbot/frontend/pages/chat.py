# filepath: frontend/pages/chat.py
"""
Main chat page for the Streamlit frontend.

This module defines the main chat page of the application, which is the first
page users see when accessing the app.
"""
import streamlit as st
import sys
import os

# Add parent directory to path to import components
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from components.chat import render_chat_interface
from utils.api import get_api_client


# Configure page settings
st.set_page_config(
    page_title="Memory-Enhanced RAG Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Page initialization
def main():
    """Initialize and render the main chat page."""
    # Check API connectivity
    api = get_api_client()
    
    if not api.is_connected():
        st.error("""
        ⚠️ **Cannot connect to backend API**
        
        Please make sure the backend server is running and accessible at the correct URL.
        
        Current backend URL: `{}`
        
        You can change this by setting the `BACKEND_URL` environment variable.
        """.format(api.base_url))
        
        # Show retry button
        if st.button("Retry Connection"):
            st.rerun()
            
        # Show instructions for starting the backend
        with st.expander("How to start the backend"):
            st.markdown("""
            You can start the backend using Docker Compose:
            
            ```bash
            docker-compose up -d
            ```
            
            Or run it directly:
            
            ```bash
            cd backend
            uvicorn app.main:app --host 0.0.0.0 --port 8000
            ```
            """)
            
        return
    
    # Render the chat interface
    render_chat_interface()
    
    # Show about information in the sidebar
    with st.sidebar:
        st.markdown("---")
        st.markdown("### About")
        st.markdown(
            """
            **Memory-Enhanced RAG Chatbot**
            
            This chatbot demonstrates multiple memory systems:
            
            - **Short-term Memory**: Recent conversation context (Redis)
            - **Semantic Memory**: Document knowledge (ChromaDB)
            - **Episodic Memory**: Past conversation history (MongoDB)
            - **Procedural Memory**: Action workflows (Neo4j)
            
            The system implements Multi-Context Processing to combine information from different memory sources.
            
            [View GitHub Repository](https://github.com/yourusername/memory-enhanced-rag)
            """
        )


if __name__ == "__main__":
    main()