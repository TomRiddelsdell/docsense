# Trading Algorithm Document Analyzer

## Project Overview

An AI-powered application that analyzes trading algorithm documentation and provides actionable feedback for improvement. The application maintains a complete audit trail of all document changes.

### Tech Stack
- **Backend**: Python with FastAPI
- **Architecture**: Domain-Driven Design (DDD) with Event Sourcing and CQRS
- **AI Agent**: Google Agent Development Kit
- **Database**: PostgreSQL (for event store and read models)
- **Frontend**: React with TypeScript, Shadcn/ui, Tailwind CSS

### Current State
- **Phase**: Implementation Foundation Complete
- **Status**: API spec, database schema, frontend, document converters, and policy templates ready

---

## Directory Structure

```
/
├── client/                         # React frontend (Vite + TypeScript + Tailwind + Shadcn/ui)
│   ├── src/
│   │   ├── components/ui/          # Shadcn/ui components (Button, Card)
│   │   ├── lib/utils.ts            # Utility functions
│   │   └── App.tsx                 # Main application component
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
│   └── VISION.md                   # Product vision and goals
├── src/                            # Backend source code
│   ├── infrastructure/
│   │   └── converters/             # Document conversion pipeline
│   │       ├── base.py             # Base classes and types
│   │       ├── word_converter.py   # DOCX converter
│   │       ├── pdf_converter.py    # PDF converter (PyMuPDF + pdfplumber)
│   │       ├── rst_converter.py    # RST to Markdown converter
│   │       ├── markdown_converter.py # Markdown passthrough
│   │       └── converter_factory.py  # Factory pattern
│   ├── domain/                     # Domain layer (to be implemented)
│   ├── application/                # Application layer (to be implemented)
│   └── api/                        # API layer (to be implemented)
├── tests/                          # Test suite (to be created)
├── main.py                         # Application entry point
└── replit.md                       # This file
```

---

## AI Agent Instructions

### CRITICAL: Documentation Conventions

When making changes to this project, you MUST follow these conventions:

#### 1. Architecture Decision Records (ADRs)
- **Location**: `/docs/decisions/`
- **Naming**: `<number>-<short-description>.md` (e.g., `002-use-fastapi-for-backend.md`)
- **When to create**: Any significant architectural or technical decision
- **Template**: Use `/docs/decisions/000-template.md`
- **Numbering**: Sequential, zero-padded to 3 digits

#### 2. Process Documentation
- **Location**: `/docs/processes/`
- **Naming**: `<number>-<process-name>.md` (e.g., `002-version-rollback.md`)
- **When to create**: Any repeatable multi-step workflow
- **Template**: Use `/docs/processes/000-template.md`
- **Numbering**: Sequential, zero-padded to 3 digits

#### 3. Change Log (MANDATORY)
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

### Code Conventions

#### Domain-Driven Design
- Use ubiquitous language from `/docs/GLOSSARY.md`
- Aggregates in `/src/domain/aggregates/`
- Events in `/src/domain/events/`
- Commands in `/src/domain/commands/`
- Value objects in `/src/domain/value_objects/`

#### Event Sourcing
- Events are immutable and named in past tense (e.g., `DocumentUploaded`)
- Events contain all data needed to reconstruct state
- Never delete events; use compensating events

#### CQRS
- Commands are named imperatively (e.g., `UploadDocument`)
- Separate read and write models
- Projections build read models from events

#### API Design
- RESTful endpoints following OpenAPI 3.0
- Commands: POST/PUT/DELETE operations
- Queries: GET operations
- Document API in `/docs/api/openapi.yaml`

### Testing Requirements
- Unit tests for domain logic
- Integration tests for event store operations
- End-to-end tests for API endpoints

---

## Recent Changes

| Date | Description | Change Log |
|------|-------------|------------|
| 2025-12-06 | Implementation foundation complete | [Link](docs/changes/2025-12-06-implementation-foundation.md) |
| 2025-12-06 | Shadcn/ui component library selected | [Link](docs/changes/2025-12-06-shadcn-ui-selection.md) |
| 2025-12-06 | Architectural decisions documented | [Link](docs/changes/2025-12-06-architectural-decisions.md) |
| 2025-12-06 | Initial documentation structure | [Link](docs/changes/2025-12-06-initial-documentation-structure.md) |

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

### Other Documentation
- [System Architecture Overview](docs/architecture/SYSTEM_OVERVIEW.md)
- [Glossary](docs/GLOSSARY.md)
- [Product Vision](docs/VISION.md)
- [Document Analysis Workflow](docs/processes/001-document-analysis-workflow.md)
