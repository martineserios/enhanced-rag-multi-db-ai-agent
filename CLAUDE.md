# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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

### Development Philosophy

**Iterative MVP Approach**: Start simple, test thoroughly, add complexity incrementally
- **Test-Driven Development (TDD)**: All medical logic must have comprehensive test coverage
- **Working MVP Focus**: Each iteration must deliver a functional, testable medical capability
- **Incremental Complexity**: Build from basic single-agent to complex multi-agent system
- **Continuous Clinical Validation**: Each MVP validated with medical professionals

**Event-Driven Architecture**: Medical AI system built on event-driven patterns
- **Medical Event Sourcing**: All patient interactions and medical decisions stored as immutable events
- **Real-Time Event Processing**: Kafka streams for medical alerts, agent coordination, and patient monitoring
- **Event-Driven Agent Coordination**: Agents communicate through medical events (patient_weight_updated, side_effect_reported, treatment_phase_changed)
- **Audit-First Design**: Complete event trail for HIPAA compliance and medical decision tracking
- **Reactive Medical Workflows**: System responds to patient events in real-time with appropriate medical interventions

### Clinical Development Standards

When developing clinical features:

1. **Clinical Validation First**: All medical logic must be validated against established protocols
2. **Patient Safety Priority**: Implement conservative thresholds with healthcare team escalation
3. **Test Coverage Requirements**: Minimum 90% test coverage for medical decision logic
4. **Multilingual Medical Accuracy**: Ensure Spanish/English medical translations are clinically accurate
5. **HIPAA-First Development**: Build privacy compliance into every feature from start
6. **Healthcare Team Feedback Loop**: Regular validation with medical professionals

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

**Current Branch**: `langgraph-shurni-imp` - Legacy branch name
**Main Branch**: `main` - Stable clinical agent foundation  

**Next Planned Branch**: `p1-task-t1-1-5-llm-provider-abc` - Implementing flexible LLM provider architecture

### Branching Workflow Rules

#### **Before Starting Any New Work**:
1. **Check Roadmap Alignment**: Identify the exact MVP/Milestone/Task from DEVELOPMENT_ROADMAP.md
2. **Create Systematic Branch**: Use the naming convention above
3. **Update CLAUDE.md**: Record the branch purpose and scope
4. **Commit Frequently**: Small, focused commits with clear messages

#### **Branch Lifecycle**:
1. **Creation**: `git checkout -b {systematic-branch-name}`
2. **Development**: Focus on single MVP/Milestone/Task scope
3. **Testing**: Complete test coverage before PR
4. **Integration**: Merge back to main via PR
5. **Cleanup**: Delete feature branch after successful merge

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