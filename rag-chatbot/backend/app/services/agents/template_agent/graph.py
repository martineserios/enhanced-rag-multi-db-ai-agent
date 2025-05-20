"""
Template Agent Graph implementation.

This module implements a LangGraph workflow template that can be used as a base
for creating new specialized agents. It provides a structured approach to
building agents with validation, processing, and response generation capabilities.
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal, Set
from datetime import datetime
import uuid
import logging
import time
import re
import json

from langgraph.graph import Graph, StateGraph, END # Import END constant
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.config import Settings
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from app.core.exceptions import ValidationError
from app.services.agents.template_agent.prompts import TemplatePromptTemplate
from app.services.database import query_postgres, query_mongo

logger = get_logger(__name__)

# Template patterns and validation rules
TEMPLATE_PATTERNS = {
    "category1": r"\b(pattern1|pattern2)\b",
    "category2": r"\b(pattern3|pattern4)\b",
    # Add more categories as needed
}

# Template-specific constants
TEMPLATE_CONSTANTS = {
    "level1": "Description of level 1",
    "level2": "Description of level 2",
    "level3": "Description of level 3",
    # Add more levels as needed
}

class TemplateChatState(TypedDict):
    """State type for the template chat graph."""
    request: ChatRequest
    conversation_id: str
    context: str
    sources: List[Dict[str, Any]]  # Information sources
    references: List[Dict[str, Any]]  # References to include
    processing_level: str  # Current processing level
    detected_terms: Dict[str, List[str]]  # Detected relevant terms
    specialized_data: List[Dict[str, Any]]  # Domain-specific data
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    next_step: Optional[Literal["process", "analyze", "generate", "store_memory", "error", "end"]]

class TemplateProcessingNode:
    """Node responsible for processing domain-specific information."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
        self.llm_service = None
        self.prompt_template = TemplatePromptTemplate()
    
    async def __call__(self, state: TemplateChatState) -> TemplateChatState:
        """Process domain-specific information based on the query."""
        request = state["request"]
        settings = state["metadata"]["settings"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Basic provider setup
            provider = request.provider.value if hasattr(request.provider, "value") else request.provider
            if not provider:
                provider = self.settings.default_llm_provider.value
            metrics["provider"] = provider
            
            # Detect domain terms (simple pattern matching)
            detected_terms = self._detect_domain_terms(request.message)
            
            sources = []
            context = ""
            specialized_data = []
            
            if self.settings.memory_enabled and request.use_memory:
                try:
                    # Initialize LLM service if needed
                    if not self.llm_service:
                        self.llm_service = get_llm_service(provider, self.settings)
                    
                    # Get domain-specific context
                    domain_context = await self.memory_manager.create_unified_context(
                        query=request.message,
                        conversation_id=state["conversation_id"],
                        memory_types=["semantic"],
                        weights={"semantic": 1.0}
                    )
                    
                    if domain_context:
                        # Add the context using the prompt template
                        context = self.prompt_template.format_context(
                            source="Domain Knowledge",
                            content=domain_context,
                            relevance=1.0
                        )
                        
                        # Get sources from memory
                        memory_sources = await self.memory_manager.get_memory_sources(
                            query=request.message,
                            conversation_id=state["conversation_id"],
                            memory_types=["semantic"]
                        )
                        
                        # Filter sources based on document type and processing level
                        sources = [
                            source for source in memory_sources
                            if source.get("document_type") in ["domain_specific", "specialized_data"]
                            and source.get("processing_level") == settings["processing_level"]
                        ]
                        
                        # Prioritize sources
                        sources = self._prioritize_sources(sources)
                        
                        # Separate specialized data
                        specialized_data = [
                            source for source in sources
                            if source.get("document_type") == "specialized_data"
                        ]
                
                except Exception as e:
                    logger.error(f"Error retrieving domain information: {str(e)}")
            
            # Get SQL and MongoDB context if requested (unchanged)
            if request.use_sql:
                try:
                    sql_results = await query_postgres(
                        question=request.message,
                        settings=settings
                    )
                    if sql_results:
                        context += self.prompt_template.format_context(
                            source="SQL Database",
                            content=sql_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying SQL database: {str(e)}")
            
            if request.use_mongo:
                try:
                    mongo_results = await query_mongo(
                        question=request.message,
                        settings=settings
                    )
                    if mongo_results:
                        context += self.prompt_template.format_context(
                            source="MongoDB",
                            content=mongo_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying MongoDB: {str(e)}")
            
            metrics["processing_time"] = time.time() - start_time
            metrics["sources_count"] = len(sources)
            metrics["specialized_data_count"] = len(specialized_data)
            
            return {
                **state,
                "detected_terms": detected_terms,
                "context": context,
                "sources": sources,
                "specialized_data": specialized_data,
                "metrics": metrics,
                "next_step": "analyze"
            }
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    def _detect_domain_terms(self, message: str) -> Dict[str, List[str]]:
        """Simple pattern-based domain term detection."""
        detected_terms = {}
        message_lower = message.lower()
        
        for category, pattern in TEMPLATE_PATTERNS.items():
            matches = list(re.finditer(pattern, message_lower))
            if matches:
                detected_terms[category] = [m.group() for m in matches]
        
        return detected_terms

    def _prioritize_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize sources based on level and relevance."""
        def get_priority_score(source: Dict[str, Any]) -> float:
            level = source.get("processing_level", "3") # Assuming a default level
            if level == "all":
                return 0.0
            try:
                # Assign a score based on the level, higher level is better
                level_score = int(level) # Assuming levels are integers or can be mapped
            except ValueError:
                level_score = 0.0 # Default score for unknown levels
            relevance = source.get("relevance", 0.0)
            # Adjust weights as needed
            return (level_score * 0.6) + (relevance * 0.4)
        
        return sorted(sources, key=get_priority_score, reverse=True)

class TemplateAnalysisNode:
    """Node responsible for analyzing processed information and preparing references."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_template = TemplatePromptTemplate()
    
    async def __call__(self, state: TemplateChatState) -> TemplateChatState:
        """Analyze processed information and prepare references based on settings."""
        settings = state["metadata"]["settings"]
        sources = state["sources"]
        specialized_data = state.get("specialized_data", [])
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Process information levels
            processed_sources = self._process_information_levels(sources)
            
            # Prepare references
            references = []
            max_references = settings.get("max_references", 3)
            
            # Include specialized data first
            for data_item in specialized_data[:max(1, max_references // 2)]:
                reference = self._create_reference(data_item, settings["reference_style"])
                references.append(reference)
            
            # Add remaining references
            remaining_slots = max_references - len(references)
            for source in processed_sources[:remaining_slots]:
                reference = self._create_reference(source, settings["reference_style"])
                references.append(reference)
            
            metrics["analysis_time"] = time.time() - start_time
            metrics["references_count"] = len(references)
            metrics["specialized_data_referenced"] = len([r for r in references if r.get("type") == "specialized_data"])
            
            return {
                **state,
                "references": references,
                "metrics": metrics,
                "next_step": "generate"
            }
            
        except Exception as e:
            logger.error(f"Analysis error: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    def _process_information_levels(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate information levels of sources."""
        processed = []
        
        for source in sources:
            level = source.get("processing_level", "3") # Assuming a default level
            
            # Validate information level (assuming levels are strings or can be validated)
            # if level not in VALID_LEVELS and level != "all": # Need to define VALID_LEVELS for this agent
            #     logger.warning(f"Invalid processing level {level} for source {source.get('title')}")
            #     continue
            
            # Add level description (if applicable)
            # source["level_description"] = TEMPLATE_CONSTANTS.get(level, "Unknown level") # Assuming TEMPLATE_CONSTANTS contains level descriptions
            processed.append(source)
        
        return processed
    
    def _create_reference(self, source: Dict[str, Any], style: str) -> Dict[str, Any]:
        """Create a reference for a source in the specified style."""
        # This needs to be implemented based on the specific reference styles for this template agent
        reference_text = self._format_reference(source, style)
        
        return {
            "title": source.get("title", "Unknown Title"),
            "type": source.get("type", "Unknown Type"),
            "level": source.get("processing_level", "Unknown Level"),
            "reference": reference_text,
            "metadata": source.get("metadata", {})
        }
    
    def _format_reference(self, source: Dict[str, Any], style: str) -> str:
        """Format reference according to specified style."""
        # This needs to be implemented based on the specific reference styles for this template agent
        title = source.get("title", "Unknown Title")
        level = source.get("processing_level", "Unknown Level")
        # Add logic for different styles based on 'style' parameter
        return f"{title} [Level {level}]"

class TemplateResponseNode:
    """Node responsible for generating responses based on processed information."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_template = TemplatePromptTemplate()
        self.llm_service = None
    
    async def __call__(self, state: TemplateChatState) -> TemplateChatState:
        """Generate a response based on processed information."""
        request = state["request"]
        settings = state["metadata"]["settings"]
        detected_terms = state["detected_terms"]
        specialized_data = state.get("specialized_data", [])
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = metrics.get("provider")
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Prepare context
            context = state["context"]
            
            if specialized_data:
                context += "\n\nSpecialized Data:\n" + "\n".join(
                    f"- {item.get('title', 'Unknown Title')}: {item.get('content', '')[:200]}..."
                    for item in specialized_data[:2]
                )
            
            if state["references"]:
                context += "\n\nReferences:\n" + "\n".join(
                    f"{i+1}. {reference.get('reference', 'Unknown Reference')}"
                    for i, reference in enumerate(state["references"])
                )
            
            # Generate system prompt
            system_prompt = self.prompt_template.get_system_prompt(
                context=context,
                settings={
                    **settings,
                    "detected_terms": detected_terms,
                    "has_specialized_data": bool(specialized_data)
                }
            )
            
            # Generate response
            response = await self.llm_service.generate_response(
                query=request.message,
                context=context,
                system_prompt=system_prompt
            )
            
            metrics["response_generation_time"] = time.time() - start_time
            metrics["response_length"] = len(response)
            
            next_step = "store_memory" if self.settings.memory_enabled and state["request"].use_memory else "end"
            
            return {
                **state,
                "response": response,
                "metrics": metrics,
                "next_step": next_step
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class TemplateMemoryStorageNode:
    """Node responsible for storing conversation in memory."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None

    async def __call__(self, state: TemplateChatState) -> TemplateChatState:
        """Store the conversation in memory if enabled."""
        if not self.settings.memory_enabled or not state["request"].use_memory:
            return {**state, "next_step": "end"}

        metrics = state.get("metrics", {})
        start_time = time.time()

        try:
            # Prepare content and metadata for storage
            content = {
                "user_message": state["request"].message,
                "assistant_message": state["response"],
                "agent_id": state["metadata"].get("agent_id", "template_agent"),
                "detected_terms": state.get("detected_terms", {}),
                "references": state.get("references", [])
            }

            metadata = {
                "provider": metrics.get("provider"),
                "timestamp": datetime.utcnow().isoformat(),
                "sources_count": metrics.get("sources_count", 0),
                "references_count": metrics.get("references_count", 0),
                "agent_id": state["metadata"].get("agent_id", "template_agent"),
                "agent_name": state["metadata"].get("agent_name", "Template Agent")
            }

            conversation_id = state["conversation_id"]
            key = f"conversation:{conversation_id}:message:{uuid.uuid4()}"

            # Use the memory manager to store the conversation
            await self.memory_manager.store_memory(
                memory_type="episodic",  # Store in episodic memory
                content=content,
                key=key,
                metadata=metadata,
                conversation_id=conversation_id
            )

            metrics["memory_storage_time"] = time.time() - start_time
            return {**state, "metrics": metrics, "next_step": "end"}

        except Exception as e:
            logger.error(f"Error storing conversation in memory: {str(e)}")
            # Don't fail the request if memory storage fails, just proceed to end
            return {**state, "next_step": "end"}


class TemplateErrorHandlerNode:
    """Node responsible for handling errors and preparing an error response."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def __call__(self, state: TemplateChatState) -> TemplateChatState:
        """Handle the error and prepare the state for termination."""
        error_message = state.get("error", "An unknown error occurred.")
        logger.error(f"Handling error in Template Agent: {error_message}")

        # Prepare the state for termination, including the error message in the response
        return {**state, "next_step": "end", "response": f"An error occurred: {error_message}"}


def router(state: TemplateChatState) -> Literal["store_memory", "error_handler", "end"]:
    """Route to next node based on state."""
    if state.get("error"):
        return "error_handler"
    if state["next_step"] == "store_memory":
        return "store_memory"
    return "end"

def create_template_agent_graph(settings: Settings) -> Graph:
    """Create the template agent graph with all nodes."""
    workflow = StateGraph(TemplateChatState)
    
    # Add nodes (without validation)
    workflow.add_node("process", TemplateProcessingNode(settings))
    workflow.add_node("analyze", TemplateAnalysisNode(settings))
    workflow.add_node("generate", TemplateResponseNode(settings))
    workflow.add_node("store_memory", TemplateMemoryStorageNode(settings))
    workflow.add_node("error_handler", TemplateErrorHandlerNode(settings))
    
    # Define edges
    workflow.add_edge("process", "analyze")
    workflow.add_edge("analyze", "generate")
    workflow.add_conditional_edges(
        "generate",
        router,
        {
            "store_memory": "store_memory",
            "error_handler": "error_handler",
            "end": END
        }
    )
    workflow.add_edge("store_memory", END)
    workflow.add_edge("error_handler", END)
    
    # Set entry point to process node
    workflow.set_entry_point("process")
    
    return workflow.compile() 