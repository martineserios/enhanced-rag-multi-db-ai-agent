"""
Medical Chat Service

Core service for handling medical conversations about obesity treatment.
Integrates with OpenAI for medical AI responses and manages conversation context.
"""

import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
import uuid

from app.core.config import get_settings
from app.services.medical_knowledge import MedicalKnowledgeBase
from app.core.logging import log_medical_decision
from app.core.llm_factory import get_provider_manager
from app.core.llm_providers import (
    LLMRequest, 
    ModelCapability, 
    ProviderType
)

logger = logging.getLogger(__name__)


class ConversationContext:
    """Manages conversation context for medical chats."""
    
    def __init__(self, session_id: str, language: str = "es"):
        self.session_id = session_id
        self.language = language
        self.messages: List[Dict[str, str]] = []
        self.created_at = datetime.now()
        self.last_activity = datetime.now()
        self.patient_id: Optional[str] = None
    
    def add_message(self, role: str, content: str):
        """Add message to conversation context."""
        self.messages.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now().isoformat()
        })
        self.last_activity = datetime.now()
        
        # Keep only last 10 messages for context management
        if len(self.messages) > 10:
            self.messages = self.messages[-10:]
    
    def get_llm_messages(self) -> List[Dict[str, str]]:
        """Get messages in LLM provider format."""
        return [{"role": msg["role"], "content": msg["content"]} for msg in self.messages]
    
    def is_expired(self, timeout_minutes: int = 30) -> bool:
        """Check if conversation context has expired."""
        return datetime.now() - self.last_activity > timedelta(minutes=timeout_minutes)


