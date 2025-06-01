"""
GLABITAI: GLP-1 Treatment Follow-up AI Agent Package

A comprehensive AI-powered clinical decision support system for GLP-1 treatment
patient care, featuring MongoDB-centric architecture with progressive AI framework adoption.

Architecture Overview:
- MongoDB: Primary clinical database (dynamic events, conversations, AI insights)
- Chroma DB: Vector database for knowledge base (MVP phase)
- Redis: Caching and session management
- PydanticAI: Type-safe clinical validation (Phase 1)
- Groq + Llama: Free, high-performance LLM integration
- Progressive Scaling: Agno (Phase 2) → LangGraph + CrewAI (Phase 3)

Clinical Focus:
- Spanish-speaking GLP-1 treatment patients
- Diabetes/obesity medication management and monitoring
- Cultural adaptations for Hispanic/Latino communities
- Evidence-based clinical decision support for GLP-1 medications
- Side effects monitoring (nausea, vomiting, gastrointestinal issues)
- HIPAA-compliant data handling
"""

__version__ = "0.1.0"
__author__ = "GLABITAI Development Team"
__description__ = "GLP-1 Treatment Follow-up AI Agent"
__license__ = "MIT"

# =============================================================================
# CORE IMPORTS - Available at package level
# =============================================================================

# Database Management (MongoDB-centric architecture)
from .database import (
    MongoDBManager,
    ChromaDBManager, 
    RedisManager,
    DatabaseConfig
)

# AI Agents (PydanticAI primary framework)
from .agents import (
    GLABITAIClinicalAgent,
    ClinicalValidationAgent,
    KnowledgeRetrievalAgent
)

# Clinical Models and Validation
from .clinical import (
    ClinicalEvent,
    PatientConversation,
    BariatricGuidance,
    ClinicalSafetyValidator
)

# Knowledge Base Management
from .knowledge import (
    ClinicalKnowledgeBase,
    VectorSearchManager,
    ClinicalContentLoader
)

# Utilities and Helpers
from .utils import (
    ConfigManager,
    LoggingManager,
    SecurityManager,
    PerformanceMonitor
)

# =============================================================================
# PACKAGE CONFIGURATION
# =============================================================================

# Default configuration settings
DEFAULT_CONFIG = {
    "mongodb": {
        "database": "glabitai_glp1_clinical",
        "collections": {
            "clinical_events": "dynamic_glp1_events",
            "conversations": "glp1_patient_conversations", 
            "ai_logs": "glp1_ai_decision_logs",
            "knowledge_chunks": "glp1_clinical_knowledge"
        }
    },
    "ai_models": {
        "primary_llm": "llama3-70b-8192",  # Groq free tier
        "fallback_llm": "llama3-8b-8192",  # Groq fallback
        "provider": "groq",  # Primary provider
        "embedding_model": "sentence-transformers/distiluse-base-multilingual-cased",
        "clinical_validation": True,
        "spanish_support": True
    },
    "clinical_settings": {
        "confidence_threshold": 0.8,
        "escalation_threshold": 0.3,
        "max_response_tokens": 500,
        "evidence_levels": ["A", "B", "C", "D"],
        "languages": ["es", "en"],
        "cultural_context": "hispanic_latino",
        "treatment_focus": "glp1_medications"
    },
    "monitoring": {
        "enable_opik": True,
        "enable_langfuse": True,
        "enable_logfire": True,
        "clinical_safety_checks": True,
        "glp1_side_effects_monitoring": True
    }
}

# =============================================================================
# QUICK START FUNCTIONS
# =============================================================================

def initialize_glabitai(config_path: str = None, env_file: str = ".env"):
    """
    Quick initialization of GLABITAI system with default configuration.
    
    Args:
        config_path: Optional path to custom configuration file
        env_file: Path to environment variables file
        
    Returns:
        Initialized GLABITAI system components
        
    Example:
        >>> from glabitai import initialize_glabitai
        >>> system = initialize_glabitai()
        >>> agent = system.clinical_agent
        >>> db = system.database_manager
    """
    from .utils import ConfigManager
    from .database import MongoDBManager
    from .agents import GLABITAIClinicalAgent
    
    # Load configuration
    config = ConfigManager(config_path=config_path, env_file=env_file)
    
    # Initialize core components
    database_manager = MongoDBManager(config=config.database)
    clinical_agent = GLABITAIClinicalAgent(config=config.ai_models)
    
    class GLABITAISystem:
        def __init__(self):
            self.config = config
            self.database_manager = database_manager
            self.clinical_agent = clinical_agent
            
    return GLABITAISystem()

