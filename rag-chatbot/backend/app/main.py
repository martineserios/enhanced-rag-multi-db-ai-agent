"""
FastAPI Main Application - GlabitAI Medical Chatbot

MVP 1: Basic Medical Chatbot for Obesity Treatment
- Medical conversation endpoint
- Bilingual support (Spanish/English)
- OpenAI integration with medical prompting
- Conversation context management
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
from datetime import datetime
from typing import Dict, Any

from app.api.endpoints import chat
from app.core.config import get_settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Get application settings
settings = get_settings()

# Create FastAPI application
app = FastAPI(
    title="GlabitAI Medical Backend",
    description="Medical AI system for obesity treatment follow-up care",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:8501"],  # Frontend origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(chat.router, prefix="/api/v1")

@app.get("/")
async def root() -> Dict[str, Any]:
    """Root endpoint with basic API information."""
    return {
        "message": "GlabitAI Medical Backend",
        "version": "0.1.0",
        "status": "active",
        "timestamp": datetime.now().isoformat(),
        "endpoints": {
            "chat": "/api/v1/chat",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check() -> Dict[str, Any]:
    """Health check endpoint for monitoring."""
    try:
        # Basic health checks with new LLM provider system
        from app.core.llm_factory import health_check_providers
        
        try:
            provider_health = await health_check_providers()
            llm_status = "healthy" if provider_health.get("summary", {}).get("status") == "healthy" else "degraded"
        except Exception:
            llm_status = "unavailable"
        
        checks = {
            "status": "healthy" if llm_status != "unavailable" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "services": {
                "api": "online",
                "llm_providers": llm_status,
                "openai": "configured" if settings.OPENAI_API_KEY else "not_configured",
                "anthropic": "configured" if settings.ANTHROPIC_API_KEY else "not_configured",
                "groq": "configured" if settings.GROQ_API_KEY else "not_configured"
            }
        }
        
        return checks
        
    except Exception as e:
        logger.error(f"Health check failed: {str(e)}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Custom 404 handler."""
    return JSONResponse(
        status_code=404,
        content={
            "error": "Endpoint not found",
            "message": "The requested endpoint does not exist",
            "available_endpoints": [
                "/",
                "/health", 
                "/api/v1/chat",
                "/docs"
            ]
        }
    )

@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Custom 500 handler."""
    logger.error(f"Internal server error: {str(exc)}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Internal server error",
            "message": "An unexpected error occurred",
            "timestamp": datetime.now().isoformat()
        }
    )

if __name__ == "__main__":
    # Run the application
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )