# filepath: frontend/pages/memory_explorer.py
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
    page_title="Memory Explorer - RAG Chatbot",
    page_icon="🧠",
    layout="wide"
)

st.title("Memory Explorer")
st.markdown(
    """
    Explore the different memory systems in the RAG chatbot. This page allows you to:
    
    - View the contents of short-term memory (conversation context)
    - Search episodic memory (past conversations)
    - Explore procedural memory (action workflows)
    - Test multi-context processing by running a combined memory query
    """
)

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
        elif hasattr(timestamp_str, 'isoformat'):
            return timestamp_str.strftime("%Y-%m-%d %H:%M:%S")
    except:
        pass
    return str(timestamp_str)

# Check if memory is enabled
memory_types = get_memory_types()
if not memory_types.get("enabled", False):
    st.warning("Memory systems are not enabled in the chatbot.")
    st.stop()

# Get conversations
@st.cache_data(ttl=60)  # Cache for 60 seconds
def get_conversations():
    try:
        response = requests.get(f"{API_URL}/api/chat/conversations")
        if response.status_code == 200:
            conversations = response.json().get("conversations", [])
            # Format timestamps
            for conv in conversations:
                if "latest_time" in conv:
                    conv["latest_time"] = format_timestamp(conv["latest_time"])
            return conversations
        else:
            st.error(f"Failed to get conversations: {response.text}")
            return []
    except Exception as e:
        st.error(f"Error connecting to backend: {str(e)}")
        return []

conversations = get_conversations()

# Create tabs for different memory types
tab1, tab2, tab3, tab4 = st.tabs([
    "🔄 Multi-Context Query", 
    "⏱️ Short-term Memory", 
    "📜 Episodic Memory",
    "📊 Procedural Memory"
])

