# GlabitAI - Medical AI Agent System

Specialized medical AI system for obesity treatment follow-up care with GLP-1 medications (Ozempic/Semaglutide).

## 🏗️ Project Structure

```
GlabitAI/
├── README.md                   # This file
├── docs/                       # 📚 Documentation
├── backend/                    # 🔧 FastAPI Backend
├── shared/                     # 🔄 Shared Components  
├── scripts/                    # 🛠️ Development Scripts
├── infrastructure/             # ☁️ Infrastructure as Code
├── notebooks/                  # 📓 Research & Development
└── build/                      # 📦 Build Artifacts (gitignored)
```

## 🚀 Quick Start

### Docker Setup
For a quick start with all services (backend and MongoDB) using Docker Compose:
```bash
# Create a .env file in the root directory with your MongoDB credentials and API keys
cp .env.example .env
# Edit .env with your actual values

make docker-build  # Build Docker images
make docker-up     # Start all services
make docker-down   # Stop all services
make docker-logs   # View logs
```

### Backend Development (without Docker)
If you prefer to run the backend directly (requires local MongoDB instance):
```bash
cd backend
make setup     # Initial setup
make run       # Start development server
make test      # Run tests
make help      # See all commands
```

### Documentation
See [`docs/gemini.md`](docs/gemini.md) for complete development guidelines.

## 🏥 Medical AI Features

- **Clinical Conversations**: Bilingual medical chat (Spanish/English)
- **GLP-1 Treatment Support**: Ozempic injection guidance and side effect management
- **Multi-Provider LLM**: OpenAI, Anthropic, and Groq integration
- **Medical Validation**: Response validation and medical disclaimer system
- **Audit Logging**: Complete medical decision tracking for compliance

## 🔧 Technology Stack

- **Backend**: FastAPI + Python 3.11+
- **LLM Providers**: OpenAI GPT-4, Anthropic Claude, Groq Llama
- **Testing**: pytest with 90% coverage requirement
- **Package Management**: uv (fast Python package manager)
- **Code Quality**: ruff (linting & formatting)

## 📋 Development Standards

- **Test-Driven Development (TDD)** mandatory for medical safety
- **90% test coverage** requirement for medical logic
- **HIPAA-compliant** design patterns
- **Medical validation** for all clinical responses

## 🔗 Key Components

- [`backend/`](backend/) - FastAPI medical API service
- [`docs/`](docs/) - Complete project documentation
- [`scripts/`](scripts/) - Development and deployment utilities

## 📞 Support

For development guidelines, see [`docs/CLAUDE.md`](docs/CLAUDE.md).