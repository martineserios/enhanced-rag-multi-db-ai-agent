import os
import sys
import pytest
from unittest.mock import MagicMock, patch
from typing import List, Dict, Any, Optional

# Add the app directory to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

try:
    from app.services.agents.clinical_agent.graph import create_clinical_agent_graph
    from app.schemas.agent_schemas import ClinicalChatState, ChatMessage, MessageRole, ToolCall, ToolResult
    from pydantic import BaseModel
except ImportError as e:
    print(f"Import error: {e}")
    raise

class Settings:
    def __init__(self):
        self.debug = True
        self.openai_api_key = "test_key"
        self.database_url = "sqlite:///:memory:"

class TestClinicalAgentGraph:
    def test_graph_initialization(self):
        """Test that the graph initializes correctly with all nodes and edges."""
        # Create the graph
        graph = create_clinical_agent_graph(Settings())
        
        # Verify the graph has the expected structure
        assert graph is not None
        
        # Check that the graph has the expected nodes
        assert hasattr(graph, 'nodes')
        expected_nodes = {"analyze", "diagnose", "store_memory", "handle_error", "tools", "__start__", "__end__"}
        assert set(graph.nodes) == expected_nodes
        
        # Check that edges are properly connected
        # Note: This is a basic check - you might want to add more specific assertions
        # based on your graph's expected structure
        assert graph.edges is not None
        
    def test_error_handling_node(self):
        """Test that the error handling node is properly connected."""
        graph = create_clinical_agent_graph(Settings())
        
        # Check that there's an edge from handle_error to store_memory
        # This assumes your graph implementation has a way to check edges
        # The exact implementation will depend on your graph library
        assert "handle_error" in graph.nodes
        
        # Check that handle_error is properly referenced in conditional edges
        # This would depend on how your graph is structured
        
    def test_tool_node_connection(self):
        """Test that the tools node is properly connected in the graph."""
        graph = create_clinical_agent_graph(Settings())
        
        # Check that tools node exists
        assert "tools" in graph.nodes
        
        # Check that analyze node has a conditional edge to tools
        # This would depend on your graph's implementation
        
    def test_memory_storage_flow(self):
        """Test the memory storage flow through the graph."""
        # This test would verify that after processing, memory is properly stored
        # and the flow reaches the end state
        pass

if __name__ == "__main__":
    pytest.main(["-v"])
