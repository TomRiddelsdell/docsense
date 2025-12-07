# ADR-008: Frontend Architecture Patterns

## Status
Accepted

## Date
2025-12-07

## Context

Phase 6 frontend implementation requires decisions on:
- Client-side routing
- Server state management
- API integration patterns
- Graph visualization library
- Real-time chat implementation

These decisions build upon ADR-002 (React Frontend) and ADR-007 (Shadcn/ui).

## Decision

### 1. Client-Side Routing: React Router v6

**Choice**: React Router DOM v6

**Rationale**:
- Industry standard for React applications
- Declarative routing with nested layouts
- Data loading patterns with loaders (optional)
- URL-based state for shareable links

**Route Structure**:
```
/                           # Home/Landing page
/documents                  # Document list
/documents/upload           # Upload new document
/documents/:id              # Document detail with tabs
/documents/:id/issues       # Deep link to issues tab
/documents/:id/chat         # Deep link to chat tab
/documents/:id/graph        # Deep link to graph tab
/policies                   # Policy management (future)
/audit                      # Audit log (future)
```

### 2. Server State Management: TanStack Query v5

**Choice**: TanStack Query (React Query)

**Rationale**:
- Automatic caching and background refetching
- Optimistic updates for better UX
- Built-in loading/error states
- Query invalidation for data consistency
- Deduplication of requests

**Patterns**:
- Queries for read operations (GET)
- Mutations for write operations (POST/PUT/DELETE)
- Query keys follow `['resource', id?, filters?]` convention
- Stale time: 5 minutes for document data

### 3. API Client: Axios

**Choice**: Axios with typed interceptors

**Rationale**:
- Familiar API for team
- Request/response interceptors for auth and error handling
- TypeScript integration with generics
- Automatic JSON transformation

**Configuration**:
- Base URL: `/api/v1` (proxied in development)
- Content-Type: `application/json` for most requests
- `multipart/form-data` for file uploads

### 4. Graph Visualization: React Flow (@xyflow/react)

**Choice**: React Flow (xyflow)

**Rationale**:
- Purpose-built for node-based graphs
- Highly customizable nodes and edges
- Built-in pan, zoom, minimap controls
- Active maintenance and community
- MIT license

**Alternatives Considered**:
- D3.js: Lower level, more implementation effort
- Vis.js: Heavier, less React-native integration
- Cytoscape: More academic focus, steeper learning curve

### 5. Chat Implementation: Client-Side State with API Integration

**Approach**: Local state + mutations

**Rationale**:
- Initial implementation without WebSocket (per ADR-002)
- Chat history managed in component state
- Messages persisted per session
- Future: Can add WebSocket for real-time if needed

**Data Flow**:
1. User types message
2. Optimistically add to local state
3. Send to backend API
4. Receive response and add to state
5. Error handling with retry option

## Consequences

### Positive
- Consistent patterns across all frontend features
- Good developer experience with type safety
- Optimistic updates improve perceived performance
- Easy to add real-time features later

### Negative
- Additional dependencies increase bundle size
- Team must learn TanStack Query patterns
- Graph visualization adds complexity

### Risks
- React Flow may have performance issues with large graphs (>1000 nodes)
  - Mitigation: Implement virtualization and lazy loading for large graphs

## Documentation Gaps Identified

1. **OpenAPI Spec**: Missing chat and parameters endpoints
   - Action: Update `docs/api/openapi.yaml` with new endpoints
   
2. **Backend Implementation**: Chat and parameters endpoints not yet implemented
   - Action: Add to Phase 6 backend tasks

3. **Testing Strategy**: No frontend testing ADR
   - Action: Document testing approach in implementation progress

## Related ADRs
- [ADR-002: React Frontend](002-react-frontend.md)
- [ADR-006: API-First Design](006-api-first-design.md)
- [ADR-007: Shadcn/ui Component Library](007-shadcn-ui-component-library.md)
