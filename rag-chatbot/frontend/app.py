# filepath: frontend/app.py
import os
import json
import requests
import streamlit as st
from datetime import datetime
import pandas as pd

# Configure page settings
st.set_page_config(
    page_title="Memory-Enhanced RAG Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API settings
API_URL = os.environ.get("BACKEND_URL", "http://backend:8000")

def get_providers():
    """Get available LLM providers from the API."""
    try:
        response = requests.get(f"{API_URL}/api/providers")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get providers: {response.text}")
            return {"providers": {}, "default": "openai"}
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return {"providers": {}, "default": "openai"}

def get_memory_types():
    """Get available memory types from the API."""
    try:
        response = requests.get(f"{API_URL}/api/memory/types")
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"Failed to get memory types: {response.text}")
            return {"enabled": False, "types": {}}
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return {"enabled": False, "types": {}}

def format_timestamp(timestamp_str):
    """Format a timestamp string to a human-readable format."""
    try:
        if isinstance(timestamp_str, str):
            dt = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            return dt.strftime("%Y-%m-%d %H:%M:%S")
    except:
        pass
    return timestamp_str

# Initialize session state
if "messages" not in st.session_state:
    st.session_state.messages = []

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = None

if "providers_info" not in st.session_state:
    st.session_state.providers_info = get_providers()

if "memory_types" not in st.session_state:
    st.session_state.memory_types = get_memory_types()

if "show_memory_details" not in st.session_state:
    st.session_state.show_memory_details = False

# Sidebar for settings
st.sidebar.title("Memory-Enhanced RAG Chatbot")
st.sidebar.markdown("---")

# LLM Provider selection
provider_info = st.session_state.providers_info
available_providers = provider_info.get("providers", ["openai"])

# Default to first provider if available, else 'openai'
default_provider = available_providers[0] if available_providers else "openai"

selected_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=available_providers,
    index=available_providers.index(default_provider) if default_provider in available_providers else 0
)

# Data source options
st.sidebar.markdown("### Data Sources")
use_rag = st.sidebar.checkbox("Use RAG (Vector Database)", value=True)
use_sql = st.sidebar.checkbox("Query SQL Database", value=False)
use_mongo = st.sidebar.checkbox("Query MongoDB", value=False)

# Memory system options
memory_types = st.session_state.memory_types
if memory_types.get("enabled", False):
    st.sidebar.markdown("### Memory Systems")
    use_short_term = st.sidebar.checkbox(
        f"{memory_types['types']['short_term']['name']}",
        value=True,
        help=memory_types['types']['short_term']['description']
    )
    
    use_episodic = st.sidebar.checkbox(
        f"{memory_types['types']['episodic']['name']}",
        value=True,
        help=memory_types['types']['episodic']['description']
    )
    
    use_procedural = st.sidebar.checkbox(
        f"{memory_types['types']['procedural']['name']}",
        value=False,
        help=memory_types['types']['procedural']['description']
    )
    
    st.sidebar.markdown("### Memory Visibility")
    st.session_state.show_memory_details = st.sidebar.checkbox(
        "Show Memory Details",
        value=st.session_state.show_memory_details,
        help="Display which memory systems were used in each response"
    )
else:
    use_short_term = False
    use_episodic = False
    use_procedural = False

# About section
st.sidebar.markdown("---")
st.sidebar.markdown("### About")
st.sidebar.markdown(
    """
    This Memory-Enhanced RAG Chatbot demonstrates:
    
    - **Short-term Memory**: Remembers recent conversation
    - **Semantic Memory**: Retrieves document knowledge
    - **Episodic Memory**: Recalls past interactions
    - **Procedural Memory**: Stores action workflows
    
    Built with LangChain, FastAPI, and Multi-Context Processing.
    """
)

# Main chatbot interface
st.title("Memory-Enhanced RAG Chatbot")
st.markdown(
    """
    This advanced chatbot uses multiple memory systems to provide more contextual responses:
    
    - **Short-term Memory**: Redis-based conversation context
    - **Semantic Memory**: ChromaDB vector database for documents
    - **Episodic Memory**: MongoDB for conversation history
    - **Procedural Memory**: Neo4j graph database for workflows
    
    The system combines these memory types using Multi-Context Processing (MCP).
    """
)

# Display previous conversations
if memory_types.get("enabled", False) and use_episodic:
    try:
        # Get previous conversations
        response = requests.get(f"{API_URL}/api/chat/conversations")
        if response.status_code == 200:
            conversations = response.json().get("conversations", [])
            
            if conversations and not st.session_state.conversation_id:
                with st.expander("Previous Conversations", expanded=False):
                    for conv in conversations:
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**{conv['latest_message'][:50]}{'...' if len(conv['latest_message']) > 50 else ''}**")
                        with col2:
                            if st.button(f"Resume", key=f"resume_{conv['conversation_id']}"):
                                st.session_state.conversation_id = conv['conversation_id']
                                st.rerun()
    except Exception as e:
        st.warning(f"Could not load previous conversations: {str(e)}")

# Display chat messages
for message in st.session_state.messages:
    avatar = "🧑‍💻" if message["role"] == "user" else "🧠"
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])
        
        # Show memory sources if enabled
        if st.session_state.show_memory_details and message.get("memory_sources"):
            memory_df = pd.DataFrame([
                {"Memory Type": k, "Used": "✅" if v else "❌"} 
                for k, v in message["memory_sources"].items()
            ])
            st.dataframe(memory_df, hide_index=True)

# Chat input
if prompt := st.chat_input("Ask something..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    
    # Display thinking indicator
    with st.chat_message("assistant", avatar="🧠"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # Prepare the request
            request_data = {
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "provider": selected_provider,
                "use_rag": use_rag,
                "use_sql": use_sql,
                "use_mongo": use_mongo,
                "use_short_term_memory": use_short_term,
                "use_episodic_memory": use_episodic,
                "use_procedural_memory": use_procedural
            }
            
            # Call the API
            response = requests.post(
                f"{API_URL}/api/chat",
                json=request_data
            )
            
            if response.status_code == 200:
                result = response.json()
                
                # Update conversation ID if it's new
                if st.session_state.conversation_id is None:
                    st.session_state.conversation_id = result.get("conversation_id")
                
                # Display the response
                message_placeholder.markdown(result["message"])
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": result["message"],
                    "memory_sources": result.get("memory_sources", {})
                })
                
                # Display memory details if enabled
                if st.session_state.show_memory_details and result.get("memory_sources"):
                    memory_df = pd.DataFrame([
                        {"Memory Type": k, "Used": "✅" if v else "❌"} 
                        for k, v in result.get("memory_sources", {}).items()
                    ])
                    st.dataframe(memory_df, hide_index=True)
            else:
                message_placeholder.error(f"Error: {response.text}")
        except Exception as e:
            message_placeholder.error(f"Error: {str(e)}")