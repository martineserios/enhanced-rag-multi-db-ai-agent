# filepath: README.md
# Memory-Enhanced RAG Chatbot

A production-ready implementation of a RAG (Retrieval-Augmented Generation) chatbot with multi-context memory, built using modern software engineering best practices.

## Architecture Overview

This system implements a cognitively-inspired artificial memory architecture with four distinct memory systems:

1. **Short-term Memory** (Redis): Stores recent conversation context in a key-value store with time-based expiration, enabling the chatbot to maintain continuity within the current conversation.

2. **Semantic Memory** (ChromaDB): Stores document knowledge as vector embeddings, enabling knowledge retrieval based on semantic similarity, which forms the foundation of RAG.

3. **Episodic Memory** (MongoDB): Records past conversation history, enabling the chatbot to recall past interactions across sessions and leverage them for future responses.

4. **Procedural Memory** (Neo4j): Represents action workflows as graph structures, enabling the chatbot to understand and explain multi-step processes.

These memory systems are orchestrated by a Memory Manager that implements **Multi-Context Processing (MCP)**, combining information from different memory types to create rich, contextual responses.

![Architecture Diagram](docs/architecture.png)

## Key Features

- **Multi-Context Processing**: Combines information from different memory systems to create rich, contextual responses
- **Flexible LLM Integration**: Supports OpenAI, Anthropic Claude, and Groq LLMs with a unified interface
- **Memory-Enhanced RAG**: Goes beyond basic RAG by incorporating multiple memory types
- **Modular Design**: Clean separation of concerns with well-defined interfaces
- **Comprehensive Testing**: Unit and integration tests ensure reliability
- **Error Handling**: Robust error handling and graceful degradation
- **Logging**: Structured logging with context for monitoring and debugging
- **Documentation**: Thoroughly documented code and API

## Technology Stack

- **Backend**: FastAPI, Python 3.11+
- **Frontend**: Streamlit
- **Databases**: 
  - Redis (Short-term Memory)
  - ChromaDB (Semantic Memory/Vector DB)
  - MongoDB (Episodic Memory)
  - Neo4j (Procedural Memory)
  - PostgreSQL (Relational Data)
- **LLM Integration**:
  - OpenAI (GPT-4, GPT-3.5)
  - Anthropic (Claude)
  - Groq (Llama, other models)
- **Deployment**: Docker Compose

## Project Structure

```
rag-chatbot/
├── docker-compose.yml        # Docker Compose configuration
├── .env                     # Environment variables
├── backend/                 # FastAPI backend
│   ├── app/                 # Application code
│   │   ├── api/             # API routes and dependencies
│   │   ├── core/            # Core functionality (logging, exceptions)
│   │   ├── services/        # Service implementations
│   │   │   ├── llm/         # LLM services
│   │   │   ├── memory/      # Memory systems
│   │   │   ├── database/    # Database connections
│   │   ├── utils/           # Utility functions
│   │   ├── main.py          # FastAPI application
│   │   └── config.py        # Configuration settings
│   └── tests/               # Unit and integration tests
├── frontend/                # Streamlit frontend
│   ├── components/          # UI components
│   ├── pages/               # Page definitions
│   ├── utils/               # Frontend utilities
│   └── app.py               # Streamlit application
└── scripts/                 # Database initialization scripts
```

## Getting Started

### Prerequisites

- Docker and Docker Compose
- API keys for the LLM providers you want to use:
  - OpenAI API key
  - Anthropic API key
  - Groq API key

### Installation and Deployment

1. Clone this repository:
   ```bash
   git clone https://github.com/yourusername/memory-enhanced-rag.git
   cd memory-enhanced-rag
   ```

2. Create a `.env` file with your API keys and configuration:
   ```bash
   # Copy the example environment file
   cp .env.example .env
   
   # Edit the .env file with your API keys
   nano .env
   ```

3. Build and start the Docker containers:
   ```bash
   docker-compose up -d
   ```

4. Access the application:
   - Frontend: http://localhost:8501
   - Backend API: http://localhost:8000/docs

### Using the Makefile

The project includes a comprehensive Makefile that simplifies common development and deployment tasks. To see all available commands:

```bash
make help
```

#### Development Commands

- Set up development environment:
  ```bash
  make setup  # Creates virtual environment and installs dependencies
  ```

