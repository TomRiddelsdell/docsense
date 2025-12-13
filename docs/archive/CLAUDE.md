# Trading Algorithm Document Analyzer

## Project Overview

An AI-powered application that analyzes trading algorithm documentation and provides actionable feedback for improvement. The application maintains a complete audit trail of all document changes using Event Sourcing and CQRS patterns.

### Tech Stack
- **Backend**: Python 3.10 with FastAPI
- **Architecture**: Domain-Driven Design (DDD) with Event Sourcing and CQRS
- **AI Agent**: Google Agent Development Kit (with multi-model support: Gemini, Claude, OpenAI)
- **Database**: PostgreSQL (event store and read models)
- **Frontend**: React with TypeScript, Shadcn/ui, Tailwind CSS, Vite
- **Testing**: pytest (373 passing tests), Vitest (frontend)

### Current State
- **Phase**: Phase 6 Frontend Complete
- **Status**: Full-stack application with React frontend, REST API, complete domain, infrastructure, application, and AI layers

---

## Quick Start

### Backend Development
```bash
# Install dependencies
poetry install

# Run the application
python main.py

# Run tests
poetry run pytest

# Type checking
poetry run pyright

# Linting
poetry run ruff check
```

### Frontend Development
```bash
cd client

# Install dependencies
npm install

# Run dev server (port 5000)
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

---

## Directory Structure

```
/
├── client/                         # React frontend (Vite + TypeScript + Tailwind + Shadcn/ui)
│   ├── src/
│   │   ├── components/             # React components
│   │   │   ├── ui/                 # Shadcn/ui components
│   │   │   ├── ChatPanel.tsx       # AI chatbot panel
│   │   │   ├── ParameterGraph.tsx  # React Flow parameter visualization
│   │   │   └── Layout.tsx          # App layout with navigation
│   │   ├── pages/                  # Route pages
│   │   │   ├── DocumentListPage.tsx
│   │   │   ├── DocumentDetailPage.tsx
│   │   │   └── UploadPage.tsx
│   │   ├── hooks/                  # React Query hooks
│   │   ├── types/                  # TypeScript DTOs
│   │   ├── lib/                    # Utilities and API client
│   │   └── App.tsx                 # Main application with routing
│   ├── vite.config.ts              # Vite config (port 5000, allowedHosts)
│   └── package.json
├── docs/                           # All project documentation
│   ├── api/
│   │   └── openapi.yaml            # Complete REST API specification
│   ├── database/
│   │   └── event_store_schema.sql  # PostgreSQL event sourcing schema
│   ├── templates/
│   │   └── policy-repositories/    # Policy template files (SEC, internal standards)
│   ├── decisions/                  # Architecture Decision Records (ADRs)
│   ├── processes/                  # Multi-step repeatable processes
│   ├── changes/                    # Append-only change log
│   ├── architecture/               # System architecture docs
│   ├── GLOSSARY.md                 # Ubiquitous language definitions
│   ├── VISION.md                   # Product vision and goals
│   └── IMPLEMENTATION_PLAN.md      # Complete roadmap to production
├── src/                            # Backend source code
│   ├── domain/                     # Domain layer (COMPLETE)
│   │   ├── aggregates/             # Document, FeedbackSession, PolicyRepository, AuditTrail
│   │   ├── events/                 # All domain events
│   │   ├── commands/               # Command definitions
│   │   ├── value_objects/          # Immutable value types
│   │   ├── services/               # Domain services
│   │   └── exceptions/             # Domain exceptions
│   ├── infrastructure/             # Infrastructure layer (COMPLETE)
│   │   ├── ai/                     # AI provider layer (COMPLETE)
│   │   │   ├── analysis/           # Analysis engine, policy evaluator, feedback generator
│   │   │   └── prompts/            # Prompt templates
│   │   ├── converters/             # Document conversion pipeline
│   │   ├── persistence/            # Event store, snapshot store, serializers
│   │   ├── repositories/           # Aggregate repositories
│   │   ├── projections/            # Read model projectors
│   │   └── queries/                # Read model query handlers
│   ├── application/                # Application layer (COMPLETE)
│   │   ├── commands/               # Command handlers (document, analysis, feedback, policy)
│   │   ├── queries/                # Query handlers (document, feedback, policy, audit)
│   │   └── services/               # Unit of work, event publisher
│   └── api/                        # API layer (COMPLETE)
│       ├── main.py                 # FastAPI application factory
│       ├── dependencies.py         # Dependency injection container
│       ├── middleware/             # Error handling, request ID
│       ├── schemas/                # Pydantic DTOs
│       └── routes/                 # API route handlers
├── tests/                          # Test suite (373 passing tests)
│   ├── domain/                     # Domain layer tests (133 tests)
│   ├── infrastructure/             # Infrastructure layer tests (55 tests)
│   ├── unit/application/           # Application layer tests (65 tests)
│   ├── unit/infrastructure/ai/     # AI layer tests (94 tests)
│   └── unit/api/                   # API layer tests (26 tests)
├── main.py                         # Application entry point
├── replit.md                       # Replit-specific documentation
└── CLAUDE.md                       # This file
```

---

## CRITICAL: Documentation Conventions

When making changes to this project, you MUST follow these conventions:

### 1. Architecture Decision Records (ADRs)
- **Location**: `/docs/decisions/`
- **Naming**: `<number>-<short-description>.md` (e.g., `002-use-fastapi-for-backend.md`)
- **When to create**: Any significant architectural or technical decision
- **Template**: Use `/docs/decisions/000-template.md`
- **Numbering**: Sequential, zero-padded to 3 digits

### 2. Process Documentation
- **Location**: `/docs/processes/`
- **Naming**: `<number>-<process-name>.md` (e.g., `002-version-rollback.md`)
- **When to create**: Any repeatable multi-step workflow
- **Template**: Use `/docs/processes/000-template.md`
- **Numbering**: Sequential, zero-padded to 3 digits

### 3. Change Log (MANDATORY)
- **Location**: `/docs/changes/`
- **Naming**: `yyyy-mm-dd-<short-description>.md` (e.g., `2025-12-06-add-user-auth.md`)
- **When to create**: After EVERY session that modifies files
- **Content**: Must include:
  - Date and author
  - Summary of changes
  - List of new/modified/deleted files
  - Rationale for changes
  - Related ADRs (if applicable)
  - Next steps

**IMPORTANT**: Always create a change log entry at the end of any development session where files were modified.

---

## Code Conventions

### Domain-Driven Design
- **Use ubiquitous language** from `/docs/GLOSSARY.md`
- **Aggregates** in `/src/domain/aggregates/`
  - `Document` - Trading algorithm documentation
  - `FeedbackSession` - AI analysis session
  - `PolicyRepository` - Regulatory and internal policies
  - `AuditTrail` - Complete change history
- **Events** in `/src/domain/events/`
- **Commands** in `/src/domain/commands/`
- **Value objects** in `/src/domain/value_objects/`

### Event Sourcing
- Events are **immutable** and named in **past tense** (e.g., `DocumentUploaded`, `AnalysisCompleted`)
- Events contain **all data needed** to reconstruct state
- **Never delete events**; use compensating events instead
- All state changes must be recorded as events

### CQRS
- **Commands** are named **imperatively** (e.g., `UploadDocument`, `GenerateFeedback`)
- Separate **read and write models**
- **Projections** build read models from events
- Commands go through command handlers
- Queries use optimized read models

### API Design
- **RESTful endpoints** following OpenAPI 3.0
- **Commands**: POST/PUT/DELETE operations
- **Queries**: GET operations
- Document all APIs in `/docs/api/openapi.yaml`
- Use Pydantic schemas for validation

### Testing Requirements
- **Unit tests** for domain logic (must pass)
- **Integration tests** for event store operations
- **End-to-end tests** for API endpoints
- Run `pytest` before committing
- Maintain test coverage above 80%

### Python Code Style
- Use **Python 3.10** features
- Follow **PEP 8** conventions
- Use **type hints** everywhere
- Run `ruff` for linting
- Run `pyright` for type checking
- Use **poetry** for dependency management

### Frontend Code Style
- Use **TypeScript** with strict mode
- Follow **React best practices**
- Use **Shadcn/ui** components for UI
- Use **React Query** for data fetching
- Use **React Router** for navigation
- Run `vitest` for testing

---

## Key Architecture Patterns

### Layered Architecture
1. **Domain Layer** - Core business logic, aggregates, events, commands
2. **Infrastructure Layer** - AI providers, persistence, projections
3. **Application Layer** - Command/query handlers, orchestration
4. **API Layer** - FastAPI routes, DTOs, middleware

### Event Sourcing Flow
```
Command → Command Handler → Aggregate → Event(s) → Event Store
                                              ↓
                                        Projections → Read Models
