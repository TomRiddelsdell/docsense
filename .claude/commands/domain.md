# Domain Context Command

You are working within a DDD bounded context. Follow these rules:

## Task
Analyze and work within the specified domain bounded context: {{domain}}

## Guidelines
1. **Maintain Domain Boundaries**: Ensure no direct dependencies between domains
2. **Layer Separation**: Respect clean architecture layers (domain → application → infrastructure → interface)
3. **Event Sourcing**: All state changes must be captured as domain events
4. **CQRS**: Separate command and query responsibilities
5. **Integration**: Use integration events and anti-corruption layers for cross-domain communication

## Domain Structure
- `src/domains/{{domain}}/domain/` - Domain entities, value objects, aggregates, events
- `src/domains/{{domain}}/application/` - Use cases, command/query handlers, DTOs
- `src/domains/{{domain}}/infrastructure/` - Repositories, external service adapters
- `src/domains/{{domain}}/interface/` - API endpoints, event subscribers

## Before Making Changes
1. Review existing domain events in the domain layer
2. Check for existing integration events
3. Verify test coverage
4. Review relevant ADRs in `/docs/decisions/`

## After Changes
1. Update or create tests (unit + integration)
2. Document new domain/integration events
3. Update `/changes/YYYY-MM-DD-description.md`
4. Check for any security implications
