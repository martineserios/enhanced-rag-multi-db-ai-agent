# GLABITAI: Notebook Development Environment

## 🏥 Project Overview

GLABITAI is a bariatric and metabolic surgery follow-up AI agent designed for comprehensive post-surgical care coordination. This development environment follows the **MongoDB-centric multi-database architecture** with **progressive AI framework adoption** (PydanticAI → Agno → LangGraph + CrewAI).

## 🏗️ Architecture Overview

Based on project artifacts, GLABITAI implements:

- **MongoDB**: Primary clinical database (dynamic events, conversations, AI insights)
- **Chroma DB**: Vector database for knowledge base (MVP phase)
- **Redis**: Caching and session management
- **PydanticAI**: Type-safe clinical validation (Phase 1)
- **Progressive Scaling**: Agno (Phase 2) → LangGraph + CrewAI (Phase 3)

## 🚀 Quick Start

### 1. Environment Setup

```bash
# Clone or create project directory
mkdir glabitai-notebook-dev
cd glabitai-notebook-dev

# Create project structure (run the setup script from artifacts)
bash setup_project_structure.sh

# Copy configuration files
cp .env.example .env
# Edit .env with your API keys and settings
```

### 2. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt

# Install development tools
pip install jupyter notebook ipykernel
```

### 3. Start Database Services

```bash
# Start core databases (MongoDB + Redis)
docker-compose up -d mongodb redis

# Optional: Start with admin interfaces
docker-compose --profile dev-tools up -d

# Optional: Start full database stack
docker-compose --profile full-stack up -d

# Check services are running
docker-compose ps
```

### 4. Initialize Jupyter Environment

```bash
# Start Jupyter notebook server
jupyter notebook

# Open browser to: http://localhost:8888
```

## 📁 Project Structure

```
glabitai-notebook-dev/
├── notebooks/                          # Development notebooks
│   ├── 01_database_setup.ipynb        # Database connections & schema
│   ├── 02_knowledge_base_setup.ipynb  # Vector DB & clinical content
│   ├── 03_ai_agent_orchestration.ipynb # PydanticAI agents
│   ├── 04_clinical_workflow_testing.ipynb # End-to-end testing
│   └── 05_integration_experiments.ipynb # WhatsApp & API testing
├── glabitai/                           # Importable package
│   ├── database/                       # Database connections & models
│   ├── agents/                         # AI agent definitions
│   ├── knowledge/                      # Knowledge base management
│   ├── clinical/                       # Clinical validation & workflows
│   └── utils/                          # Utilities & helpers
├── data/                              # Sample data & clinical guidelines
├── config/                            # Configuration files
├── logs/                              # Development logs
├── .env                               # Environment variables
├── docker-compose.yml                 # Database services
└── requirements.txt                   # Python dependencies
```

## 🗄️ Database Services

### Core Services (Always Available)

- **MongoDB**: `localhost:27017` - Primary clinical database
- **Redis**: `localhost:6379` - Caching and sessions

### Development Tools (--profile dev-tools)

- **Mongo Express**: `http://localhost:8081` - MongoDB admin interface
- **Redis Commander**: `http://localhost:8088` - Redis admin interface

### Full Stack (--profile full-stack)

- **PostgreSQL**: `localhost:5432` - Structured reference data
- **InfluxDB**: `http://localhost:8086` - Time-series metrics
- **Neo4j**: `http://localhost:7474` - Medical relationship networks

## 🔧 Configuration

### Environment Variables (.env)

Key configuration sections:

- **AI Models**: OpenAI API keys, model settings
- **Databases**: Connection strings, credentials
- **Clinical Settings**: Safety thresholds, escalation rules
- **Monitoring**: Opik, Langfuse, Logfire integration
- **Security**: Encryption keys, JWT settings

### Docker Services Management

```bash
# Start core services only
docker-compose up -d

# Start with development tools
docker-compose --profile dev-tools up -d

# Start everything
docker-compose --profile full-stack up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f mongodb
```

## 🧠 AI Agent Architecture (Phase 1: PydanticAI)

### Clinical Agent Structure