```

### Document Analysis Flow
1. User uploads document → `DocumentUploaded` event
2. Document converted to markdown → `DocumentConverted` event
3. AI analyzes document → `AnalysisCompleted` event
4. Feedback generated → `FeedbackGenerated` event
5. User views feedback via read model queries

---

## AI Provider Integration

The system supports multiple AI providers:
- **Google Gemini** (primary)
- **Anthropic Claude**
- **OpenAI GPT**

Configuration in `/src/infrastructure/ai/`:
- `analysis/` - Document analysis engine
- `prompts/` - Prompt templates for each provider
- Policy evaluation and feedback generation

---

## Key References

### Architecture Decision Records
- [ADR-001: DDD with Event Sourcing and CQRS](docs/decisions/001-use-ddd-event-sourcing-cqrs.md)
- [ADR-002: React Frontend](docs/decisions/002-react-frontend.md)
- [ADR-003: Multi-Model AI Support](docs/decisions/003-multi-model-ai-support.md)
- [ADR-004: Document Format Conversion](docs/decisions/004-document-format-conversion.md)
- [ADR-005: Policy Repository System](docs/decisions/005-policy-repository-system.md)
- [ADR-006: API-First Design](docs/decisions/006-api-first-design.md)
- [ADR-007: Shadcn/ui Component Library](docs/decisions/007-shadcn-ui-component-library.md)
- [ADR-009: Document Self-Containment Requirements](docs/decisions/009-document-self-containment-requirements.md)

### Other Documentation
- [Implementation Plan](docs/IMPLEMENTATION_PLAN.md) - Complete roadmap to production
- [System Architecture Overview](docs/architecture/SYSTEM_OVERVIEW.md)
- [Glossary](docs/GLOSSARY.md) - Ubiquitous language definitions
- [Product Vision](docs/VISION.md)
- [Document Analysis Workflow](docs/processes/001-document-analysis-workflow.md)
- [OpenAPI Specification](docs/api/openapi.yaml)

### Recent Changes
See `/docs/changes/` for complete change history. Latest changes:
- 2025-12-07: Self-Containment Requirements
- 2025-12-07: Phase 6 Frontend Complete
- 2025-12-07: Phase 5 API Layer complete
- 2025-12-06: Phase 4 AI Agent Integration complete

---

## Common Development Tasks

### Adding a New Feature
1. Create an ADR if it's an architectural decision
2. Define domain events and commands (if needed)
3. Implement aggregate changes (if needed)
4. Create command/query handlers
5. Add API endpoints
6. Update OpenAPI spec
7. Write tests (domain → infrastructure → application → API)
8. Run test suite: `pytest`
9. Create change log entry

### Fixing a Bug
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Ensure all tests pass
4. Create change log entry

### Updating Documentation
1. Update relevant files in `/docs/`
2. Keep GLOSSARY.md updated with new terms
3. Create change log entry if significant

### Making Architectural Changes
1. **Always** create an ADR first
2. Get consensus on the approach
3. Update IMPLEMENTATION_PLAN.md if needed
4. Implement changes
5. Update related documentation
6. Create change log entry

---

## Troubleshooting

### Backend Issues
- **Import errors**: Check `poetry install` has been run
- **Test failures**: Run `pytest -v` for verbose output
- **Type errors**: Run `pyright` to check type issues
- **Linting errors**: Run `ruff check` to see all issues

### Frontend Issues
- **Build errors**: Check `npm install` in `/client/`
- **Test failures**: Run `npm test` in `/client/`
- **Port conflicts**: Frontend runs on port 5000 (configured in `vite.config.ts`)

### Database Issues
- **Schema**: See `/docs/database/event_store_schema.sql`
- **Event sourcing**: Events are append-only, never modify existing events

---

## Important Notes

- **NEVER** delete events from the event store
- **ALWAYS** use ubiquitous language from GLOSSARY.md
- **ALWAYS** create change log entries after modifying files
- **ALWAYS** run tests before committing
- **NEVER** modify code without understanding the domain model first
- Read relevant ADRs before making architectural changes
- Follow the layered architecture - don't skip layers
- Use dependency injection via `/src/api/dependencies.py`

---

## Getting Help

- Review `/docs/GLOSSARY.md` for domain terminology
- Check `/docs/decisions/` for architectural context
- See `/docs/processes/` for common workflows
- Consult `/docs/IMPLEMENTATION_PLAN.md` for roadmap
- Read test files to understand expected behavior
