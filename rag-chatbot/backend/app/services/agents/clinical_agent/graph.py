"""
Clinical Agent implementation (Spanish-speaking).

This module implements a LangGraph workflow for a Spanish-speaking clinical agent that provides
direct diagnosis and treatment recommendations based on symptoms and medical history.
"""
import json
import logging
import re
import time
import uuid
from datetime import datetime
from typing import (Annotated, Any, Callable, Dict, List, Literal, Optional,
                    TypedDict)

from app.api.models.chat import ChatRequest, ChatResponse
from app.config import Settings
from app.core.logging import get_logger
from app.services.agents.clinical_agent.tools import get_clinical_tools
from app.services.database import query_mongo, query_postgres
from app.services.llm.factory import get_llm_service
from app.services.memory.manager import get_memory_manager
from langchain_core.tools import BaseTool
from langgraph.graph import END, Graph, StateGraph
from langgraph.prebuilt import ToolNode

logger = get_logger(__name__)

# Spanish medical terminology patterns for symptom and condition detection
MEDICAL_TERMS = {
    "sintomas": r"\b(dolor|fiebre|tos|dolor de cabeza|nausea|vomito|fatiga|mareo|erupcion|hinchazon)\b",
    "condiciones": r"\b(diabetes|hipertension|asma|artritis|infeccion|inflamacion|enfermedad|sindrome)\b",
    "severidad": r"\b(severo|leve|moderado|agudo|cronico|emergencia|urgente)\b",
    "duracion": r"\b(dias|semanas|meses|anos|repentino|gradual|persistente|intermitente)\b"
}

class ClinicalChatState(TypedDict):
    """State type for the clinical chat graph."""
    request: ChatRequest
    conversation_id: str
    medical_context: str
    detected_terms: Dict[str, List[str]]
    patient_history: Dict[str, Any]
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    messages: List[Dict[str, Any]]  # Added for tool node compatibility
    next_step: Optional[Literal["analyze", "diagnose", "treat", "use_tool", "store_memory", "error", "end"]]
    available_tools: List[Dict[str, Any]]
    tool_calls: List[Dict[str, Any]]
    tool_results: List[Dict[str, Any]]

