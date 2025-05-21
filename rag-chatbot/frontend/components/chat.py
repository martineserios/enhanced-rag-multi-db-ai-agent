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
from components.graph_visualizer import render_graph_visualizer


def render_chat_interface():
    """
    Render the main chat interface (chat history and input).
    """
    st.title("Memory-Enhanced RAG Chatbot")

    # Initialize API client (if not already done in app.py)
    api = get_api_client()

    # Display chat messages
    for message in st.session_state.get("messages", []) :
        avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            # Display message content
            st.markdown(message["content"])

            # For assistant messages, show agent info and memory sources
            if message["role"] == "assistant":
                # Show agent info if available
                if message.get("agent_name"): # Check if agent_name exists in message metadata
                    st.caption(f"Agent: {message['agent_name']}")

                # Show memory sources if enabled from session state
                if st.session_state.get("show_memory_details", False) and message.get("memory_sources"):
                    with st.expander("Memory Sources Used"):
                        # Ensure memory_sources is a dictionary before creating DataFrame
                        memory_sources_data = message.get("memory_sources", {})
                        if isinstance(memory_sources_data, dict):
                            memory_df = pd.DataFrame([
                                {"Memory Type": k, "Used": "✅" if v else "❌"}
                                for k, v in memory_sources_data.items()
                            ])
                            st.dataframe(memory_df, hide_index=True)
                        else:
                            st.warning("Unexpected format for memory sources.") # Optional warning

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
                    "conversation_id": st.session_state.get("conversation_id"), # Get from session state
                    "provider": st.session_state.get("selected_provider"), # Get from session state
                    "agent_id": st.session_state.get("selected_agent_id"), # Get from session state
                    "agent_settings": st.session_state.get("current_agent_settings", {})  # Include current agent settings from session state
                }

                # Send request to API using the API client from session state or initialized here
                api = get_api_client() # Ensure api client is available
                response = api.chat(request_data)

                # Update conversation ID if it's new
                if not st.session_state.get("conversation_id"):
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

                # Display memory details if enabled (check session state)
                if st.session_state.get("show_memory_details", False) and response.get("memory_sources"):
                     with st.expander("Memory Sources Used"):
                        # Ensure memory_sources is a dictionary before creating DataFrame
                        memory_sources_data = response.get("memory_sources", {})
                        if isinstance(memory_sources_data, dict):
                            memory_df = pd.DataFrame([
                                {"Memory Type": k, "Used": "✅" if v else "❌"}
                                for k, v in memory_sources_data.items()
                            ])
                            st.dataframe(memory_df, hide_index=True)
                        else:
                            st.warning("Unexpected format for memory sources in response.") # Optional warning

            except APIError as e:
                message_placeholder.error(f"Error: {str(e)}")
            except Exception as e:
                message_placeholder.error(f"Unexpected error: {str(e)}")

def render_agent_sidebar_settings():
    """
    Render the agent-specific settings and graph visualization in the sidebar.
    This function assumes agent information, settings, and graph data are
    available in st.session_state.
    """
    # Retrieve data from session state
    agents_info = st.session_state.get("agents_info")
    selected_agent_id = st.session_state.get("selected_agent_id")
    agent_settings = st.session_state.get("agent_settings")
    agent_graph_data = st.session_state.get("agent_graph_data")

    if not agents_info or not selected_agent_id:
        st.info("Select an agent to view settings and workflow.")
        return

    # Display agent graph visualization if available
    if agent_graph_data:
        st.markdown("---")
        render_graph_visualizer(agent_graph_data)

    # Display agent-specific settings
    if agent_settings:
        st.markdown("---")
        agent_info = agent_settings # Use fetched agent_settings directly
        st.markdown(f"### {agent_info.get('agent_name', 'Agent Settings')} Settings")

        # Get the settings schema and current settings
        schema = agent_info.get("settings_schema", {}) # Corrected key
        current_settings = agent_info.get("settings", {}) or {}

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

        # Store current settings in session state to be used in chat requests
        st.session_state.current_agent_settings = current_settings

        # Create settings controls based on the schema
        for group_name, settings_list in settings_groups.items():
            if settings_list:
                st.markdown(f"#### {group_name}")

                for prop_name in settings_list:
                    prop_schema = schema.get("properties", {}).get(prop_name, {})
                    if not prop_schema:
                        continue

                    # Use st.sidebar for controls
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
                            index=prop_schema.get("enum", []).index(current_settings.get(prop_name, prop_schema.get("default", prop_schema.get("enum", [""])[0])))
                             if current_settings.get(prop_name, prop_schema.get("default")) in prop_schema.get("enum", []) else 0,
                            help=prop_schema.get("description", "")
                        )

# Ensure the main chat interface function is not called when this module is imported
if __name__ == "__main__":
    render_chat_interface()