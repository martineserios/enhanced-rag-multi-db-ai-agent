# filepath: frontend/components/memory_explorer.py
"""
Memory explorer component for the Streamlit UI.

This module provides a memory exploration interface for viewing and
understanding the different memory systems in the chatbot.
"""
import os
import json
import requests
import streamlit as st
import pandas as pd
from datetime import datetime
from typing import Dict, List, Any, Optional

from utils.api import get_api_client, APIError
from utils.formatters import format_timestamp, truncate_text


def render_memory_explorer():
    """
    Render the memory exploration interface.
    
    This function:
    1. Provides an overview of the memory systems
    2. Allows querying different memory types
    3. Visualizes how memory systems interact
    4. Demonstrates Multi-Context Processing
    """
    st.title("Memory Explorer")
    st.markdown(
        """
        Explore the different memory systems in the RAG chatbot. This interface allows you to:
        
        - View the contents of short-term memory (conversation context)
        - Search episodic memory (past conversations)
        - Explore procedural memory (action workflows)
        - Test multi-context processing by querying all memory types
        """
    )
    
    # Initialize API client
    api = get_api_client()
    
    # Get memory types info
    try:
        memory_types = api.get_memory_types()
        memory_enabled = memory_types.get("enabled", False)
        
        if not memory_enabled:
            st.warning("Memory systems are not enabled in the backend.")
            st.stop()
    except APIError as e:
        st.error(f"Error getting memory types: {str(e)}")
        memory_types = {"enabled": False, "types": {}}
    
    # Create tabs for memory exploration
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🔄 Multi-Context Query", 
        "📊 Memory Overview", 
        "⏱️ Short-term Memory", 
        "📜 Episodic Memory",
        "📋 Procedural Memory"
    ])
    
    with tab1:
        render_multi_context_query(api)
    
    with tab2:
        render_memory_overview(api, memory_types)
    
    with tab3:
        render_short_term_memory(api)
    
    with tab4:
        render_episodic_memory(api)
    
    with tab5:
        render_procedural_memory(api)


