# Template Agent

A base template agent that provides a structured foundation for building specialized agents using LangGraph. This template follows the same architecture and best practices as the medical research agent but is designed to be domain-agnostic and easily adaptable.

## Purpose

The template agent serves as a starting point for creating new specialized agents. It provides:

1. A standardized graph-based architecture
2. Reusable components for common agent tasks
3. Best practices for prompt management
4. Structured state management
5. Error handling and logging patterns

## Structure

```
template_agent/
├── graph.py          # Graph implementation and node definitions
├── prompts.py        # Prompt templates and management
└── README.md         # This documentation
```

## Core Components

### 1. Graph Nodes

The template provides four base nodes that can be customized for specific domains:

- `TemplateValidationNode`: Validates queries and domain-specific terms
- `TemplateProcessingNode`: Processes domain-specific information
- `TemplateAnalysisNode`: Analyzes information and prepares references
- `TemplateResponseNode`: Generates domain-specific responses

### 2. State Management

Uses `TemplateChatState` TypedDict for type-safe state management:
```python
class TemplateChatState(TypedDict):
    request: ChatRequest
    conversation_id: str
    context: str
    sources: List[Dict[str, Any]]
    references: List[Dict[str, Any]]
    processing_level: str
    detected_terms: Dict[str, List[str]]
    specialized_data: List[Dict[str, Any]]
    response: Optional[str]
    error: Optional[str]
    metadata: Dict[str, Any]
    metrics: Dict[str, Any]
    next_step: Optional[Literal["process", "analyze", "generate", "error", "end"]]
```

### 3. Prompt Management

The `TemplatePromptTemplate` class provides a foundation for domain-specific prompts:
- Validation prompts
- Processing prompts
- Analysis prompts
- Response generation prompts

## Creating a New Agent

### 1. Basic Setup

1. Create a new directory for your agent:
```bash
mkdir -p app/services/agents/your_agent
```

2. Copy the template files:
```bash
cp template_agent/graph.py your_agent/
cp template_agent/prompts.py your_agent/
```

3. Rename the classes and files to match your domain:
```python
# In graph.py
class YourDomainChatState(TypedDict):
    # Customize state for your domain

class YourDomainValidationNode:
    # Customize validation for your domain
```

### 2. Customizing Components

#### A. State Management
```python
class YourDomainChatState(TypedDict):
    # Add domain-specific fields
    domain_specific_field: str
    # Modify existing fields as needed
    specialized_data: List[YourDomainDataType]
```

#### B. Validation Node
```python
class YourDomainValidationNode:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.llm_service = None
        self.prompt_template = YourDomainPromptTemplate()
    
    async def _detect_domain_terms(self, message: str) -> Dict[str, List[str]]:
        # Implement domain-specific term detection
        pass
```

#### C. Processing Node
```python
class YourDomainProcessingNode:
    async def _enhance_query_with_terms(self, query: str, terms: Dict[str, List[str]]) -> str:
        # Implement domain-specific query enhancement
        pass
```

#### D. Analysis Node
```python
class YourDomainAnalysisNode:
    def _create_reference(self, source: Dict[str, Any], style: str) -> Dict[str, Any]:
        # Implement domain-specific reference creation
        pass
```

#### E. Response Node
```python
class YourDomainResponseNode:
    async def _validate_response(self, response: str, terms: Dict[str, List[str]], references: List[Dict[str, Any]]) -> str:
        # Implement domain-specific response validation
        pass
```

### 3. Customizing Prompts

1. Create a domain-specific prompt template:
```python
class YourDomainPromptTemplate(BasePromptTemplate):
    # Define domain-specific prompts
    DOMAIN_SPECIFIC_PROMPT = "Your domain-specific prompt template"
    
    def get_domain_specific_prompt(self, **kwargs) -> str:
        return self.DOMAIN_SPECIFIC_PROMPT.format(**kwargs)
```

2. Update system prompts:
```python
def get_system_prompt(self, context: Optional[str] = None, settings: Optional[Dict[str, Any]] = None, **kwargs) -> str:
    # Customize system prompt for your domain
    prompt = "You are a domain-specific assistant..."
    # Add domain-specific instructions
    return prompt
```

### 4. Adding Domain-Specific Features

1. Add domain-specific patterns:
```python
DOMAIN_PATTERNS = {
    "category1": r"\b(pattern1|pattern2)\b",
    "category2": r"\b(pattern3|pattern4)\b"
}
```

2. Add domain-specific constants:
```python
DOMAIN_CONSTANTS = {
    "level1": "Description of level 1",
    "level2": "Description of level 2"
}
```

3. Add custom validation rules:
```python
async def _validate_domain_specific_rule(self, input: str) -> None:
    # Implement domain-specific validation
    pass
```

## Best Practices

1. **State Management**
   - Keep state types consistent
   - Use TypedDict for type safety
   - Document state fields

2. **Error Handling**
   - Use custom exceptions
   - Implement proper error recovery
   - Log errors with context

3. **Prompt Management**
   - Keep prompts in separate file
   - Use clear, structured templates
   - Document prompt purposes

4. **Testing**
   - Test each node independently
   - Test complete workflows
   - Include error cases

## Example: Creating a Legal Agent

```python
# In graph.py
LEGAL_PATTERNS = {
    "statute": r"\b(statute|law|regulation|act)\b",
    "case": r"\b(case|precedent|ruling|judgment)\b",
    "jurisdiction": r"\b(jurisdiction|venue|court|tribunal)\b"
}

class LegalChatState(TemplateChatState):
    # Add legal-specific fields
    case_law: List[Dict[str, Any]]
    statutes: List[Dict[str, Any]]
    jurisdiction: str

class LegalValidationNode(TemplateValidationNode):
    async def _detect_legal_terms(self, message: str) -> Dict[str, List[str]]:
        # Implement legal term detection
        pass
```

## Maintenance

1. **Regular Updates**
   - Update domain patterns
   - Refresh prompt templates
   - Monitor performance

2. **Documentation**
   - Document domain-specific features
   - Update README
   - Include usage examples

3. **Testing**
   - Add new test cases
   - Update existing tests
   - Monitor coverage

## Contributing

When contributing to the template agent:

1. Follow the established patterns
2. Document new features
3. Add appropriate tests
4. Update this README

## Troubleshooting

Common issues and solutions:

1. **State Management**
   - Check state type definitions
   - Verify state transitions
   - Monitor state consistency

2. **Prompt Issues**
   - Validate prompt templates
   - Check prompt formatting
   - Verify prompt parameters

3. **Performance**
   - Monitor response times
   - Check memory usage
   - Review caching strategy 