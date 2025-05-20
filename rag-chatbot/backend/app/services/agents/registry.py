"""
Agent registry for managing available chat agents.

This module provides a central registry for all available chat agents.
It allows for dynamic registration and discovery of agent implementations.
"""
from typing import Dict, Type, List, Any
from .base import BaseAgent
from app.config import get_settings
from app.core.logging import get_logger

logger = get_logger(__name__)

class AgentRegistry:
    """Registry for managing available chat agents"""
    
    _agents: Dict[str, Type[BaseAgent]] = {}
    
    @classmethod
    def register(cls, agent_class: Type[BaseAgent]) -> None:
        """
        Register a new agent type.
        
        Args:
            agent_class: The agent class to register
            
        Raises:
            ValueError: If an agent with the same ID is already registered
        """
        try:
            # Temporarily instantiate to get the agent_id string
            temp_agent_instance = agent_class(get_settings()) # Pass settings instance
            agent_id = temp_agent_instance.agent_id
        except Exception as e:
            logger.error(f"Failed to instantiate agent class {agent_class.__name__} for registration: {e}", exc_info=True)
            # If instantiation fails, we cannot get the ID reliably, skip registration
            return

        logger.info(f"Registering agent with ID: {agent_id}", extra={"agent_id": agent_id})
        if agent_id in cls._agents:
            logger.warning(f"Agent with ID '{agent_id}' is already registered. Skipping registration.", extra={"agent_id": agent_id})
            return
        cls._agents[agent_id] = agent_class
        logger.info(f"Successfully registered agent: {agent_id}", extra={"agent_id": agent_id})
    
    @classmethod
    def unregister(cls, agent_id: str) -> None:
        """
        Unregister an agent type.
        
        Args:
            agent_id: The ID of the agent to unregister
            
        Raises:
            KeyError: If no agent with the given ID is registered
        """
        logger.info(f"Attempting to unregister agent with ID: {agent_id}")
        if agent_id not in cls._agents:
            logger.warning(f"Attempted to unregister unknown agent ID: {agent_id}", extra={"agent_id": agent_id})
            raise KeyError(f"No agent with ID '{agent_id}' is registered")
        del cls._agents[agent_id]
        logger.info(f"Successfully unregistered agent: {agent_id}", extra={"agent_id": agent_id})
    
    @classmethod
    def get_agent_class(cls, agent_id: str) -> Type[BaseAgent]:
        """
        Get agent class by ID.
        
        Args:
            agent_id: The ID of the agent to get
            
        Returns:
            The agent class
            
        Raises:
            KeyError: If no agent with the given ID is registered
        """
        logger.info(f"Attempting to get agent class for ID: {agent_id}")
        if agent_id not in cls._agents:
            logger.error(f"Agent ID '{agent_id}' not found in registry.", extra={"agent_id": agent_id})
            raise KeyError(f"No agent with ID '{agent_id}' is registered")
        logger.info(f"Successfully retrieved agent class for ID: {agent_id}", extra={"agent_id": agent_id})
        return cls._agents[agent_id]
    
    @classmethod
    def list_agents(cls) -> List[Dict[str, Any]]:
        """
        List all available agents with their metadata.
        
        Returns:
            List of dictionaries containing agent metadata
        """
        logger.info("Listing all registered agents.")
        settings = get_settings()
        
        agents = []
        for agent_class in cls._agents.values():
            # Create an instance to access properties
            try:
                agent = agent_class(settings)
                agents.append({
                    "id": agent.agent_id,
                    "name": agent.agent_name,
                    "description": agent.agent_description,
                    "settings_schema": agent.agent_settings_schema
                })
                logger.debug(f"Successfully listed agent: {agent.agent_id}")
            except Exception as e:
                logger.error(f"Error listing agent {agent_class.__name__}: {str(e)}", extra={"agent_class": agent_class.__name__, "error": str(e)})
        logger.info(f"Finished listing agents. Found {len(agents)} agents.")
        return agents
    
    @classmethod
    def is_registered(cls, agent_id: str) -> bool:
        """
        Check if an agent is registered.
        
        Args:
            agent_id: The ID of the agent to check
            
        Returns:
            True if the agent is registered, False otherwise
        """
        logger.debug(f"Checking if agent ID is registered: {agent_id}")
        return agent_id in cls._agents 