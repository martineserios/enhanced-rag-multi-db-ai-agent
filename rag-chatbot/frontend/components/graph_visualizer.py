"""
Graph visualization component for the Streamlit UI.

This module provides visualization of agent graphs using Mermaid diagrams.
"""
import streamlit as st
import graphviz
from typing import Dict, Any, Optional
import copy

def generate_mermaid_graph(graph_data: Dict[str, Any]) -> str:
    """
    Generate a Mermaid diagram from the graph data.
    
    Args:
        graph_data: Dictionary containing graph structure and metadata
        
    Returns:
        str: Mermaid diagram syntax
    """
    # Start with graph definition
    mermaid = "graph TD\n"
    
    # Add nodes
    nodes = graph_data.get("nodes", {})
    for node_id, node_info in nodes.items():
        # Format node label with any additional info
        label = node_info.get("name", node_id)
        if node_info.get("description"):
            label += f"\n{node_info['description']}"
        
        # Add node with styling
        style = node_info.get("style", "")
        mermaid += f'    {node_id}["{label}"]{style}\n'
    
    # Add edges
    edges = graph_data.get("edges", [])
    for edge in edges:
        from_node = edge["from"]
        to_node = edge["to"]
        label = edge.get("label", "")
        
        # Add edge with optional label
        if label:
            mermaid += f"    {from_node} -->|{label}| {to_node}\n"
        else:
            mermaid += f"    {from_node} --> {to_node}\n"
    
    return mermaid

def get_langgraph_node_type(node_id: str, node_info: Dict[str, Any]) -> str:
    """
    Determine the LangGraph node type based on node ID and information.
    
    Args:
        node_id: The ID of the node
        node_info: Information about the node
        
    Returns:
        str: The node type classification
    """
    # First check if the type is explicitly set
    if "type" in node_info:
        return node_info["type"]
    
    # Try to infer from node name/description/ID
    node_name = node_info.get("name", "").lower()
    node_desc = node_info.get("description", "").lower()
    node_id_lower = node_id.lower()
    
    # Common LangGraph node type patterns
    if any(x in node_id_lower or x in node_name or x in node_desc for x in ["router", "decide", "branch", "choose"]):
        return "router"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["error", "exception", "fail"]):
        return "error"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["action", "tool", "function", "api", "call"]):
        return "action"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["input", "start", "begin", "entry"]):
        return "input"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["output", "end", "finish", "complete", "done"]):
        return "output"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["memory", "state", "store", "context"]):
        return "memory"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["process", "transform", "convert"]):
        return "process"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["conditional", "check", "if", "validate"]):
        return "conditional"
    elif any(x in node_id_lower or x in node_name or x in node_desc for x in ["human", "user", "interact"]):
        return "human"
    
    # Default fallback
    return "default"

