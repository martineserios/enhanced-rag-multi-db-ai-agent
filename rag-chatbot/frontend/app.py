# filepath: frontend/app.py
import os
import json
import requests
import streamlit as st
from datetime import datetime
import pandas as pd

# Import our logging utilities
from utils.logging import setup_logging, get_logger, log_execution_time
from components.chat import render_chat_interface, render_agent_sidebar_settings # Import necessary function
from utils.api import get_api_client, APIError # Import APIError

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

if "agents_info" not in st.session_state:
    try:
        response = requests.get(f"{API_URL}/api/chat/agents")
        if response.status_code == 200:
            st.session_state.agents_info = response.json()
        else:
            st.error(f"Failed to get agents: {response.text}")
            st.session_state.agents_info = {"agents": [], "default_agent_id": "standard"}
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        st.session_state.agents_info = {"agents": [], "default_agent_id": "standard"}

if "selected_agent_id" not in st.session_state:
    st.session_state.selected_agent_id = st.session_state.agents_info.get("default_agent_id", "standard")

if "agent_settings" not in st.session_state:
    st.session_state.agent_settings = {}

# Sidebar for settings
st.sidebar.title("Memory-Enhanced RAG Chatbot")
st.sidebar.markdown("---")

# Agent selection
agents_info = st.session_state.agents_info
available_agents = agents_info.get("agents", [])
default_agent_id = agents_info.get("default_agent_id", "standard")

if not available_agents:
    st.sidebar.error("No agents available. Please check your backend configuration.")
    st.stop()

# Create a mapping of agent IDs to their display names
agent_options = {agent["id"]: agent["name"] for agent in available_agents}

# Agent selection dropdown
selected_agent_id = st.sidebar.selectbox(
    "Chat Agent",
    options=list(agent_options.keys()),
    format_func=lambda x: agent_options.get(x, x),
    index=list(agent_options.keys()).index(st.session_state.get("selected_agent_id", default_agent_id)) if st.session_state.get("selected_agent_id", default_agent_id) in agent_options else 0,
    help="Select which chat agent to use"
)

# Update selected agent in session state
st.session_state.selected_agent_id = selected_agent_id

# Get agent settings and graph data if they've changed
if selected_agent_id != st.session_state.get("last_selected_agent_id"):
    try:
        response = requests.get(f"{API_URL}/api/chat/agents/{selected_agent_id}/settings")
        if response.status_code == 200:
            st.session_state.agent_settings = response.json()
            st.session_state.last_selected_agent_id = selected_agent_id
        else:
            st.error(f"Failed to get agent settings: {response.text}")
            st.session_state.agent_settings = {}
    except Exception as e:
        st.error(f"Error getting agent settings: {str(e)}")

    # Also fetch graph data here when agent changes
    try:
        api = get_api_client() # Ensure api client is available
        graph_data = api.get_agent_graph(selected_agent_id)
        st.session_state.agent_graph_data = graph_data
    except APIError as e:
        st.sidebar.warning(f"Could not load agent graph: {str(e)}")
        st.session_state.agent_graph_data = None
    except Exception as e:
        st.sidebar.warning(f"An unexpected error occurred while loading agent graph: {str(e)}")
        st.session_state.agent_graph_data = None

# Call the dedicated function from chat.py to render sidebar settings and graph
with st.sidebar:
    render_agent_sidebar_settings()

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
render_chat_interface() # Call the main chat interface function