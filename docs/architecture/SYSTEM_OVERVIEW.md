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
┌──────────────────────────────┐
│        AI AGENT              │
│  ┌────────────────────────┐  │
│  │  Google Agent Dev Kit  │  │
│  │  - Document Parser     │  │
│  │  - Analysis Engine     │  │
│  │  - Feedback Generator  │  │
│  └────────────────────────┘  │
└──────────────────────────────┘
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
- `AuditLogView`: Chronological audit entries
- `VersionHistoryView`: Document version timeline

### AI Agent

Document analysis powered by Google Agent Development Kit:

**Document Parser**
- Extracts text from PDF, Word, Markdown
- Identifies structure (sections, code blocks, formulas)
- Preserves formatting metadata

**Analysis Engine**
- Evaluates document against quality criteria
- Identifies issues and improvement opportunities
- Generates confidence scores

**Feedback Generator**
- Creates actionable suggestions
- Provides explanations and examples
- Formats before/after comparisons

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
| Frontend | React/Vue (TBD) |
| API | Python FastAPI |
| Event Store | PostgreSQL with event sourcing schema |
| Read Models | PostgreSQL |
| AI Agent | Google Agent Development Kit |
| File Storage | Local filesystem / Object storage |
| Authentication | JWT tokens |

## Key Design Decisions

See [ADR-001: Use DDD with Event Sourcing and CQRS](../decisions/001-use-ddd-event-sourcing-cqrs.md) for the architectural rationale.

## Scalability Considerations

- **Horizontal scaling**: API layer is stateless, can run multiple instances
- **Read model optimization**: Projections can be tailored for specific query patterns
- **Event store partitioning**: Can partition by document ID for large volumes
- **AI Agent queuing**: Analysis requests can be queued for load management

## Security Considerations

- All API endpoints require authentication
- Document access is scoped to owner
- Audit trail is immutable
- Sensitive data encryption at rest
- HTTPS for all communications
