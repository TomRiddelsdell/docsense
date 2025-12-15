# Trading Algorithm Document Analyzer

**An AI-powered application for analyzing and improving trading algorithm documentation**

[![Tests](https://img.shields.io/badge/tests-373%20passing-green)]() 
[![Python](https://img.shields.io/badge/python-3.12-blue)]()
[![React](https://img.shields.io/badge/react-18-blue)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 📋 Quick Links

- **[🚀 Complete Setup Guide](SETUP_FROM_SCRATCH.md)** - **NEW!** Comprehensive setup for new machines & forks
- **[⚡ Quick Setup](docs/processes/003-development-environment-setup.md)** - Fast setup for experienced devs
- **[API Documentation](http://localhost:8000/docs)** - Interactive OpenAPI docs (when running)
- **[Architecture Decisions](docs/decisions/)** - ADRs explaining technical choices
- **[Implementation Plan](docs/IMPLEMENTATION_PLAN.md)** - Development roadmap

---

## 🚀 Quick Start

> **🏢 Setting up for your organization?** See **[SETUP_FROM_SCRATCH.md](SETUP_FROM_SCRATCH.md)** for comprehensive step-by-step instructions including all dependencies, database migrations, and verification steps.

### Option 1: Dev Container (Recommended)

```bash
# Clone repository
git clone https://github.com/TomRiddelsdell/docsense.git
cd docsense

# Open in VS Code
code .

# Click "Reopen in Container" when prompted
# Everything is pre-configured!
```

### Option 2: Local Development

```bash
# Clone and setup
git clone https://github.com/TomRiddelsdell/docsense.git
cd docsense

# Backend
poetry install
cp .env.example .env
# Edit .env with your AI API key (Anthropic/OpenAI/Gemini)
python main.py

# Frontend (new terminal)
cd client
npm install
npm run dev
```

**Access the application**:
- Frontend: http://localhost:5000
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/docs

See [Development Environment Setup](docs/processes/003-development-environment-setup.md) for detailed instructions.

---

## 🎯 What It Does

The Trading Algorithm Document Analyzer helps financial institutions create compliant, high-quality trading algorithm documentation by:

1. **📄 Document Upload** - Supports PDF, Word, and Markdown formats
2. **🔄 Smart Conversion** - Preserves structure, formulas, and formatting
3. **🤖 AI Analysis** - Multi-model AI reviews content for completeness and clarity
4. **💡 Actionable Feedback** - Specific suggestions with explanations
5. **✅ User Control** - Accept or reject each suggestion individually
6. **📊 Audit Trail** - Complete history of all changes via Event Sourcing
7. **📈 Version Management** - Track document evolution over time

---

## 🏗️ Architecture

**Design Patterns**:
- **Domain-Driven Design (DDD)** - Business logic isolated in domain layer
- **Event Sourcing** - Complete audit trail of all state changes
- **CQRS** - Separate read and write models for scalability
- **Multi-Model AI** - Support for Claude, GPT, and Gemini

**Tech Stack**:
```
┌─────────────────────────────────────────────────┐
│  Frontend: React + TypeScript + Shadcn/ui      │
│  (Vite, Tailwind CSS, React Query, React Flow) │
└─────────────────────────────────────────────────┘
                       ↓ REST API
┌─────────────────────────────────────────────────┐
│  Backend: Python + FastAPI                      │
│  (asyncpg, Pydantic, LiteLLM)                  │
├─────────────────────────────────────────────────┤
│  Domain Layer - Aggregates, Events, Commands   │
│  Application Layer - Command/Query Handlers    │
│  Infrastructure Layer - Event Store, AI        │
└─────────────────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────┐
│  PostgreSQL 15                                  │
│  - Event Store (source of truth)               │
│  - Read Models (projections)                   │
└─────────────────────────────────────────────────┘
```

See [System Architecture Overview](docs/architecture/SYSTEM_OVERVIEW.md) for details.

---

## 📚 Documentation Structure

### Core Documentation

| Document | Purpose |
|----------|---------|
| [VISION.md](docs/VISION.md) | Product vision, goals, and target users |
| [GLOSSARY.md](docs/GLOSSARY.md) | Ubiquitous language and domain terms |
| [IMPLEMENTATION_PLAN.md](docs/IMPLEMENTATION_PLAN.md) | Development roadmap and future plans |

### Architecture Decisions (ADRs)

All major technical decisions are documented in `docs/decisions/`:

| ADR | Decision |
|-----|----------|
| [001](docs/decisions/001-use-ddd-event-sourcing-cqrs.md) | Use DDD + Event Sourcing + CQRS |
| [002](docs/decisions/002-react-frontend.md) | React for frontend |
| [003](docs/decisions/003-multi-model-ai-support.md) | Multi-model AI support |
| [004](docs/decisions/004-document-format-conversion.md) | Document format conversion strategy |
| [007](docs/decisions/007-shadcn-ui-component-library.md) | Shadcn/ui component library |
| [011](docs/decisions/011-ai-provider-implementation.md) | AI provider abstraction layer |
| [012](docs/decisions/012-doppler-secret-management.md) | Doppler for secrets management |
| [014](docs/decisions/014-semantic-intermediate-representation.md) | Semantic IR for document analysis |
| [016](docs/decisions/016-event-versioning-strategy.md) | Event versioning and upcasting |

[View all ADRs →](docs/decisions/)

### Processes

Repeatable processes documented in `docs/processes/`:

| Process | Description |
|---------|-------------|
| [001-document-analysis-workflow.md](docs/processes/001-document-analysis-workflow.md) | End-to-end document analysis workflow |
| [002-production-deployment.md](docs/processes/002-production-deployment.md) | Production deployment checklist and procedures |
| [003-development-environment-setup.md](docs/processes/003-development-environment-setup.md) | Development environment setup guide |
| [004-evolving-events.md](docs/processes/004-evolving-events.md) | How to evolve event schemas safely |

### Analysis & Reports

| Document | Purpose |
|----------|---------|
| [production-readiness-review.md](docs/analysis/production-readiness-review.md) | Production readiness assessment with critical issues |
| [document-conversion-improvement-recommendations.md](docs/analysis/document-conversion-improvement-recommendations.md) | Document conversion enhancement recommendations |

### Configuration

| File | Purpose |
|------|---------|
| [environment-variables.md](docs/deployment/environment-variables.md) | All environment variables explained |
| [event_store_schema.sql](docs/database/event_store_schema.sql) | PostgreSQL event store schema |
| [projection_failure_tracking.sql](docs/database/projection_failure_tracking.sql) | Projection health monitoring schema |

---

## 🧪 Testing

```bash
# Run all tests (373 tests)
poetry run pytest

# Run with coverage
poetry run pytest --cov=src --cov-report=html

# Run specific test suite
poetry run pytest tests/unit/domain/
poetry run pytest tests/integration/

# Frontend tests
cd client
npm test
```

**Test Coverage**:
- **Domain Layer**: 133 tests
- **Infrastructure Layer**: 55 tests  
- **Application Layer**: 65 tests
- **AI Layer**: 94 tests
- **API Layer**: 26 tests

See [TEST_COVERAGE_SUMMARY.md](docs/testing/TEST_COVERAGE_SUMMARY.md) for detailed metrics.

---

## 🔧 Development

### Project Structure

```
/
├── client/                   # React frontend
│   ├── src/
│   │   ├── components/       # UI components (Shadcn/ui)
│   │   ├── pages/           # Route pages
│   │   ├── hooks/           # React Query hooks
│   │   └── types/           # TypeScript types
│   └── package.json
├── src/                     # Python backend
│   ├── domain/              # Domain layer (DDD)
│   │   ├── aggregates/      # Document, FeedbackSession, etc.
│   │   ├── events/          # Domain events
│   │   ├── commands/        # Commands
│   │   └── value_objects/   # Value objects
│   ├── application/         # Application layer
│   │   ├── commands/        # Command handlers
│   │   ├── queries/         # Query handlers
│   │   └── services/        # Application services
│   ├── infrastructure/      # Infrastructure layer
│   │   ├── persistence/     # Event store, repositories
│   │   ├── projections/     # Read model projectors
│   │   ├── converters/      # Document converters
│   │   └── ai/              # AI integration
│   └── api/                 # API layer (FastAPI)
│       ├── routes/          # API endpoints
│       ├── schemas/         # Pydantic DTOs
│       └── middleware/      # API middleware
├── tests/                   # Test suite
├── docs/                    # Documentation
└── main.py                  # Application entry point
```

### Available Commands

**Backend**:
```bash
python main.py              # Run application
poetry run pytest           # Run tests
poetry run pyright          # Type checking
poetry run ruff check       # Linting
```

**Frontend**:
```bash
npm run dev                 # Development server
npm run build               # Production build
npm test                    # Run tests
npm run lint                # Linting
```

---

## 🚀 Production Deployment

See [Production Deployment Process](docs/processes/002-production-deployment.md) for complete deployment guide.

**Critical Requirements**:
- PostgreSQL 15+
- At least one AI provider API key (Anthropic/OpenAI/Gemini)
- Proper CORS configuration (no wildcards!)
- Environment variable validation
- Database migrations applied

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests (`poetry run pytest`)
5. Commit (`git commit -m 'Add amazing feature'`)
6. Push (`git push origin feature/amazing-feature`)
7. Open a Pull Request

**Before submitting**:
- All tests pass
- Code follows project style (ruff, black, isort)
- Type checking passes (pyright)
- Documentation updated
- ADR created for architectural changes

---

## 📖 Learning Path

**New to the project?** Follow this learning path:

1. **Understand the vision**: Read [VISION.md](docs/VISION.md)
2. **Learn the language**: Review [GLOSSARY.md](docs/GLOSSARY.md)
3. **Set up locally**: Follow [Development Environment Setup](docs/processes/003-development-environment-setup.md)
4. **Explore the codebase**: Start with `src/domain/aggregates/document.py`
5. **Understand workflows**: Read [Document Analysis Workflow](docs/processes/001-document-analysis-workflow.md)
6. **Review architecture**: Check [ADRs](docs/decisions/) and [SYSTEM_OVERVIEW.md](docs/architecture/SYSTEM_OVERVIEW.md)
7. **Run tests**: Execute `poetry run pytest -v` and explore test files
8. **Make changes**: Pick an issue and contribute!

---

## 📝 License

MIT License - see [LICENSE](LICENSE) for details

---

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- UI components from [shadcn/ui](https://ui.shadcn.com/)
- AI integration via [LiteLLM](https://github.com/BerriAI/litellm)
- Event Sourcing patterns inspired by [Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)

---

**Questions?** Open an issue or check the [documentation](docs/).