with tab1:
    st.markdown("### Multi-Context Memory Query")
    st.markdown(
        """
        Test the Multi-Context Processing capability by running a query across all memory systems.
        This simulates how the chatbot combines information from different memory types.
        """
    )
    
    col1, col2 = st.columns([3, 1])
    with col1:
        query = st.text_input("Enter query to search across all memory types:")
    
    with col2:
        conversation_id = st.selectbox(
            "Conversation (optional):",
            options=["None"] + [conv["conversation_id"] for conv in conversations],
            format_func=lambda x: "None" if x == "None" else x[:8] + "..."
        )
    
    if st.button("Search All Memory Types"):
        if not query:
            st.warning("Please enter a query.")
        else:
            with st.spinner("Searching across all memory types..."):
                try:
                    params = {"query": query}
                    if conversation_id != "None":
                        params["conversation_id"] = conversation_id
                    
                    response = requests.get(f"{API_URL}/api/memory/", params=params)
                    
                    if response.status_code == 200:
                        results = response.json().get("results", {})
                        
                        has_results = any(len(results.get(k, [])) > 0 for k in results)
                        
                        if not has_results:
                            st.info("No results found in any memory system.")
                        else:
                            # Short-term memory results
                            if results.get("short_term"):
                                with st.expander("⏱️ Short-term Memory Results", expanded=True):
                                    for i, item in enumerate(results["short_term"]):
                                        st.markdown(f"**Result {i+1}:** {item['content']}")
                                        st.caption(f"Timestamp: {format_timestamp(item['timestamp'])}")
                                        st.divider()
                            
                            # Semantic memory results
                            if results.get("semantic"):
                                with st.expander("🧠 Semantic Memory Results", expanded=True):
                                    for i, item in enumerate(results["semantic"]):
                                        st.markdown(f"**Document {i+1}:**")
                                        st.text(item['content'][:300] + ("..." if len(item['content']) > 300 else ""))
                                        st.divider()
                            
                            # Episodic memory results
                            if results.get("episodic"):
                                with st.expander("📜 Episodic Memory Results", expanded=True):
                                    for i, item in enumerate(results["episodic"]):
                                        st.markdown(f"**Conversation {i+1}:** {item['content']}")
                                        st.caption(f"Timestamp: {format_timestamp(item['timestamp'])}")
                                        st.divider()
                            
                            # Procedural memory results
                            if results.get("procedural"):
                                with st.expander("📊 Procedural Memory Results", expanded=True):
                                    for i, item in enumerate(results["procedural"]):
                                        st.markdown(f"**Step {item.get('order', i+1)}:** {item['content']}")
                                        st.divider()
                    else:
                        st.error(f"Error searching memory: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab2:
    st.markdown("### Short-term Memory")
    st.markdown(
        """
        Short-term memory stores recent conversation context using Redis.
        It enables the chatbot to maintain continuity in the current conversation.
        """
    )
    
    # Conversation selection
    selected_conversation = st.selectbox(
        "Select conversation:",
        options=[conv["conversation_id"] for conv in conversations],
        format_func=lambda x: x[:8] + "..." if x else "None",
        key="st_conversation"
    )
    
    if selected_conversation:
        if st.button("View Short-term Memory"):
            with st.spinner("Loading short-term memory..."):
                try:
                    response = requests.get(f"{API_URL}/api/memory/short-term/{selected_conversation}")
                    
                    if response.status_code == 200:
                        memory_items = response.json().get("results", [])
                        
                        if not memory_items:
                            st.info("No short-term memory found for this conversation.")
                        else:
                            st.markdown(f"Found {len(memory_items)} memory items:")
                            
                            for i, item in enumerate(memory_items):
                                with st.expander(f"Memory #{i+1} - {format_timestamp(item.get('timestamp', ''))}"):
                                    st.markdown("**User Message:**")
                                    st.markdown(f"{item.get('message', 'N/A')}")
                                    st.markdown("**Response:**")
                                    st.markdown(f"{item.get('response', 'N/A')}")
                    else:
                        st.error(f"Error retrieving short-term memory: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    else:
        st.info("Select a conversation to view its short-term memory.")

with tab3:
    st.markdown("### Episodic Memory")
    st.markdown(
        """
        Episodic memory stores past conversation history in MongoDB.
        It enables the chatbot to recall past interactions across sessions.
        """
    )
    
    col1, col2 = st.columns(2)
    
    with col1:
        search_by = st.radio(
            "Search by:",
            options=["Conversation", "Keyword"],
            horizontal=True
        )
    
    with col2:
        if search_by == "Conversation":
            episodic_conversation = st.selectbox(
                "Select conversation:",
                options=[conv["conversation_id"] for conv in conversations],
                format_func=lambda x: x[:8] + "..." if x else "None",
                key="ep_conversation"
            )
            search_param = ("conversation_id", episodic_conversation)
        else:
            keyword = st.text_input("Enter keyword to search:", key="ep_keyword")
            search_param = ("keyword", keyword)
    
    if st.button("Search Episodic Memory"):
        if (search_by == "Conversation" and not episodic_conversation) or (search_by == "Keyword" and not keyword):
            st.warning(f"Please enter a {search_by.lower()} to search.")
        else:
            with st.spinner("Searching episodic memory..."):
                try:
                    param_name, param_value = search_param
                    response = requests.get(f"{API_URL}/api/memory/episodic", params={param_name: param_value})
                    
                    if response.status_code == 200:
                        results = response.json().get("results", [])
                        
                        if not results:
                            st.info("No matching conversations found in episodic memory.")
                        else:
                            st.markdown(f"Found {len(results)} conversation entries:")
                            
                            # Convert to DataFrame for display
                            df_data = []
                            for item in results:
                                df_data.append({
                                    "Timestamp": format_timestamp(item.get("timestamp", "")),
                                    "User Message": item.get("user_message", "")[:50] + ("..." if len(item.get("user_message", "")) > 50 else ""),
                                    "Bot Response": item.get("bot_response", "")[:50] + ("..." if len(item.get("bot_response", "")) > 50 else ""),
                                    "Conversation ID": item.get("conversation_id", "")[:8] + "..."
                                })
                            
                            df = pd.DataFrame(df_data)
                            st.dataframe(df, use_container_width=True)
                            
                            # Show full conversations in expanders
                            for i, item in enumerate(results):
                                with st.expander(f"Conversation {i+1} - {format_timestamp(item.get('timestamp', ''))}"):
                                    st.markdown("**User:**")
                                    st.markdown(f"{item.get('user_message', 'N/A')}")
                                    st.markdown("**Assistant:**")
                                    st.markdown(f"{item.get('bot_response', 'N/A')}")
                                    st.caption(f"Conversation ID: {item.get('conversation_id', 'N/A')}")
                    else:
                        st.error(f"Error searching episodic memory: {response.text}")
                except Exception as e:
                    st.error(f"Error: {str(e)}")

with tab4:
    st.markdown("### Procedural Memory")
    st.markdown(
        """
        Procedural memory stores action workflows in a Neo4j graph database.
        It enables the chatbot to understand and explain multi-step processes.
        """
    )
    
    # List available procedures
    procedures = ["document_upload", "database_query", "chat_process"]
    
    selected_procedure = st.selectbox(
        "Select procedure to view:",
        options=procedures
    )
    
    if st.button("View Procedure"):
        with st.spinner(f"Loading procedure '{selected_procedure}'..."):
            try:
                response = requests.get(f"{API_URL}/api/memory/procedural", params={"procedure_name": selected_procedure})
                
                if response.status_code == 200:
                    result = response.json()
                    steps = result.get("steps", [])
                    
                    if not steps:
                        st.info(f"No steps found for procedure '{selected_procedure}'.")
                    else:
                        st.markdown(f"### {selected_procedure.replace('_', ' ').title()} Procedure")
                        st.markdown(f"Found {len(steps)} steps:")
                        
                        # Display as a numbered list
                        for step in sorted(steps, key=lambda x: x.get("order", 0)):
                            st.markdown(f"**Step {step.get('order', 0) + 1}:** {step.get('description', 'N/A')}")
                            st.caption(f"Action: {step.get('action', 'N/A')}")
                            st.divider()
                        
                        # Visualize as a flowchart
                        st.markdown("### Procedure Flowchart")
                        
                        # Create Mermaid flowchart
                        mermaid_code = """
                        graph TD
                            classDef start fill:#d4edda,stroke:#28a745,stroke-width:2px;
                            classDef process fill:#cce5ff,stroke:#007bff,stroke-width:2px;
                            classDef end fill:#f8d7da,stroke:#dc3545,stroke-width:2px;
                        """
                        
                        # Add nodes
                        for step in steps:
                            step_id = f"step{step.get('order', 0)}"
                            step_desc = step.get('description', 'Step').replace('"', "'")
                            mermaid_code += f'\n    {step_id}["{step_desc}"]'
                        
                        # Add connections
                        for i in range(len(steps) - 1):
                            mermaid_code += f'\n    step{i} --> step{i+1}'
                        
                        # Add styling
                        mermaid_code += '\n    class step0 start;'
                        for i in range(1, len(steps) - 1):
                            mermaid_code += f'\n    class step{i} process;'
                        mermaid_code += f'\n    class step{len(steps) - 1} end;'
                        
                        st.code(mermaid_code, language="mermaid")
                        
                else:
                    st.error(f"Error retrieving procedure: {response.text}")
            except Exception as e:
                st.error(f"Error: {str(e)}")