class MedicalChatService:
    """Service for medical AI conversations."""
    
    def __init__(self):
        self.settings = get_settings()
        self.knowledge_base = MedicalKnowledgeBase()
        self.contexts: Dict[str, ConversationContext] = {}
        
        # Reset provider manager to pick up latest routing configuration
        from app.core.llm_factory import reset_provider_manager
        reset_provider_manager()
        self.provider_manager = get_provider_manager()
        
        logger.info("Medical Chat Service initialized with flexible LLM providers")
    
    async def get_medical_response(
        self,
        message: str,
        language: str = "es",
        session_id: str = None,
        patient_id: str = None
    ) -> Dict[str, Any]:
        """
        Get medical AI response for patient query.
        
        Args:
            message: Patient's message/question
            language: Language code (es/en)
            session_id: Session identifier for context
            patient_id: Patient identifier for logging
            
        Returns:
            Dict with AI response and metadata
        """
        try:
            # Get or create conversation context
            context = self._get_or_create_context(session_id, language)
            if patient_id:
                context.patient_id = patient_id
            
            # Get relevant medical knowledge
            relevant_knowledge = self.knowledge_base.get_relevant_knowledge(
                query=message,
                language=language
            )
            
            # Build system prompt with medical knowledge
            system_prompt = self._build_medical_system_prompt(
                language=language,
                knowledge=relevant_knowledge
            )
            
            # Prepare messages for LLM provider
            messages = []
            
            # Add conversation history
            messages.extend(context.get_llm_messages())
            
            # Add current user message
            messages.append({"role": "user", "content": message})
            
            # Create LLM request with medical context
            llm_request = LLMRequest(
                messages=messages,
                system_prompt=system_prompt,
                patient_id=patient_id,
                session_id=context.session_id,
                medical_context={
                    "patient_safety_level": "standard",
                    "medical_domain": "obesity_treatment",
                    "language": language,
                    "requires_disclaimer": True
                }
            )
            
            # Get response using appropriate provider for clinical conversation (Groq first)
            llm_response = await self.provider_manager.generate_medical_response(
                capability=ModelCapability.CLINICAL_CONVERSATION,
                request=llm_request,
                fallback_providers=[ProviderType.GROQ, ProviderType.OPENAI, ProviderType.ANTHROPIC]
            )
            
            # Add messages to context
            context.add_message("user", message)
            context.add_message("assistant", llm_response.content)
            
            # Log medical decision with provider information
            decision_id = str(uuid.uuid4())
            log_medical_decision(
                decision_id=decision_id,
                decision_type="medical_response",
                input_data={
                    "message": message,
                    "language": language,
                    "session_id": context.session_id,
                    "provider": llm_response.provider.value
                },
                output_data={
                    "response": llm_response.content,
                    "knowledge_used": len(relevant_knowledge),
                    "model": llm_response.model,
                    "medical_validated": llm_response.medical_validated
                },
                confidence_score=llm_response.confidence_score or 0.85
            )
            
            return {
                "content": llm_response.content,
                "language": language,
                "session_id": context.session_id,
                "context_preserved": True,
                "knowledge_sources": len(relevant_knowledge),
                "provider": llm_response.provider.value,
                "model": llm_response.model,
                "medical_validated": llm_response.medical_validated
            }
            
        except Exception as e:
            logger.error(f"Error getting medical response: {str(e)}")
            
            # Return fallback response
            fallback_message = (
                "Lo siento, no puedo procesar su consulta en este momento. "
                "Por favor consulte con su médico tratante."
                if language == "es" else
                "I'm sorry, I cannot process your query at this time. "
                "Please consult with your healthcare provider."
            )
            
            return {
                "content": fallback_message,
                "language": language,
                "session_id": session_id or str(uuid.uuid4()),
                "context_preserved": False,
                "error": True
            }
    
    def _get_or_create_context(self, session_id: str, language: str) -> ConversationContext:
        """Get existing context or create new one."""
        if not session_id:
            session_id = str(uuid.uuid4())
        
        if session_id in self.contexts:
            context = self.contexts[session_id]
            if not context.is_expired(self.settings.CONVERSATION_TIMEOUT_MINUTES):
                return context
            else:
                # Remove expired context
                del self.contexts[session_id]
        
        # Create new context
        context = ConversationContext(session_id, language)
        self.contexts[session_id] = context
        return context
    
    def _build_medical_system_prompt(self, language: str, knowledge: List[Dict]) -> str:
        """Build system prompt with medical knowledge."""
        
        base_prompt_es = """Eres un asistente médico especializado en el tratamiento de la obesidad con medicamentos GLP-1 (como Ozempic/Semaglutide). Tu papel es:

RESPONSABILIDADES:
- Proporcionar información precisa sobre tratamientos GLP-1
- Ayudar con técnicas de inyección y manejo de efectos secundarios  
- Ofrecer orientación sobre expectativas del tratamiento
- Detectar situaciones que requieren atención médica inmediata

LIMITACIONES IMPORTANTES:
- NO puedes diagnosticar condiciones médicas
- NO puedes cambiar dosis de medicamentos
- SIEMPRE recomienda consultar con el médico para decisiones médicas importantes
- Mantén un tono profesional pero empático

INFORMACIÓN MÉDICA RELEVANTE:
{knowledge_content}

Responde en español de manera clara, precisa y comprensible. Incluye el disclaimer médico cuando sea apropiado."""

        base_prompt_en = """You are a medical assistant specialized in obesity treatment with GLP-1 medications (like Ozempic/Semaglutide). Your role is:

RESPONSIBILITIES:
- Provide accurate information about GLP-1 treatments
- Help with injection techniques and side effect management
- Offer guidance on treatment expectations
- Detect situations requiring immediate medical attention

IMPORTANT LIMITATIONS:
- You CANNOT diagnose medical conditions
- You CANNOT change medication doses
- ALWAYS recommend consulting with doctor for important medical decisions
- Maintain a professional but empathetic tone

RELEVANT MEDICAL INFORMATION:
{knowledge_content}

Respond in English clearly, accurately and understandably. Include medical disclaimer when appropriate."""
        
        # Format knowledge content
        knowledge_content = "\n".join([
            f"- {item['title']}: {item['content']}"
            for item in knowledge[:5]  # Limit to top 5 relevant items
        ])
        
        if language == "es":
            return base_prompt_es.format(knowledge_content=knowledge_content)
        else:
            return base_prompt_en.format(knowledge_content=knowledge_content)
    
    
    async def get_session_context(self, session_id: str) -> Dict[str, Any]:
        """Get conversation context for session."""
        if session_id not in self.contexts:
            raise Exception("Session not found")
        
        context = self.contexts[session_id]
        
        return {
            "session_id": context.session_id,
            "language": context.language,
            "messages": context.messages,
            "created_at": context.created_at.isoformat(),
            "last_activity": context.last_activity.isoformat(),
            "patient_id": context.patient_id,
            "message_count": len(context.messages)
        }
    
    async def health_check(self) -> Dict[str, Any]:
        """Check service health including all LLM providers."""
        from app.core.llm_factory import health_check_providers
        
        provider_health = await health_check_providers()
        
        return {
            "knowledge_base_loaded": self.knowledge_base.is_loaded(),
            "active_sessions": len(self.contexts),
            "service_status": "operational",
            "providers": provider_health
        }