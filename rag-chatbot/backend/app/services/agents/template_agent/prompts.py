"""
Prompt template for the template agent.

This module defines the prompt templates used by the template agent for
domain-specific processing and response generation.
"""
from typing import Dict, Any, Optional, List
from app.services.agents.base import BasePromptTemplate

class TemplatePromptTemplate(BasePromptTemplate):
    """Prompt template for the template agent."""
    
    # Processing prompts
    QUERY_ENHANCEMENT_PROMPT = (
        "Enhance this query with relevant domain-specific terminology and concepts. "
        "Include related terms, conditions, and procedures.\n\n"
        "Original query: {query}\n"
        "Detected terms: {terms}\n\n"
        "Provide an enhanced query that maintains the original intent "
        "while incorporating relevant domain terminology. "
        "Focus on:\n"
        "1. Domain-specific concepts\n"
        "2. Related procedures\n"
        "3. Relevant context\n"
        "4. Domain guidelines\n"
        "5. Processing requirements"
    )
    
    # Analysis prompts
    REFERENCE_VALIDATION_PROMPT = (
        "Validate these references for accuracy and completeness. "
        "Check for:\n"
        "1. Proper formatting\n"
        "2. Complete information\n"
        "3. Accurate level assignment\n"
        "4. Appropriate domain terminology\n\n"
        "References: {references}\n\n"
        "Provide validation in JSON format with the following structure:\n"
        "{\n"
        '  "valid_references": [{"reference": {...}, "is_valid": true}],\n'
        '  "invalid_references": [{"reference": {...}, "issues": ["issue1", "issue2"]}],\n'
        '  "suggestions": [{"reference": {...}, "suggestion": "..."}]\n'
        "}"
    )
    
    # Response generation prompts
    RESPONSE_VALIDATION_PROMPT = (
        "Validate this domain-specific response for:\n"
        "1. Accuracy of information\n"
        "2. Proper use of domain terminology\n"
        "3. Appropriate reference usage\n"
        "4. Clarity and completeness\n"
        "5. Domain-specific guidelines\n\n"
        "Original query terms: {terms}\n"
        "References used: {references}\n"
        "Response: {response}\n\n"
        "Provide validation in JSON format with the following structure:\n"
        "{\n"
        '  "is_valid": boolean,\n'
        '  "accuracy_score": float,\n'
        '  "terminology_score": float,\n'
        '  "reference_score": float,\n'
        '  "clarity_score": float,\n'
        '  "issues": ["issue1", "issue2"],\n'
        '  "suggestions": ["suggestion1", "suggestion2"]\n'
        "}"
    )
    
    def get_system_prompt(
        self,
        context: Optional[str] = None,
        settings: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> str:
        """
        Get the system prompt for the template agent.
        
        Args:
            context: Optional context information to include
            settings: Optional agent settings to customize the prompt
            **kwargs: Additional parameters for prompt customization
            
        Returns:
            The formatted system prompt
        """
        # Base system prompt
        prompt = (
            "You are a domain-specific assistant specialized in providing accurate "
            "and well-referenced responses. Your responses should be precise, "
            "well-cited, and include appropriate domain context. Always prioritize "
            "authoritative sources and domain guidelines when available."
        )
        
        # Add domain terminology context if provided
        detected_terms = kwargs.get("detected_terms", {})
        if detected_terms:
            prompt += "\n\nDetected Domain Terminology:"
            for category, terms in detected_terms.items():
                if terms:
                    prompt += f"\n- {category.title()}: {', '.join(terms)}"
        
        # Add specialized data context if available
        has_specialized_data = kwargs.get("has_specialized_data", False)
        if has_specialized_data:
            prompt += (
                "\n\nSpecialized domain data is available for this query. "
                "Prioritize information from these sources in your response."
            )
        
        # Add context if provided
        if context:
            prompt += (
                "\n\nYou have access to the following domain-specific information "
                "that may help answer the user's question. Use this information to "
                "provide a well-referenced response:\n\n"
                f"{context}"
            )
        
        # Add reference style instructions
        reference_style = settings.get("reference_style", "standard") if settings else "standard"
        max_references = settings.get("max_references", 5) if settings else 5
        processing_level = settings.get("processing_level", "all") if settings else "all"
        
        prompt += f"\n\nReference Guidelines:"
        prompt += f"\n- Use {reference_style} reference style"
        prompt += f"\n- Include up to {max_references} relevant references"
        prompt += f"\n- Prioritize {processing_level} level information"
        prompt += "\n- Always cite domain guidelines when available"
        prompt += "\n- Include relevant metadata in references"
        
        # Add domain-specific instructions
        prompt += (
            "\n\nResponse Guidelines:"
            "\n1. Always provide accurate domain-specific information"
            "\n2. Include relevant context"
            "\n3. Note any limitations or uncertainties"
            "\n4. Disclose if information is from non-authoritative sources"
            "\n5. Include relevant domain guidelines when available"
            "\n6. Note the level of authority for each claim"
            "\n7. Use appropriate domain terminology"
            "\n8. Maintain professional tone"
            "\n9. Include relevant statistics when available"
            "\n10. Structure the response clearly"
        )
        
        # Add disclaimer
        prompt += (
            "\n\nIMPORTANT: Your responses are for informational purposes only. "
            "Always verify information with authoritative sources in the domain."
        )
        
        return prompt
    
    def get_query_validation_prompt(self, query: str) -> str:
        """Get the prompt for validating queries."""
        return self.QUERY_VALIDATION_PROMPT.format(query=query)
    
    def get_query_enhancement_prompt(self, query: str, terms: Dict[str, List[str]]) -> str:
        """Get the prompt for enhancing queries."""
        return self.QUERY_ENHANCEMENT_PROMPT.format(
            query=query,
            terms=terms
        )
    
    def get_reference_validation_prompt(self, references: List[Dict[str, Any]]) -> str:
        """Get the prompt for validating references."""
        return self.REFERENCE_VALIDATION_PROMPT.format(references=references)
    
    def get_response_validation_prompt(
        self,
        response: str,
        terms: Dict[str, List[str]],
        references: List[Dict[str, Any]]
    ) -> str:
        """Get the prompt for validating responses."""
        return self.RESPONSE_VALIDATION_PROMPT.format(
            response=response,
            terms=terms,
            references=references
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
            f"## {source} (Relevance: {relevance:.2f})\n"
            f"Content:\n{content}\n"
            f"Processing Level: {self._get_processing_level(source)}\n"
            f"Relevance Score: {relevance:.2f}\n"
            "Please use this information appropriately in your response, "
            "citing the source according to the specified reference style.\n"
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
                f"Domain Query: {message}\n"
                f"Additional Context: {context}\n"
                "Please provide a well-referenced response with appropriate citations."
            )
        return (
            f"Domain Query: {message}\n"
            "Please provide a well-referenced response with appropriate citations."
        )
    
    def _get_processing_level(self, source: str) -> str:
        """
        Get the processing level for a source.
        
        Args:
            source: The source of the context
            
        Returns:
            The processing level as a string
        """
        source_lower = source.lower()
        if "guideline" in source_lower:
            return "Level 1 (Domain Guidelines)"
        elif "authoritative" in source_lower:
            return "Level 1 (Authoritative Source)"
        elif "primary" in source_lower:
            return "Level 2 (Primary Source)"
        elif "secondary" in source_lower:
            return "Level 3 (Secondary Source)"
        elif "tertiary" in source_lower:
            return "Level 4 (Tertiary Source)"
        else:
            return "Level 5 (General Information)" 