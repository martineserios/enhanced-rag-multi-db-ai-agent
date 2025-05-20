"""
Prompt templates for the medical research agent.

This module defines the prompt templates used by the medical research agent
for generating responses to medical queries with proper citations and evidence levels.
"""
from typing import Dict, Any, Optional, List
from app.services.agents.base import BasePromptTemplate

class MedicalResearchPromptTemplate(BasePromptTemplate):
    """Prompt template for the medical research agent."""
    
    # Validation prompts
    QUERY_VALIDATION_PROMPT = (
        "Validate if this medical query is appropriate for research purposes. "
        "Check for:\n"
        "1. Personal medical advice requests\n"
        "2. Emergency situations\n"
        "3. Inappropriate or harmful content\n\n"
        "Query: {query}\n\n"
        "Provide validation in JSON format with the following structure:\n"
        "{\n"
        '  "is_appropriate": boolean,\n'
        '  "concerns": ["concern1", "concern2"],\n'
        '  "suggestions": ["suggestion1", "suggestion2"]\n'
        "}\n\n"
        "Rules for JSON formatting:\n"
        "1. The response MUST be a valid JSON object\n"
        "2. The response MUST start with '{' and end with '}'\n"
        "3. All keys MUST be double-quoted strings\n"
        "4. All string values MUST be double-quoted\n"
        "5. Arrays MUST use square brackets []\n"
        "6. Boolean values must be true or false (lowercase)\n"
        "7. Do not include any explanatory text outside the JSON object\n\n"
        "Example of valid response:\n"
        '{"is_appropriate": true, "concerns": ["query is too broad"], "suggestions": ["specify the medical condition", "include relevant symptoms"]}'
    )
    
    # Literature retrieval prompts
    QUERY_ENHANCEMENT_PROMPT = (
        "Enhance this medical query with relevant terminology and concepts. "
        "Include related medical terms, conditions, and procedures.\n\n"
        "Original query: {query}\n"
        "Detected medical terms: {terms}\n\n"
        "Provide an enhanced query that maintains the original intent "
        "while incorporating relevant medical terminology. "
        "Focus on:\n"
        "1. Medical conditions and diagnoses\n"
        "2. Treatments and procedures\n"
        "3. Relevant anatomy and physiology\n"
        "4. Clinical guidelines and standards\n"
        "5. Research methodologies"
    )
    
    # Evidence processing prompts
    CITATION_VALIDATION_PROMPT = (
        "Validate these medical citations for accuracy and completeness. "
        "Check for:\n"
        "1. Proper formatting\n"
        "2. Complete information\n"
        "3. Accurate evidence levels\n"
        "4. Appropriate medical terminology\n\n"
        "Citations: {citations}\n\n"
        "Provide validation in JSON format with the following structure:\n"
        "{\n"
        '  "valid_citations": [{"citation": {...}, "is_valid": true}],\n'
        '  "invalid_citations": [{"citation": {...}, "issues": ["issue1", "issue2"]}],\n'
        '  "suggestions": [{"citation": {...}, "suggestion": "..."}]\n'
        "}\n\n"
        "Rules for JSON formatting:\n"
        "1. The response MUST be a valid JSON object\n"
        "2. The response MUST start with '{' and end with '}'\n"
        "3. All keys MUST be double-quoted strings\n"
        "4. All string values MUST be double-quoted\n"
        "5. Arrays MUST use square brackets []\n"
        "6. Boolean values must be true or false (lowercase)\n"
        "7. Objects in arrays must be complete and properly formatted\n"
        "8. Do not include any explanatory text outside the JSON object\n\n"
        "Example of valid response:\n"
        '{"valid_citations": [{"citation": {"title": "Clinical Guidelines for Hypertension", "authors": ["Smith J", "Jones M"], "year": "2023"}, "is_valid": true}], "invalid_citations": [{"citation": {"title": "Hypertension Study"}, "issues": ["missing authors", "missing year"]}], "suggestions": [{"citation": {"title": "Hypertension Study"}, "suggestion": "Add authors and publication year"}]}'
    )
    
    # Response generation prompts
    RESPONSE_VALIDATION_PROMPT = (
        "Validate this medical response for:\n"
        "1. Accuracy of medical information\n"
        "2. Proper use of medical terminology\n"
        "3. Appropriate citation usage\n"
        "4. Clarity and completeness\n"
        "5. Absence of harmful or inappropriate content\n\n"
        "Original query terms: {terms}\n"
        "Citations used: {citations}\n"
        "Response: {response}\n\n"
        "Provide validation in JSON format with the following structure:\n"
        "{\n"
        '  "is_valid": boolean,\n'
        '  "accuracy_score": float,\n'
        '  "terminology_score": float,\n'
        '  "citation_score": float,\n'
        '  "clarity_score": float,\n'
        '  "issues": ["issue1", "issue2"],\n'
        '  "suggestions": ["suggestion1", "suggestion2"]\n'
        "}\n\n"
        "Rules for JSON formatting:\n"
        "1. The response MUST be a valid JSON object\n"
        "2. The response MUST start with '{' and end with '}'\n"
        "3. All keys MUST be double-quoted strings\n"
        "4. All string values MUST be double-quoted\n"
        "5. Arrays MUST use square brackets []\n"
        "6. Boolean values must be true or false (lowercase)\n"
        "7. Float values must be between 0.0 and 1.0\n"
        "8. Do not include any explanatory text outside the JSON object\n\n"
        "Example of valid response:\n"
        '{"is_valid": true, "accuracy_score": 0.95, "terminology_score": 0.9, "citation_score": 0.85, "clarity_score": 0.8, "issues": ["missing citation for treatment recommendation"], "suggestions": ["add citation for the recommended treatment", "clarify the dosage information"]}'
    )
    
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the medical research agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        # Base system prompt
        prompt = (
            "You are a medical research assistant specialized in providing evidence-based "
            "responses with citations from medical literature, clinical guidelines, and "
            "research papers. Your responses should be accurate, well-cited, and include "
            "appropriate clinical context. Always prioritize peer-reviewed sources and "
            "clinical guidelines when available."
        )
        
        # Add medical terminology context if provided
        medical_terms = kwargs.get("medical_terms", {})
        if medical_terms:
            prompt += "\n\nDetected Medical Terminology:"
            for category, terms in medical_terms.items():
                if terms:
                    prompt += f"\n- {category.title()}: {', '.join(terms)}"
        
        # Add clinical guidelines context if available
        has_guidelines = kwargs.get("has_guidelines", False)
        if has_guidelines:
            prompt += (
                "\n\nClinical guidelines are available for this query. "
                "Prioritize information from these guidelines in your response."
            )
        
        # Add context if provided
        if context:
            prompt += (
                "\n\nYou have access to the following medical literature and guidelines "
                "that may help answer the user's question. Use this information to "
                "provide an evidence-based response with appropriate citations:\n\n"
                f"{context}"
            )
        
        # Add citation style instructions
        citation_style = settings.get("citation_style", "AMA") if settings else "AMA"
        max_citations = settings.get("max_citations", 5) if settings else 5
        evidence_level = settings.get("evidence_level", "all") if settings else "all"
        
        prompt += f"\n\nCitation Guidelines:"
        prompt += f"\n- Use {citation_style} citation style"
        prompt += f"\n- Include up to {max_citations} relevant citations"
        prompt += f"\n- Prioritize {evidence_level} level evidence"
        prompt += "\n- Always cite clinical guidelines when available"
        prompt += "\n- Include publication year and journal name in citations"
        
        # Add medical-specific instructions
        prompt += (
            "\n\nMedical Response Guidelines:"
            "\n1. Always provide evidence-based information"
            "\n2. Include relevant clinical context"
            "\n3. Note any limitations or uncertainties"
            "\n4. Disclose if information is from non-peer-reviewed sources"
            "\n5. Include relevant clinical guidelines when available"
            "\n6. Note the level of evidence for each claim"
            "\n7. Be clear about any off-label uses or experimental treatments"
            "\n8. Use appropriate medical terminology"
            "\n9. Maintain professional and clinical tone"
            "\n10. Include relevant statistics when available"
        )
        
        # Add disclaimer
        prompt += (
            "\n\nIMPORTANT: Your responses are for informational purposes only and "
            "should not be considered medical advice. Always consult with qualified "
            "healthcare professionals for medical decisions."
        )
        
        return prompt
    
    def get_query_validation_prompt(self, query: str) -> str:
        """Get the prompt for validating medical queries."""
        return self.QUERY_VALIDATION_PROMPT.format(query=query)
    
    def get_query_enhancement_prompt(self, query: str, terms: Dict[str, List[str]]) -> str:
        """Get the prompt for enhancing medical queries."""
        return self.QUERY_ENHANCEMENT_PROMPT.format(
            query=query,
            terms=terms
        )
    
    def get_citation_validation_prompt(self, citations: List[Dict[str, Any]]) -> str:
        """Get the prompt for validating medical citations."""
        return self.CITATION_VALIDATION_PROMPT.format(citations=citations)
    
    def get_response_validation_prompt(
        self,
        response: str,
        terms: Dict[str, List[str]],
        citations: List[Dict[str, Any]]
    ) -> str:
        """Get the prompt for validating medical responses."""
        return self.RESPONSE_VALIDATION_PROMPT.format(
            response=response,
            terms=terms,
            citations=citations
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
            source: The source of the context (e.g. "Medical Literature", "Clinical Guidelines")
            content: The context content
            relevance: Relevance score for the context (0.0 to 1.0)
            
        Returns:
            Formatted context string
        """
        return (
            f"## {source} (Relevance: {relevance:.2f})\n"
            f"Content:\n{content}\n"
            f"Evidence Level: {self._get_evidence_level(source)}\n"
            f"Relevance Score: {relevance:.2f}\n"
            "Please use this information appropriately in your response, "
            "citing the source according to the specified citation style.\n"
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
                f"Medical Query: {message}\n"
                f"Additional Clinical Context: {context}\n"
                "Please provide an evidence-based response with appropriate citations."
            )
        return (
            f"Medical Query: {message}\n"
            "Please provide an evidence-based response with appropriate citations."
        )
    
    def _get_evidence_level(self, source: str) -> str:
        """
        Get the evidence level for a source.
        
        Args:
            source: The source of the context
            
        Returns:
            The evidence level as a string
        """
        source_lower = source.lower()
        if "systematic review" in source_lower or "meta-analysis" in source_lower:
            return "Level 1 (Systematic Review)"
        elif "randomized controlled trial" in source_lower or "rct" in source_lower:
            return "Level 2 (RCT)"
        elif "cohort study" in source_lower or "case-control" in source_lower:
            return "Level 3 (Observational Study)"
        elif "case series" in source_lower or "case report" in source_lower:
            return "Level 4 (Case Study)"
        else:
            return "Level 5 (Expert Opinion)" 