# Health Agent Documentation

Complete documentation for the Health Agent system - an AI-powered health coaching bot built with PydanticAI, PostgreSQL, and Telegram.

---

## 📚 Documentation Structure

```
docs/
├── adrs/              # Architecture Decision Records
├── architecture/      # System diagrams and architecture
├── api/               # API and interface documentation
├── development/       # Developer guides
├── deployment/        # Deployment and operations
├── troubleshooting/   # Common issues and solutions
└── user/              # End-user documentation
```

---

## 🚀 Quick Start

**New to the project?** Start here:

1. **Users**: [User Guide](user/) - How to use the Telegram bot
2. **Developers**: [Getting Started](development/getting-started.md) - 5-minute setup
3. **Operators**: [Deployment Guide](deployment/) - Production deployment

---

## 📖 Documentation by Role

### For End Users

- **[User Guide](user/)** - Complete guide to using the Health Agent bot
  - Food tracking with photos and text
  - Reminders and notifications
  - Gamification (XP, streaks, challenges)
  - Custom tracking categories
  - Privacy and data management

---

### For Developers

#### Getting Started
- **[Quick Setup](development/getting-started.md)** - Get running in 5 minutes
- **[Full Development Guide](../DEVELOPMENT.md)** - Comprehensive setup and workflows

#### Best Practices
- **[Code Style Guide](development/code-style.md)** - Python standards, formatting, type hints
- **[Testing Guide](development/testing.md)** - Unit, integration, and API tests
- **[Git Workflow](development/git-workflow.md)** - Branching strategy and commits

#### Feature Development
- **[Adding Features](development/adding-features.md)** - Step-by-step guide to building features
  - Adding agent tools
  - Creating database tables
  - Building API endpoints
  - Writing tests

---

### For Architects and Technical Leads

#### Architecture Decision Records (ADRs)
- **[ADR-001: PydanticAI Framework](adrs/001-pydantic-ai-agent-framework.md)** - Why PydanticAI over LangChain
- **[ADR-002: Three-Tier Memory](adrs/002-three-tier-memory-architecture.md)** - PostgreSQL + Markdown + Mem0
- **[ADR-003: Dual-Mode Architecture](adrs/003-dual-mode-bot-api-architecture.md)** - Bot + API in one codebase
- **[ADR-004: Multi-Agent Consensus](adrs/004-multi-agent-nutrition-consensus.md)** - 3-agent food analysis
- **[ADR-005: PostgreSQL + pgvector](adrs/005-postgresql-pgvector-semantic-search.md)** - Vector search design

#### System Architecture
- **[Component Diagram](architecture/component-diagram.md)** - High-level system overview
- **[Sequence Diagrams](architecture/sequence-diagrams.md)** - Interaction flows (7 key flows)
- **[Data Flow Diagram](architecture/data-flow-diagram.md)** - Data movement patterns
- **[Deployment Architecture](architecture/deployment-diagram.md)** - Production setup

---

### For Operations and DevOps

#### Deployment
- **[Deployment Guide](deployment/)** - Complete deployment documentation
  - Environment setup
  - Database migrations
  - Docker configuration
  - CI/CD pipeline
  - Scaling strategies

#### Troubleshooting
- **[Troubleshooting Guide](troubleshooting/)** - Common issues and solutions
  - Bot not responding
  - Database connection errors
  - API authentication issues
  - Performance problems
  - Log analysis

---

### For API Integration

#### API Reference
- **[REST API Documentation](../API_README.md)** - HTTP endpoints, authentication, rate limiting
- **[Agent Interface](api/agent-interface.md)** - PydanticAI tools (30+ tools)
- **[Service Layer](api/service-layer.md)** - Business logic services
- **[Database Schema](api/database-schema.md)** - Complete schema reference (20+ tables)

---

## 🎯 Key Concepts

### PydanticAI Agents

Health Agent uses **PydanticAI** for conversational AI:
- Type-safe tool calling
- Structured outputs with validation
- Multi-model support (Claude 3.5 Sonnet, GPT-4o)
- Dependency injection via RunContext

**Learn more**: [ADR-001](adrs/001-pydantic-ai-agent-framework.md)

---

### Three-Tier Memory Architecture

Data stored across three tiers:
1. **PostgreSQL** - Structured, queryable data (food entries, XP, reminders)
2. **Markdown Files** - Human-readable config (profile.md, preferences.md)
3. **Mem0 + pgvector** - Semantic memory for long-term context

**Learn more**: [ADR-002](adrs/002-three-tier-memory-architecture.md), [MEMORY_ARCHITECTURE.md](../docs/MEMORY_ARCHITECTURE.md)

---

### Multi-Agent Nutrition Consensus

Food photo analysis uses 4 agents:
- 3 specialist agents (conservative, moderate, optimistic)
- 1 moderator agent (builds consensus)
- USDA FoodData Central verification

**Result**: 30% reduction in calorie estimation errors

**Learn more**: [ADR-004](adrs/004-multi-agent-nutrition-consensus.md)

---

### Gamification System

Engage users through:
- **XP & Levels**: Award points for healthy activities
- **Streaks**: Track consecutive days of activity
- **Achievements**: Unlock badges for milestones
- **Challenges**: Goal-based challenges with rewards

**Formula**: XP for level N = N² × 100

