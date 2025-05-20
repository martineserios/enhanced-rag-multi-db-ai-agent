"""
Medical Research Graph Agent implementation.

This module implements the LangGraph workflow for the medical research agent,
providing sophisticated medical literature processing, evidence-based responses,
and citation management with specialized medical terminology and clinical guidelines.
"""
from typing import Dict, List, Any, Optional, TypedDict, Annotated, Literal, Set
from datetime import datetime
import uuid
import logging
import time
import re
import json

from langgraph.graph import Graph, StateGraph, END
from langgraph.prebuilt import ToolNode

from app.core.logging import get_logger
from app.config import Settings
from app.api.models.chat import ChatRequest, ChatResponse
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from app.core.exceptions import ValidationError
from app.services.agents.medical_research.prompts import MedicalResearchPromptTemplate
from app.services.database import query_postgres, query_mongo

logger = get_logger(__name__)

# Medical terminology patterns and validation rules
MEDICAL_TERMS = {
    "diagnosis": r"\b(diagnos|dx|diagnosed|diagnosing)\b",
    "treatment": r"\b(treat|tx|therapy|therapeutic|medication|drug|prescription)\b",
    "symptom": r"\b(symptom|sign|manifestation|presentation|complaint)\b",
    "procedure": r"\b(procedure|surgery|operation|intervention|technique)\b",
    "anatomy": r"\b(organ|tissue|system|structure|anatomy|physiology)\b"
}

EVIDENCE_LEVELS = {
    "1": "Systematic review of randomized controlled trials",
    "2": "Randomized controlled trial",
    "3": "Non-randomized controlled trial",
    "4": "Case-control or cohort study",
    "5": "Case series or expert opinion"
}

class MedicalChatState(TypedDict):
    """State type for the medical chat graph."""
    request: ChatRequest
    conversation_id: str
    medical_context: str
    evidence_sources: List[Dict[str, Any]]  # Medical literature sources
    citations: List[Dict[str, Any]]  # Citations to include
    evidence_level: str  # Current evidence level
    medical_terms: Dict[str, List[str]]  # Detected medical terminology
    clinical_guidelines: List[Dict[str, Any]]  # Relevant clinical guidelines
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    next_step: Optional[Literal["literature", "evidence", "response", "store_memory", "error", "end"]]
    next_step: Optional[Literal["literature", "evidence", "response", "error", "end"]]

