# System Architecture Overview

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              FRONTEND                                    │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │   Upload    │  │  Analysis   │  │   Version   │  │   Export    │    │
│  │   Panel     │  │    View     │  │   History   │  │   Dialog    │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ REST API
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           API GATEWAY                                    │
│  ┌─────────────────────────────────────────────────────────────────┐    │
│  │  Authentication  │  Rate Limiting  │  Request Routing           │    │
│  └─────────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┴───────────────┐
                    │                               │
                    ▼                               ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│       COMMAND SIDE           │    │        QUERY SIDE            │
│  ┌────────────────────────┐  │    │  ┌────────────────────────┐  │
│  │   Command Handlers     │  │    │  │    Query Handlers      │  │
│  └────────────────────────┘  │    │  └────────────────────────┘  │
│             │                │    │             │                │
│             ▼                │    │             ▼                │
│  ┌────────────────────────┐  │    │  ┌────────────────────────┐  │
│  │   Domain Aggregates    │  │    │  │    Read Models         │  │
│  │  - Document            │  │    │  │  - DocumentView        │  │
│  │  - FeedbackSession     │  │    │  │  - FeedbackView        │  │
│  │  - AuditTrail          │  │    │  │  - AuditLogView        │  │
│  └────────────────────────┘  │    │  │  - VersionHistoryView  │  │
│             │                │    │  └────────────────────────┘  │
│             ▼                │    │             ▲                │
│  ┌────────────────────────┐  │    │             │                │
│  │   Event Store          │──┼────┼─────────────┘                │
│  └────────────────────────┘  │    │         Projections          │
└──────────────────────────────┘    └──────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│                   AI AGENT LAYER                          │
│  ┌────────────────────────────────────────────────────┐  │
│  │              Model Abstraction Layer               │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────────────┐ │  │
│  │  │  Gemini  │  │  OpenAI  │  │  Anthropic Claude│ │  │
│  │  └──────────┘  └──────────┘  └──────────────────┘ │  │
│  └────────────────────────────────────────────────────┘  │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Document Converter │ Analysis Engine │ Feedback   │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
                │
                ▼
┌──────────────────────────────────────────────────────────┐
│                  POLICY REPOSITORY                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Policy Management │ Compliance Rules │ Validation │  │
│  └────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────┘
```

## Components

### Frontend Layer

The web-based user interface providing:
- **Upload Panel**: Drag-and-drop document upload with format validation
- **Analysis View**: Display of AI-generated feedback with accept/reject controls
- **Version History**: Timeline view of document versions and changes
- **Export Dialog**: Format selection and download for final documents

### API Gateway

Entry point for all API requests:
- **Authentication**: JWT-based authentication and authorization
- **Rate Limiting**: Protection against abuse and overload
- **Request Routing**: Directs commands to write side, queries to read side

### Command Side (Write Model)

Handles all state-changing operations:

**Command Handlers**
- Validate incoming commands
- Load aggregates from event store
- Execute domain logic
- Persist new events

**Domain Aggregates**
- `Document`: Manages document lifecycle and versions
- `FeedbackSession`: Manages analysis sessions and suggestions
- `PolicyRepository`: Manages compliance rules and requirements
- `AuditTrail`: Records all auditable actions

**Event Store**
- Append-only storage for all domain events
- Source of truth for system state
- Enables event replay and time-travel debugging

### Query Side (Read Model)

Handles all read operations:

**Projections**
- Subscribe to events from Event Store
- Build optimized read models
- Maintain eventual consistency

**Read Models**
- `DocumentView`: Current document state for display
- `FeedbackView`: Pending and resolved feedback items
- `PolicyView`: Policy repositories and their rules
- `ComplianceView`: Document compliance status
- `AuditLogView`: Chronological audit entries
- `VersionHistoryView`: Document version timeline

### AI Agent Layer

Multi-model document analysis with policy-aware evaluation:

**Model Abstraction**
- Supports multiple AI providers (Google Gemini, OpenAI, Anthropic)
- Provider selection based on task and data sensitivity
- Consistent interface across all models

**Document Converter**
- Converts Word, PDF, RST, Markdown to canonical format
- Preserves structure (sections, code blocks, formulas, tables)
- Extracts metadata for context

**Analysis Engine**
- Evaluates document against assigned Policy Repository
- Identifies compliance issues and improvement opportunities
- Long-running analysis (up to 3 min/page, 100 page max)
- Progress tracking with partial results

**Feedback Generator**
- Creates actionable suggestions requiring user acceptance
- Provides explanations with before/after comparisons
- Links findings to specific policy requirements

### Policy Repository

Manages regulatory and compliance requirements:

**Policy Management**
- Define Policy Repositories for different regulatory contexts
- Configure policies with MUST/SHOULD/MAY requirements
- Create validation rules with AI prompt templates

**Document Assignment**
- Assign documents to Policy Repositories
- Track compliance status per document
- Generate compliance reports

## Data Flow

### Command Flow (Write)

```
1. User action (e.g., Accept Change)
           │
           ▼
