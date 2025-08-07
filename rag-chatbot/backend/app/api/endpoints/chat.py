"""
Chat API endpoint for medical conversations

MVP 1: Basic Medical Chatbot
- Medical conversation with OpenAI integration
- Bilingual support (Spanish/English)  
- Conversation context management
- Medical response validation
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, field_validator
from typing import Dict, List, Any, Optional
import logging
from datetime import datetime
import uuid

from app.services.medical_chat import MedicalChatService
from app.core.config import get_settings
from app.core.logging import log_medical_interaction

router = APIRouter()
logger = logging.getLogger(__name__)

# Initialize medical chat service
medical_chat_service = MedicalChatService()


class ChatRequest(BaseModel):
    """Request model for medical chat."""
    
    message: str
    language: str = "es"
    session_id: Optional[str] = None
    patient_id: Optional[str] = None
    
    @field_validator("message")
    @classmethod
    def validate_message(cls, v):
        """Validate message content."""
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        if len(v) > 1000:
            raise ValueError("Message too long (max 1000 characters)")
        return v.strip()
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, v):
        """Validate language code."""
        supported = ["es", "en"]
        if v not in supported:
            raise ValueError(f"Language must be one of: {supported}")
        return v


class ChatResponse(BaseModel):
    """Response model for medical chat."""
    
    message: str
    session_id: str
    language: str
    timestamp: str
    medical_disclaimer: str
    context_preserved: bool = True
    response_time_ms: int
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


@router.post("/chat", response_model=ChatResponse)
async def chat_with_medical_ai(
    request: ChatRequest,
    settings = Depends(get_settings)
) -> ChatResponse:
    """
    Chat with medical AI for obesity treatment guidance.
    
    Provides medically accurate responses about GLP-1 treatments,
    side effects, injection techniques, and general treatment support
    in Spanish or English.
    """
    start_time = datetime.now()
    
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())
        
        # Log medical interaction for audit
        log_medical_interaction(
            patient_id=request.patient_id or "anonymous",
            interaction_type="chat_request",
            details={
                "message_length": len(request.message),
                "language": request.language,
                "session_id": session_id
            }
        )
        
        # Get medical AI response
        ai_response = await medical_chat_service.get_medical_response(
            message=request.message,
            language=request.language,
            session_id=session_id,
            patient_id=request.patient_id
        )
        
        # Calculate response time
        end_time = datetime.now()
        response_time_ms = int((end_time - start_time).total_seconds() * 1000)
        
        # Log successful response
        log_medical_interaction(
            patient_id=request.patient_id or "anonymous",
            interaction_type="chat_response",
            details={
                "response_length": len(ai_response["content"]),
                "response_time_ms": response_time_ms,
                "session_id": session_id
            }
        )
        
        # Return response
        return ChatResponse(
            message=ai_response["content"],
            session_id=session_id,
            language=request.language,
            timestamp=end_time.isoformat(),
            medical_disclaimer=settings.MEDICAL_DISCLAIMER,
            context_preserved=ai_response.get("context_preserved", True),
            response_time_ms=response_time_ms
        )
        
    except Exception as e:
        logger.error(f"Chat endpoint error: {str(e)}")
        
        # Log error for medical audit
        log_medical_interaction(
            patient_id=request.patient_id or "anonymous",
            interaction_type="chat_error",
            details={
                "error": str(e),
                "session_id": session_id
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail={
                "error": "Medical chat service unavailable",
                "message": "Unable to process medical query at this time",
                "timestamp": datetime.now().isoformat()
            }
        )


@router.get("/chat/health")
async def chat_service_health() -> Dict[str, Any]:
    """Health check for chat service."""
    try:
        # Check medical chat service health
        health_status = await medical_chat_service.health_check()
        
        return {
            "status": "healthy" if health_status["openai_configured"] else "degraded",
            "timestamp": datetime.now().isoformat(),
            "services": health_status,
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Chat health check failed: {str(e)}")
        raise HTTPException(
            status_code=503,
            detail="Chat service health check failed"
        )


@router.get("/chat/sessions/{session_id}/context")
async def get_session_context(session_id: str) -> Dict[str, Any]:
    """
    Get conversation context for a session.
    
    Useful for debugging and understanding conversation flow.
    """
    try:
        context = await medical_chat_service.get_session_context(session_id)
        
        return {
            "session_id": session_id,
            "message_count": len(context.get("messages", [])),
            "language": context.get("language", "es"),
            "created_at": context.get("created_at"),
            "last_activity": context.get("last_activity"),
            "context_summary": context.get("summary", "No context available")
        }
        
    except Exception as e:
        logger.error(f"Error retrieving session context: {str(e)}")
        raise HTTPException(
            status_code=404,
            detail="Session context not found"
        )