class MedicalValidationNode:
    """Node responsible for validating medical chat requests and terminology."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = None
        self.prompt_template = MedicalResearchPromptTemplate()
    
    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Validate the medical chat request and check medical terminology."""
        request = state["request"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Basic validation
            provider = request.provider.value if hasattr(request.provider, "value") else request.provider
            if not provider:
                provider = self.settings.default_llm_provider.value
            
            # Check provider API key
            api_key_attr = f"{provider}_api_key"
            if not getattr(self.settings, api_key_attr, None):
                raise ValidationError(f"{provider.capitalize()} API key is not configured")
            
            # Validate medical-specific settings
            settings = state["metadata"].get("settings", {})
            if not isinstance(settings.get("evidence_level"), str):
                raise ValidationError("Invalid evidence level setting")
            if not isinstance(settings.get("citation_style"), str):
                raise ValidationError("Invalid citation style setting")
            
            # Detect medical terminology
            medical_terms = await self._detect_medical_terminology(request.message)
            
            # Update metrics
            metrics["validation_time"] = time.time() - start_time
            metrics["provider"] = provider
            metrics["medical_terms_detected"] = len(medical_terms)
            
            return {
                **state,
                "medical_terms": medical_terms,
                "metrics": metrics,
                "next_step": "literature"
            }
            
        except Exception as e:
            logger.error(f"Medical validation error: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    async def _detect_medical_terminology(self, message: str) -> Dict[str, List[str]]:
        """Detect medical terminology in the message."""
        detected_terms = {}
        message_lower = message.lower()
        
        # Log start of detection
        logger.info(f"Starting medical terminology detection for message: {message[:100]}...")
        
        # Pattern-based detection with detailed logging
        for category, pattern in MEDICAL_TERMS.items():
            logger.debug(f"Checking medical pattern for category '{category}': {pattern}")
            matches = list(re.finditer(pattern, message_lower))
            
            if matches:
                terms = [m.group() for m in matches]
                detected_terms[category] = terms
                logger.info(
                    f"Found {len(terms)} medical terms in category '{category}': "
                    f"{', '.join(terms)}"
                )
            else:
                logger.debug(f"No medical terms found for category '{category}'")
        
        # Log summary of detection
        if detected_terms:
            total_terms = sum(len(terms) for terms in detected_terms.values())
            categories = list(detected_terms.keys())
            logger.info(
                f"Medical terminology detection complete. Found {total_terms} terms "
                f"across {len(categories)} categories: {', '.join(categories)}"
            )
        else:
            logger.info("No medical terminology detected in message")
        
        return detected_terms

class MedicalLiteratureNode:
    """Node responsible for retrieving medical literature and guidelines."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
        self.llm_service = None
        self.prompt_template = MedicalResearchPromptTemplate()
    
    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Retrieve medical literature and guidelines based on the query."""
        request = state["request"]
        settings = state["metadata"]["settings"]
        medical_terms = state["medical_terms"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            evidence_sources = []
            medical_context = ""
            clinical_guidelines = []
            
            if self.settings.memory_enabled and request.use_memory:
                try:
                    # Initialize LLM service if needed
                    if not self.llm_service:
                        provider = metrics.get("provider")
                        self.llm_service = get_llm_service(provider, self.settings)
                    
                    # Enhance query with medical terminology
                    enhanced_query = await self._enhance_query_with_terminology(
                        request.message,
                        medical_terms
                    )
                    
                    # Get medical literature context
                    literature_context = await self.memory_manager.create_unified_context(
                        query=enhanced_query,
                        conversation_id=state["conversation_id"],
                        memory_types=["semantic"],  # Use semantic memory for medical literature
                        weights={"semantic": 1.0}  # Prioritize semantic memory
                    )
                    
                    if literature_context:
                        # Process and categorize medical sources
                        for source in literature_context.get("sources", []):
                            source_data = {
                                "title": source.get("title"),
                                "type": source.get("document_type"),
                                "evidence_level": source.get("evidence_level"),
                                "content": source.get("content"),
                                "relevance": source.get("relevance", 1.0),
                                "publication_date": source.get("publication_date"),
                                "authors": source.get("authors", []),
                                "keywords": source.get("keywords", [])
                            }
                            
                            evidence_sources.append(source_data)
                            
                            # Separate clinical guidelines
                            if source.get("document_type") == "clinical_guidelines":
                                clinical_guidelines.append(source_data)
                        
                        medical_context = literature_context.get("content", "")
                        
                        # Prioritize sources based on evidence level and relevance
                        evidence_sources = self._prioritize_sources(evidence_sources)
                
                except Exception as e:
                    logger.error(f"Error retrieving medical literature: {str(e)}")
            
            # Get SQL context if requested
            if request.use_sql:
                try:
                    sql_results = await query_postgres(
                        question=request.message,
                        settings=settings
                    )
                    if sql_results:
                        medical_context += self.prompt_template.format_context(
                            source="SQL Database",
                            content=sql_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying SQL database: {str(e)}")
            
            # Get MongoDB context if requested
            if request.use_mongo:
                try:
                    mongo_results = await query_mongo(
                        question=request.message,
                        settings=settings
                    )
                    if mongo_results:
                        medical_context += self.prompt_template.format_context(
                            source="MongoDB",
                            content=mongo_results,
                            relevance=0.8
                        )
                except Exception as e:
                    logger.error(f"Error querying MongoDB: {str(e)}")
            
            metrics["literature_retrieval_time"] = time.time() - start_time
            metrics["sources_count"] = len(evidence_sources)
            metrics["guidelines_count"] = len(clinical_guidelines)
            
            return {
                **state,
                "medical_context": medical_context,
                "evidence_sources": evidence_sources,
                "clinical_guidelines": clinical_guidelines,
                "metrics": metrics,
                "next_step": "evidence"
            }
            
        except Exception as e:
            logger.error(f"Error in medical literature retrieval: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    async def _enhance_query_with_terminology(
        self,
        query: str,
        medical_terms: Dict[str, List[str]]
    ) -> str:
        """Enhance the query with detected medical terminology."""
        if not medical_terms:
            return query
        
        prompt = self.prompt_template.get_query_enhancement_prompt(
            query=query,
            terms=medical_terms
        )
        
        try:
            enhanced = await self.llm_service.generate_response(
                query=prompt,
                context="",
                system_prompt="You are a medical query enhancement specialist."
            )
            return enhanced
        except Exception as e:
            logger.warning(f"Error enhancing query: {str(e)}")
            return query
    
    def _prioritize_sources(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Prioritize sources based on evidence level and relevance."""
        def get_evidence_score(source: Dict[str, Any]) -> float:
            level = source.get("evidence_level", "5")
            if level == "all":
                return 0.0
            try:
                level_score = 6 - int(level)  # Higher levels (1-2) get higher scores
            except ValueError:
                level_score = 0.0
            relevance = source.get("relevance", 0.0)
            return (level_score * 0.7) + (relevance * 0.3)  # Weighted scoring
        
        return sorted(sources, key=get_evidence_score, reverse=True)

class MedicalEvidenceNode:
    """Node responsible for processing evidence and managing citations."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = None
        self.prompt_template = MedicalResearchPromptTemplate()
    
    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Process evidence and prepare citations based on settings."""
        settings = state["metadata"]["settings"]
        evidence_sources = state["evidence_sources"]
        clinical_guidelines = state.get("clinical_guidelines", [])
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = metrics.get("provider")
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Process and validate evidence levels
            processed_sources = await self._process_evidence_levels(evidence_sources)
            
            # Prepare citations based on style and max count
            citations = []
            max_citations = settings.get("max_citations", 5)
            
            # Include clinical guidelines first if available
            for guideline in clinical_guidelines[:max(1, max_citations // 2)]:
                citation = self._create_citation(guideline, settings["citation_style"])
                citations.append(citation)
            
            # Add remaining citations from other sources
            remaining_slots = max_citations - len(citations)
            for source in processed_sources[:remaining_slots]:
                citation = self._create_citation(source, settings["citation_style"])
                citations.append(citation)
            
            # Validate citations with LLM
            citations = await self._validate_citations(citations)
            
            metrics["evidence_processing_time"] = time.time() - start_time
            metrics["citations_count"] = len(citations)
            metrics["guidelines_cited"] = len([c for c in citations if c["type"] == "clinical_guidelines"])
            
            return {
                **state,
                "citations": citations,
                "metrics": metrics,
                "next_step": "response"
            }
            
        except Exception as e:
            logger.error(f"Error in evidence processing: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    async def _process_evidence_levels(self, sources: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Process and validate evidence levels of sources."""
        processed = []
        
        for source in sources:
            level = source.get("evidence_level", "5")
            
            # Validate evidence level
            if level not in EVIDENCE_LEVELS and level != "all":
                logger.warning(f"Invalid evidence level {level} for source {source.get('title')}")
                continue
            
            # Add evidence level description
            source["evidence_description"] = EVIDENCE_LEVELS.get(level, "Unknown evidence level")
            processed.append(source)
        
        return processed
    
    def _create_citation(self, source: Dict[str, Any], style: str) -> Dict[str, Any]:
        """Create a citation for a source in the specified style."""
        citation_text = self._format_citation(source, style)
        
        return {
            "title": source["title"],
            "type": source["type"],
            "evidence_level": source["evidence_level"],
            "evidence_description": source.get("evidence_description", ""),
            "citation": citation_text,
            "authors": source.get("authors", []),
            "publication_date": source.get("publication_date"),
            "keywords": source.get("keywords", [])
        }
    
    def _format_citation(self, source: Dict[str, Any], style: str) -> str:
        """Format citation according to specified style."""
        title = source["title"]
        level = source["evidence_level"]
        authors = source.get("authors", [])
        date = source.get("publication_date", "")
        
        if style == "AMA":
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            return f"{author_str}. {title}. Evidence Level: {level}. {date}"
        elif style == "APA":
            author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            return f"{author_str} ({date}). {title} [Evidence Level {level}]."
        else:  # Vancouver
            return f"{title} [Evidence Level {level}]. {date}"
    
    async def _validate_citations(self, citations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Validate citations using LLM for accuracy and completeness."""
        if not citations:
            return citations
        
        prompt = self.prompt_template.get_citation_validation_prompt(citations)
        
        try:
            validation = await self.llm_service.generate_response(
                query=prompt,
                context="",
                system_prompt="You are a medical citation validator."
            )
            # Process validation and update citations if needed
            # This would parse the LLM response and update the citations accordingly
        except Exception as e:
            logger.warning(f"Error in citation validation: {str(e)}")
        
        return citations

class MedicalResponseNode:
    """Node responsible for generating evidence-based medical responses."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.prompt_template = MedicalResearchPromptTemplate()
        self.llm_service = None
    
    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Generate an evidence-based medical response."""
        request = state["request"]
        settings = state["metadata"]["settings"]
        medical_terms = state["medical_terms"]
        clinical_guidelines = state.get("clinical_guidelines", [])
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = metrics.get("provider")
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Prepare context with citations and guidelines
            context = state["medical_context"]
            
            # Add clinical guidelines if available
            if clinical_guidelines:
                context += "\n\nClinical Guidelines:\n" + "\n".join(
                    f"- {guideline['title']}: {guideline['content'][:200]}..."
                    for guideline in clinical_guidelines[:2]  # Include top 2 guidelines
                )
            
            # Add citations
            if state["citations"]:
                context += "\n\nCitations:\n" + "\n".join(
                    f"{i+1}. {citation['citation']}"
                    for i, citation in enumerate(state["citations"])
                )
            
            # Generate system prompt with medical context
            system_prompt = self.prompt_template.get_system_prompt(
                context=context,
                settings={
                    **settings,
                    "medical_terms": medical_terms,
                    "has_guidelines": bool(clinical_guidelines)
                }
            )
            
            # Generate response
            response = await self.llm_service.generate_response(
                query=request.message,
                context=context,
                system_prompt=system_prompt
            )
            
            # Validate response
            response = await self._validate_response(
                response,
                medical_terms,
                state["citations"]
            )
            
            metrics["response_generation_time"] = time.time() - start_time
            metrics["response_length"] = len(response)
            
            return {
                **state,
                "response": response,
                "metrics": metrics,
                "next_step": "store_memory"  # Transition to store_memory node
            }
            
        except Exception as e:
            logger.error(f"Error generating medical response: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    async def _validate_response(
        self,
        response: str,
        medical_terms: Dict[str, List[str]],
        citations: List[Dict[str, Any]]
    ) -> str:
        """Validate the medical response for accuracy and completeness."""
        prompt = self.prompt_template.get_response_validation_prompt(
            response=response,
            terms=medical_terms,
            citations=citations
        )
        
        try:
            validation = await self.llm_service.generate_response(
                query=prompt,
                context="",
                system_prompt="You are a medical response validator."
            )
            # Process validation and update response if needed
            # This would parse the LLM response and update the response accordingly
        except Exception as e:
            logger.warning(f"Error in response validation: {str(e)}")
        
        return response

class MedicalMemoryStorageNode:
    """Node responsible for storing medical conversation in memory."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None

    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Store the medical conversation in memory if enabled."""
        if not self.settings.memory_enabled or not state["request"].use_memory:
            return {**state, "next_step": "end"}

        metrics = state.get("metrics", {})
        start_time = time.time()

        try:
            # Prepare content and metadata for storage
            content = {
                "user_message": state["request"].message,
                "assistant_message": state["response"],
                "agent_id": "medical_research",
                "medical_terms": state.get("medical_terms", {}),
                "citations": state.get("citations", [])
            }

            metadata = {
                "provider": metrics.get("provider"),
                "timestamp": datetime.utcnow().isoformat(),
                "evidence_sources_count": metrics.get("sources_count", 0),
                "citations_count": metrics.get("citations_count", 0),
                "agent_id": "medical_research",
                "agent_name": "Medical Research Agent"
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
            logger.error(f"Error storing medical conversation in memory: {str(e)}")
            # Don't fail the request if memory storage fails, just proceed to end
            return {**state, "next_step": "end"}

class MedicalErrorHandlerNode:
    """Node responsible for handling errors and preparing an error response."""

    def __init__(self, settings: Settings):
        self.settings = settings

    async def __call__(self, state: MedicalChatState) -> MedicalChatState:
        """Handle the error and prepare the state for termination."""
        error_message = state.get("error", "An unknown error occurred during medical research.")
        logger.error(f"Handling error in Medical Research Agent: {error_message}")

        # You might want to format the error message nicely for the user
        # state["response"] = f"Error: {error_message}"

        # Transition to the end of the graph
        return {**state, "next_step": "end", "response": f"An error occurred: {error_message}"}

def router(state: MedicalChatState) -> str:
    """Route to the next node based on state."""
    if state.get("error"):
        # If there's an error, route to the error handler
        return "error_handler"
    # Otherwise, route based on the next_step
    return state.get("next_step", "end")

def create_medical_agent_graph(settings: Settings) -> Graph:
    """
    Create the medical agent graph with all nodes.
    
    This graph defines the workflow for processing medical research queries.
    """
    # Create the graph
    workflow = StateGraph(MedicalChatState)
    
    # Add nodes
    workflow.add_node("validation", MedicalValidationNode(settings))
    workflow.add_node("literature", MedicalLiteratureNode(settings))
    workflow.add_node("evidence", MedicalEvidenceNode(settings))
    workflow.add_node("generate_response_node", MedicalResponseNode(settings))
    workflow.add_node("store_memory", MedicalMemoryStorageNode(settings))
    workflow.add_node("error_handler", MedicalErrorHandlerNode(settings)) # Add the error handler node
    
    # Define edges with conditional routing
    workflow.add_conditional_edges(
        "validation", # Source node
        router,       # Router function
        {             # Mapping of router output to next node
            "literature": "literature",
            "error_handler": "error_handler", # Route to error_handler on error
            "end": END
        }
    )
    workflow.add_edge("literature", "evidence")
    workflow.add_edge("evidence", "generate_response_node")
    workflow.add_conditional_edges(
        "generate_response_node", # Source node
        router,                   # Router function
        {                         # Mapping of router output to next node
            "store_memory": "store_memory",
            "error_handler": "error_handler", # Route to error_handler on error
            "end": END
        }
    )
    workflow.add_edge("store_memory", END) # Transition to END after storing memory
    workflow.add_edge("error_handler", END) # Transition from error_handler to END
    
    # Set entry and exit points
    workflow.set_entry_point("validation")
    
    # Compile the graph
    return workflow.compile() 