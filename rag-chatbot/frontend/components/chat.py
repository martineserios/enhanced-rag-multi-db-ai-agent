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
    
    if "memory_types" not in st.session_state:
        try:
            st.session_state.memory_types = api.get_memory_types()
        except APIError as e:
            st.error(f"Error getting memory types: {str(e)}")
            st.session_state.memory_types = {"enabled": False, "types": {}}
    
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
                        st.caption(f"{format_timestamp(conv['latest_time'])} · {conv['message_count']} messages")
                    
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
                                        "memory_sources": msg.get("memory_sources", {})
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
        
        # Data source options
        st.markdown("### Data Sources")
        use_rag = st.checkbox("Use RAG (Vector Database)", value=True)
        use_sql = st.checkbox("Query SQL Database", value=False)
        use_mongo = st.checkbox("Query MongoDB", value=False)
        
        # Memory system options
        memory_types = st.session_state.memory_types
        if memory_types.get("enabled", False):
            st.markdown("### Memory Systems")
            use_memory = st.checkbox("Use Memory", value=True)
            
            if use_memory:
                memory_options = {}
                
                for memory_type, info in memory_types.get("types", {}).items():
                    if info.get("enabled", False):
                        memory_options[memory_type] = st.checkbox(
                            f"{info.get('name', memory_type)}",
                            value=True,
                            help=info.get('description', '')
                        )
                
                show_memory_details = st.checkbox(
                    "Show Memory Details", 
                    value=False,
                    help="Display which memory systems were used in each response"
                )
            else:
                memory_options = {memory_type: False for memory_type in memory_types.get("types", {})}
                show_memory_details = False
        else:
            use_memory = False
            memory_options = {}
            show_memory_details = False
    
    # Display chat messages
    for message in st.session_state.messages:
        avatar = "🧑‍💻" if message["role"] == "user" else "🤖"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"])
            
            # Show memory sources if enabled
            if show_memory_details and message.get("memory_sources"):
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
                memory_types_list = [
                    memory_type for memory_type, enabled in memory_options.items() if enabled
                ] if use_memory else []
                
                request_data = {
                    "message": prompt,
                    "conversation_id": st.session_state.conversation_id,
                    "provider": selected_provider,
                    "use_rag": use_rag,
                    "use_sql": use_sql,
                    "use_mongo": use_mongo,
                    "use_memory": use_memory,
                    "memory_types": memory_types_list if memory_types_list else None
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
                    "memory_sources": response.get("memory_sources", {})
                })
                
                # Display memory details if enabled
                if show_memory_details and response.get("memory_sources"):
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