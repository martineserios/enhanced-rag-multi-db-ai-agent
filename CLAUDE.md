# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Architecture

GlabitAI is a specialized medical AI system focused on obesity treatment follow-up care with GLP-1 medications (Ozempic/Semaglutide). The system combines a multi-project repository architecture with clinical AI agents for comprehensive patient monitoring and healthcare team coordination.

### Core Components

- **rag-chatbot/**: Main FastAPI backend with multi-database memory architecture and LangGraph agent workflows
- **glabitai-notebook-dev/**: Jupyter development environment for clinical AI prototyping with PydanticAI
- **Obesity Treatment Agent**: New clinical specialization for GLP-1 treatment follow-up (see OBESITY_TREATMENT_AI_AGENT.md)

### Multi-Database Clinical Architecture

The system implements a medically-oriented memory architecture:

1. **Patient Clinical Data** (MongoDB): Medical history, treatment events, clinical alerts, patient journey phases
2. **Real-time Monitoring** (Redis): Session data, active patient status, immediate health metrics
3. **Medical Knowledge Base** (ChromaDB): GLP-1 treatment protocols, side effect management, clinical guidelines
4. **Treatment Workflows** (Neo4j): Complex medical decision trees, multidisciplinary team coordination
5. **Structured Medical Data** (PostgreSQL): Patient demographics, appointment schedules, team assignments

### Clinical Agent System

Specialized for obesity treatment with:
- **Patient Journey State Management**: 6 distinct treatment phases from pre-treatment to withdrawal
- **Proactive Health Monitoring**: Weight tracking, side effect assessment, psychological state evaluation
- **Multidisciplinary Team Alerts**: Intelligent routing to doctor, nutritionist, psychologist, trainer
- **Bilingual Clinical Support**: Spanish/English medical terminology and cultural adaptation
- **HIPAA-Compliant Communication**: Secure WhatsApp and mobile app integration

## Development Commands

### Primary Development (rag-chatbot)

```bash
# Setup clinical development environment
make setup                    # Creates venv with medical AI dependencies using uv

# Development servers for clinical testing
make dev-backend             # Run FastAPI with medical agent extensions
make dev-frontend            # Run Streamlit clinical dashboard
make dev                     # Run both for integrated clinical testing

# Docker services for medical data infrastructure
make build                   # Build images with clinical database support
make up                      # Start all medical databases and services
make down                    # Stop clinical infrastructure
make check-services          # Verify medical database connectivity

# Clinical testing and validation
make test                    # Run all tests including clinical agent tests
make test-backend            # Backend medical logic tests
make lint                    # Medical code quality with ruff
make dev-test                # Clinical tests with medical coverage reporting

# Medical database management
make db-init                 # Initialize clinical databases with medical schemas
make db-backup               # Backup patient data (HIPAA-compliant)
make db-restore              # Restore clinical databases
```

### Clinical Development Environment (glabitai-notebook-dev)

```bash
# Clinical database services
docker-compose up -d mongodb redis          # Core clinical data systems
docker-compose --profile dev-tools up -d    # With clinical admin interfaces
docker-compose --profile full-stack up -d   # Full medical infrastructure

# Clinical AI development
jupyter notebook                             # Start clinical agent development environment
```

### Obesity Treatment Agent Development

```bash
# Clinical agent testing
cd rag-chatbot/backend
pytest tests/test_clinical_agent.py         # Obesity agent specific tests
pytest tests/integration/test_clinical_flow.py  # End-to-end clinical workflow tests

# Medical knowledge base testing
pytest tests/test_medical_knowledge.py      # GLP-1 protocol validation
pytest tests/test_patient_monitoring.py     # Patient journey state management
```

## Clinical Configuration

### Medical Environment Variables

```bash
# Clinical AI Models (required for medical accuracy)
OPENAI_API_KEY=              # GPT-4 for complex medical reasoning
ANTHROPIC_API_KEY=           # Claude for clinical conversation
GROQ_API_KEY=                # Llama for medical knowledge retrieval

# Medical Database Connections
MONGO_URI=                   # Patient clinical data and medical events
POSTGRES_URI=                # Structured medical demographics
REDIS_HOST=                  # Real-time patient monitoring
NEO4J_URI=                   # Medical decision workflows
CHROMA_HOST=                 # Clinical knowledge base

# Clinical Communication
WHATSAPP_API_TOKEN=          # Patient communication primary channel
MOBILE_APP_API_KEY=          # Secondary patient interface
MEDICAL_TEAM_NOTIFICATIONS=  # Healthcare team alert system

# HIPAA Compliance
MEDICAL_ENCRYPTION_KEY=      # Patient data encryption
AUDIT_LOG_RETENTION=         # Clinical interaction logging
PHI_ANONYMIZATION=           # Patient data anonymization for research
```

### Clinical Service URLs

- Clinical API: http://localhost:8000 (FastAPI with medical endpoints)
- Clinical Dashboard: http://localhost:8501 (Streamlit healthcare team interface)
- Medical API Documentation: http://localhost:8000/docs (Clinical endpoint specs)
- Patient Monitoring: http://localhost:8000/clinical/monitoring (Real-time patient dashboard)

## Medical Code Quality Standards

Clinical code requires enhanced standards:
- **Medical Terminology Validation**: All clinical terms must pass medical accuracy checks
- **HIPAA Compliance**: All patient data handling must meet healthcare privacy standards
- **Bilingual Medical Support**: Spanish/English medical translations validated by healthcare professionals
- **Clinical Decision Audit**: All AI medical decisions must be logged and traceable
- **Medical Error Handling**: Graceful degradation with immediate healthcare team notification

## Obesity Treatment Agent Architecture

### Patient Journey State Machine

6 distinct clinical phases managed as agent states:
1. **Pre-Treatment**: Baseline collection, injection training, expectation setting
2. **Treatment Initiation (Weeks 1-4)**: Side effect monitoring, technique mastery, emergency alerts
3. **Adaptation & Titration (Weeks 4-12)**: Effectiveness evaluation, habit formation, plateau management
4. **Maintenance (Months 3-6)**: Long-term adherence, motivation sustainability, progress visualization
5. **Mid-Treatment Evaluation (Month 6)**: Comprehensive assessment, continuation decisions
6. **Treatment Withdrawal (Months 6-12+)**: Safe discontinuation, weight maintenance, autonomous support

### Clinical Monitoring Workflows

- **Daily**: Side effect assessment, medication compliance, mood tracking
- **Weekly**: Weight trends, behavioral patterns, treatment adherence
- **Monthly**: Comprehensive health evaluation, goal reassessment, team coordination
- **Emergency**: Severe adverse reactions, psychological crises, treatment abandonment risk

### Multidisciplinary Team Integration

Single AI coordinator routing to:
- **Primary Doctor**: Medical supervision, prescription management, health emergencies
- **Nutritionist**: Dietary modification, eating behavior analysis, nutrition education
- **Psychologist**: Emotional support, eating disorder prevention, motivation maintenance
- **Personal Trainer**: Exercise prescription, physical activity monitoring, fitness goals

## Medical Development Workflow

When developing clinical features:

1. **Clinical Validation First**: All medical logic must be validated against established protocols
2. **Patient Safety Priority**: Implement conservative thresholds with healthcare team escalation
3. **Multilingual Medical Accuracy**: Ensure Spanish/English medical translations are clinically accurate
4. **HIPAA-First Development**: Build privacy compliance into every feature from start
5. **Healthcare Team Feedback Loop**: Regular validation with medical professionals

## Current Development Branch

Branch: `langgraph-shurni-imp` - Implementing LangGraph workflows for complex medical decision trees and patient journey state management.

Main branch: `main` - Stable clinical agent foundation

## Medical Alert Thresholds

Critical for patient safety - implement conservative medical thresholds:
- **Weight Loss Rate**: >2kg/week triggers medical consultation
- **Side Effects**: Persistent nausea >3 days, severe fatigue, allergic reactions
- **Psychological Indicators**: Depression scores, eating disorder patterns, treatment abandonment risk
- **Medication Compliance**: Missed doses >2 consecutive, injection technique problems
- **Emergency Escalation**: Immediate healthcare team notification for severe adverse events