2. API receives command
           │
           ▼
3. Command Handler validates
           │
           ▼
4. Load Aggregate from Event Store
           │
           ▼
5. Execute domain logic
           │
           ▼
6. Generate new events
           │
           ▼
7. Persist events to Event Store
           │
           ▼
8. Publish events for projections
```

### Query Flow (Read)

```
1. User requests data (e.g., View Feedback)
           │
           ▼
2. API routes to Query Handler
           │
           ▼
3. Query Handler reads from Read Model
           │
           ▼
4. Return formatted response
```

### Analysis Flow

```
1. AnalyzeDocument command received
           │
           ▼
2. Load document from storage
           │
           ▼
3. Convert to parseable format
           │
           ▼
4. Record DocumentConverted event
           │
           ▼
5. Send to AI Agent
           │
           ▼
6. Agent analyzes document
           │
           ▼
7. Generate feedback items
           │
           ▼
8. Store as FeedbackGenerated events
           │
           ▼
9. Update FeedbackView projection
```

## Technology Stack

| Layer | Technology |
|-------|------------|
| Frontend | React with TypeScript, Shadcn/ui, Tailwind CSS |
| API | Python FastAPI (API-First Design) |
| Event Store | PostgreSQL with event sourcing schema |
| Read Models | PostgreSQL |
| AI Models | Multi-provider: Google Gemini, OpenAI, Anthropic Claude |
| Document Conversion | python-docx, pdfplumber, docutils |
| File Storage | Local filesystem / Object storage |
| Authentication | JWT tokens (deferred; open access initially) |

## Key Design Decisions

| ADR | Decision |
|-----|----------|
| [ADR-001](../decisions/001-use-ddd-event-sourcing-cqrs.md) | DDD with Event Sourcing and CQRS |
| [ADR-002](../decisions/002-react-frontend.md) | React frontend with deferred real-time |
| [ADR-003](../decisions/003-multi-model-ai-support.md) | Multi-model AI with user acceptance workflow |
| [ADR-004](../decisions/004-document-format-conversion.md) | Document format conversion to Markdown |
| [ADR-005](../decisions/005-policy-repository-system.md) | Policy repository for compliance |
| [ADR-006](../decisions/006-api-first-design.md) | API-first design for integration |
| [ADR-007](../decisions/007-shadcn-ui-component-library.md) | Shadcn/ui component library |

## Scalability Considerations

- **Horizontal scaling**: API layer is stateless, can run multiple instances
- **Read model optimization**: Projections can be tailored for specific query patterns
- **Event store partitioning**: Can partition by document ID for large volumes
- **AI Agent queuing**: Analysis requests can be queued for load management

## Security Considerations

### Production Security (Target State)
- All API endpoints require authentication
- Document access is scoped to owner
- Audit trail is immutable
- Sensitive data encryption at rest
- HTTPS for all communications
- Model selection constraints for sensitive documents

### Interim Access Controls (Open Access Phase)

During initial development with deferred authentication:

1. **Network Isolation**: Deploy in private network, not publicly accessible
2. **No Sensitive Documents**: Do not upload real trading strategy documents until auth is implemented
3. **Test Data Only**: Use synthetic/test documents for development
4. **Audit Logging**: All actions logged even without user identity
5. **Priority**: Authentication should be implemented before handling sensitive content

**Risk Mitigation**: The open access phase is intended for internal development and testing only. Production deployment with sensitive documents requires full authentication implementation.