class ClinicalAnalysisNode:
    """Node responsible for analyzing symptoms and medical history in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
        self.llm_service = None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Analyze symptoms and medical history in Spanish."""
        request = state["request"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = request.provider.value if hasattr(request.provider, "value") else request.provider
                if not provider:
                    provider = self.settings.default_llm_provider.value
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Detect medical terms in Spanish
            detected_terms = self._detect_medical_terms(request.message)
            
            # Get patient history if available
            patient_history = {}
            if self.settings.memory_enabled and request.use_memory:
                try:
                    history_context = await self.memory_manager.create_unified_context(
                        query=request.message,
                        conversation_id=state["conversation_id"],
                        memory_types=["episodic"],
                        weights={"episodic": 1.0}
                    )
                    if history_context:
                        patient_history = history_context
                except Exception as e:
                    logger.error(f"Error retrieving patient history: {str(e)}")
            
            metrics["analysis_time"] = time.time() - start_time
            metrics["terms_detected"] = sum(len(terms) for terms in detected_terms.values())
            
            # Check if we need to use any tools
            logger.info("[TOOL_DETECTION] Starting tool detection for message")
            tool_calls = self._detect_tool_usage(request.message)
            
            if tool_calls:
                logger.info(f"[TOOL_DETECTION] Detected {len(tool_calls)} tool calls needed for this message")
                for i, tool_call in enumerate(tool_calls, 1):
                    logger.info(f"[TOOL_CALL] {i}. {tool_call['name']} with args: {tool_call['args']}")
                    logger.debug(f"[TOOL_CALL_DETAILS] Tool call {i} details: {json.dumps(tool_call, indent=2)}")
            else:
                logger.info("[TOOL_DETECTION] No tool calls needed for this message")
            
            return {
                **state,
                "detected_terms": detected_terms,
                "patient_history": patient_history,
                "metrics": metrics,
                "tool_calls": tool_calls if tool_calls else [],
                "next_step": "use_tool" if tool_calls else "diagnose"
            }
            
        except Exception as e:
            logger.error(f"Error in clinical analysis: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}
    
    def _detect_medical_terms(self, message: str) -> Dict[str, List[str]]:
        """Detect medical terms in Spanish message."""
        detected = {}
        for category, pattern in MEDICAL_TERMS.items():
            matches = re.findall(pattern, message, re.IGNORECASE)
            if matches:
                detected[category] = list(set(matches))  # Remove duplicates
        return detected
        
    def _detect_tool_usage(self, message: str) -> List[Dict[str, Any]]:
        """
        Detect if the message requires using any tools.
        
        Args:
            message: User's message
            
        Returns:
            List of tool calls to make, or empty list if no tools needed
        """
        logger.debug(f"Checking if tools are needed for message: {message}")
        
        # Simple keyword-based detection - in a real implementation, you might use an LLM
        # to determine if tools are needed and with what parameters
        
        # Check for medication-related queries
        medication_terms = [
            "medicamento", "medicina", "pastilla", "comprimido", "cápsula",
            "dosis", "efectos secundarios", "contraindicaciones", "para qué sirve"
        ]
        
        if any(term in message.lower() for term in medication_terms):
            logger.debug("Medication-related terms detected, checking for specific medications")
            # Extract medication name (simplified example)
            # In a real implementation, you'd use more sophisticated NLP
            medication_match = re.search(r'\b(paracetamol|ibuprofeno|aspirina|omeprazol)\b', message, re.IGNORECASE)
            if medication_match:
                medication = medication_match.group(1).lower()
                tool_call = {
                    "name": "lookup_medication",
                    "args": {
                        "medication_name": medication,
                        "language": "es"
                    }
                }
                logger.info(f"Tool call detected: {tool_call}")
                return [tool_call]
            else:
                logger.debug("No specific medication name detected in message")
        else:
            logger.debug("No medication-related terms detected in message")
                
        return []

class ClinicalDiagnosisNode:
    """Node responsible for generating clinical diagnosis in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Generate clinical diagnosis based on symptoms and history in Spanish."""
        request = state["request"]
        detected_terms = state["detected_terms"]
        patient_history = state["patient_history"]
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            # Initialize LLM service if needed
            if not self.llm_service:
                provider = metrics.get("provider")
                self.llm_service = get_llm_service(provider, self.settings)
            
            # Prepare context for diagnosis
            context = f"Usuario: {request.message}\n\n"
            
            # Add detected terms to context
            detected_terms = state.get("detected_terms", {})
            if detected_terms.get("sintomas"):
                context += f"Síntomas: {', '.join(detected_terms['sintomas'])}\n"
            if detected_terms.get("condiciones"):
                context += f"Condiciones Conocidas: {', '.join(detected_terms['condiciones'])}\n"
            if detected_terms.get("severidad"):
                context += f"Severidad: {', '.join(detected_terms['severidad'])}\n"
            if detected_terms.get("duracion"):
                context += f"Duración: {', '.join(detected_terms['duracion'])}\n"
            if patient_history:
                context += f"\nHistorial del Paciente:\n{patient_history}\n"
                
            # Add tool results to context if available
            if state.get("tool_results"):
                tools_used = len(state["tool_results"])
                logger.info(f"Incorporating results from {tools_used} tools into context")
                context += "\nInformación de herramientas:\n"
                for i, result in enumerate(state["tool_results"], 1):
                    if isinstance(result, dict) and "content" in result:
                        logger.debug(f"Tool {i} result (content): {result['content'][:200]}...")
                        context += f"\nHerramienta {i}:\n{result['content']}\n"
                    else:
                        result_str = str(result)
                        logger.debug(f"Tool {i} result (raw): {result_str[:200]}...")
                        context += f"\nHerramienta {i}:\n{result_str}\n"
                metrics["tools_used"] = tools_used
            
            # Generate diagnosis in Spanish
            system_prompt = (
                "Eres un asistente clínico enfocado en proporcionar diagnósticos claros y recomendaciones. "
                "Basándote en los síntomas y el historial del paciente, proporciona:\n"
                "1. Un diagnóstico claro o posibles diagnósticos\n"
                "2. Nivel de urgencia (emergencia, urgente, rutina)\n"
            )

            # Get settings from state metadata
            settings = state["metadata"]["settings"]

            # Conditionally add follow-up steps and treatment recommendations based on settings
            if settings.get("include_follow_up", False):
                system_prompt += "3. Pasos recomendados a seguir\n"
            
            if settings.get("include_treatment_options", False):
                 # Adjust the numbering if follow-up was not included
                treatment_step_number = 4 if settings.get("include_follow_up", False) else 3
                system_prompt += f"{treatment_step_number}. Recomendaciones de tratamiento\n\n"

            system_prompt += "Sé directo y claro en tu evaluación. Responde siempre en español."
            
            diagnosis = await self.llm_service.generate_response(
                query=request.message,
                context=context,
                system_prompt=system_prompt
            )
            
            metrics["diagnosis_time"] = time.time() - start_time
            metrics["diagnosis_length"] = len(diagnosis)
            
            return {
                **state,
                "response": diagnosis,
                "metrics": metrics,
                "next_step": "store_memory"
            }
            
        except Exception as e:
            logger.error(f"Error generating diagnosis: {str(e)}")
            return {**state, "error": str(e), "next_step": "error"}

class ClinicalMemoryStorageNode:
    """Node responsible for storing clinical conversation in memory."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.memory_manager = get_memory_manager() if settings.memory_enabled else None
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Store the clinical conversation in memory if enabled."""
        if not self.settings.memory_enabled or not state["request"].use_memory:
            return {**state, "next_step": "end"}
        
        metrics = state.get("metrics", {})
        start_time = time.time()
        
        try:
            content = {
                "user_message": state["request"].message,
                "assistant_message": state["response"],
                "agent_id": "clinical_es",
                "detected_terms": state["detected_terms"],
                "patient_history": state["patient_history"]
            }
            
            metadata = {
                "provider": metrics.get("provider"),
                "timestamp": datetime.utcnow().isoformat(),
                "agent_id": "clinical_es",
                "agent_name": "Asistente Clínico"
            }
            
            message_key = f"conversation:{state['conversation_id']}:message:{uuid.uuid4()}"
            
            await self.memory_manager.store_memory(
                memory_type="episodic",
                content=content,
                key=message_key,
                metadata=metadata,
                conversation_id=state["conversation_id"]
            )
            
            metrics["memory_storage_time"] = time.time() - start_time
            return {**state, "metrics": metrics, "next_step": "end"}
            
        except Exception as e:
            logger.error(f"Error storing clinical conversation: {str(e)}")
            return {**state, "next_step": "end"}

class ClinicalErrorHandlerNode:
    """Node responsible for handling clinical errors in Spanish."""
    
    def __init__(self, settings: Settings):
        self.settings = settings
    
    async def __call__(self, state: ClinicalChatState) -> ClinicalChatState:
        """Handle errors in clinical processing."""
        error_message = state.get("error", "Ocurrió un error durante la evaluación clínica.")
        logger.error(f"Clinical error: {error_message}")
        
        return {
            **state,
            "response": (
                "Lo siento, pero encontré un error al procesar su solicitud. "
                "Para emergencias médicas, por favor contacte a los servicios de emergencia o a su proveedor de salud inmediatamente. "
                f"Detalles del error: {error_message}"
            ),
            "next_step": "end"
        }

def router(state: ClinicalChatState) -> str:
    """Route to the next node based on state."""
    if state.get("error"):
        return "error"
    return state.get("next_step", "end")

def tool_router(state: ClinicalChatState) -> str:
    """Route to tools if needed, otherwise continue to next step."""
    # If we have tool calls, route to tools node
    if state.get("tool_calls"):
        logger.info(f"[TOOL_ROUTER] Routing to tools node with {len(state['tool_calls'])} tool calls")
        return "tools"
    logger.debug("[TOOL_ROUTER] No tool calls, proceeding to next step")
    return state.get("next_step", "end")

def create_clinical_agent_graph(settings: Settings) -> callable:
    """Create the Spanish-speaking clinical agent graph with tool support."""
    builder = StateGraph(ClinicalChatState)
    
    # Initialize nodes
    analysis_node = ClinicalAnalysisNode(settings)
    diagnosis_node = ClinicalDiagnosisNode(settings)
    memory_node = ClinicalMemoryStorageNode(settings)
    error_node = ClinicalErrorHandlerNode(settings)
    
    # Get available tools
    tools = get_clinical_tools()
    logger.info(f"[TOOL_INIT] Initializing tool node with {len(tools)} tools")
    tool_node = ToolNode([t for t in tools if isinstance(t, BaseTool)])
    logger.info(f"[TOOL_INIT] Tool node created with tools: {[t.name for t in tools if hasattr(t, 'name')]}")
    logger.debug(f"[TOOL_INIT] Full tool details: {[{'name': t.name, 'description': t.description} for t in tools if hasattr(t, 'name')]}")
    logger.info("[TOOL_INIT] Tool node initialized successfully")
    
    # Add nodes to graph
    builder.add_node("analyze", analysis_node)
    builder.add_node("diagnose", diagnosis_node)
    builder.add_node("store_memory", memory_node)
    builder.add_node("handle_error", error_node)  # Changed from "error" to "handle_error"
    builder.add_node("tools", tool_node)
    
    # Set entry point
    builder.set_entry_point("analyze")
    
    # Add edges with tool support
    builder.add_conditional_edges(
        "analyze",
        router,
        {
            "diagnose": "diagnose",
            "use_tool": "tools",
            "store_memory": "store_memory",
            "end": END,
            "error": "handle_error"  # Updated to match the new node name
        }
    )
    
    # After tools complete, route based on next_step
    builder.add_conditional_edges(
        "tools",
        tool_router,
        {
            "diagnose": "diagnose",
            "store_memory": "store_memory",
            "end": END,
            "error": "handle_error"  # Updated to match the new node name
        }
    )
    
    # Standard flow
    builder.add_conditional_edges(
        "diagnose",
        lambda state: state.get("next_step", "store_memory"),
        {
            "store_memory": "store_memory",
            "end": END,
            "error": "handle_error"  
        }
    )

    # Memory and error handling
    builder.add_edge("store_memory", END)
    builder.add_edge("handle_error", "store_memory")  

    # Initialize available tools in the state
    def init_state(state: ClinicalChatState) -> ClinicalChatState:
        # Create the messages list that the tool node expects
        messages = []
        
        # Add user message if it doesn't exist
        if "request" in state and state["request"].message:
            messages.append({
                "role": "user",
                "content": state["request"].message,
                "name": "user"
            })
        
        # Add any existing messages from the state
        if "messages" in state and isinstance(state["messages"], list):
            messages.extend(state["messages"])
        
        # Prepare tool calls in the format expected by the tool node
        tool_calls = []
        if state.get("tool_calls"):
            for i, tool_call in enumerate(state["tool_calls"]):
                tool_calls.append({
                    "type": "function",
                    "id": f"call_{i}",
                    "function": {
                        "name": tool_call["name"],
                        "arguments": json.dumps(tool_call.get("args", {})),
                    }
                })
        
        # Add tool call to the last message if we have tool calls
        if tool_calls and messages:
            messages[-1]["tool_calls"] = tool_calls
        
        return {
            **state,
            "messages": messages,
            "available_tools": [
                {
                    "name": tool.name,
                    "description": tool.description,
                    "args_schema": tool.args_schema.schema() if hasattr(tool, 'args_schema') else {}
                }
                for tool in tools if hasattr(tool, 'name')
            ],
            "tool_calls": tool_calls,
            "tool_results": state.get("tool_results", [])
        }
    
    compiled_graph = builder.compile()
    
    # Log graph compilation success
    logger.info("Clinical agent graph compiled successfully")
    
    # Wrap the compiled graph to initialize state
    async def wrapped_graph(state: ClinicalChatState):
        logger.debug("Initializing graph state with tools")
        initialized_state = init_state(state)
        logger.debug("Invoking graph with initialized state")
        result = await compiled_graph.ainvoke(initialized_state)
        logger.debug("Graph execution completed")
        return result
    
    logger.info("Returning wrapped graph function")
    return wrapped_graph