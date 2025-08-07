"""
LLM Provider Abstract Base Class and Implementations

Flexible architecture for handling different LLM model providers in the medical AI system.
Supports OpenAI, Anthropic, and Groq with medical-specific configurations.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class ProviderType(Enum):
    """Supported LLM provider types."""
    OPENAI = "openai"
    ANTHROPIC = "anthropic" 
    GROQ = "groq"


class ModelCapability(Enum):
    """Model capabilities for medical AI tasks."""
    MEDICAL_REASONING = "medical_reasoning"
    CLINICAL_CONVERSATION = "clinical_conversation"
    KNOWLEDGE_RETRIEVAL = "knowledge_retrieval"
    PATIENT_MONITORING = "patient_monitoring"


@dataclass
class ModelConfig:
    """Configuration for a specific model."""
    provider: ProviderType
    model_name: str
    max_tokens: int = 1500
    temperature: float = 0.3
    capabilities: List[ModelCapability] = field(default_factory=list)
    medical_validated: bool = False
    hipaa_compliant: bool = False


@dataclass 
class LLMRequest:
    """Standardized request format for all LLM providers."""
    messages: List[Dict[str, str]]
    model_config: Optional[ModelConfig] = None
    system_prompt: Optional[str] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    patient_id: Optional[str] = None
    session_id: Optional[str] = None
    medical_context: Optional[Dict[str, Any]] = None


@dataclass
class LLMResponse:
    """Standardized response format from all LLM providers."""
    content: str
    provider: ProviderType
    model: str
    usage: Optional[Dict[str, Any]] = None
    confidence_score: Optional[float] = None
    medical_validated: bool = False
    metadata: Optional[Dict[str, Any]] = None
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = datetime.now()


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    def __init__(self, api_key: str, default_config: ModelConfig):
        self.api_key = api_key
        self.default_config = default_config
        self.provider_type = self._get_provider_type()
        self.client = None
        self._initialize_client()
    
    @abstractmethod
    def _get_provider_type(self) -> ProviderType:
        """Get the provider type."""
        pass
    
    @abstractmethod 
    def _initialize_client(self) -> None:
        """Initialize the provider-specific client."""
        pass
    
    @abstractmethod
    async def _make_api_call(self, request: LLMRequest) -> Dict[str, Any]:
        """Make the actual API call to the provider."""
        pass
    
    async def generate_response(self, request: LLMRequest) -> LLMResponse:
        """Generate response using the provider's API."""
        try:
            # Validate medical context if provided
            if request.medical_context:
                await self._validate_medical_request(request)
            
            # Make API call
            raw_response = await self._make_api_call(request)
            
            # Process response
            response = self._process_response(raw_response, request)
            
            # Apply medical validation if needed
            if request.medical_context and self.default_config.medical_validated:
                response.medical_validated = await self._validate_medical_response(response, request)
            
            return response
            
        except Exception as e:
            logger.error(f"Error generating response from {self.provider_type.value}: {str(e)}")
            return self._create_error_response(str(e), request)
    
    @abstractmethod
    def _process_response(self, raw_response: Dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Process the raw API response into standardized format."""
        pass
    
    async def _validate_medical_request(self, request: LLMRequest) -> None:
        """Validate medical request parameters."""
        # Ensure conservative temperature for medical accuracy
        if request.temperature and request.temperature > 0.5:
            logger.warning(f"High temperature ({request.temperature}) may reduce medical accuracy")
        
        # Validate medical context
        medical_context = request.medical_context or {}
        required_fields = ["patient_safety_level", "medical_domain"]
        
        for required_field in required_fields:
            if required_field not in medical_context:
                logger.warning(f"Missing medical context field: {required_field}")
    
    async def _validate_medical_response(self, response: LLMResponse, request: LLMRequest) -> bool:
        """Validate medical response for accuracy and safety."""
        # Basic medical validation checks
        content = response.content.lower()
        
        # Check for dangerous medical advice patterns
        dangerous_patterns = [
            "ignore your doctor",
            "stop taking medication",
            "don't need medical attention"
        ]
        
        for pattern in dangerous_patterns:
            if pattern in content:
                logger.error(f"Dangerous medical advice detected: {pattern}")
                return False
        
        # Check for required medical disclaimers
        disclaimer_patterns = [
            "consulte con su médico",
            "consult with your doctor",
            "medical professional"
        ]
        
        has_disclaimer = any(pattern in content for pattern in disclaimer_patterns)
        medical_context = request.medical_context or {}
        if not has_disclaimer and medical_context.get("requires_disclaimer", True):
            logger.warning("Medical response missing required disclaimer")
        
        return True
    
    def _create_error_response(self, error_message: str, request: LLMRequest) -> LLMResponse:
        """Create error response with fallback content."""
        fallback_content = (
            "Lo siento, no puedo procesar su consulta médica en este momento. "
            "Por favor consulte con su médico tratante para obtener asistencia personalizada."
        )
        
        return LLMResponse(
            content=fallback_content,
            provider=self.provider_type,
            model="error_fallback",
            medical_validated=True,
            metadata={"error": error_message, "fallback": True}
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check provider health and availability."""
        return {
            "provider": self.provider_type.value,
            "client_initialized": self.client is not None,
            "api_key_configured": bool(self.api_key),
            "medical_validated": self.default_config.medical_validated,
            "hipaa_compliant": self.default_config.hipaa_compliant
        }
    
    def get_supported_capabilities(self) -> List[ModelCapability]:
        """Get list of supported medical capabilities."""
        return self.default_config.capabilities.copy()


class OpenAIProvider(LLMProvider):
    """OpenAI provider implementation for medical reasoning."""
    
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.OPENAI
    
    def _initialize_client(self) -> None:
        """Initialize OpenAI client."""
        try:
            from openai import OpenAI
            self.client = OpenAI(api_key=self.api_key)
        except ImportError:
            logger.error("OpenAI package not installed")
            raise ImportError("Please install openai package: pip install openai")
    
    async def _make_api_call(self, request: LLMRequest) -> Dict[str, Any]:
        """Make OpenAI API call."""
        messages = request.messages.copy()
        
        # Add system prompt if provided
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})
        
        # Use request config or default
        config = request.model_config or self.default_config
        temperature = request.temperature or config.temperature
        max_tokens = request.max_tokens or config.max_tokens
        
        try:
            response = self.client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                presence_penalty=0.1,
                frequency_penalty=0.1
            )
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage._asdict() if response.usage else None
            }
        except Exception as e:
            logger.error(f"OpenAI API error: {str(e)}")
            raise
    
    def _process_response(self, raw_response: Dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Process OpenAI response."""
        return LLMResponse(
            content=raw_response["content"].strip(),
            provider=self.provider_type,
            model=raw_response["model"],
            usage=raw_response["usage"],
            confidence_score=0.85,  # Default confidence for OpenAI
            metadata={"provider_specific": "openai_response"}
        )


class AnthropicProvider(LLMProvider):
    """Anthropic provider implementation for clinical conversations."""
    
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.ANTHROPIC
    
    def _initialize_client(self) -> None:
        """Initialize Anthropic client."""
        try:
            import anthropic
            self.client = anthropic.Anthropic(api_key=self.api_key)
        except ImportError:
            logger.error("Anthropic package not installed")
            raise ImportError("Please install anthropic package: pip install anthropic")
    
    async def _make_api_call(self, request: LLMRequest) -> Dict[str, Any]:
        """Make Anthropic API call."""
        # Convert messages format for Anthropic
        messages = []
        system_message = None
        
        for msg in request.messages:
            if msg["role"] == "system":
                system_message = msg["content"]
            else:
                messages.append({
                    "role": msg["role"],
                    "content": msg["content"]
                })
        
        # Add system prompt if provided
        if request.system_prompt:
            system_message = request.system_prompt
        
        # Use request config or default
        config = request.model_config or self.default_config
        temperature = request.temperature or config.temperature
        max_tokens = request.max_tokens or config.max_tokens
        
        try:
            response = self.client.messages.create(
                model=config.model_name,
                system=system_message or "",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "content": response.content[0].text,
                "model": response.model,
                "usage": {
                    "prompt_tokens": response.usage.input_tokens,
                    "completion_tokens": response.usage.output_tokens,
                    "total_tokens": response.usage.input_tokens + response.usage.output_tokens
                }
            }
        except Exception as e:
            logger.error(f"Anthropic API error: {str(e)}")
            raise
    
    def _process_response(self, raw_response: Dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Process Anthropic response."""
        return LLMResponse(
            content=raw_response["content"].strip(),
            provider=self.provider_type,
            model=raw_response["model"],
            usage=raw_response["usage"],
            confidence_score=0.88,  # Higher confidence for clinical conversations
            metadata={"provider_specific": "anthropic_response"}
        )


class GroqProvider(LLMProvider):
    """Groq provider implementation for fast knowledge retrieval."""
    
    def _get_provider_type(self) -> ProviderType:
        return ProviderType.GROQ
    
    def _initialize_client(self) -> None:
        """Initialize Groq client."""
        try:
            from groq import Groq
            self.client = Groq(api_key=self.api_key)
        except ImportError:
            logger.error("Groq package not installed") 
            raise ImportError("Please install groq package: pip install groq")
    
    async def _make_api_call(self, request: LLMRequest) -> Dict[str, Any]:
        """Make Groq API call."""
        messages = request.messages.copy()
        
        # Add system prompt if provided
        if request.system_prompt:
            messages.insert(0, {"role": "system", "content": request.system_prompt})
        
        # Use request config or default
        config = request.model_config or self.default_config
        temperature = request.temperature or config.temperature
        max_tokens = request.max_tokens or config.max_tokens
        
        try:
            response = self.client.chat.completions.create(
                model=config.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            return {
                "content": response.choices[0].message.content,
                "model": response.model,
                "usage": response.usage._asdict() if response.usage else None
            }
        except Exception as e:
            logger.error(f"Groq API error: {str(e)}")
            raise
    
    def _process_response(self, raw_response: Dict[str, Any], request: LLMRequest) -> LLMResponse:
        """Process Groq response."""
        return LLMResponse(
            content=raw_response["content"].strip(),
            provider=self.provider_type,
            model=raw_response["model"],
            usage=raw_response["usage"],
            confidence_score=0.82,  # Good for fast retrieval
            metadata={"provider_specific": "groq_response"}
        )


class LLMProviderManager:
    """Manager for coordinating multiple LLM providers."""
    
    def __init__(self):
        self.providers: Dict[ProviderType, LLMProvider] = {}
        self.capability_routing: Dict[ModelCapability, List[ProviderType]] = {}
        self._setup_default_routing()
    
    def _setup_default_routing(self):
        """Setup default capability routing."""
        self.capability_routing = {
            ModelCapability.MEDICAL_REASONING: [ProviderType.OPENAI],
            ModelCapability.CLINICAL_CONVERSATION: [ProviderType.ANTHROPIC, ProviderType.OPENAI],
            ModelCapability.KNOWLEDGE_RETRIEVAL: [ProviderType.GROQ, ProviderType.OPENAI],
            ModelCapability.PATIENT_MONITORING: [ProviderType.OPENAI, ProviderType.ANTHROPIC]
        }
    
    def register_provider(self, provider: LLMProvider):
        """Register an LLM provider."""
        self.providers[provider.provider_type] = provider
        logger.info(f"Registered {provider.provider_type.value} provider")
    
    def get_provider_for_capability(self, capability: ModelCapability) -> Optional[LLMProvider]:
        """Get best provider for specific medical capability."""
        provider_types = self.capability_routing.get(capability, [])
        
        for provider_type in provider_types:
            if provider_type in self.providers:
                provider = self.providers[provider_type]
                if capability in provider.get_supported_capabilities():
                    return provider
        
        # Fallback to any available provider
        return next(iter(self.providers.values())) if self.providers else None
    
    async def generate_medical_response(
        self, 
        capability: ModelCapability,
        request: LLMRequest,
        fallback_providers: Optional[List[ProviderType]] = None
    ) -> LLMResponse:
        """Generate response using appropriate provider for medical capability."""
        
        # Get primary provider
        provider = self.get_provider_for_capability(capability)
        
        if not provider:
            raise ValueError(f"No provider available for capability: {capability}")
        
        try:
            # Set medical context
            if not request.medical_context:
                request.medical_context = {}
            request.medical_context["capability"] = capability.value
            
            response = await provider.generate_response(request)
            return response
            
        except Exception as e:
            logger.error(f"Primary provider {provider.provider_type.value} failed: {str(e)}")
            
            # Try fallback providers
            if fallback_providers:
                for fallback_type in fallback_providers:
                    if fallback_type in self.providers:
                        try:
                            fallback_provider = self.providers[fallback_type]
                            logger.info(f"Trying fallback provider: {fallback_type.value}")
                            return await fallback_provider.generate_response(request)
                        except Exception as fallback_error:
                            logger.error(f"Fallback provider {fallback_type.value} also failed: {str(fallback_error)}")
            
            # Return error response if all providers fail
            return self._create_fallback_response(str(e), request)
    
    async def health_check_all(self) -> Dict[str, Any]:
        """Health check for all registered providers."""
        results = {}
        
        for provider_type, provider in self.providers.items():
            try:
                results[provider_type.value] = await provider.health_check()
            except Exception as e:
                results[provider_type.value] = {
                    "status": "error",
                    "error": str(e)
                }
        
        return {
            "providers": results,
            "total_providers": len(self.providers),
            "healthy_providers": sum(
                1 for result in results.values() 
                if isinstance(result, dict) and result.get("client_initialized", False)
            )
        }
    
    def _create_fallback_response(self, error_message: str, request: LLMRequest) -> LLMResponse:
        """Create fallback response when all providers fail."""
        fallback_content = (
            "Lo siento, no puedo procesar su consulta médica en este momento. "
            "Por favor consulte con su médico tratante para obtener asistencia personalizada."
        )
        
        return LLMResponse(
            content=fallback_content,
            provider=ProviderType.OPENAI,  # Default fallback provider
            model="error_fallback",
            medical_validated=True,
            metadata={"error": error_message, "fallback": True}
        )