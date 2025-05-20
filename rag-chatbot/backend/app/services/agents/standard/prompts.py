"""
Prompt templates for the standard agent.

This module defines the prompt templates used by the standard agent
for generating responses to user queries.
"""
from typing import Dict, Any, Optional, List
from app.services.agents.base import BasePromptTemplate

class StandardPromptTemplate(BasePromptTemplate):
    """Prompt template for the standard agent."""
    
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the standard agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        # Base system prompt
        prompt = (
            "You are a helpful AI assistant that provides accurate and informative "
            "responses. You have access to various sources of information including "
            "memory, databases, and knowledge bases. Use this information to provide "
            "the most helpful and accurate responses possible."
        )
        
        # Add context if provided
        if context:
            prompt += (
                "\n\nYou have access to the following information that may help answer "
                "the user's question. Use this information if relevant, but you don't "
                "have to use it all:\n\n"
                f"{context}"
            )
        
        # Add any additional instructions based on settings
        if settings:
            if settings.get("use_memory", True):
                prompt += (
                    "\n\nYou can use information from previous conversations stored in "
                    "memory to provide more contextually relevant responses."
                )
            if settings.get("use_sql", True):
                prompt += (
                    "\n\nYou can query SQL databases to find relevant information. "
                    "When using database information, cite the source appropriately."
                )
            if settings.get("use_mongo", True):
                prompt += (
                    "\n\nYou can query MongoDB collections to find relevant information. "
                    "When using database information, cite the source appropriately."
                )
        
        return prompt
    
    def format_context(
        self,
        source: str,
        content: str,
        relevance: float = 1.0
    ) -> str:
        """
        Format context information for inclusion in the prompt.
        
        Args:
            source: The source of the context (e.g. "Memory", "SQL Database")
            content: The context content
            relevance: Relevance score for the context (0.0 to 1.0)
            
        Returns:
            Formatted context string
        """
        return f"## {source} (Relevance: {relevance:.2f})\n{content}\n"
    
    def format_user_message(
        self,
        message: str,
        **kwargs
    ) -> str:
        """
        Format a user message for inclusion in the prompt.
        
        Args:
            message: The user's message
            **kwargs: Additional parameters for message formatting
            
        Returns:
            Formatted user message
        """
        return f"User: {message}" 