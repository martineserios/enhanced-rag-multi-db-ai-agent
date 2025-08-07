# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Approach

**Test-Driven Development (TDD) is MANDATORY** for all code in this medical AI project. Given the critical nature of healthcare applications, every line of code must be thoroughly tested before implementation.

### TDD Workflow (Non-Negotiable)
1. **Red**: Write a failing test that defines desired behavior
2. **Green**: Write the minimal code to make the test pass
3. **Refactor**: Improve code quality while keeping tests green
4. **Repeat**: Continue the cycle for each new feature or bug fix

**Why TDD is Critical for Medical AI**:
- **Patient Safety**: Every clinical decision must be validated through comprehensive test scenarios
- **Regulatory Compliance**: Medical software requires documented test coverage for FDA/regulatory approval
- **Code Quality**: TDD ensures robust, maintainable code in complex medical workflows
- **Confidence**: Comprehensive test suites enable safe refactoring and feature additions

## Project Architecture

GlabitAI is a specialized medical AI system focused on obesity treatment follow-up care with GLP-1 medications (Ozempic/Semaglutide). The system combines a multi-project repository architecture with clinical AI agents for comprehensive patient monitoring and healthcare team coordination.

### Core Components

- **rag-chatbot/**: Main FastAPI backend with multi-database memory architecture and LangGraph agent workflows
- **glabitai-notebook-dev/**: Jupyter development environment for clinical AI prototyping with PydanticAI
- **Obesity Treatment Agent**: New clinical specialization for GLP-1 treatment follow-up (see OBESITY_TREATMENT_AI_AGENT.md)

### Multi-Database Clinical Architecture with Hybrid Memory System

The system implements a medically-oriented memory architecture with hybrid Mem0 integration:

#### **Primary Memory Layer (Mem0 Self-Hosted)**
- **Patient Episodes**: Long-term treatment history and medical conversations
- **Clinical Context**: Cross-agent memory sharing for specialist coordination  
- **Knowledge Memory**: Medical protocol integration with agent decision-making
- **HIPAA-Compliant**: Agent-level isolation with end-to-end encryption

#### **Database Storage Layer**
1. **Patient Clinical Data** (MongoDB): Medical history, treatment events, clinical alerts, patient journey phases
2. **Real-time Monitoring** (Redis): Session data, active patient status, immediate health metrics
3. **Medical Knowledge Base** (ChromaDB): GLP-1 treatment protocols, side effect management, clinical guidelines
4. **Treatment Workflows** (Neo4j): Complex medical decision trees, multidisciplinary team coordination
5. **Structured Medical Data** (PostgreSQL): Patient demographics, appointment schedules, team assignments

#### **Custom Medical Memory Components**
- **Patient Journey State Management**: Treatment phase transitions and clinical milestones
- **Clinical Alert Memory**: Emergency escalation patterns and resolution tracking
- **Treatment Protocol Versioning**: Medical guideline updates and compliance tracking

### Clinical Agent System

Specialized for obesity treatment with:
- **Patient Journey State Management**: 6 distinct treatment phases from pre-treatment to withdrawal
- **Proactive Health Monitoring**: Weight tracking, side effect assessment, psychological state evaluation
- **Multidisciplinary Team Alerts**: Intelligent routing to doctor, nutritionist, psychologist, trainer
- **Bilingual Clinical Support**: Spanish/English medical terminology and cultural adaptation
- **HIPAA-Compliant Communication**: Secure WhatsApp and mobile app integration

## Development Commands

### Primary Development (rag-chatbot)

**Package Management**: UV is the preferred package manager for this project - fast, reliable, and handles virtual environments automatically.

```bash
# Setup clinical development environment
uv venv                      # Create virtual environment
uv sync                      # Install dependencies from pyproject.toml
source .venv/bin/activate    # Activate environment (Linux/Mac)

# Development servers for clinical testing  
uv run uvicorn app.main:app --reload  # Run FastAPI backend
uv run streamlit run app/ui/dashboard.py  # Run Streamlit dashboard

# Clinical testing and validation (TDD Workflow)
uv run pytest               # Run all tests including clinical agent tests
uv run pytest tests/backend/  # Backend medical logic tests only
uv run pytest --cov=app --cov-report=html --cov-fail-under=90  # Test coverage validation (90% minimum)
uv run pytest -x            # Stop at first failure (useful during TDD red-green cycle)
uv run pytest --lf          # Run last failed tests (TDD iteration)
uv run ruff check           # Medical code quality with ruff linting
uv run ruff format          # Code formatting
uv run mypy app/            # Type checking

# Package management with UV
uv add <package>            # Add new dependency
uv add --dev <package>      # Add development dependency
uv remove <package>         # Remove dependency
uv lock                     # Update lock file
uv tree                     # Show dependency tree

# Docker services for medical data infrastructure
make build                   # Build images with clinical database support
make up                      # Start all medical databases and services
make down                    # Stop clinical infrastructure
make check-services          # Verify medical database connectivity

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
# Clinical agent testing (using UV)
cd rag-chatbot/backend
uv run pytest tests/test_clinical_agent.py         # Obesity agent specific tests
uv run pytest tests/integration/test_clinical_flow.py  # End-to-end clinical workflow tests

# Medical knowledge base testing
uv run pytest tests/test_medical_knowledge.py      # GLP-1 protocol validation
uv run pytest tests/test_patient_monitoring.py     # Patient journey state management
```

## Clinical Configuration

### Medical Environment Variables

```bash
# Clinical AI Models (required for medical accuracy)
OPENAI_API_KEY=              # GPT-4 for complex medical reasoning
ANTHROPIC_API_KEY=           # Claude for clinical conversation
GROQ_API_KEY=                # Llama for medical knowledge retrieval

# Memory System Configuration (Mem0 Self-Hosted)
MEM0_HOST=                   # Self-hosted Mem0 instance URL
MEM0_API_KEY=                # Authentication for Mem0 API
MEM0_ENCRYPTION_KEY=         # Patient memory encryption key
MEM0_AGENT_ISOLATION=true    # Enable agent-level memory isolation

# Event-Driven Architecture Configuration
KAFKA_BROKERS=               # MSK Kafka cluster endpoints
KAFKA_SECURITY_PROTOCOL=SASL_SSL # Security protocol for medical data
EVENT_STORE_TOPIC=medical_events # Primary topic for medical event sourcing
MEDICAL_ALERTS_TOPIC=clinical_alerts # High-priority medical alerts
AGENT_COORDINATION_TOPIC=agent_events # Inter-agent communication events

# Medical Database Connections
MONGO_URI=                   # Patient clinical data and medical events
POSTGRES_URI=                # Structured medical demographics
REDIS_HOST=                  # Real-time patient monitoring
NEO4J_URI=                   # Medical decision workflows
CHROMA_HOST=                 # Clinical knowledge base

# AWS Infrastructure (Primary Cloud Platform)
AWS_REGION=us-east-1         # Primary region for medical data
AWS_BACKUP_REGION=us-west-2  # Secondary region for disaster recovery
AWS_KMS_KEY_ID=              # Customer-managed encryption keys
AWS_HIPAA_BAA=true           # HIPAA Business Associate Agreement

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

Clinical code requires enhanced standards with TDD at the core:
- **Test-First Medical Logic**: Write test cases defining medical behavior before any clinical code implementation
- **Medical Terminology Validation**: All clinical terms must pass medical accuracy checks through automated test suites
- **HIPAA Compliance**: All patient data handling must meet healthcare privacy standards - validate through privacy-focused test cases
- **Bilingual Medical Support**: Spanish/English medical translations validated by healthcare professionals and automated test scenarios
- **Clinical Decision Audit**: All AI medical decisions must be logged and traceable - verify through comprehensive test coverage
- **Medical Error Handling**: Graceful degradation with immediate healthcare team notification - test all failure scenarios
- **TDD Medical Coverage**: Every clinical decision path must have corresponding test coverage before deployment

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

### Development Philosophy

**Test-Driven Development (TDD) First**: Write tests before implementation - critical for medical safety and reliability
- **Red-Green-Refactor Cycle**: Write failing test → Make it pass → Refactor for quality
- **Medical Safety Through Testing**: Every clinical decision must be validated through comprehensive test scenarios
- **Test Coverage Requirement**: Minimum 90% coverage for all medical logic and patient-facing features
- **Mock Medical Scenarios**: Create realistic patient interaction test cases before building features

**Iterative MVP Approach**: Start simple, test thoroughly, add complexity incrementally
- **Working MVP Focus**: Each iteration must deliver a functional, testable medical capability
- **Incremental Complexity**: Build from basic single-agent to complex multi-agent system
- **Continuous Clinical Validation**: Each MVP validated with medical professionals through automated testing

**Event-Driven Architecture**: Medical AI system built on event-driven patterns
- **Medical Event Sourcing**: All patient interactions and medical decisions stored as immutable events
- **Real-Time Event Processing**: Kafka streams for medical alerts, agent coordination, and patient monitoring
- **Event-Driven Agent Coordination**: Agents communicate through medical events (patient_weight_updated, side_effect_reported, treatment_phase_changed)
- **Audit-First Design**: Complete event trail for HIPAA compliance and medical decision tracking
- **Reactive Medical Workflows**: System responds to patient events in real-time with appropriate medical interventions

### Clinical Development Standards

When developing clinical features, follow these mandatory practices:

1. **Test-Driven Development (TDD) Mandatory**: Write tests BEFORE writing any medical logic - no exceptions for patient safety
   - Write failing test cases that define expected medical behavior
   - Implement minimal code to make tests pass
   - Refactor while keeping tests green
   - Add edge cases and error scenarios before feature completion

2. **Clinical Validation First**: All medical logic must be validated against established protocols through automated tests
3. **Patient Safety Priority**: Implement conservative thresholds with healthcare team escalation - all validated through test scenarios
4. **Test Coverage Requirements**: Minimum 90% test coverage for medical decision logic - use `uv run pytest --cov` to verify
5. **Multilingual Medical Accuracy**: Ensure Spanish/English medical translations are clinically accurate with dedicated test cases
6. **HIPAA-First Development**: Build privacy compliance into every feature from start - test data anonymization and access controls
7. **Healthcare Team Feedback Loop**: Regular validation with medical professionals through automated test scenarios
8. **UV Package Management**: Use `uv` for all Python environment and dependency management - faster installs, better dependency resolution, and automatic virtual environment handling

## Development Branch Strategy

**Systematic Branch Naming Convention**: Each development effort follows a structured naming pattern aligned with the DEVELOPMENT_ROADMAP.md architecture.

### Branch Naming Schema

```
{phase}-{milestone-type}-{component-identifier}
```

**Components**:
- **Phase**: `p1-foundation` | `p2-intelligence` | `p3-communication` | `p4-production`  
- **Milestone Type**: `mvp` | `milestone` | `task`
- **Component Identifier**: Descriptive kebab-case name

### Branch Name Examples

#### **MVP Branches** (Cross-layer implementations):
```
mvp-01-basic-medical-chatbot          # MVP 1: Basic Medical Chatbot
mvp-02-patient-data-system           # MVP 2: Patient Data System  
mvp-03-medical-alert-system          # MVP 3: Medical Alert System
mvp-04-multi-agent-foundation        # MVP 4: Multi-Agent Foundation
mvp-05-memory-enhanced-system        # MVP 5: Memory-Enhanced System
```

#### **Milestone Branches** (Single layer focus):
```
p1-milestone-m1-1-core-foundation    # M1.1: Project Setup & Basic API Framework
p1-milestone-m1-1-5-llm-provider-abc # M1.1.5: Flexible LLM Provider Architecture
p1-milestone-m1-2-patient-data       # M1.2: Patient Data Models & Database Integration
p2-milestone-m2-1-langgraph-agents   # M2.1: LangGraph Integration & Basic Agent Framework
p2-milestone-m2-2-mem0-deployment    # M2.2: Mem0 Deployment & Memory Architecture
```

#### **Task Branches** (Specific implementation focus):
```
p1-task-t1-1-2-llm-provider-abc           # T1.1.2: LLM Provider ABC architecture
p1-task-t1-1-5-1-abc-interface-design     # T1.1.5.1: Design ABC interface + data structures
p1-task-t1-1-5-2-openai-provider          # T1.1.5.2: Implement OpenAIProvider concrete class
p2-task-t2-2-1-langgraph-setup           # T2.2.1: LangGraph setup + agent workflows
p3-task-t3-6-1-whatsapp-api-setup        # T3.6.1: WhatsApp Business API setup
```

### Current Development State

**Current Branch**: `p1-task-t1-1-2-llm-provider-abc` - Implementing flexible LLM provider ABC architecture
**Main Branch**: `main` - Stable clinical agent foundation  
**Dev Branch**: `dev` - Development integration branch

**Current Task**: T1.1.2 - LLM Provider ABC architecture + OpenAI/Anthropic/Groq implementations (MVP 1, Week 1, Day 2)

### Branching Workflow Rules

#### **Before Starting Any New Work**:
1. **Check Roadmap Alignment**: Identify the exact MVP/Milestone/Task from DEVELOPMENT_ROADMAP.md
2. **Create Systematic Branch**: Use the naming convention above
3. **Write Tests First**: Create failing test cases that define the expected behavior (TDD mandatory)
4. **Update CLAUDE.md**: Record the branch purpose and scope
5. **Commit Frequently**: Small, focused commits with clear messages

#### **Branch Lifecycle**:
1. **Creation**: `git checkout -b {systematic-branch-name}`
2. **Test Creation**: Write failing tests first (Red phase of TDD)
3. **Implementation**: Write minimal code to make tests pass (Green phase of TDD)
4. **Refactoring**: Improve code quality while keeping tests green (Refactor phase of TDD)
5. **Coverage Validation**: Ensure 90% test coverage with `uv run pytest --cov`
6. **Integration**: Merge back to main via PR only after all tests pass
7. **Cleanup**: Delete feature branch after successful merge

#### **Branch Scope Guidelines**:
- **MVP Branches**: Complete cross-layer functionality (1-2 weeks)
- **Milestone Branches**: Single architectural layer implementation (3-5 days)  
- **Task Branches**: Specific implementation (1-2 days)

This systematic approach ensures development stays aligned with the architectural roadmap and provides clear traceability from branch names to project requirements.

## Cloud Infrastructure Architecture

### AWS-Based Medical-Grade Deployment

**Primary Platform**: Amazon Web Services (AWS)
- **Rationale**: Superior HIPAA compliance, mature healthcare infrastructure, comprehensive AI/ML services
- **Architecture Pattern**: Multi-region deployment with event-driven microservices
- **Compliance**: AWS HIPAA Business Associate Agreement (BAA) with customer-managed KMS keys

**Core AWS Services** (Event-Driven Medical Architecture):
- **EKS (Kubernetes)**: Container orchestration for medical-grade availability (99.95% SLA)
- **MSK (Kafka)**: Primary event streaming backbone for medical events and agent coordination
- **RDS Multi-AZ**: PostgreSQL with automated backups and cross-region replication
- **DocumentDB**: MongoDB-compatible service for patient clinical data
- **ElastiCache**: Redis for real-time patient monitoring with encryption
- **EventBridge**: AWS-native event routing for medical alerts and healthcare team notifications
- **Kinesis**: Real-time patient data streaming and analytics
- **Lambda**: Serverless medical event processors for real-time responses
- **Bedrock**: AI/ML inference with medical model fine-tuning capabilities
- **KMS**: Customer-managed encryption keys for patient data protection

**Deployment Strategy**:
- **Primary Region**: us-east-1 (Virginia) - Main medical data processing
- **Backup Region**: us-west-2 (Oregon) - Disaster recovery and data replication
- **Edge Locations**: CloudFront for global patient access with low latency
- **Auto Scaling**: Horizontal pod autoscaling for 1000+ concurrent patients

## Memory System Architecture

### Hybrid Mem0 + Custom Medical Memory

**Implementation Strategy**: Self-hosted Mem0 with specialized medical components
- **Performance**: 26% better accuracy, 91% faster response times for medical queries
- **Compliance**: HIPAA-compliant with agent-level memory isolation
- **Integration**: Native LangGraph compatibility with medical workflow states
- **Cost Efficiency**: 3-year TCO of $51k-102k (vs $135k-270k for custom solutions)

**Memory Architecture Layers**:
```
┌─────────────────────────────────────┐
│         Mem0 Memory Layer           │
│  ┌─────────────┬─────────────────┐  │
│  │  Patient    │    Clinical     │  │
│  │  Episodes   │    Context      │  │
│  └─────────────┴─────────────────┘  │
└─────────────────────────────────────┘
                  ↕
┌─────────────────────────────────────┐
│      Custom Medical Components      │
│  • Journey state management        │
│  • Clinical alert memory           │
│  • Treatment protocol versioning   │
└─────────────────────────────────────┘
                  ↕
┌─────────────────────────────────────┐
│       Multi-Database Layer         │
│  MongoDB │ Redis │ ChromaDB │ Neo4j│
└─────────────────────────────────────┘
```

## Medical Alert Thresholds

Critical for patient safety - implement conservative medical thresholds:
- **Weight Loss Rate**: >2kg/week triggers medical consultation
- **Side Effects**: Persistent nausea >3 days, severe fatigue, allergic reactions
- **Psychological Indicators**: Depression scores, eating disorder patterns, treatment abandonment risk
- **Medication Compliance**: Missed doses >2 consecutive, injection technique problems
- **Emergency Escalation**: Immediate healthcare team notification for severe adverse events