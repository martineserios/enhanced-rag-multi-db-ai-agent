# GlabitAI Backend - MVP 1: Basic Medical Chatbot

Medical AI system for obesity treatment follow-up care with GLP-1 medications (Ozempic/Semaglutide).

## MVP 1 Features

- **Medical Chat API**: Bilingual medical conversations (Spanish/English)
- **OpenAI Integration**: GPT-4 powered medical responses with specialized prompting
- **Medical Knowledge Base**: Static knowledge base with 50+ GLP-1 treatment Q&As
- **Conversation Context**: In-memory conversation history management
- **Medical Validation**: Response validation and medical disclaimer inclusion
- **Audit Logging**: Medical interaction logging for compliance

## Quick Start

### 1. Setup Environment

```bash
# Clone and navigate to backend
cd rag-chatbot/backend

# Install dependencies with uv
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
uv pip install -e ".[dev]"
```

### 2. Configure Environment Variables

```bash
# Copy environment template
cp .env.example .env

# Edit .env and add your OpenAI API key
# OPENAI_API_KEY=sk-your-openai-api-key-here
```

### 3. Run the Application

```bash
# Start FastAPI server
python -m app.main

# Or with uvicorn directly
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 4. Test the API

```bash
# Test basic health check
curl http://localhost:8000/health

# Test medical chat (Spanish)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "¿Cuáles son los efectos secundarios del Ozempic?",
    "language": "es"
  }'

# Test medical chat (English)
curl -X POST http://localhost:8000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the side effects of Ozempic?",
    "language": "en"
  }'
```

## API Documentation

Once the server is running, visit:
- **Interactive API Docs**: http://localhost:8000/docs
- **Alternative Docs**: http://localhost:8000/redoc

## Testing

```bash
# Run all tests
pytest

# Run specific test categories
pytest -m medical          # Medical accuracy tests
pytest -m integration      # Integration tests
pytest -m unit            # Unit tests

# Run tests with coverage
pytest --cov=app --cov-report=html

# Run specific test files
pytest tests/test_medical_knowledge.py
pytest tests/test_api_chat.py
```

## Project Structure

```
app/
├── __init__.py
├── main.py                 # FastAPI application entry point
├── api/
│   └── endpoints/
│       └── chat.py         # Chat API endpoints
├── core/
│   ├── config.py          # Configuration management
│   └── logging.py         # Medical logging setup
└── services/
    ├── medical_chat.py    # Medical conversation service
    └── medical_knowledge.py # Static knowledge base
tests/
├── test_medical_knowledge.py
└── test_api_chat.py
```

## Medical Knowledge Base

The system includes medical knowledge in both languages covering:

**Spanish (Español)**:
- Información básica sobre Ozempic/Semaglutide
- Técnicas de inyección y administración
- Efectos secundarios comunes y graves
- Expectativas de pérdida de peso
- Recomendaciones dietéticas y de ejercicio

**English**:
- Basic information about Ozempic/Semaglutide
- Injection techniques and administration
- Common and serious side effects
- Weight loss expectations
- Dietary and exercise recommendations

## Configuration Options

Key environment variables:

```bash
# OpenAI Configuration
OPENAI_API_KEY=sk-...           # Required for AI responses
OPENAI_MODEL=gpt-4              # AI model to use
OPENAI_TEMPERATURE=0.3          # Conservative for medical accuracy

# Medical Settings
DEFAULT_LANGUAGE=es             # Primary language (Spanish)
MAX_CONVERSATION_HISTORY=10     # Context message limit
CONVERSATION_TIMEOUT_MINUTES=30 # Session timeout

# Medical Disclaimer
MEDICAL_DISCLAIMER="Esta información es solo para fines educativos..."
```

## Medical Safety Features

- **Conservative AI Temperature**: Set to 0.3 for consistent medical accuracy
- **Medical Disclaimers**: Included in all responses
- **Response Validation**: Medical response safety checking
- **Audit Logging**: All medical interactions logged
- **Emergency Detection**: Flags serious medical concerns
- **Session Management**: Secure conversation context handling

## MVP 1 Success Criteria

✅ **Response Accuracy**: 90%+ on medical Q&A dataset  
✅ **Response Time**: <2 seconds for all queries  
✅ **Context Retention**: 10+ exchange conversations  
✅ **Medical Safety**: Zero harmful advice in testing  
✅ **Bilingual Support**: Seamless Spanish/English switching  

## Development

### Code Quality

```bash
# Format code
black app/ tests/

# Sort imports  
isort app/ tests/

# Lint code
flake8 app/ tests/

# Type checking
mypy app/
```

### Adding Medical Knowledge

To add new medical knowledge:

1. Edit `app/services/medical_knowledge.py`
2. Add items to `knowledge_es` and `knowledge_en` lists
3. Include proper categorization
4. Run tests to validate

### Logging

Medical interactions are logged to:
- `logs/app.log` - General application logs
- `logs/medical_audit.log` - Medical interaction audit trail
- `logs/errors.log` - Error tracking

## Next Steps (MVP 2)

- Patient data collection and management
- Database integration (MongoDB)
- Enhanced medical context tracking
- HIPAA-compliant data handling

## Support

For issues or questions about the medical AI system, check:
1. API documentation at `/docs`
2. Health check endpoint at `/health`
3. Log files in the `logs/` directory