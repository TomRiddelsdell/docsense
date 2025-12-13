# ADR 016: Event Versioning Strategy

**Date**: 2025-12-13  
**Status**: ✅ Accepted  
**Deciders**: Engineering Team  
**Related**: [ADR 001: DDD, Event Sourcing, CQRS](001-use-ddd-event-sourcing-cqrs.md)

---

## Context

In an event-sourced system, events are the source of truth and are **immutable** once persisted. However, business requirements evolve, requiring changes to event schemas over time. We need a strategy to:

1. Allow event schemas to evolve without breaking existing events
2. Support multiple event versions coexisting in the event store
3. Enable code to read events written by older versions
4. Maintain backward compatibility across deployments
5. Support aggregate reconstruction from mixed-version event streams

Without a versioning strategy, schema changes would break the system's ability to replay historical events, violating the fundamental principle of event sourcing.

---

## Decision

We adopt a **multi-version event strategy** combining:

1. **Weak Schema Evolution** (preferred)
2. **Event Upcasting** (when necessary)
3. **Tolerant Reader Pattern** (always)

### 1. Weak Schema Evolution

**Default approach**: Add only optional fields to events.

```python
# Version 1
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    content_type: str

# Version 2 - Add optional fields (safe, no migration needed)
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    content_type: str
    file_size: Optional[int] = None  # ✅ Optional field
    uploaded_by_user_id: Optional[str] = None  # ✅ Optional field
    version: int = 2
```

**Benefits**:
- No migration needed
- Old events remain readable
- New code handles both versions
- Zero downtime deployment

**When to use**: 95% of schema changes (adding metadata, audit fields, optional data)

---

### 2. Event Upcasting

**When needed**: Adding required fields, renaming fields, restructuring data.

Upcasters transform old event versions to new versions at **read time**.

```python
class DocumentUploadedV1ToV2Upcaster:
    """Transform DocumentUploaded V1 → V2."""
    
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentUploaded" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new required fields with sensible defaults."""
        return {
            **event_data,
            "version": 2,
            "file_size": 0,  # Default for historical events
            "uploaded_by_user_id": "system",  # System user
        }
```

**Key Principles**:
- Upcasting happens at **deserialization time** (not stored)
- Original events remain **immutable** in storage
- Multiple upcasters can chain (V1 → V2 → V3)
- Upcasters are **pure functions** (no side effects)

**When to use**: 
- Adding required fields
- Renaming fields
- Changing field types
- Restructuring nested data

---

### 3. Tolerant Reader Pattern

All event deserialization must tolerate missing fields.

```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    content_type: str
    file_size: Optional[int] = None  # ✅ Can be missing
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentUploaded':
        """Tolerant reader - handles missing optional fields."""
        return cls(
            document_id=data['document_id'],
            file_name=data['file_name'],
            content_type=data['content_type'],
            file_size=data.get('file_size'),  # ✅ Tolerant
        )
```

---

## Implementation Architecture

### Event Version Registry

```python
# /src/domain/events/versions.py
EVENT_VERSIONS = {
    "DocumentUploaded": 2,
    "DocumentConverted": 1,
    "AnalysisStarted": 1,
    "AnalysisCompleted": 1,
    "FeedbackProvided": 1,
    "PolicyAdded": 1,
    # ... all event types
}
```

### Upcaster Registry

```python
# /src/infrastructure/persistence/event_upcaster.py
class UpcasterRegistry:
    def __init__(self):
        self._upcasters: List[EventUpcaster] = []
    
    def register(self, upcaster: EventUpcaster) -> None:
        self._upcasters.append(upcaster)
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        event_type = event_data.get('event_type')
        version = event_data.get('version', 1)
        
        # Apply upcasters in sequence
        for upcaster in self._upcasters:
            if upcaster.can_upcast(event_type, version):
                event_data = upcaster.upcast(event_data)
                version = event_data['version']
        
        return event_data
```

### Event Store Integration

```python
# In EventStore.deserialize_event()
def deserialize_event(self, event_data: Dict[str, Any]) -> DomainEvent:
    # 1. Apply upcasting
    event_data = self._upcaster_registry.upcast(event_data)
    
    # 2. Deserialize to current version
    event_class = self._event_registry.get(event_data['event_type'])
    return event_class.from_dict(event_data)
```

---

## Evolution Patterns

### Pattern 1: Add Optional Field (Weak Schema) ✅

```python
# No migration needed!
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    new_field: Optional[str] = None  # ✅ Add with default
```

### Pattern 2: Add Required Field (Needs Upcaster) ⚠️

```python
# Step 1: Create upcaster
class DocumentUploadedV1ToV2Upcaster:
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **event_data,
            "version": 2,
            "required_field": "default_value",
        }

# Step 2: Update event
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    required_field: str  # Now required
    version: int = 2
```

### Pattern 3: Rename Field (Needs Upcaster) ⚠️

```python
class DocumentUploadedV1ToV2Upcaster:
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        data = {**event_data, "version": 2}
        # Rename: old_name → new_name
        if 'old_name' in data:
            data['new_name'] = data.pop('old_name')
        return data
```

### Pattern 4: Remove Field (Mark Deprecated) ⚠️

