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
client/
├── src/
│   ├── assets/              # Static assets (images, icons)
│   ├── components/
│   │   └── ui/              # Shadcn/ui components (Button, Card, etc.)
│   ├── context/             # React context providers (to be implemented)
│   ├── hooks/               # Custom React hooks (to be implemented)
│   ├── lib/
│   │   └── utils.ts         # Utility functions (cn helper for Tailwind)
│   ├── pages/               # Route-level components (to be implemented)
│   ├── services/            # API client services (to be implemented)
│   ├── types/               # TypeScript type definitions (to be implemented)
│   ├── App.tsx              # Main application component
│   ├── main.tsx             # Application entry point
│   └── index.css            # Global styles with Tailwind imports
├── public/
├── index.html               # HTML entry point
├── vite.config.ts           # Vite configuration (port 5000, allowedHosts: true)
├── tsconfig.json            # TypeScript configuration
├── tsconfig.app.json        # App-specific TypeScript config
├── eslint.config.js         # ESLint configuration
└── package.json
```

Note: Directories marked "(to be implemented)" exist as empty placeholders for Phase 6 (Frontend Implementation). Currently implemented with content: components/ui/ (Shadcn/ui Button, Card), lib/utils.ts (cn helper), assets/ (react.svg), App.tsx, main.tsx, index.css.

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
