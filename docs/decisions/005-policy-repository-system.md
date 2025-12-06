# ADR-005: Policy Repository System for Regulatory Compliance

## Status
Accepted

## Date
2025-12-06

## Context

Trading algorithm documentation must comply with regulatory, compliance, and legal requirements. These requirements vary by:
- Jurisdiction (e.g., SEC, FCA, ESMA)
- Algorithm type (quantitative systematic strategies)
- Use case (index publishing)
- Internal organizational policies

Users need to:
1. Define sets of policies as "Policy Repositories"
2. Assign documents to specific Policy Repositories
3. Have AI analyze documents against those policies
4. Track compliance status over time

## Decision

We will implement a **Policy Repository System** as a first-class domain concept.

### 1. Domain Model

```
PolicyRepository (Aggregate Root)
├── id: UUID
├── name: string
├── description: string
├── jurisdiction: string (optional)
├── policies: Policy[]
├── created_at: datetime
└── version: int

Policy
├── id: UUID
├── name: string
├── description: string
├── requirement_type: enum (MUST, SHOULD, MAY)
├── validation_rules: ValidationRule[]
└── examples: Example[]

ValidationRule
├── rule_type: enum (CONTENT_REQUIRED, FORMAT_REQUIRED, SECTION_REQUIRED, ...)
├── parameters: dict
└── ai_prompt_template: string

DocumentPolicyAssignment
├── document_id: UUID
├── policy_repository_id: UUID
├── assigned_at: datetime
├── assigned_by: user_id
└── compliance_status: enum (PENDING, COMPLIANT, NON_COMPLIANT, PARTIAL)
```

### 2. Policy Repository Examples

**Regulatory Repository: "SEC Index Publishing"**
- Must include methodology description
- Must document rebalancing rules
- Must specify holiday calendar
- Must include backtesting results

**Compliance Repository: "Internal Algo Documentation Standard"**
- Should include risk metrics
- Must document data sources
- Should include code review sign-off

### 3. Integration with AI Analysis

When analyzing a document:
1. Load assigned Policy Repository
2. Include policy requirements in AI context
3. AI evaluates document against each policy
4. Generate compliance report with specific findings

### 4. Events

- `PolicyRepositoryCreated`
- `PolicyAdded`
- `PolicyUpdated`
- `PolicyRemoved`
- `DocumentAssignedToRepository`
- `ComplianceStatusUpdated`

## Consequences

### Positive
- Centralized policy management
- Consistent compliance evaluation
- Audit trail of policy assignments and compliance
- Reusable across multiple documents
- AI analysis is policy-aware

### Negative
- Additional complexity in domain model
- Policies need ongoing maintenance
- AI may interpret policies inconsistently

### Mitigation
- Provide policy templates for common regulatory frameworks
- Allow policy validation rules to include explicit examples
- Human review of AI compliance findings

## Related ADRs
- [ADR-001: DDD with Event Sourcing and CQRS](001-use-ddd-event-sourcing-cqrs.md)
- [ADR-003: Multi-Model AI Support](003-multi-model-ai-support.md)
- [ADR-006: API-First Design](006-api-first-design.md)