**Learn more**: [Service Layer - Gamification](api/service-layer.md#4-gamification-services)

---

## 📊 Project Statistics

**Codebase**:
- ~25,000 lines of Python code
- 140+ Python files
- 20+ database tables
- 30+ agent tools
- 100+ test cases

**Documentation**:
- 5 ADRs (Architecture Decision Records)
- 4 architecture diagrams
- 12+ guides and references
- 10,000+ lines of documentation

**Technology Stack**:
- **AI**: PydanticAI, Claude 3.5 Sonnet, GPT-4o
- **Backend**: Python 3.11+, FastAPI, PostgreSQL 14+
- **Extensions**: pgvector (vector search), Mem0 (semantic memory)
- **Integration**: Telegram Bot API, OpenAI API, Anthropic API, USDA FoodData Central
- **Deployment**: Docker Compose, GitHub Actions CI/CD

---

## 🔗 External References

### Official Documentation
- [PydanticAI](https://ai.pydantic.dev/) - Agent framework
- [PostgreSQL](https://www.postgresql.org/docs/) - Database
- [pgvector](https://github.com/pgvector/pgvector) - Vector similarity search
- [Mem0](https://docs.mem0.ai/) - Semantic memory library
- [FastAPI](https://fastapi.tiangolo.com/) - REST API framework
- [python-telegram-bot](https://python-telegram-bot.org/) - Telegram integration

### Research Papers
- [Multi-Agent Debate Reduces Hallucination](https://arxiv.org/abs/2305.14325)
- [Semantic Memory Improves LLM Recall by 26%](https://docs.mem0.ai/research)

---

## 🛠️ Development Workflow

### Standard Feature Development

```
1. Prime project context (/command-invoke prime)
2. Plan the feature (/command-invoke plan-feature)
3. Create feature branch (git checkout -b feature/my-feature)
4. Implement (add tools, database, tests)
5. Validate (/command-invoke validate)
6. Create PR (gh pr create)
7. Deploy (merge to main → CI/CD)
```

**Detailed guide**: [Adding Features](development/adding-features.md)

---

### Git Workflow

```
main (production)
├── feature/water-tracking
├── fix/timezone-bug
└── docs/api-reference
```

**Commit message format**:
```
feat: Add water intake tracking

- Created water tracking category
- Added daily water goal setting
- Implemented XP rewards

Closes #123
```

**Learn more**: [Git Workflow](development/git-workflow.md)

---

## 📝 Writing Documentation

### Documentation Standards

- **Format**: Markdown
- **Style**: Clear, concise, code examples
- **Diagrams**: Mermaid (renders in GitHub)
- **Naming**: kebab-case.md
- **Links**: Relative paths for internal docs

### Contributing to Docs

1. Edit documentation files in `/docs/`
2. Use existing docs as templates
3. Include code examples
4. Update this index if adding new docs
5. Preview with Markdown viewer

---

## 🔍 Finding What You Need

### Search by Topic

**Food Tracking**:
- User: [Food Tracking](user/#food-tracking)
- Developer: [Agent Tools](api/agent-interface.md#2-food-tracking-tools)
- Architecture: [Data Flow](architecture/data-flow-diagram.md#1-food-entry-data-flow)

**Reminders**:
- User: [Reminders](user/#reminders)
- Developer: [Reminder Service](api/service-layer.md#5-reminder-services)
- Database: [Reminder Tables](api/database-schema.md#reminder-tables)

**Gamification**:
- User: [Gamification](user/#gamification)
- Developer: [Gamification Services](api/service-layer.md#4-gamification-services)
- Architecture: [Gamification Flow](architecture/sequence-diagrams.md#4-gamification-xp-award-flow)

**Memory System**:
- Architecture: [Memory ADR](adrs/002-three-tier-memory-architecture.md)
- Developer: [Memory Services](api/service-layer.md#1-memory-services)
- Reference: [MEMORY_ARCHITECTURE.md](../docs/MEMORY_ARCHITECTURE.md)

---

## 📅 Documentation Roadmap

### Completed ✅
- Architecture Decision Records (5 ADRs)
- System architecture diagrams (4 diagrams)
- API and service documentation
- Developer guides (getting started, testing, code style, git workflow)
- Deployment guides
- Troubleshooting guide
- User guide

### Planned 📋
- Video tutorials (screen recordings)
- API client libraries (Python, JavaScript)
- Integration examples (mobile app, web dashboard)
- Performance optimization guide
- Security audit documentation

---

## 🤝 Contributing

### For Internal Contributors

1. Follow [Code Style Guide](development/code-style.md)
2. Write tests ([Testing Guide](development/testing.md))
3. Use [Git Workflow](development/git-workflow.md)
4. Update relevant documentation
5. Create PR with clear description

### For External Contributors

1. Open an issue first (discuss changes)
2. Fork the repository
3. Create feature branch
4. Submit PR with tests and docs
5. Respond to code review feedback

---

## 📞 Support

### For Users
- In-bot help: Type "help" in Telegram
- User guide: [docs/user/](user/)

### For Developers
- Development guide: [docs/development/](development/)
- Troubleshooting: [docs/troubleshooting/](troubleshooting/)
- GitHub Issues: [Create issue](https://github.com/gpt153/health-agent/issues)

### For Operators
- Deployment guide: [docs/deployment/](deployment/)
- Monitoring: [Deployment - Monitoring](deployment/#monitoring)

---

## 📜 License

[Add license information]

---

## ✍️ Revision History

- **2025-01-18**: Initial comprehensive documentation created for Phase 3.7
  - 5 Architecture Decision Records
  - 4 System architecture diagrams
  - 12+ guides and references
  - Complete API, developer, deployment, and user documentation

---

**Last Updated**: 2025-01-18
**Documentation Version**: 1.0.0
**Project Version**: [Current version]