def create_clinical_agent(model: str = "llama3-70b-8192", spanish_support: bool = True):
    """
    Quick creation of a GLP-1 clinical agent with default settings.
    
    Args:
        model: Groq Llama model to use for clinical validation
        spanish_support: Enable Spanish language processing
        
    Returns:
        Configured GLABITAIClinicalAgent for GLP-1 treatment
        
    Example:
        >>> from glabitai import create_clinical_agent
        >>> agent = create_clinical_agent()
        >>> response = await agent.process_patient_query("Me siento muy nauseosa con la semaglutida")
    """
    from .agents import GLABITAIClinicalAgent
    
    return GLABITAIClinicalAgent(
        model=model,
        provider="groq",  # Using Groq for free Llama models
        spanish_support=spanish_support,
        clinical_validation=True,
        cultural_adaptations=True,
        treatment_focus="glp1_medications"
    )

def setup_knowledge_base(clinical_guidelines_path: str = "./data/glp1_clinical_guidelines"):
    """
    Quick setup of GLP-1 clinical knowledge base with vector search.
    
    Args:
        clinical_guidelines_path: Path to GLP-1 clinical guidelines directory
        
    Returns:
        Configured ClinicalKnowledgeBase for GLP-1 treatment
        
    Example:
        >>> from glabitai import setup_knowledge_base
        >>> kb = setup_knowledge_base()
        >>> results = await kb.search_clinical_guidance("semaglutide side effects")
    """
    from .knowledge import ClinicalKnowledgeBase
    
    return ClinicalKnowledgeBase(
        vector_db="chroma",  # MVP phase default
        content_path=clinical_guidelines_path,
        collections=[
            "glp1_clinical_guidelines",
            "glp1_medication_protocols",
            "glp1_side_effects_management",
            "nutrition_guidance_glp1",
            "diabetes_management_protocols", 
            "cultural_adaptations"
        ]
    )

# =============================================================================
# CLINICAL SAFETY & VALIDATION
# =============================================================================

def validate_clinical_response(response: dict, patient_context: dict = None):
    """
    Validate clinical response for safety and compliance.
    
    Args:
        response: AI-generated clinical response 
        patient_context: Optional patient context for validation
        
    Returns:
        Validation results with safety flags
        
    Example:
        >>> from glabitai import validate_clinical_response
        >>> validation = validate_clinical_response(ai_response, patient_data)
        >>> if validation.escalation_required:
        ...     notify_clinician(validation.safety_flags)
    """
    from .clinical import ClinicalSafetyValidator
    
    validator = ClinicalSafetyValidator()
    return validator.validate_response(response, patient_context)

# =============================================================================
# DEVELOPMENT UTILITIES
# =============================================================================

def get_sample_data(data_type: str = "conversations"):
    """
    Get sample data for development and testing.
    
    Args:
        data_type: Type of sample data ("conversations", "clinical_events", "guidelines")
        
    Returns:
        Sample data for testing
    """
    from .utils import SampleDataGenerator
    
    generator = SampleDataGenerator()
    return generator.get_sample_data(data_type)

def setup_development_monitoring():
    """
    Setup monitoring and observability for development environment.
    
    Returns:
        Configured monitoring system
    """
    from .utils import PerformanceMonitor
    
    return PerformanceMonitor(
        enable_opik=True,
        enable_langfuse=True,
        enable_logfire=True,
        development_mode=True
    )

# =============================================================================
# PACKAGE HEALTH CHECK
# =============================================================================

def health_check():
    """
    Perform system health check and return status.
    
    Returns:
        Health check results
    """
    health_status = {
        "package_version": __version__,
        "dependencies": {},
        "configuration": {},
        "services": {}
    }
    
    # Check core dependencies
    try:
        import pydantic_ai
        health_status["dependencies"]["pydantic_ai"] = "✅ Available"
    except ImportError:
        health_status["dependencies"]["pydantic_ai"] = "❌ Missing"
    
    try:
        import pymongo
        health_status["dependencies"]["pymongo"] = "✅ Available"
    except ImportError:
        health_status["dependencies"]["pymongo"] = "❌ Missing"
    
    try:
        import chromadb
        health_status["dependencies"]["chromadb"] = "✅ Available"
    except ImportError:
        health_status["dependencies"]["chromadb"] = "❌ Missing"
    
    return health_status

# =============================================================================
# MODULE EXPORTS
# =============================================================================

__all__ = [
    # Version info
    "__version__",
    "__author__", 
    "__description__",
    
    # Core classes
    "MongoDBManager",
    "ChromaDBManager",
    "RedisManager",
    "GLABITAIClinicalAgent",
    "ClinicalKnowledgeBase",
    
    # Models
    "ClinicalEvent",
    "PatientConversation", 
    "BariatricGuidance",
    
    # Quick start functions
    "initialize_glabitai",
    "create_clinical_agent",
    "setup_knowledge_base",
    
    # Utilities
    "validate_clinical_response",
    "get_sample_data",
    "setup_development_monitoring",
    "health_check",
    
    # Configuration
    "DEFAULT_CONFIG"
]