def render_multi_context_query(api):
    """
    Render the multi-context query interface.
    
    Args:
        api: API client instance
    """
    st.markdown("### Multi-Context Query")
    st.markdown(
        """
        This demonstrates Multi-Context Processing by querying all memory systems at once.
        Enter a query below to see how information is retrieved from different memory types
        and combined into a unified context.
        """
    )
    
    # Create query form
    query = st.text_input("Enter a query to search across all memory types")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        conversation_id = st.text_input(
            "Conversation ID (optional)",
            help="Provide a conversation ID to include context from that conversation"
        )
    
    with col2:
        search_button = st.button("Search All Memory")
    
    if search_button and query:
        with st.spinner("Searching across all memory types..."):
            try:
                # Prepare parameters
                params = {"query": query}
                if conversation_id:
                    params["conversation_id"] = conversation_id
                
                # Call API
                response = api.session.get(
                    f"{api.base_url}/api/memory",
                    params=params,
                    timeout=10
                )
                response.raise_for_status()
                results = response.json().get("results", {})
                
                # Process results
                has_results = any(len(results.get(memory_type, [])) > 0 for memory_type in results)
                
                if not has_results:
                    st.info("No results found in any memory system.")
                else:
                    # Show unified context view
                    with st.expander("Unified Context View", expanded=True):
                        try:
                            # Get unified context
                            context_response = api.session.get(
                                f"{api.base_url}/api/memory/context",
                                params=params,
                                timeout=10
                            )
                            context_response.raise_for_status()
                            context_data = context_response.json()
                            
                            st.markdown("### Unified Context")
                            st.markdown(
                                """
                                This is the combined context that would be provided to the LLM
                                when generating a response to your query. It integrates information
                                from all memory systems.
                                """
                            )
                            
                            if context_data.get("context"):
                                st.text_area(
                                    "Context",
                                    value=context_data.get("context", ""),
                                    height=400,
                                    disabled=True
                                )
                                st.caption(f"Context length: {context_data.get('context_length', 0)} characters")
                            else:
                                st.info("No unified context was generated from the memory systems.")
                        except Exception as e:
                            st.warning(f"Could not retrieve unified context: {str(e)}")
                    
                    # Display results from each memory type
                    st.markdown("### Results from Memory Systems")
                    
                    # Short-term memory results
                    if results.get("short_term") and len(results["short_term"]) > 0:
                        with st.expander("⏱️ Short-term Memory Results", expanded=True):
                            st.markdown(f"Found {len(results['short_term'])} items in short-term memory.")
                            
                            for i, item in enumerate(results["short_term"]):
                                st.markdown(f"**Item {i+1}:**")
                                if "user_message" in item and "assistant_message" in item:
                                    st.markdown(f"**User:** {item['user_message']}")
                                    st.markdown(f"**Assistant:** {item['assistant_message']}")
                                else:
                                    st.markdown(f"**Content:** {item.get('content', '')}")
                                
                                if "timestamp" in item:
                                    st.caption(f"Timestamp: {format_timestamp(item['timestamp'])}")
                                
                                st.divider()
                    
                    # Semantic memory results
                    if results.get("semantic") and len(results["semantic"]) > 0:
                        with st.expander("🧠 Semantic Memory Results", expanded=True):
                            st.markdown(f"Found {len(results['semantic'])} items in semantic memory.")
                            
                            for i, item in enumerate(results["semantic"]):
                                st.markdown(f"**Document {i+1}:**")
                                st.text_area(
                                    f"Content {i+1}",
                                    value=item.get("content", ""),
                                    height=150,
                                    disabled=True
                                )
                                
                                if "relevance_score" in item:
                                    score = item["relevance_score"]
                                    score_percentage = f"{int(score * 100)}%" if isinstance(score, float) else "N/A"
                                    st.caption(f"Relevance: {score_percentage}")
                                
                                if "metadata" in item:
                                    st.caption(f"Source: {item.get('metadata', {}).get('filename', 'Unknown')}")
                                
                                st.divider()
                    
                    # Episodic memory results
                    if results.get("episodic") and len(results["episodic"]) > 0:
                        with st.expander("📜 Episodic Memory Results", expanded=True):
                            st.markdown(f"Found {len(results['episodic'])} items in episodic memory.")
                            
                            for i, item in enumerate(results["episodic"]):
                                st.markdown(f"**Conversation {i+1}:**")
                                if "user_message" in item and "assistant_message" in item:
                                    st.markdown(f"**User:** {item['user_message']}")
                                    st.markdown(f"**Assistant:** {item['assistant_message']}")
                                else:
                                    st.markdown(f"**Content:** {item.get('content', '')}")
                                
                                if "timestamp" in item:
                                    st.caption(f"Timestamp: {format_timestamp(item['timestamp'])}")
                                
                                if "conversation_id" in item:
                                    st.caption(f"Conversation ID: {item['conversation_id']}")
                                
                                st.divider()
                    
                    # Procedural memory results
                    if results.get("procedural") and len(results["procedural"]) > 0:
                        with st.expander("📊 Procedural Memory Results", expanded=True):
                            st.markdown(f"Found {len(results['procedural'])} items in procedural memory.")
                            
                            for procedure in results["procedural"]:
                                if "name" in procedure:
                                    st.markdown(f"**Procedure:** {procedure['name']}")
                                
                                # Display steps
                                if "steps" in procedure:
                                    steps = procedure["steps"]
                                    st.markdown(f"**Steps ({len(steps)}):**")
                                    
                                    for i, step in enumerate(sorted(steps, key=lambda x: x.get("order", i))):
                                        st.markdown(f"{i+1}. {step.get('description', '')}")
                                
                                st.divider()
            
            except APIError as e:
                st.error(f"Error querying memory: {str(e)}")
            except Exception as e:
                st.error(f"Unexpected error: {str(e)}")


