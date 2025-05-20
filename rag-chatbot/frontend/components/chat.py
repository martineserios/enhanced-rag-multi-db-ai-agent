# filepath: frontend/components/chat.py
"""
Chat component for the Streamlit UI.

This module provides the main chat interface for interacting with the
Memory-Enhanced RAG Chatbot.
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


def render_chat_interface():
    """
    Render the main chat interface.
    
    This function:
    1. Displays the chat history
    2. Handles user input
    3. Sends requests to the backend API
    4. Displays responses
    """
    st.title("Memory-Enhanced RAG Chatbot")
    
    # Initialize API client
    api = get_api_client()
    
    # Initialize session state for chat
    if "messages" not in st.session_state:
        st.session_state.messages = []
    
    if "conversation_id" not in st.session_state:
        st.session_state.conversation_id = None
        
    if "providers_info" not in st.session_state:
        try:
            st.session_state.providers_info = api.get_providers()
        except APIError as e:
            st.error(f"Error connecting to backend: {str(e)}")
            st.session_state.providers_info = {"providers": {}, "default": "groq"}
    
    if "agents_info" not in st.session_state:
        try:
            st.session_state.agents_info = api.get_agents()
        except APIError as e:
            st.error(f"Error getting agents: {str(e)}")
            st.session_state.agents_info = {"agents": [], "default_agent_id": "standard"}
    
    if "selected_agent_id" not in st.session_state:
        st.session_state.selected_agent_id = st.session_state.agents_info.get("default_agent_id", "standard")
    
    if "agent_settings" not in st.session_state:
        st.session_state.agent_settings = {}
    
    # Load previous conversations if available
    if api.is_connected() and st.session_state.conversation_id is None:
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown("### Start a new conversation or continue a previous one")
        
        with col2:
            if st.button("New Conversation", type="primary"):
                st.session_state.conversation_id = None
                st.session_state.messages = []
                st.rerun()
        
        try:
            conversations = api.get_conversations()
            if conversations and len(conversations.get("conversations", [])) > 0:
                st.markdown("### Previous Conversations")
                
                for conv in conversations.get("conversations", [])[:5]:  # Show last 5 conversations
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"**{truncate_text(conv['latest_message'], 50)}**")
                        st.caption(
                            f"{format_timestamp(conv['latest_time'])} · "
                            f"{conv['message_count']} messages · "
                            f"Agent: {conv.get('agent_name', 'Unknown')}"
                        )
                    
                    with col2:
                        if st.button("Resume", key=f"resume_{conv['conversation_id']}"):
                            # Load conversation history
                            try:
                                history = api.get_conversation_history(conv['conversation_id'])
                                
                                # Clear current messages
                                st.session_state.messages = []
                                
                                # Add messages from history (oldest first)
                                for msg in reversed(history.get("messages", [])):
                                    st.session_state.messages.append({
                                        "role": "user",
                                        "content": msg.get("user_message", "")
                                    })
                                    st.session_state.messages.append({
                                        "role": "assistant",
                                        "content": msg.get("assistant_message", ""),
                                        "memory_sources": msg.get("memory_sources", {}),
                                        "agent_id": msg.get("agent_id"),
                                        "agent_name": msg.get("agent_name")
                                    })
                                
                                # Set conversation ID
                                st.session_state.conversation_id = conv['conversation_id']
                                st.rerun()
                            except APIError as e:
                                st.error(f"Error loading conversation: {str(e)}")
        except APIError as e:
            st.warning(f"Could not load previous conversations: {str(e)}")
    
    # Sidebar for settings
    with st.sidebar:
        st.title("Settings")
        
        # LLM Provider selection
        provider_info = st.session_state.providers_info
        available_providers = [
            provider for provider, available in provider_info.get("providers", {}).items() if available
        ]
        
        if not available_providers:
            # Use the default provider from the API response if available
            default_provider = provider_info.get("default", "groq")
            available_providers = [default_provider]
        
        selected_provider = st.selectbox(
            "LLM Provider",
            options=available_providers,
            index=available_providers.index(provider_info.get("default", "groq")) 
            if provider_info.get("default", "groq") in available_providers else 0
        )
        
        # Agent selection
        agents_info = st.session_state.agents_info
        available_agents = agents_info.get("agents", [])
        default_agent_id = agents_info.get("default_agent_id", "standard")
        
        if not available_agents:
            st.error("No agents available. Please check your backend configuration.")
            st.stop()
        
        # Create a mapping of agent IDs to their display names
        agent_options = {agent["id"]: agent["name"] for agent in available_agents}
        
        # Agent selection dropdown
        selected_agent_id = st.selectbox(
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
                agent_settings = api.get_agent_settings(selected_agent_id)
                st.session_state.agent_settings = agent_settings
                st.session_state.last_selected_agent_id = selected_agent_id
            except APIError as e:
                st.error(f"Error getting agent settings: {str(e)}")
        
        # Display agent-specific settings
        if st.session_state.agent_settings:
            agent_info = st.session_state.agent_settings
            st.markdown(f"### {agent_info['agent_name']} Settings")
            
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
                    st.markdown(f"#### {group_name}")
                    
                    for prop_name in settings_list:
                        prop_schema = schema.get("properties", {}).get(prop_name, {})
                        if not prop_schema:
                            continue
                        
                        if prop_schema.get("type") == "boolean":
                            current_settings[prop_name] = st.checkbox(
                                prop_schema.get("description", prop_name),
                                value=current_settings.get(prop_name, prop_schema.get("default", False)),
                                help=prop_schema.get("description", "")
                            )
                        elif prop_schema.get("type") == "integer":
                            current_settings[prop_name] = st.number_input(
                                prop_schema.get("description", prop_name),
                                min_value=prop_schema.get("minimum", 0),
                                max_value=prop_schema.get("maximum", 100),
                                value=current_settings.get(prop_name, prop_schema.get("default", 0)),
                                help=prop_schema.get("description", "")
                            )
                        elif prop_schema.get("type") == "number":
                            current_settings[prop_name] = st.number_input(
                                prop_schema.get("description", prop_name),
                                min_value=float(prop_schema.get("minimum", 0.0)),
                                max_value=float(prop_schema.get("maximum", 1.0)),
                                value=float(current_settings.get(prop_name, prop_schema.get("default", 0.0))),
                                step=0.1,
                                help=prop_schema.get("description", "")
                            )
                        elif prop_schema.get("type") == "string" and "enum" in prop_schema:
                            current_settings[prop_name] = st.selectbox(
                                prop_schema.get("description", prop_name),
                                options=prop_schema.get("enum", []),
                                index=prop_schema.get("enum", []).index(current_settings.get(prop_name, prop_schema.get("default", prop_schema.get("enum", [""])[0]))),
                                help=prop_schema.get("description", "")
                            )
    
    # Display chat messages
    for message in st.session_state.messages:
        avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            # Display message content
            st.markdown(message["content"])
            
            # For assistant messages, show agent info and memory sources
            if message["role"] == "assistant":
                # Show agent info if available
                if message.get("agent_name"):
                    st.caption(f"Agent: {message['agent_name']}")
                
                # Show memory sources if enabled
                if current_settings.get("show_memory_details", False) and message.get("memory_sources"):
                    with st.expander("Memory Sources Used"):
                        memory_df = pd.DataFrame([
                            {"Memory Type": k, "Used": "✅" if v else "❌"} 
                            for k, v in message.get("memory_sources", {}).items()
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
                response = api.chat(request_data)
                
                # Update conversation ID if it's new
                if not st.session_state.conversation_id:
                    st.session_state.conversation_id = response.get("conversation_id")
                
                # Display the response
                message_placeholder.markdown(response["message"])
                
                # Add assistant message to chat history
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": response["message"],
                    "memory_sources": response.get("memory_sources", {}),
                    "agent_id": response.get("agent_id"),
                    "agent_name": response.get("agent_name")
                })
                
                # Display memory details if enabled
                if current_settings.get("show_memory_details", False) and response.get("memory_sources"):
                    with st.expander("Memory Sources Used"):
                        memory_df = pd.DataFrame([
                            {"Memory Type": k, "Used": "✅" if v else "❌"} 
                            for k, v in response.get("memory_sources", {}).items()
                        ])
                        st.dataframe(memory_df, hide_index=True)
                
            except APIError as e:
                message_placeholder.error(f"Error: {str(e)}")
            except Exception as e:
                message_placeholder.error(f"Unexpected error: {str(e)}")


if __name__ == "__main__":
    render_chat_interface()