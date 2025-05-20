"""
Chat agents package.

This package provides different implementations of chat agents,
each with its own approach to processing conversations.
"""

from .base import BaseAgent, AgentError, AgentConfigurationError, AgentProcessingError
from .factory import AgentFactory
from .registry import AgentRegistry
from app.core.logging import get_logger

logger = get_logger(__name__)

# Removed agent import and registration logic - now handled in main.py

__all__ = [
    "BaseAgent",
    "AgentError",
    "AgentConfigurationError",
    "AgentProcessingError",
    "AgentFactory",
    "AgentRegistry",
    # Removed individual agent imports from __all__ as they are now imported in main.py
    # "StandardAgent",
    # "StandardGraphAgent",
    # "MedicalResearchAgent",
    # "TemplateAgent"
] 