def generate_dot_graph(graph_data: Dict[str, Any], theme: str = "Default") -> str:
    """
    Generate an aesthetically enhanced Graphviz DOT string from the graph data.
    
    Args:
        graph_data: Dictionary containing graph structure and metadata
        theme: Color theme to apply (Default, Dark, Pastel, Bold)
    Returns:
        str: Graphviz DOT syntax
    """
    # Start with graph definition and global attributes
    dot = 'digraph finite_state_machine {\n'
    dot += '  rankdir=TB;\n'  # Top-to-bottom layout
    dot += '  bgcolor="transparent";\n'  # Transparent background
    
    # Apply theme-specific global settings
    if theme == "Dark":
        dot += '  node [style="filled,rounded", fontname="Arial", fontsize=12, fontcolor="#FFFFFF", margin="0.38,0.38"];\n'
        dot += '  edge [color="#7f8c8d", fontname="Arial", fontsize=10, fontcolor="#DDDDDD", penwidth=1.2];\n'
    else:
        dot += '  node [style="filled,rounded", fontname="Arial", fontsize=12, fontcolor="#333333", margin="0.38,0.38"];\n'
        dot += '  edge [color="#666666", fontname="Arial", fontsize=10, fontcolor="#555555", penwidth=1.2];\n'
    
    # Define color schemes based on LangGraph node types for each theme
    node_type_colors = {
        "Default": {
            "router": "#3498db",      # Blue
            "action": "#2ecc71",      # Green
            "input": "#9b59b6",       # Purple
            "output": "#f39c12",      # Orange
            "error": "#e74c3c",       # Red
            "memory": "#1abc9c",      # Turquoise
            "process": "#34495e",     # Dark blue
            "conditional": "#f1c40f", # Yellow
            "human": "#e67e22",       # Darker orange
            "default": "#95a5a6"      # Gray
        },
        "Dark": {
            "router": "#3498db",      # Blue
            "action": "#2ecc71",      # Green
            "input": "#9b59b6",       # Purple
            "output": "#f39c12",      # Orange
            "error": "#e74c3c",       # Red
            "memory": "#1abc9c",      # Turquoise
            "process": "#7f8c8d",     # Light gray
            "conditional": "#f1c40f", # Yellow
            "human": "#e67e22",       # Darker orange
            "default": "#34495e"      # Dark blue
        },
        "Pastel": {
            "router": "#D6EAF8",      # Light blue
            "action": "#D5F5E3",      # Light green
            "input": "#EBDEF0",       # Light purple
            "output": "#FCF3CF",      # Light yellow
            "error": "#FADBD8",       # Light red
            "memory": "#D1F2EB",      # Light turquoise
            "process": "#D6DBDF",     # Light gray
            "conditional": "#F9E79F", # Light yellow
            "human": "#F6DDCC",       # Light orange
            "default": "#EAEDED"      # Light gray
        },
        "Bold": {
            "router": "#3498db",      # Blue
            "action": "#2ecc71",      # Green
            "input": "#9b59b6",       # Purple
            "output": "#f39c12",      # Orange
            "error": "#e74c3c",       # Red
            "memory": "#1abc9c",      # Turquoise
            "process": "#34495e",     # Dark blue
            "conditional": "#f1c40f", # Yellow
            "human": "#e67e22",       # Darker orange
            "default": "#95a5a6"      # Gray
        }
    }
    
    # Set border colors for each theme
    border_colors = {
        "Default": "#2c3e50",
        "Dark": "#3498db",
        "Pastel": "#95a5a6",
        "Bold": "#2c3e50"
    }
    
    # Add nodes with enhanced styling
    nodes = graph_data.get("nodes", {})
    for node_id, node_info in nodes.items():
        label = node_info.get("name", node_id)
        description = node_info.get("description", "")
        
        # Determine the LangGraph node type
        langgraph_type = get_langgraph_node_type(node_id, node_info)
        
        # Format the label with HTML for better text formatting
        html_label = f'<<TABLE BORDER="0" CELLBORDER="0" CELLSPACING="0" CELLPADDING="4">'
        html_label += f'<TR><TD><B>{label}</B></TD></TR>'
        if description:
            html_label += f'<TR><TD>{description}</TD></TR>'
        html_label += '</TABLE>>'
        
        # Get color based on LangGraph node type and theme
        node_color = node_info.get("color")
        if not node_color:
            node_color = node_type_colors[theme].get(langgraph_type, node_type_colors[theme]["default"])
        
        # Use rounded rectangle shape
        shape = node_info.get("shape", "rect")
        border_color = border_colors[theme]
        
        # Apply special styling for important nodes
        if node_info.get("important", False):
            dot += f'  {node_id} [shape={shape}, style="filled,rounded", label={html_label}, fillcolor="{node_color}", color="{border_color}", penwidth=2.0];\n'
        else:
            dot += f'  {node_id} [shape={shape}, style="filled,rounded", label={html_label}, fillcolor="{node_color}", color="{border_color}"];\n'
    
    # Add edges with better styling
    edges = graph_data.get("edges", [])
    for edge in edges:
        from_node = edge["from"]
        to_node = edge["to"]
        label = edge.get("label", "")
        edge_style = edge.get("style", "")
        
        # Get edge color based on theme or explicit setting
        edge_color = edge.get("color")
        if not edge_color:
            if theme == "Dark":
                edge_color = "#7f8c8d"
            elif theme == "Bold":
                edge_color = "#34495e"
            else:
                edge_color = "#666666"
        
        # Style based on edge type
        if edge.get("type") == "primary":
            edge_style = "bold"
            if theme == "Dark":
                edge_color = "#3498db"
            elif theme == "Bold":
                edge_color = "#e74c3c"
            else:
                edge_color = "#2980b9"
        elif edge.get("type") == "conditional":
            edge_style = "dashed"
        
        # Add edge definition with styling
        style_attr = f'style="{edge_style}"' if edge_style else ""
        dot += f'  {from_node} -> {to_node} [label="{label}", color="{edge_color}", {style_attr}];\n'
    
    dot += '}\n'
    return dot

def render_graph_visualizer(graph_data: Optional[Dict[str, Any]] = None):
    """
    Render an enhanced graph visualization component.
    
    Args:
        graph_data: Optional dictionary containing graph structure and metadata
    """
    if not graph_data:
        st.info("No graph data available for the selected agent.")
        return
    
    st.markdown("### Agent Workflow Graph")
    
    # Add options for customization (removed corner radius)
    with st.expander("Visualization Options"):
        col1, col2 = st.columns(2)
        with col1:
            direction = st.selectbox(
                "Graph Direction", 
                options=["Top to Bottom", "Left to Right"], 
                index=0
            )
        with col2:
            theme = st.selectbox(
                "Color Theme", 
                options=["Default", "Dark", "Pastel", "Bold"], 
                index=0
            )
    
    # Apply customization options
    rankdir = "TB" if direction == "Top to Bottom" else "LR"
    
    # Generate Graphviz DOT string with the selected direction and theme
    dot_diagram = generate_dot_graph(graph_data, theme)
    dot_diagram = dot_diagram.replace("rankdir=TB", f"rankdir={rankdir}")
    
    # Use Streamlit's built-in Graphviz chart rendering
    try:
        st.graphviz_chart(dot_diagram)
    except Exception as e:
        st.error(f"Error rendering graphviz chart: {e}")
        st.code(dot_diagram, language="dot")
    
    # Add download options
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            label="Download as DOT",
            data=dot_diagram,
            file_name="agent_graph.dot",
            mime="text/plain"
        )
    with col2:
        # Create a PNG download option (this requires running Graphviz)
        try:
            import graphviz
            graph = graphviz.Source(dot_diagram)
            # We'll just offer the PNG option; the actual implementation would need more work
            st.download_button(
                label="Download as PNG",
                data="Placeholder - requires server-side implementation",
                file_name="agent_graph.png",
                mime="image/png",
                disabled=True
            )
            st.caption("PNG download requires server-side implementation")
        except ImportError:
            pass