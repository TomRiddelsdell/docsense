# ADR-003: Multi-Model AI Support with User Acceptance Workflow

## Status
Accepted

## Date
2025-12-06

## Context

The document analyzer requires AI-powered analysis to provide actionable feedback on trading algorithm documentation. Key constraints:

- Analysis may take up to 3 minutes per page
- Documents can be up to 100 pages (potentially 5 hours per document)
- User acceptance of recommended changes is mandatory
- Multi-model support is preferred over vendor lock-in
- Documents contain sensitive trading strategy information

## Decision

We will implement a **multi-model AI abstraction layer** with the following design:

### 1. Model Abstraction Interface

```python
class AIModelProvider(ABC):
    @abstractmethod
    async def analyze_section(self, content: str, policy_context: dict) -> AnalysisResult:
        pass
    
    @abstractmethod
    async def generate_suggestion(self, issue: Issue, context: dict) -> Suggestion:
        pass
```

### 2. Supported Providers (Initial)
- Google Gemini (via Google Agent Development Kit)
- OpenAI GPT-4
- Anthropic Claude

### 3. User Acceptance Workflow

All AI-generated suggestions require explicit user action:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Pending   │────▶│  Reviewed   │────▶│  Accepted   │
│             │     │             │     │  or         │
│             │◀────│             │     │  Rejected   │
└─────────────┘     └─────────────┘     └─────────────┘
      │                                        │
      └────────── User Decision Required ──────┘
```

### 4. Long-Running Analysis Strategy

- Background job processing for document analysis
- Page-by-page processing with progress tracking
- Ability to pause/resume analysis
- Partial results available as analysis progresses

## Consequences

### Positive
- No vendor lock-in; can switch models based on performance/cost
- Explicit user acceptance ensures human oversight
- Progress visibility during long-running analyses
- Sensitive data can be routed to appropriate models

### Negative
- Abstraction layer adds complexity
- Different models may produce inconsistent output formats
- Need to manage multiple API credentials

### Security Considerations
- Model selection can be constrained by data sensitivity
- On-premise model options may be needed for highly sensitive docs
- Audit trail of which model processed which content

## Related ADRs
- [ADR-001: DDD with Event Sourcing and CQRS](001-use-ddd-event-sourcing-cqrs.md)
- [ADR-004: Document Format Conversion](004-document-format-conversion.md)
- [ADR-005: Policy Repository System](005-policy-repository-system.md)
