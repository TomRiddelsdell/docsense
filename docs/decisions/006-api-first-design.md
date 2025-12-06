# ADR-006: API-First Design for Tool Integration

## Status
Accepted

## Date
2025-12-06

## Context

Integration with other tools is a key requirement. The system must expose functionality programmatically for:
- Automated document analysis pipelines
- Integration with document management systems
- CI/CD integration for documentation quality gates
- Custom tooling and scripting
- Third-party application integration

The organization is large, suggesting multiple teams and systems that need to interact with the document analyzer.

## Decision

We will adopt an **API-First design** approach where:

1. All functionality is exposed through a RESTful API
2. The web frontend is a consumer of the API (no special backend routes)
3. API is designed and documented before implementation
4. OpenAPI 3.0 specification is the source of truth

### 1. API Structure

```
/api/v1/
├── /documents
│   ├── POST   /                    # Upload document
│   ├── GET    /                    # List documents
│   ├── GET    /{id}                # Get document details
│   ├── DELETE /{id}                # Delete document
│   ├── POST   /{id}/analyze        # Start analysis
│   └── GET    /{id}/analysis       # Get analysis results
│
├── /policies
│   ├── POST   /repositories        # Create policy repository
│   ├── GET    /repositories        # List repositories
│   ├── GET    /repositories/{id}   # Get repository details
│   ├── POST   /repositories/{id}/policies  # Add policy
│   └── PUT    /repositories/{id}/policies/{pid}  # Update policy
│
├── /assignments
│   ├── POST   /                    # Assign document to repository
│   ├── GET    /document/{id}       # Get assignments for document
│   └── GET    /repository/{id}     # Get documents in repository
│
├── /suggestions
│   ├── GET    /document/{id}       # Get suggestions for document
│   ├── POST   /{id}/accept         # Accept suggestion
│   ├── POST   /{id}/reject         # Reject suggestion
│   └── POST   /{id}/modify         # Accept with modifications
│
├── /audit
│   ├── GET    /document/{id}       # Audit trail for document
│   └── GET    /events              # System-wide audit events
│
└── /health
    └── GET    /                    # Health check
```

### 2. API Design Principles

- **Consistent naming**: Plural nouns for resources
- **HTTP semantics**: Proper use of GET, POST, PUT, DELETE
- **Pagination**: All list endpoints support pagination
- **Filtering**: Query parameters for filtering and search
- **Versioning**: URL-based versioning (/api/v1/)
- **Error responses**: Consistent error format with codes and messages

### 3. Authentication (Future)

- API keys for service-to-service integration
- JWT tokens for user sessions
- OAuth2 for third-party integrations

### 4. Rate Limiting

- Configurable per-client rate limits
- Special limits for long-running operations (analysis)

### 5. Documentation

OpenAPI spec located at: `/docs/api/openapi.yaml`
- Auto-generated client libraries
- Interactive API documentation (Swagger UI)

## Consequences

### Positive
- Clean separation of concerns
- Easy integration with any tool that speaks HTTP
- Frontend and API can be developed independently
- Enables automation and scripting
- Single source of truth for API contract

### Negative
- More upfront design effort
- Need to maintain API documentation
- Versioning complexity as API evolves

## Related ADRs
- [ADR-001: DDD with Event Sourcing and CQRS](001-use-ddd-event-sourcing-cqrs.md)
- [ADR-002: React Frontend](002-react-frontend.md)
- [ADR-005: Policy Repository System](005-policy-repository-system.md)
