"""
Clinical Agent Tools.

This module contains tools that can be used by the clinical agent to perform specific tasks
like looking up medication information, checking drug interactions, etc.
"""
from typing import Dict, Any, Optional, List, Type, Union
from pydantic import BaseModel, Field
from langchain_core.tools import BaseTool, StructuredTool, tool
from app.core.logging import get_logger
import requests

logger = get_logger(__name__)

class BaseClinicalTool(BaseTool):
    """Base class for all clinical tools."""
    
    def _handle_error(self, error: Exception) -> str:
        """Handle errors in a user-friendly way."""
        logger.error(f"Error in {self.name}: {str(error)}")
        return f"Lo siento, ocurrió un error al procesar su solicitud. Por favor, intente nuevamente más tarde."


class MedicationLookupInput(BaseModel):
    """Input for the medication lookup tool."""
    medication_name: str = Field(..., description="The name of the medication to look up")
    language: str = Field("es", description="Language for the response (default: es for Spanish)")


class MedicationLookupTool(BaseClinicalTool):
    """Tool for looking up medication information."""
    
    name: str = "lookup_medication"
    description: str = """
    Busca información sobre medicamentos incluyendo dosis, efectos secundarios y precauciones.
    Útil cuando el paciente pregunta sobre medicamentos específicos o cuando se necesita
    verificar información sobre un medicamento.
    """
    args_schema: Type[BaseModel] = MedicationLookupInput
    
    def _run(
        self, 
        medication_name: str, 
        language: str = "es",
        **kwargs
    ) -> str:
        """Look up medication information.
        
        Args:
            medication_name: Name of the medication to look up
            language: Language for the response (default: "es")
            **kwargs: Additional context (may include request_id, conversation_id, etc.)
            
        Returns:
            Formatted information about the medication
        """
        # Extract request context for logging
        request_id = kwargs.get('request_id', 'unknown')
        conversation_id = kwargs.get('conversation_id', 'unknown')
        
        # Add context to logger
        logger_ctx = logger.bind(
            request_id=request_id,
            conversation_id=conversation_id,
            tool_name=self.name
        )
        
        logger_ctx.info(f"[TOOL_START] Starting execution")
        logger_ctx.debug(
            "[TOOL_INPUT]",
            medication_name=medication_name,
            language=language,
            **{k: v for k, v in kwargs.items() if k not in ['request_id', 'conversation_id']}
        )
        
        try:
            logger_ctx.info("[TOOL_ACTION] Looking up medication")
            # This is a mock implementation - in a real system, you would
            # call a medication database API here
            mock_data = {
                "paracetamol": {
                    "name": "Paracetamol",
                    "description": "Analgésico y antipirético utilizado para aliviar el dolor y reducir la fiebre.",
                    "dose": "500-1000mg cada 6-8 horas (máx. 4000mg/día)",
                    "side_effects": "Puede causar daño hepático en dosis altas o con consumo de alcohol.",
                    "precautions": "Evitar con enfermedad hepática o consumo de alcohol. Consultar en embarazo/lactancia."
                },
                "ibuprofeno": {
                    "name": "Ibuprofeno",
                    "description": "Antiinflamatorio no esteroideo (AINE) que reduce el dolor, la inflamación y la fiebre.",
                    "dose": "200-400mg cada 6-8 horas (máx. 1200-2400mg/día según indicación médica)",
                    "side_effects": "Puede causar malestar estomacal, úlceras y aumentar el riesgo de sangrado.",
                    "precautions": "Evitar con úlceras, enfermedad renal o cardiaca. Tomar con alimentos."
                },
                "omeprazol": {
                    "name": "Omeprazol",
                    "description": "Inhibidor de la bomba de protones que reduce la producción de ácido estomacal.",
                    "dose": "20-40mg una vez al día, preferiblemente por la mañana.",
                    "side_effects": "Dolor de cabeza, diarrea, dolor abdominal, náuseas.",
                    "precautions": "Tomar 30-60 minutos antes de la primera comida del día. No masticar ni triturar las cápsulas."
                },
                "aspirina": {
                    "name": "Ácido Acetilsalicílico (Aspirina)",
                    "description": "Antiinflamatorio, analgésico, antipirético y antiagregante plaquetario.",
                    "dose": "Dosis varía según indicación (analgésica: 325-650mg cada 4-6h, antiagregante: 75-325mg/día)",
                    "side_effects": "Puede causar malestar estomacal, úlceras, sangrado y síndrome de Reye en niños.",
                    "precautions": "Evitar en niños con fiebre. No usar si hay trastornos de coagulación o alergia a AINEs."
                }
            }
            
            med_key = medication_name.lower()
            if med_key in mock_data:
                med = mock_data[med_key]
                result = (
                    f"Información sobre {med['name']}:\n"
                    f"• Descripción: {med['description']}\n"
                    f"• Dosis: {med['dose']}\n"
                    f"• Efectos secundarios: {med['side_effects']}\n"
                    f"• Precauciones: {med['precautions']}"
                )
                logger_ctx.info(
                    "[TOOL_SUCCESS] Found medication information",
                    medication=medication_name,
                    result_length=len(result)
                )
                return result
            else:
                error_msg = f"No information found for medication: {medication_name}"
                logger_ctx.warning(
                    "[TOOL_WARNING] Medication not found",
                    medication=medication_name
                )
                return f"No se encontró información sobre {medication_name} en la base de datos."
                
        except Exception as e:
            logger_ctx.error(
                "[TOOL_ERROR] Error in tool execution",
                error=str(e),
                error_type=type(e).__name__,
                exc_info=True
            )
            return self._handle_error(e)


def get_clinical_tools() -> list[BaseClinicalTool]:
    """Get all available clinical tools.
    
    Returns:
        List of instantiated clinical tools
    """
    tools = [
        MedicationLookupTool()
    ]
    logger.info(f"Registered {len(tools)} clinical tools: {[t.name for t in tools]}")
    return tools