```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    # deprecated_field removed from signature
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DocumentUploaded':
        # Ignore deprecated fields during deserialization
        return cls(
            document_id=data['document_id'],
            file_name=data['file_name'],
            # deprecated_field ignored
        )
```

---

## Migration Process

### For Adding Optional Fields (No Downtime)

1. ✅ Add optional field with default value
2. ✅ Deploy code
3. ✅ New events include field, old events work fine
4. ✅ Done!

### For Adding Required Fields (Requires Upcaster)

1. ⚠️ Create upcaster with default value
2. ⚠️ Register upcaster in event store
3. ⚠️ Add integration tests
4. ⚠️ Update event class with required field
5. ⚠️ Deploy code
6. ⚠️ Verify old events upcast correctly
7. ✅ Done!

### For Breaking Changes (Last Resort)

1. 🔴 Create entirely new event type (e.g., `DocumentUploadedV2`)
2. 🔴 Support both event types in aggregates
3. 🔴 Migrate aggregates gradually
4. 🔴 Deprecate old event type
5. 🔴 Remove after all aggregates migrated

**Avoid if possible** - breaking changes are expensive!

---

## Testing Strategy

### 1. Upcaster Unit Tests

```python
def test_document_uploaded_v1_to_v2_upcaster():
    upcaster = DocumentUploadedV1ToV2Upcaster()
    
    v1_data = {
        "event_type": "DocumentUploaded",
        "version": 1,
        "document_id": "doc-123",
        "file_name": "test.pdf",
        "content_type": "application/pdf",
    }
    
    v2_data = upcaster.upcast(v1_data)
    
    assert v2_data["version"] == 2
    assert v2_data["file_size"] == 0  # Default
    assert v2_data["uploaded_by_user_id"] == "system"
```

### 2. Integration Tests

```python
@pytest.mark.integration
async def test_aggregate_reconstruction_with_mixed_versions():
    """Test aggregate can be reconstructed from V1 and V2 events."""
    # Store V1 event
    v1_event = {...}  # Old format
    await event_store.append(v1_event)
    
    # Store V2 event
    v2_event = {...}  # New format
    await event_store.append(v2_event)
    
    # Reconstruct aggregate - should work!
    events = await event_store.get_events(aggregate_id)
    aggregate = Document.from_events(events)
    
    assert aggregate is not None
```

### 3. Backward Compatibility Tests

```python
def test_new_code_reads_old_events():
    """Ensure new code can deserialize old event formats."""
    old_event_json = load_from_production_snapshot()
    event = event_store.deserialize_event(old_event_json)
    assert event is not None
```

---

## Consequences

### Positive ✅

1. **Zero Data Migration**: Old events never need updating
2. **Zero Downtime Deployments**: Code changes compatible with existing events
3. **Audit Trail Preserved**: Original events remain immutable
4. **Backward Compatible**: New code reads old events
5. **Gradual Evolution**: Schema evolves incrementally
6. **Testable**: Upcasters are pure functions, easy to test

### Negative ⚠️

1. **Upcaster Complexity**: Need to maintain upcasters for each version
2. **Read Performance**: Upcasting adds overhead during deserialization
3. **Testing Burden**: Must test all version combinations
4. **Code Maintenance**: Old version handling code persists
5. **Documentation Overhead**: Need to document evolution history

### Mitigations

- **Performance**: Cache upcasted events in projections (read models)
- **Complexity**: Keep upcasters simple, limit chaining depth
- **Testing**: Automate version compatibility tests in CI
- **Cleanup**: Archive upcasters after 2 years of no V1 events

---

## Alternatives Considered

### Alternative 1: Big Bang Schema Migration ❌

**Rejected**: Violates event immutability, risks data loss, requires downtime.

### Alternative 2: Copy-and-Replace Events ❌

**Rejected**: Loses event timestamps, breaks audit trail, expensive for large stores.

### Alternative 3: Event Type Per Version ❌

```python
DocumentUploadedV1
DocumentUploadedV2
DocumentUploadedV3
```

**Rejected**: Explosion of event types, aggregate complexity, difficult to maintain.

### Alternative 4: Schema Registry (Avro/Protobuf) 🤔

**Considered but deferred**: Would provide formal schema evolution with backward/forward compatibility, but adds significant infrastructure complexity. May revisit if upcasting becomes unmaintainable.

---

## Related Decisions

- [ADR 001: Use DDD, Event Sourcing, CQRS](001-use-ddd-event-sourcing-cqrs.md) - Foundation
- [ADR 004: Document Format Conversion](004-document-format-conversion.md) - Events affected
- [ADR 005: Policy Repository System](005-policy-repository-system.md) - Events affected

---

## References

- [Martin Fowler - Event Sourcing](https://martinfowler.com/eaaDev/EventSourcing.html)
- [Greg Young - Versioning in an Event Sourced System](https://leanpub.com/esversioning)
- [Event Store - Event Versioning](https://developers.eventstore.com/server/v21.10/streams.html#event-versioning)
- [Microsoft - Event Versioning Patterns](https://docs.microsoft.com/en-us/azure/architecture/patterns/event-sourcing)

---

## Revision History

| Date | Changes | Author |
|------|---------|--------|
| 2025-12-13 | Initial version | Engineering Team |
