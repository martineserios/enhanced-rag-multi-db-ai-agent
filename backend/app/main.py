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

from app.api.endpoints import chat, patient
from app.core.config import get_settings
from app.core.logging import setup_logging
from app.db.mongodb import connect_to_mongo, close_mongo_connection

from app.db.mongodb import connect_to_mongo, close_mongo_connection

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

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
    lifespan=lifespan
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
app.include_router(patient.router, prefix="/api/v1")

from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    await connect_to_mongo()
    yield
    await close_mongo_connection()

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

        # Check MongoDB connection status
        mongo_status = "unavailable"
        try:
            from app.db.mongodb import mongodb
            if mongodb.client and await mongodb.client.admin.command('ping'):
                mongo_status = "healthy"
            else:
                mongo_status = "unhealthy"
        except Exception:
            mongo_status = "unhealthy"
        
        checks = {
            "status": "healthy" if llm_status != "unavailable" and mongo_status == "healthy" else "degraded",
            "timestamp": datetime.now().isoformat(),
            "version": "0.1.0",
            "services": {
                "api": "online",
                "llm_providers": llm_status,
                "mongodb": mongo_status,
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
    """Custom 404 handler for unmatched routes only."""
    from fastapi import HTTPException
    # If this is an HTTPException with detail, let it pass through
    if isinstance(exc, HTTPException) and hasattr(exc, 'detail'):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )
    
    # Otherwise use custom response for unmatched routes
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