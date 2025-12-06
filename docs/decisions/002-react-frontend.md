# ADR-002: React Frontend with Deferred Real-Time Features

## Status
Accepted

## Date
2025-12-06

## Context

The Trading Algorithm Document Analyzer needs a web-based frontend for document management, AI-driven analysis review, and policy compliance workflows. The application will serve a large organization with eventual authentication requirements.

Key requirements:
- Large organization deployment
- Complex document review workflows
- User acceptance of AI-recommended changes
- Real-time updates are non-essential initially
- Integration with policy repositories
- API-first backend design

## Decision

We will use **React** as the frontend framework with the following approach:

1. **React with TypeScript** for type safety and maintainability at scale
2. **Deferred real-time features** - initial implementation uses polling; WebSocket support added later if needed
3. **Component library**: To be determined (Shadcn/ui)
4. **State management**: React Query for server state, React Context for UI state
5. **Authentication-ready**: Design components with auth hooks even before implementing login

## Architecture

```
frontend/
├── src/
│   ├── components/          # Reusable UI components
│   │   ├── documents/       # Document upload, list, viewer
│   │   ├── analysis/        # AI feedback display, accept/reject
│   │   ├── policies/        # Policy repository management
│   │   └── common/          # Buttons, modals, forms
│   ├── pages/               # Route-level components
│   ├── hooks/               # Custom React hooks
│   ├── api/                 # API client and types
│   ├── stores/              # State management
│   └── utils/               # Helper functions
├── public/
└── package.json
```

## Consequences

### Positive
- React has extensive ecosystem and community support
- TypeScript improves code quality for large codebases
- Deferring real-time reduces initial complexity
- Component-based architecture supports team collaboration

### Negative
- React bundle size larger than alternatives (Vue, Svelte)
- Additional build tooling complexity
- Team must be familiar with React patterns

### Risks
- If real-time becomes essential, refactoring to WebSocket may require significant changes
- Mitigation: Design data fetching layer with abstraction that can switch polling to WebSocket

## Related ADRs
- [ADR-001: DDD with Event Sourcing and CQRS](001-use-ddd-event-sourcing-cqrs.md)
- [ADR-006: API-First Design](006-api-first-design.md)