def render_memory_overview(api, memory_types):
    """
    Render an overview of all memory systems.
    
    Args:
        api: API client instance
        memory_types: Memory type information
    """
    st.markdown("### Memory Systems Overview")
    st.markdown(
        """
        This chatbot uses four distinct memory systems inspired by human cognitive architecture:
        """
    )
    
    # Check memory health
    try:
        health_response = api.session.get(f"{api.base_url}/api/memory/health", timeout=5)
        health_response.raise_for_status()
        health_data = health_response.json()
        memory_health = health_data.get("status", {})
    except Exception:
        memory_health = {}
    
    # Display memory systems info
    col1, col2 = st.columns(2)
    
    types_info = memory_types.get("types", {})
    
    with col1:
        st.markdown("#### Short-term Memory (Redis)")
        st.markdown(
            """
            Stores recent conversation context with time-based expiration.
            This allows the chatbot to maintain continuity in the current conversation.
            """
        )
        status = "Enabled ✅" if types_info.get("short_term", {}).get("enabled", False) else "Disabled ❌"
        health = "Healthy ✅" if memory_health.get("short_term", False) else "Unhealthy ❌"
        st.markdown(f"**Status:** {status} | **Health:** {health}")
        
        st.markdown("#### Episodic Memory (MongoDB)")
        st.markdown(
            """
            Records conversation history across sessions.
            This allows the chatbot to recall past interactions and learn from them.
            """
        )
        status = "Enabled ✅" if types_info.get("episodic", {}).get("enabled", False) else "Disabled ❌"
        health = "Healthy ✅" if memory_health.get("episodic", False) else "Unhealthy ❌"
        st.markdown(f"**Status:** {status} | **Health:** {health}")
    
    with col2:
        st.markdown("#### Semantic Memory (ChromaDB)")
        st.markdown(
            """
            Stores document knowledge as vector embeddings.
            This forms the foundation of RAG, enabling retrieval based on semantic similarity.
            """
        )
        status = "Enabled ✅" if types_info.get("semantic", {}).get("enabled", False) else "Disabled ❌"
        health = "Healthy ✅" if memory_health.get("semantic", False) else "Unhealthy ❌"
        st.markdown(f"**Status:** {status} | **Health:** {health}")
        
        st.markdown("#### Procedural Memory (Neo4j)")
        st.markdown(
            """
            Represents action workflows as graph structures.
            This allows the chatbot to understand and explain multi-step processes.
            """
        )
        status = "Enabled ✅" if types_info.get("procedural", {}).get("enabled", False) else "Disabled ❌"
        health = "Healthy ✅" if memory_health.get("procedural", False) else "Unhealthy ❌"
        st.markdown(f"**Status:** {status} | **Health:** {health}")
    
    # Memory weights
    st.markdown("### Memory Weights")
    st.markdown(
        """
        These weights determine the relative importance of different memory types
        when combining information for responses. Higher weights give more importance
        to that memory type.
        """
    )
    
    weights = memory_types.get("weights", {})
    
    if weights:
        # Create weight visualization
        weight_data = [
            {"Memory Type": memory_type, "Weight": weight}
            for memory_type, weight in weights.items()
        ]
        
        weights_df = pd.DataFrame(weight_data)
        
        # Create a horizontal bar chart
        st.bar_chart(weights_df.set_index("Memory Type"))
    else:
        st.info("Memory weights information not available.")


