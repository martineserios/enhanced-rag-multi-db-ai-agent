"""
Prompt templates for the standard graph-based agent.

This module defines the prompt templates used by the standard graph-based agent
for generating responses to user queries.
"""
from typing import Dict, Any, Optional, List
from app.services.agents.base import BasePromptTemplate

class StandardGraphPromptTemplate(BasePromptTemplate):
    """Prompt template for the standard graph agent."""
    
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the standard graph agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        # Base system prompt
        prompt = (
            "You are a sophisticated AI assistant that uses advanced reasoning and "
            "task decomposition to provide accurate and informative responses. You have "
            "access to various sources of information including memory, databases, and "
            "knowledge bases. You can break down complex questions into simpler steps "
            "and use multiple sources of information to build comprehensive answers."
        )
        
        # Add context if provided
        if context:
            prompt += (
                "\n\nYou have access to the following information that may help answer "
                "the user's question. Analyze this information carefully and use it to "
                "build a comprehensive response:\n\n"
                f"{context}"
            )
        
        # Add any additional instructions based on settings
        if settings:
            if settings.get("use_memory", True):
                prompt += (
                    "\n\nYou can use information from previous conversations stored in "
                    "memory to provide more contextually relevant responses. When using "
                    "memory, consider both recent conversations and relevant historical "
                    "information."
                )
            if settings.get("use_sql", True):
                prompt += (
                    "\n\nYou can query SQL databases to find relevant information. "
                    "When using database information, cite the source appropriately and "
                    "explain how the data supports your response."
                )
            if settings.get("use_mongo", True):
                prompt += (
                    "\n\nYou can query MongoDB collections to find relevant information. "
                    "When using database information, cite the source appropriately and "
                    "explain how the data supports your response."
                )
        
        # Add graph-specific instructions
        prompt += (
            "\n\nYou are part of a graph-based conversation system that can handle "
            "complex reasoning and task decomposition. You can use this capability to:"
            "\n1. Break down complex questions into simpler steps"
            "\n2. Use multiple sources of information to build comprehensive answers"
            "\n3. Validate information from different sources"
            "\n4. Provide well-structured and detailed responses"
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
        return (
            f"## {source} (Relevance: {relevance:.2f})\n"
            f"Content:\n{content}\n"
            f"Analysis: This information has a relevance score of {relevance:.2f} "
            "to the current query. Consider this when incorporating it into your response.\n"
        )
    
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
        # Add any additional context from kwargs
        context = kwargs.get("context", "")
        if context:
            return f"User Query: {message}\nAdditional Context: {context}"
        return f"User Query: {message}" 