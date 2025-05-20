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
    index=list(agent_options.keys()).index(st.session_state.selected_agent_id) if st.session_state.selected_agent_id in agent_options else 0,
    help="Select which chat agent to use"
)

# Update selected agent in session state
st.session_state.selected_agent_id = selected_agent_id

# Get agent settings if they've changed
if selected_agent_id != st.session_state.get("last_selected_agent_id"):
    try:
        response = requests.get(f"{API_URL}/api/chat/agents/{selected_agent_id}/settings")
        if response.status_code == 200:
            st.session_state.agent_settings = response.json()
            st.session_state.last_selected_agent_id = selected_agent_id
        else:
            st.error(f"Failed to get agent settings: {response.text}")
    except Exception as e:
        st.error(f"Error getting agent settings: {str(e)}")

# Display agent-specific settings
if st.session_state.agent_settings:
    agent_info = st.session_state.agent_settings
    st.sidebar.markdown(f"### {agent_info['agent_name']} Settings")
    
    # Get the settings schema and current settings
    schema = agent_info.get("schema", {})
    current_settings = agent_info.get("settings", {})
    
    # Group settings by category
    settings_groups = {
        "Memory Systems": [
            "short_term_memory",
            "semantic_memory",
            "episodic_memory",
            "procedural_memory"
        ],
        "Data Sources": [
            "use_rag",
            "use_sql",
            "use_mongo"
        ],
        "Agent Settings": []  # Will be populated with remaining settings
    }
    
    # Add remaining settings to Agent Settings group
    all_settings = set(schema.get("properties", {}).keys())
    for group in settings_groups.values():
        all_settings -= set(group)
    settings_groups["Agent Settings"] = list(all_settings)
    
    # Create settings controls based on the schema
    for group_name, settings_list in settings_groups.items():
        if settings_list:  # Only show groups that have settings
            st.sidebar.markdown(f"#### {group_name}")
            
            for prop_name in settings_list:
                prop_schema = schema.get("properties", {}).get(prop_name, {})
                if not prop_schema:
                    continue
                
                if prop_schema.get("type") == "boolean":
                    current_settings[prop_name] = st.sidebar.checkbox(
                        prop_schema.get("description", prop_name),
                        value=current_settings.get(prop_name, prop_schema.get("default", False)),
                        help=prop_schema.get("description", "")
                    )
                elif prop_schema.get("type") == "integer":
                    current_settings[prop_name] = st.sidebar.number_input(
                        prop_schema.get("description", prop_name),
                        min_value=prop_schema.get("minimum", 0),
                        max_value=prop_schema.get("maximum", 100),
                        value=current_settings.get(prop_name, prop_schema.get("default", 0)),
                        help=prop_schema.get("description", "")
                    )
                elif prop_schema.get("type") == "number":
                    current_settings[prop_name] = st.sidebar.number_input(
                        prop_schema.get("description", prop_name),
                        min_value=float(prop_schema.get("minimum", 0.0)),
                        max_value=float(prop_schema.get("maximum", 1.0)),
                        value=float(current_settings.get(prop_name, prop_schema.get("default", 0.0))),
                        step=0.1,
                        help=prop_schema.get("description", "")
                    )
                elif prop_schema.get("type") == "string" and "enum" in prop_schema:
                    current_settings[prop_name] = st.sidebar.selectbox(
                        prop_schema.get("description", prop_name),
                        options=prop_schema.get("enum", []),
                        index=prop_schema.get("enum", []).index(current_settings.get(prop_name, prop_schema.get("default", prop_schema.get("enum", [""])[0]))),
                        help=prop_schema.get("description", "")
                    )

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
if provider_info.get("enabled", False) and provider_info.get("types", {}).get("episodic_memory", False):
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
if prompt := st.chat_input("Ask a question..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    
    # Display user message
    with st.chat_message("user", avatar="🧑‍💻"):
        st.markdown(prompt)
    
    # Display assistant message with loading indicator
    with st.chat_message("assistant", avatar="🤖"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")
        
        try:
            # Prepare request data
            request_data = {
                "message": prompt,
                "conversation_id": st.session_state.conversation_id,
                "provider": selected_provider,
                "agent_id": selected_agent_id,
                "agent_settings": current_settings  # Include all agent settings
            }
            
            # Send request to API
            response = requests.post(f"{API_URL}/api/chat", json=request_data)
            response.raise_for_status()
            response_data = response.json()
            
            # Update conversation ID if it's new
            if not st.session_state.conversation_id:
                st.session_state.conversation_id = response_data.get("conversation_id")
            
            # Display the response
            message_placeholder.markdown(response_data["message"])
            
            # Add assistant message to chat history
            st.session_state.messages.append({
                "role": "assistant",
                "content": response_data["message"],
                "memory_sources": response_data.get("memory_sources", {}),
                "agent_id": response_data.get("agent_id"),
                "agent_name": response_data.get("agent_name")
            })
            
            # Display memory details if enabled
            if st.session_state.show_memory_details and response_data.get("memory_sources"):
                with st.expander("Memory Sources Used"):
                    memory_df = pd.DataFrame([
                        {"Memory Type": k, "Used": "✅" if v else "❌"} 
                        for k, v in response_data.get("memory_sources", {}).items()
                    ])
                    st.dataframe(memory_df, hide_index=True)
            
        except requests.exceptions.RequestException as e:
            message_placeholder.error(f"Error: {str(e)}")
        except Exception as e:
            message_placeholder.error(f"Unexpected error: {str(e)}")