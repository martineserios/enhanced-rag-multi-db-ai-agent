# filepath: backend/app/main.py
"""
Main FastAPI application.

This module defines the main FastAPI application, including routes,
middleware, event handlers, and configuration.
"""
import os
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, List, Any, Optional

from fastapi import FastAPI, Request, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi

from app.core.logging import setup_logging, get_logger
from app.core.exceptions import BaseAppException
from app.config import Settings, get_settings
from app.api.middleware import RequestLoggingMiddleware, PerformanceMonitoringMiddleware
from app.api.routes import chat, memory, documents, debug
from app.services.database.postgres import init_postgres
from app.services.database.mongo import init_mongo
from app.services.memory.manager import init_memory_manager
from app.services.llm.factory import check_llm_providers, close_llm_services
from app.services.agents.registry import AgentRegistry


logger = get_logger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Startup and shutdown events for the FastAPI application.
    
    This context manager:
    1. Initializes services on startup
    2. Cleans up resources on shutdown
    
    Args:
        app: FastAPI application instance
    """
    try:
        # Get settings
        settings = get_settings()
        
        # Configure logging
        setup_logging(level=settings.get_log_level(), json_format=settings.log_json)
        
        logger.info(
            f"Starting {settings.app_name} v{settings.app_version}",
            extra={"debug_mode": settings.debug}
        )
        
        # Initialize databases
        await init_postgres(settings)
        await init_mongo(settings)
        
        # Initialize memory manager if enabled
        if settings.memory_enabled:
            await init_memory_manager(settings)
            logger.info("Memory manager initialized with enabled memory types", 
                       extra={"memory_types": settings.get_enabled_memory_types()})
        
        # Check LLM providers
        llm_status = await check_llm_providers(settings)
        logger.info("LLM providers status", extra={"llm_status": llm_status})
        
        # --- Agent Registration ---
        logger.info("Starting agent registration.")
        try:
            from app.services.agents.standard.service import StandardAgent
            from app.services.agents.standard_graph.service import StandardGraphAgent
            from app.services.agents.clinical_agent.service import ClinicalAgent
            from app.services.agents.template_agent.service import TemplateAgent

            AgentRegistry.register(StandardAgent)
            AgentRegistry.register(StandardGraphAgent)
            AgentRegistry.register(ClinicalAgent)
            AgentRegistry.register(TemplateAgent)
            logger.info("Agent registration complete.")

        except Exception as e:
             logger.error(f"Error during agent registration: {e}", exc_info=True)
             # Depending on how critical agent registration is, you might want to raise the exception
             # raise e # Uncomment to fail startup if agent registration fails
        # --- End Agent Registration ---

        # Application startup complete
        logger.info(f"{settings.app_name} startup complete")
        
        # Yield control back to FastAPI
        yield
        
        # Shutdown logic
        logger.info(f"Shutting down {settings.app_name}")
        
        # Close LLM services
        close_llm_services()
        
        # Close memory manager if enabled
        if settings.memory_enabled:
            from app.services.memory.manager import get_memory_manager
            try:
                memory_manager = get_memory_manager()
                await memory_manager.close()
            except Exception as e:
                logger.error(f"Error closing memory manager: {str(e)}")
        
        logger.info(f"{settings.app_name} shutdown complete")
        
    except Exception as e:
        logger.exception(f"Error during application lifecycle: {str(e)}")
        # Re-raise to let FastAPI handle the error
        raise


def create_application() -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Returns:
        Configured FastAPI application instance
    """
    # Get settings
    settings = get_settings()
    
    # Create FastAPI app
    app = FastAPI(
        title=settings.app_name,
        description="Memory-Enhanced RAG Chatbot API",
        version=settings.app_version,
        debug=settings.debug,
        lifespan=lifespan,
        docs_url=None,  # We'll use a custom docs endpoint
        redoc_url=None  # Disable ReDoc
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Add custom middleware
    app.add_middleware(RequestLoggingMiddleware)
    app.add_middleware(PerformanceMonitoringMiddleware)
    
    # Add exception handlers
    @app.exception_handler(BaseAppException)
    async def handle_app_exception(request: Request, exc: BaseAppException):
        """Handle custom application exceptions."""
        return JSONResponse(
            status_code=exc.status_code,
            content=exc.to_dict()
        )
    
    # Include routers
    app.include_router(chat.router, prefix="/api/chat", tags=["chat"])
    app.include_router(memory.router, prefix="/api/memory", tags=["memory"])
    app.include_router(documents.router, prefix="/api/documents", tags=["documents"])
    
    # Only include debug routes in development
    import os
    if os.getenv("ENVIRONMENT", "production").lower() == "development":
        logger.info("Running in development mode - enabling debug endpoints")
        app.include_router(debug.router, prefix="/api/debug", tags=["debug"])
    
    # Add custom docs endpoint
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Serve custom Swagger UI."""
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title=f"{settings.app_name} - API Documentation",
            swagger_favicon_url="",
        )
    
    # Customize OpenAPI schema
    def custom_openapi():
        """
        Generate custom OpenAPI schema.
        
        This function is called by FastAPI to generate the OpenAPI schema.
        We can customize the schema here if needed.
        """
        if app.openapi_schema:
            return app.openapi_schema
        
        openapi_schema = get_openapi(
            title=settings.app_name,
            version=settings.app_version,
            description="Memory-Enhanced RAG Chatbot API built with FastAPI",
            routes=app.routes,
        )
        
        # Example customization: Add a security scheme
        # openapi_schema["components"] = {"securitySchemes": {"bearerAuth": {"type": "http", "scheme": "bearer"}}}
        # openapi_schema["security"] = [{"bearerAuth": []}]

        # Add external documentation link
        # openapi_schema["externalDocs"] = {
        #     "description": "Find more info here",
        #     "url": "https://example.com/docs"
        # }
        
        app.openapi_schema = openapi_schema
        return app.openapi_schema
    
    app.openapi = custom_openapi
    
    # Add health check endpoint
    @app.get("/health", tags=["health"])
    async def health_check(settings: Settings = Depends(get_settings)):
        """
        Check if the API is running properly.
        
        Returns:
            Health status and configuration information
        """
        health_info = {
            "status": "healthy",
            "version": settings.app_version,
            "debug": settings.debug
        }
        
        # Check LLM providers if needed
        llm_status = await check_llm_providers(settings)
        health_info["llm_providers"] = llm_status
        health_info["default_llm_provider"] = settings.default_llm_provider.value
        
        # Check memory status
        health_info["memory_enabled"] = settings.memory_enabled
        if settings.memory_enabled:
            health_info["memory_types"] = settings.get_enabled_memory_types()
        
        return health_info
    
    # Add providers endpoint
    @app.get("/api/providers", tags=["providers"])
    async def get_providers(settings: Settings = Depends(get_settings)):
        """
        Get available LLM providers and the default provider.
        Returns:
            Dictionary with provider availability and default provider
        """
        llm_status = await check_llm_providers(settings)
        return {
            "providers": llm_status,
            "default": settings.default_llm_provider.value
        }
    
    # Return the configured app
    return app


# Create the application instance
app = create_application()

if __name__ == "__main__":
    """
    Run the application directly for development.
    
    In production, use a proper ASGI server like uvicorn or hypercorn.
    """
    import uvicorn
    
    settings = get_settings()
    uvicorn.run(
        "app.main:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=settings.debug,
        log_level=settings.log_level.lower()
    )