```python
from glabitai.agents import GLABITAIClinicalAgent
from glabitai.database import MongoDBManager

# Type-safe clinical validation
agent = GLABITAIClinicalAgent(
    model="gpt-4",
    clinical_safety_enabled=True,
    spanish_language_support=True
)

# MongoDB integration for clinical events
db = MongoDBManager()
```

### Knowledge Base Integration

```python
from glabitai.knowledge import ClinicalKnowledgeBase

# Vector search with clinical context
knowledge_base = ClinicalKnowledgeBase(
    vector_db="chroma",  # MVP phase
    collections=[
        "clinical_guidelines",
        "nutrition_guidance", 
        "psychological_support",
        "exercise_protocols"
    ]
)
```

## 📚 Development Workflow

### 1. Database Setup (`01_database_setup.ipynb`)

- Test MongoDB connection and create clinical collections
- Initialize Chroma DB with clinical guidelines
- Setup Redis caching
- Create sample patient data

### 2. Knowledge Base (`02_knowledge_base_setup.ipynb`)

- Load clinical guidelines (ASMBS, Mexican protocols)
- Create embeddings for Spanish/English content
- Test vector search functionality

### 3. AI Agents (`03_ai_agent_orchestration.ipynb`)

- Initialize PydanticAI clinical agents
- Test type-safe clinical responses
- Implement knowledge base integration

### 4. Clinical Workflows (`04_clinical_workflow_testing.ipynb`)

- End-to-end patient interaction simulation
- Test clinical event storage in MongoDB
- Validate escalation logic

### 5. Integration Testing (`05_integration_experiments.ipynb`)

- WhatsApp message simulation
- API endpoint prototyping
- Performance benchmarking

## 🔍 Monitoring & Observability

### Development Monitoring Stack

- **Opik**: Clinical safety monitoring and evaluation
- **Langfuse**: Conversation tracking and cost analysis
- **Logfire**: PydanticAI type validation monitoring

### Access Monitoring Dashboards

- Opik: Configure in `.env` → `OPIK_API_KEY`
- Langfuse: Configure in `.env` → `LANGFUSE_SECRET_KEY`
- Logfire: Configure in `.env` → `LOGFIRE_API_KEY`

## 🔒 Security & Compliance

### HIPAA Considerations

- All PHI data stays in local MongoDB
- Encryption keys configured in `.env`
- Audit logging enabled by default
- Type-safe data handling with PydanticAI

### Development Security

- Environment variables for all secrets
- Local database deployment
- Encrypted communication patterns
- Input validation and sanitization

## 🚧 Troubleshooting

### Common Issues

1. **MongoDB Connection Failed**: Check Docker service status
2. **Port Conflicts**: Modify ports in docker-compose.yml
3. **API Key Errors**: Verify .env configuration
4. **Memory Issues**: Increase Docker memory allocation

### Database Reset

```bash
# Stop services
docker-compose down

# Remove volumes (WARNING: Deletes all data)
docker-compose down -v

# Restart fresh
docker-compose up -d
```

### Service Health Checks

```bash
# Check all services
docker-compose ps

# Test MongoDB connection
docker exec glabitai-mongodb mongosh --eval "db.runCommand('ping')"

# Test Redis connection  
docker exec glabitai-redis redis-cli ping
```

## 📈 Next Steps

### Phase 2: Performance Optimization (Agno Integration)

- High-performance routine query processing
- Enhanced concurrent patient handling
- Advanced caching strategies

### Phase 3: Complex Workflows (LangGraph + CrewAI)

- Multi-specialist coordination
- Complex clinical decision trees
- Advanced monitoring and analytics

## 🤝 Development Guidelines

1. **Follow MongoDB-centric architecture** from project artifacts
2. **Use PydanticAI for all clinical validation** (type safety)
3. **Implement progressive complexity** (simple → complex workflows)
4. **Maintain Spanish language support** throughout development
5. **Test clinical safety features** in every iteration
6. **Document clinical decision logic** for regulatory compliance

## 📞 Support & Resources

- **Project Artifacts**: Reference established architecture decisions
- **MongoDB Documentation**: https://docs.mongodb.com/
- **PydanticAI Documentation**: https://ai.pydantic.dev/
- **Clinical Guidelines**: ASMBS official protocols
- **Development Issues**: Check logs in `./logs/` directory