def render_short_term_memory(api):
    """
    Render the short-term memory interface.
    
    Args:
        api: API client instance
    """
    st.markdown("### Short-term Memory")
    st.markdown(
        """
        Short-term memory stores recent conversation context using Redis.
        It enables the chatbot to maintain continuity in the current conversation.
        """
    )
    
    # Get conversations for selection
    try:
        conversations = api.get_conversations().get("conversations", [])
        
        if not conversations:
            st.info("No conversations found. Start a chat to create conversation history.")
            return
        
        # Select a conversation
        selected_conversation = st.selectbox(
            "Select a conversation to view its short-term memory",
            options=[conv["conversation_id"] for conv in conversations],
            format_func=lambda x: next(
                (f"{conv['latest_message'][:30]}... ({format_timestamp(conv['latest_time'])})" 
                for conv in conversations if conv["conversation_id"] == x),
                x
            )
        )
        
        if selected_conversation:
            # Get short-term memory for the conversation
            try:
                response = api.session.get(
                    f"{api.base_url}/api/memory/short-term/{selected_conversation}",
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                memory_items = data.get("items", [])
                
                if not memory_items:
                    st.info("No short-term memory found for this conversation.")
                    return
                
                st.success(f"Found {len(memory_items)} items in short-term memory.")
                
                # Display memory items
                for i, item in enumerate(memory_items):
                    # Format timestamp
                    timestamp = format_timestamp(item.get("timestamp", ""))
                    
                    with st.expander(f"Memory Item {i+1} - {timestamp}", expanded=i == 0):
                        st.markdown(f"**User Message:**")
                        st.markdown(item.get("user_message", ""))
                        
                        st.markdown(f"**Assistant Message:**")
                        st.markdown(item.get("assistant_message", ""))
                        
                        # Display metadata if available
                        if "metadata" in item and item["metadata"]:
                            st.markdown("**Metadata:**")
                            st.json(item["metadata"])
            
            except Exception as e:
                st.error(f"Error retrieving short-term memory: {str(e)}")
    
    except APIError as e:
        st.error(f"Error retrieving conversations: {str(e)}")


def render_episodic_memory(api):
    """
    Render the episodic memory interface.
    
    Args:
        api: API client instance
    """
    st.markdown("### Episodic Memory")
    st.markdown(
        """
        Episodic memory stores past conversation history in MongoDB.
        It enables the chatbot to recall past interactions across sessions.
        """
    )
    
    # Search options
    search_type = st.radio(
        "Search by",
        options=["Conversation ID", "Keyword"],
        horizontal=True
    )
    
    if search_type == "Conversation ID":
        # Get conversations for selection
        try:
            conversations = api.get_conversations().get("conversations", [])
            
            if not conversations:
                st.info("No conversations found. Start a chat to create conversation history.")
                return
            
            # Select a conversation
            selected_conversation = st.selectbox(
                "Select a conversation",
                options=[conv["conversation_id"] for conv in conversations],
                format_func=lambda x: next(
                    (f"{conv['latest_message'][:30]}... ({format_timestamp(conv['latest_time'])})" 
                    for conv in conversations if conv["conversation_id"] == x),
                    x
                )
            )
            
            if st.button("Search Episodic Memory") and selected_conversation:
                # Get episodic memory for the conversation
                try:
                    response = api.session.get(
                        f"{api.base_url}/api/memory/episodic",
                        params={"conversation_id": selected_conversation},
                        timeout=10
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    render_episodic_results(data)
                
                except Exception as e:
                    st.error(f"Error retrieving episodic memory: {str(e)}")
        
        except APIError as e:
            st.error(f"Error retrieving conversations: {str(e)}")
    
    else:  # Keyword search
        # Keyword search form
        keyword = st.text_input("Enter keyword to search for")
        
        if st.button("Search Episodic Memory") and keyword:
            # Search episodic memory by keyword
            try:
                response = api.session.get(
                    f"{api.base_url}/api/memory/episodic",
                    params={"keyword": keyword},
                    timeout=10
                )
                response.raise_for_status()
                data = response.json()
                
                render_episodic_results(data)
            
            except Exception as e:
                st.error(f"Error searching episodic memory: {str(e)}")


def render_episodic_results(data):
    """
    Render episodic memory search results.
    
    Args:
        data: Episodic memory search results
    """
    memory_items = data.get("items", [])
    
    if not memory_items:
        st.info("No episodic memory found matching the criteria.")
        return
    
    st.success(f"Found {len(memory_items)} items in episodic memory.")
    
    # Create a DataFrame for display
    df_data = []
    for item in memory_items:
        df_data.append({
            "Timestamp": format_timestamp(item.get("timestamp", "")),
            "User Message": truncate_text(item.get("user_message", ""), 50),
            "Assistant Message": truncate_text(item.get("assistant_message", ""), 50),
            "Conversation ID": truncate_text(item.get("conversation_id", ""), 10)
        })
    
    if df_data:
        st.dataframe(
            pd.DataFrame(df_data),
            use_container_width=True,
            hide_index=True
        )
    
    # Display full items in expanders
    for i, item in enumerate(memory_items):
        # Format timestamp
        timestamp = format_timestamp(item.get("timestamp", ""))
        
        with st.expander(f"Memory Item {i+1} - {timestamp}", expanded=i == 0):
            st.markdown(f"**User Message:**")
            st.markdown(item.get("user_message", ""))
            
            st.markdown(f"**Assistant Message:**")
            st.markdown(item.get("assistant_message", ""))
            
            st.markdown(f"**Conversation ID:** {item.get('conversation_id', '')}")
            
            # Display metadata if available
            if "metadata" in item and item["metadata"]:
                st.markdown("**Metadata:**")
                st.json(item["metadata"])


def render_procedural_memory(api):
    """
    Render the procedural memory interface.
    
    Args:
        api: API client instance
    """
    st.markdown("### Procedural Memory")
    st.markdown(
        """
        Procedural memory stores step-by-step processes as graph structures in Neo4j.
        It enables the chatbot to understand and explain multi-step procedures.
        """
    )
    
    # List known procedures
    known_procedures = ["document_upload", "database_query", "chat_process"]
    
    # Procedure selection
    procedure_name = st.selectbox(
        "Select a procedure to view",
        options=known_procedures
    )
    
    if st.button("View Procedure") and procedure_name:
        # Get procedural memory for the selected procedure
        try:
            response = api.session.get(
                f"{api.base_url}/api/memory/procedural/{procedure_name}",
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            procedure = data.get("procedure", {})
            
            if not procedure:
                st.info(f"No procedure found with name '{procedure_name}'.")
                return
            
            # Display procedure
            st.success(f"Retrieved procedure: {procedure_name}")
            
            # Get steps
            steps = procedure.get("steps", [])
            
            if steps:
                # Sort steps by order
                sorted_steps = sorted(steps, key=lambda x: x.get("order", 0))
                
                # Display as a process
                st.markdown(f"### {procedure_name.replace('_', ' ').title()} Procedure")
                
                for i, step in enumerate(sorted_steps):
                    st.markdown(
                        f"**Step {i+1}:** {step.get('description', '')}"
                    )
                    
                    if "action" in step and step["action"]:
                        st.caption(f"Action: {step['action']}")
                
                # Display as a flowchart
                st.markdown("### Procedure Flowchart")
                
                # Create a mermaid flowchart
                mermaid_code = """
                graph TD;
                    classDef start fill:#d4edda,stroke:#28a745,stroke-width:2px;
                    classDef process fill:#cce5ff,stroke:#007bff,stroke-width:2px;
                    classDef end fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
                """
                
                # Add nodes
                for i, step in enumerate(sorted_steps):
                    node_id = f"step{i}"
                    label = step.get("description", f"Step {i+1}")
                    # Replace quotes in label
                    label = label.replace('"', "'")
                    mermaid_code += f'\n    {node_id}["{label}"];'
                
                # Add connections
                for i in range(len(sorted_steps) - 1):
                    mermaid_code += f"\n    step{i} --> step{i+1};"
                
                # Add styling
                mermaid_code += f"\n    class step0 start;"
                for i in range(1, len(sorted_steps) - 1):
                    mermaid_code += f"\n    class step{i} process;"
                if len(sorted_steps) > 1:
                    mermaid_code += f"\n    class step{len(sorted_steps) - 1} end;"
                
                st.code(mermaid_code, language="mermaid")
            
            else:
                st.warning(f"Procedure '{procedure_name}' has no steps defined.")
        
        except Exception as e:
            st.error(f"Error retrieving procedural memory: {str(e)}")
    
    # Form for creating a new procedure
    with st.expander("Create New Procedure", expanded=False):
        st.markdown("### Create a New Procedure")
        st.markdown(
            """
            Define a new step-by-step procedure to store in procedural memory.
            This allows the chatbot to learn new processes.
            """
        )
        
        with st.form("new_procedure_form"):
            # Procedure name
            new_procedure_name = st.text_input(
                "Procedure Name",
                help="A unique identifier for this procedure (use lowercase and underscores)"
            )
            
            # Steps (dynamic list)
            steps = []
            step_count = st.number_input(
                "Number of Steps",
                min_value=1,
                max_value=10,
                value=3
            )
            
            for i in range(step_count):
                st.markdown(f"**Step {i+1}**")
                col1, col2 = st.columns([3, 1])
                
                with col1:
                    description = st.text_input(
                        f"Description {i+1}",
                        key=f"description_{i}"
                    )
                
                with col2:
                    action = st.text_input(
                        f"Action {i+1}",
                        key=f"action_{i}"
                    )
                
                steps.append({
                    "description": description,
                    "action": action,
                    "order": i
                })
            
            # Metadata
            metadata = st.text_area(
                "Metadata (JSON)",
                value="{\n  \"author\": \"User\",\n  \"category\": \"Custom\"\n}",
                help="Optional metadata as JSON"
            )
            
            # Submit button
            submitted = st.form_submit_button("Create Procedure")
            
            if submitted:
                if not new_procedure_name:
                    st.error("Procedure name is required")
                elif not all(step["description"] for step in steps):
                    st.error("All steps must have a description")
                else:
                    try:
                        # Parse metadata JSON
                        try:
                            metadata_dict = json.loads(metadata)
                        except json.JSONDecodeError:
                            metadata_dict = {}
                        
                        # Prepare procedure data
                        procedure_data = {
                            "name": new_procedure_name,
                            "steps": steps,
                            "metadata": metadata_dict
                        }
                        
                        # Create procedure
                        response = api.session.post(
                            f"{api.base_url}/api/memory/procedural",
                            json=procedure_data,
                            timeout=10
                        )
                        response.raise_for_status()
                        result = response.json()
                        
                        st.success(f"Procedure '{new_procedure_name}' created successfully!")
                        st.json(result)
                    
                    except Exception as e:
                        st.error(f"Error creating procedure: {str(e)}")


if __name__ == "__main__":
    render_memory_explorer()