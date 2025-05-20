"""
Factory for creating chat agent instances.

This module provides a factory for creating instances of chat agents.
It uses the agent registry to look up agent classes and creates instances
with the appropriate settings.
"""
from typing import Dict, Any
from app.config import Settings, get_settings
from .base import BaseAgent, AgentError
from .registry import AgentRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

class AgentFactory:
    """Factory for creating chat agent instances"""
    
    @staticmethod
    def create_agent(agent_id: str, settings: Settings) -> BaseAgent:
        """
        Create an instance of a chat agent.
        
        Args:
            agent_id: The ID of the agent to create
            settings: Application settings to pass to the agent
            
        Returns:
            An instance of the requested agent
            
        Raises:
            AgentError: If the agent cannot be created
        """
        logger.info(f"Attempting to create agent with ID: {agent_id}")
        try:
            agent_class = AgentRegistry.get_agent_class(agent_id)
            return agent_class(settings)
        except KeyError as e:
            logger.error(f"Unknown agent ID encountered: {agent_id}", extra={"agent_id": agent_id})
            raise AgentError(f"Unknown agent ID: {agent_id}") from e
        except Exception as e:
            logger.error(f"Error creating agent {agent_id}: {str(e)}", extra={"agent_id": agent_id, "error": str(e)})
            raise AgentError(f"Error creating agent {agent_id}: {str(e)}") from e
    
    @staticmethod
    def get_default_agent(settings: Settings) -> BaseAgent:
        """
        Get the default agent instance.
        
        Args:
            settings: Application settings to pass to the agent
            
        Returns:
            An instance of the default agent
            
        Raises:
            AgentError: If no default agent is configured or cannot be created
        """
        default_agent_id = getattr(settings, "default_agent_id", "standard")
        logger.info(f"Getting default agent with ID: {default_agent_id}")
        return AgentFactory.create_agent(default_agent_id, settings)
    
    @staticmethod
    def list_available_agents() -> Dict[str, Any]:
        """
        Get information about available agents.
        
        Returns:
            Dictionary with agent information
        """
        settings = get_settings()
        agents = AgentRegistry.list_agents()
        
        return {
            "agents": agents,
            "default_agent_id": getattr(settings, "default_agent_id", "standard")
        }