- Run development servers:
  ```bash
  make dev-backend   # Run backend in development mode
  make dev-frontend  # Run frontend in development mode
  make dev          # Run both frontend and backend
  ```

#### Docker Operations

- Manage Docker containers:
  ```bash
  make build   # Build all Docker images
  make up      # Start all services
  make down    # Stop all services
  make restart # Restart all services
  make logs    # View service logs
  make ps      # List running containers
  ```

#### Database Management

- Database operations:
  ```bash
  make db-init    # Initialize all databases
  make db-backup  # Create database backups
  make db-restore # Restore from backups
  ```

#### Testing and Quality

- Run tests and checks:
  ```bash
  make test         # Run all tests
  make test-backend # Run backend tests
  make test-frontend # Run frontend tests
  make lint         # Run linting checks
  ```

#### Maintenance

- Maintenance tasks:
  ```bash
  make clean        # Remove temporary files and caches
  make prune        # Remove unused Docker resources
  make shell-backend  # Open shell in backend container
  make shell-frontend # Open shell in frontend container
  ```

### Configuration Options

Key configuration options in the `.env` file:

```
# LLM API Keys
OPENAI_API_KEY=your_openai_api_key
ANTHROPIC_API_KEY=your_anthropic_api_key
GROQ_API_KEY=your_groq_api_key

# Default LLM Provider (openai, anthropic, groq)
DEFAULT_LLM_PROVIDER=openai

# Memory Settings
MEMORY_ENABLED=true
ENABLE_SHORT_TERM_MEMORY=true
ENABLE_SEMANTIC_MEMORY=true
ENABLE_EPISODIC_MEMORY=true
ENABLE_PROCEDURAL_MEMORY=true
SHORT_TERM_TTL=3600

# Vector DB Settings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=1000
CHUNK_OVERLAP=200
```

## API Documentation

The API documentation is available at `/docs` when the application is running, and includes all endpoints with request/response examples.

### Key Endpoints

- **Chat**: `/api/chat/`
  - Send a chat message and get a response
  - Configurable to use different memory systems and LLM providers

- **Memory**: `/api/memory/`
  - Query memory systems
  - Get unified context from multiple memory sources

- **Documents**: `/api/documents/`
  - Upload documents for RAG
  - Search and manage documents

## Multi-Context Processing

The core innovation in this system is Multi-Context Processing (MCP), which:

1. Distributes information across specialized memory systems
2. Retrieves relevant information from each memory system in parallel
3. Combines the information into a unified context
4. Provides this rich context to the LLM for response generation

This approach enables the chatbot to:
- Remember recent interactions (short-term memory)
- Recall factual knowledge (semantic memory)
- Learn from past conversations (episodic memory)
- Understand step-by-step processes (procedural memory)

## Testing

The project includes comprehensive tests for all components:

- **Unit Tests**: Test individual components in isolation
- **Integration Tests**: Test components working together
- **Memory System Tests**: Verify memory implementations
- **LLM Service Tests**: Verify LLM integrations

To run the tests:

```bash
# Run all tests
cd backend
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/integration/

# Run with coverage
pytest --cov=app
```

## Development

### Setting Up a Development Environment

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install dependencies:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Run the backend in development mode:
   ```bash
   uvicorn app.main:app --reload
   ```

4. In another terminal, run the frontend:
   ```bash
   cd frontend
   streamlit run app.py
   ```

### Code Style and Quality

The project follows these style guidelines:

- **PEP 8**: Python style guide
- **Type Hints**: Used throughout for better IDE support and documentation
- **Docstrings**: Google-style docstrings for all functions and classes
- **Error Handling**: Appropriate exception handling with custom exceptions
- **Logging**: Structured logging with context

## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests to ensure they pass: `pytest`
5. Commit your changes: `git commit -am 'Add new feature'`
6. Push to the branch: `git push origin feature/my-feature`
7. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [LangChain](https://github.com/langchain-ai/langchain) for the foundation of LLM orchestration
- [FastAPI](https://fastapi.tiangolo.com/) for the API framework
- [Streamlit](https://streamlit.io/) for the frontend
- [ChromaDB](https://www.trychroma.com/) for the vector database
- All the database providers (Redis, MongoDB, Neo4j) for their excellent software

---

*This project demonstrates a comprehensive implementation of a memory-enhanced RAG chatbot, following best practices in software engineering and AI system design.*