# filepath: frontend/app.py
import os
import json
import requests
import streamlit as st
from datetime import datetime
import pandas as pd

# Import our logging utilities
from utils.logging import setup_logging, get_logger, log_execution_time

# Configure logging
logger = get_logger(__name__)
setup_logging(level=os.environ.get("LOG_LEVEL", "INFO"))

# Configure page settings
st.set_page_config(
    page_title="Memory-Enhanced RAG Chatbot",
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API settings
API_URL = os.environ.get("BACKEND_URL", "http://backend:8000")

@log_execution_time()
def get_providers():
    """
    Get available LLM providers from the API.
    
    Returns:
        dict: Dictionary containing provider information including:
            - providers: List of available provider names
            - default: Default provider name
            - status: Status of each provider
    """
    try:
        logger.info(f"Fetching available providers from {API_URL}/api/providers")
        response = requests.get(f"{API_URL}/api/providers")
        
        if response.status_code == 200:
            providers_data = response.json()
            logger.debug(f"Received providers data: {json.dumps(providers_data, indent=2)}")
            
            # Get default provider from environment or use first available
            default_provider = os.environ.get("DEFAULT_LLM_PROVIDER")
            if default_provider and default_provider.lower() in providers_data.get("providers", []):
                providers_data["default"] = default_provider.lower()
                logger.info(f"Using default provider from env: {default_provider}")
            elif "providers" in providers_data and providers_data["providers"]:
                providers_data["default"] = providers_data["providers"][0]
                logger.info(f"Using first available provider as default: {providers_data['default']}")
            
            return providers_data
            
        else:
            error_msg = f"Failed to get providers: {response.status_code} - {response.text}"
            logger.error(error_msg)
            st.error(error_msg)
            return {"providers": [], "default": os.environ.get("DEFAULT_LLM_PROVIDER", "openai")}
            
    except Exception as e:
        error_msg = f"Error connecting to backend: {str(e)}"
        logger.exception(error_msg)
        st.error(error_msg)
        return {"providers": [], "default": os.environ.get("DEFAULT_LLM_PROVIDER", "openai")}

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

# Ensure available_providers is a list
available_providers = provider_info.get("providers", [])
if isinstance(available_providers, dict):
    # If it's a dict, convert it to a list of keys
    available_providers = list(available_providers.keys())
    logger.warning("Providers data was in dict format, converted to list of provider names")

# Log provider information
logger.info(f"Available providers: {available_providers}")
logger.info(f"Provider info: {json.dumps(provider_info, indent=2)}")

# If no providers are available, show an error and disable the chat
if not available_providers:
    error_msg = "No LLM providers configured. Please check your backend configuration."
    logger.error(error_msg)
    st.sidebar.error(error_msg)
    st.error("No LLM providers are available. Please check your backend configuration and restart the server.")
    st.stop()

# Get default provider from provider_info or environment
default_provider = None
if "default" in provider_info and provider_info["default"] in available_providers:
    default_provider = provider_info["default"]
    logger.info(f"Using configured default provider: {default_provider}")

if not default_provider and available_providers:
    default_provider = available_providers[0]
    logger.info(f"No default provider configured, using first available: {default_provider}")

# Initialize selected_provider in session state if not exists
if "selected_provider" not in st.session_state:
    st.session_state.selected_provider = default_provider
    logger.info(f"Initialized selected_provider in session state: {st.session_state.selected_provider}")

# If the previously selected provider is no longer available, reset to default
if st.session_state.selected_provider not in available_providers:
    if default_provider:  # Only reset if we have a valid default
        logger.warning(
            f"Previously selected provider '{st.session_state.selected_provider}' "
            f"is no longer available. Resetting to default: {default_provider}"
        )
        st.session_state.selected_provider = default_provider
    else:
        st.session_state.selected_provider = available_providers[0] if available_providers else None

# Provider selection dropdown
# Safely determine the default index for the dropdown
default_index = 0
if available_providers:  # Only try to find index if we have providers
    selected = st.session_state.get("selected_provider")
    if selected and selected in available_providers:
        try:
            default_index = available_providers.index(selected)
        except (ValueError, AttributeError):
            logger.warning(f"Could not find index for provider '{selected}' in available providers")
            default_index = 0
    else:
        logger.info(f"Selected provider not found in available providers, using default index 0")

selected_provider = st.sidebar.selectbox(
    "LLM Provider",
    options=available_providers,
    index=default_index if available_providers else 0,
    help="Select the language model to use for generating responses"
)

# Update the selected provider in session state
st.session_state.selected_provider = selected_provider

# Show a warning if the default provider is not available
if default_provider and selected_provider != default_provider:
    st.sidebar.warning(f"Default provider '{default_provider}' is not available. Using '{selected_provider}' instead.")

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