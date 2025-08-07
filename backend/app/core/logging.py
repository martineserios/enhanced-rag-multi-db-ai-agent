"""
Logging configuration for GlabitAI Backend

Medical-grade logging with audit trail capabilities
for healthcare compliance.
"""

import logging
import logging.config
import sys
from datetime import datetime
from typing import Dict, Any

from app.core.config import get_settings


def setup_logging() -> None:
    """
    Setup logging configuration for medical application.
    
    Includes:
    - Console logging for development
    - File logging for audit trails
    - Medical interaction logging
    - Error tracking for patient safety
    """
    settings = get_settings()
    
    logging_config: Dict[str, Any] = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": settings.LOG_FORMAT,
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "detailed": {
                "format": (
                    "%(asctime)s - %(name)s - %(levelname)s - "
                    "%(module)s:%(funcName)s:%(lineno)d - %(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S"
            },
            "medical_audit": {
                "format": (
                    "MEDICAL_AUDIT - %(asctime)s - %(levelname)s - "
                    "%(message)s"
                ),
                "datefmt": "%Y-%m-%d %H:%M:%S"
            }
        },
        "handlers": {
            "console": {
                "level": settings.LOG_LEVEL,
                "class": "logging.StreamHandler",
                "formatter": "standard",
                "stream": sys.stdout
            },
            "file": {
                "level": "INFO",
                "class": "logging.FileHandler",
                "formatter": "detailed",
                "filename": "logs/app.log",
                "mode": "a",
                "encoding": "utf-8"
            },
            "medical_audit": {
                "level": "INFO", 
                "class": "logging.FileHandler",
                "formatter": "medical_audit",
                "filename": "logs/medical_audit.log",
                "mode": "a",
                "encoding": "utf-8"
            },
            "error_file": {
                "level": "ERROR",
                "class": "logging.FileHandler", 
                "formatter": "detailed",
                "filename": "logs/errors.log",
                "mode": "a",
                "encoding": "utf-8"
            }
        },
        "loggers": {
            "": {  # Root logger
                "handlers": ["console", "file", "error_file"],
                "level": settings.LOG_LEVEL,
                "propagate": False
            },
            "app.services.medical": {
                "handlers": ["console", "medical_audit", "error_file"],
                "level": "INFO",
                "propagate": False
            },
            "app.api": {
                "handlers": ["console", "file"],
                "level": "INFO", 
                "propagate": False
            },
            "uvicorn": {
                "handlers": ["console"],
                "level": "INFO",
                "propagate": False
            },
            "fastapi": {
                "handlers": ["console", "file"],
                "level": "INFO",
                "propagate": False
            }
        }
    }
    
    # Create logs directory if it doesn't exist
    import os
    os.makedirs("logs", exist_ok=True)
    
    # Apply logging configuration
    logging.config.dictConfig(logging_config)
    
    # Log startup message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured for {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Log level set to: {settings.LOG_LEVEL}")


def get_medical_logger() -> logging.Logger:
    """
    Get logger specifically for medical interactions.
    
    Used for audit trails and medical decision logging
    required for healthcare compliance.
    """
    return logging.getLogger("app.services.medical")


def log_medical_interaction(
    patient_id: str,
    interaction_type: str,
    details: Dict[str, Any],
    user_agent: str = "system"
) -> None:
    """
    Log medical interaction for audit purposes.
    
    Args:
        patient_id: Anonymized patient identifier
        interaction_type: Type of interaction (chat, alert, decision)
        details: Interaction details for audit
        user_agent: Source of the interaction
    """
    medical_logger = get_medical_logger()
    
    audit_entry = {
        "timestamp": datetime.now().isoformat(),
        "patient_id": patient_id,
        "interaction_type": interaction_type,
        "user_agent": user_agent,
        "details": details
    }
    
    medical_logger.info(f"Medical interaction logged: {audit_entry}")


def log_medical_decision(
    decision_id: str,
    decision_type: str,
    input_data: Dict[str, Any],
    output_data: Dict[str, Any],
    confidence_score: float = 0.0
) -> None:
    """
    Log medical AI decisions for audit and safety tracking.
    
    Args:
        decision_id: Unique decision identifier
        decision_type: Type of medical decision made
        input_data: Input data that led to decision
        output_data: AI decision output
        confidence_score: AI confidence in decision
    """
    medical_logger = get_medical_logger()
    
    decision_entry = {
        "timestamp": datetime.now().isoformat(),
        "decision_id": decision_id,
        "decision_type": decision_type,
        "input_data": input_data,
        "output_data": output_data,
        "confidence_score": confidence_score
    }
    
    medical_logger.info(f"Medical decision logged: {decision_entry}")