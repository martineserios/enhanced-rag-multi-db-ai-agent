"""
Clinical prompt templates (Spanish-speaking).

This module defines the prompt templates used by the Spanish-speaking clinical agent for
direct diagnosis and treatment recommendations.
"""
from typing import Dict, Any, Optional, List
from app.services.agents.base import BasePromptTemplate

class ClinicalPromptTemplate(BasePromptTemplate):
    """Prompt template for the Spanish-speaking clinical agent."""
    
    # Analysis prompts
    SYMPTOM_ANALYSIS_PROMPT = (
        "Analiza estos síntomas e información médica para identificar posibles condiciones:\n\n"
        "Síntomas: {sintomas}\n"
        "Condiciones Conocidas: {condiciones}\n"
        "Severidad: {severidad}\n"
        "Duración: {duracion}\n"
        "Historial del Paciente: {historial}\n\n"
        "Proporciona un análisis estructurado enfocado en:\n"
        "1. Síntomas principales y su significancia\n"
        "2. Posibles condiciones subyacentes\n"
        "3. Factores de riesgo y señales de alerta\n"
        "4. Nivel de urgencia\n"
        "5. Acciones inmediatas recomendadas"
    )
    
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the Spanish-speaking clinical agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        # Base system prompt
        prompt = (
            "Eres un asistente clínico enfocado en proporcionar evaluaciones médicas claras y accionables. "
            "Tu rol es:\n"
            "1. Analizar síntomas e historial médico\n"
            "2. Proporcionar diagnósticos claros o posibles condiciones\n"
            "3. Evaluar el nivel de urgencia\n"
            "4. Recomendar acciones inmediatas\n"
            "5. Sugerir opciones de tratamiento\n\n"
            "Siempre prioriza la seguridad del paciente y la comunicación clara. "
            "Sé directo y específico en tus recomendaciones."
        )
        
        # Add detected terms context if provided
        detected_terms = kwargs.get("detected_terms", {})
        if detected_terms:
            prompt += "\n\nInformación Detectada:"
            for category, terms in detected_terms.items():
                if terms:
                    prompt += f"\n- {category.title()}: {', '.join(terms)}"
        
        # Add patient history if available
        patient_history = kwargs.get("patient_history", {})
        if patient_history:
            prompt += "\n\nHistorial del Paciente:\n" + str(patient_history)
        
        # Add context if provided
        if context:
            prompt += f"\n\nContexto Adicional:\n{context}"
        
        # Add clinical guidelines
        prompt += (
            "\n\nGuías Clínicas:"
            "\n1. Siempre evalúa la urgencia primero"
            "\n2. Considera condiciones comunes antes que las raras"
            "\n3. Busca señales de alerta y signos de advertencia"
            "\n4. Considera el historial médico del paciente"
            "\n5. Recomienda el nivel de atención apropiado"
            "\n6. Sé claro sobre cuándo buscar atención de emergencia"
            "\n7. Proporciona recomendaciones específicas y accionables"
            "\n8. Considera posibles complicaciones"
            "\n9. Nota cualquier contraindicación"
            "\n10. Incluye recomendaciones de seguimiento"
        )
        
        # Add disclaimer
        prompt += (
            "\n\nIMPORTANTE: Este es un asistente de IA que proporciona orientación general. "
            "Para emergencias médicas, llame a los servicios de emergencia inmediatamente. "
            "Siempre consulte con profesionales de la salud para decisiones médicas."
        )
        
        return prompt
    
    def get_symptom_analysis_prompt(
        self,
        sintomas: List[str],
        condiciones: List[str],
        severidad: List[str],
        duracion: List[str],
        historial: Optional[Dict[str, Any]] = None
    ) -> str:
        """Get the prompt for analyzing symptoms and medical information in Spanish."""
        return self.SYMPTOM_ANALYSIS_PROMPT.format(
            sintomas=", ".join(sintomas) if sintomas else "Ninguno reportado",
            condiciones=", ".join(condiciones) if condiciones else "Ninguna reportada",
            severidad=", ".join(severidad) if severidad else "No especificada",
            duracion=", ".join(duracion) if duracion else "No especificada",
            historial=str(historial) if historial else "Sin historial significativo"
        )
    
    def format_context(
        self,
        source: str,
        content: str,
        relevance: float = 1.0
    ) -> str:
        """
        Format context information for inclusion in the prompt.
        
        Args:
            source: The source of the context
            content: The context content
            relevance: Relevance score for the context (0.0 to 1.0)
            
        Returns:
            Formatted context string
        """
        return (
            f"## {source} (Relevancia: {relevance:.2f})\n"
            f"Contenido:\n{content}\n"
            "Por favor, considera esta información en tu evaluación clínica.\n"
        )
    
    def format_user_message(
        self,
        message: str,
        **kwargs
    ) -> str:
        """
        Format a user message for inclusion in the prompt.
        
        Args:
            message: The user's message
            **kwargs: Additional parameters for message formatting
            
        Returns:
            Formatted user message
        """
        # Add any additional context from kwargs
        context = kwargs.get("context", "")
        if context:
            return (
                f"Reporte del Paciente: {message}\n"
                f"Contexto Adicional: {context}\n"
                "Por favor, proporciona una evaluación clínica y recomendaciones."
            )
        return (
            f"Reporte del Paciente: {message}\n"
            "Por favor, proporciona una evaluación clínica y recomendaciones."
        ) 