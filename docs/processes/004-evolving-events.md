# Process 004: Evolving Events

**Status**: Active  
**Owner**: Engineering Team  
**Last Updated**: 2025-12-13

---

## Overview

This document describes the process for evolving event schemas in our event-sourced system. Events are immutable once persisted, but business requirements change. This process ensures schema evolution without breaking existing events.

**Related**:
- [ADR 016: Event Versioning Strategy](../decisions/016-event-versioning-strategy.md)
- [ADR 001: DDD, Event Sourcing, CQRS](../decisions/001-use-ddd-event-sourcing-cqrs.md)

---

## Key Principles

1. **Events are Immutable**: Never modify events in storage
2. **Backward Compatible**: New code must read old events
3. **Gradual Evolution**: Prefer small, incremental changes
4. **Tolerant Reader**: Handle missing optional fields gracefully
5. **Test Thoroughly**: Verify all version combinations work

---

## Types of Changes

### 🟢 Safe Changes (No Migration)

These changes require no data migration or upcasters:

#### 1. Add Optional Field

**When**: Adding new metadata, audit fields, or optional data.

**Steps**:
```python
# Step 1: Add optional field to event
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    content_type: str
    file_size: Optional[int] = None  # ✅ New optional field
    version: int = 1  # Version unchanged
```

**No other steps needed!** 🎉
- Old events work without the field
- New events include the field
- Zero downtime deployment

**Example**:
```python
# Old event (still valid)
{
    "event_type": "DocumentUploaded",
    "document_id": "doc-123",
    "file_name": "test.pdf",
    "content_type": "application/pdf"
}

# New event (includes optional field)
{
    "event_type": "DocumentUploaded",
    "document_id": "doc-124",
    "file_name": "test2.pdf",
    "content_type": "application/pdf",
    "file_size": 1024000
}
```

---

### 🟡 Moderate Changes (Requires Upcaster)

These changes require an upcaster to transform old events:

#### 2. Add Required Field

**When**: New field is essential for business logic.

**Steps**:

1. **Create Upcaster**:
```python
# /src/infrastructure/persistence/event_upcaster.py
class DocumentUploadedV1ToV2Upcaster:
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentUploaded" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **event_data,
            "version": 2,
            "file_size": 0,  # Sensible default
        }
```

2. **Register Upcaster**:
```python
# In create_upcaster_registry()
def create_upcaster_registry() -> UpcasterRegistry:
    registry = UpcasterRegistry()
    registry.register(DocumentUploadedV1ToV2Upcaster())  # ← Add here
    return registry
```

3. **Update Event Version**:
```python
# /src/domain/events/versions.py
EVENT_VERSIONS = {
    "DocumentUploaded": 2,  # ← Increment version
}
```

4. **Update Event Class**:
```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    content_type: str
    file_size: int  # ✅ Now required
    version: int = 2  # ← New version
```

5. **Add Tests**:
```python
def test_document_uploaded_v1_to_v2_upcaster():
    upcaster = DocumentUploadedV1ToV2Upcaster()
    
    v1_data = {
        "event_type": "DocumentUploaded",
        "version": 1,
        "document_id": "doc-123",
        "file_name": "test.pdf",
    }
    
    v2_data = upcaster.upcast(v1_data)
    assert v2_data["version"] == 2
    assert v2_data["file_size"] == 0
```

6. **Deploy** (zero downtime):
   - New code reads V1 events via upcaster
   - New events written as V2
   - Old code not affected (only writes V1)

#### 3. Rename Field

**When**: Field name is confusing or violates naming conventions.

**Steps**:

1. **Create Upcaster**:
```python
class DocumentUploadedV1ToV2Upcaster:
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentUploaded" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        data = {**event_data, "version": 2}
        # Rename: filename → file_name
        if 'filename' in data:
            data['file_name'] = data.pop('filename')
        return data
```

2. Follow steps 2-6 from "Add Required Field" above.

#### 4. Change Field Type

**When**: Field type is incorrect (e.g., string → int).

**Steps**:

1. **Create Upcaster with Conversion**:
```python
class DocumentUploadedV1ToV2Upcaster:
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentUploaded" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        data = {**event_data, "version": 2}
        # Convert: file_size from string to int
        if 'file_size' in data and isinstance(data['file_size'], str):
            data['file_size'] = int(data['file_size'])
        return data
```

2. Follow steps 2-6 from "Add Required Field" above.

---

### 🔴 Breaking Changes (Avoid!)

These changes should be avoided as they require complex migration:

#### 5. Remove Required Field

**Avoid**: Creates incompatibility with old code.

**If unavoidable**:
1. Mark field as deprecated in documentation
2. Make field optional first (deploy, wait)
3. Update all code to not use field
4. Remove field from event (tolerant reader ignores it)
5. Wait 6+ months before cleanup

#### 6. Split Event into Multiple Events

**Avoid**: Complex migration, breaks event history.

**If unavoidable**:
1. Create new event types
2. Support both old and new in aggregates
3. Gradually migrate aggregates
4. Deprecate old event type
5. Remove after all aggregates migrated

---

## Checklist for Event Evolution

Use this checklist for every event schema change:

### Planning Phase

- [ ] Identify the type of change (optional field, required field, etc.)
- [ ] Choose appropriate strategy (weak schema vs. upcaster)
- [ ] Design upcaster with sensible defaults
- [ ] Document change in VERSION_HISTORY

### Implementation Phase

- [ ] Create upcaster class (if needed)
- [ ] Register upcaster in registry
- [ ] Update EVENT_VERSIONS
- [ ] Update event class
- [ ] Update event class docstring with version notes

### Testing Phase

- [ ] Write upcaster unit tests
- [ ] Test with V1 event data
- [ ] Test with V2 event data
- [ ] Test aggregate reconstruction with mixed versions
- [ ] Test backward compatibility (new code, old events)

### Deployment Phase

- [ ] Deploy to staging
- [ ] Run integration tests
- [ ] Verify old events still work
- [ ] Deploy to production
- [ ] Monitor for errors
- [ ] Verify new events use new version

### Documentation Phase

- [ ] Update ADR if strategy changed
- [ ] Document breaking changes in CHANGELOG
- [ ] Update API documentation
- [ ] Add migration notes for team

---

## Testing Strategy

### Unit Tests

Test each upcaster in isolation:

```python
def test_upcaster():
    upcaster = MyEventV1ToV2Upcaster()
    
    # Test can_upcast
    assert upcaster.can_upcast("MyEvent", 1) is True
    assert upcaster.can_upcast("MyEvent", 2) is False
    assert upcaster.can_upcast("OtherEvent", 1) is False
    
    # Test upcast
    v1_data = {"event_type": "MyEvent", "version": 1, "field": "value"}
    v2_data = upcaster.upcast(v1_data)
    
    assert v2_data["version"] == 2
    assert v2_data["new_field"] == "default"
```

### Integration Tests

Test with real event store:

```python
@pytest.mark.integration
async def test_mixed_version_reconstruction():
    """Test aggregate reconstruction with V1 and V2 events."""
    event_store = create_event_store()
    
    # Store V1 event (old format)
    v1_event_json = {
        "event_type": "DocumentUploaded",
        "version": 1,
        "document_id": "doc-123",
        "file_name": "test.pdf",
    }
    await event_store.append_raw(aggregate_id, v1_event_json)
    
    # Store V2 event (new format)
    v2_event_json = {
        "event_type": "DocumentUploaded",
        "version": 2,
        "document_id": "doc-123",
        "file_name": "test2.pdf",
        "file_size": 1024,
    }
    await event_store.append_raw(aggregate_id, v2_event_json)
    
    # Reconstruct aggregate - should work!
    events = await event_store.get_events(aggregate_id)
    aggregate = Document.from_events(events)
    
    assert aggregate is not None
    assert len(aggregate.uncommitted_events) == 0
```

### Backward Compatibility Tests

Test new code with old events:

```python
def test_backward_compatibility():
    """Test new code can deserialize old events."""
    # Load production snapshot of V1 event
    old_event_json = load_production_event("doc-uploaded-v1.json")
    
    # Deserialize with current code
    event = event_store.deserialize_event(old_event_json)
    
    # Verify it works
    assert event is not None
    assert event.event_type == "DocumentUploaded"
    assert event.version == 2  # Upcasted to V2
```

---

## Common Pitfalls

### ❌ Don't: Modify Events in Database

```sql
-- ❌ NEVER DO THIS
UPDATE events 
SET payload = jsonb_set(payload, '{file_size}', '0')
WHERE event_type = 'DocumentUploaded';
```

**Why**: Violates immutability, loses audit trail, risks data corruption.

### ❌ Don't: Default to Required Fields

```python
# ❌ Don't
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    file_size: int  # Required, breaks old events!
```

**Instead**: Make it optional first, deploy, then make required with upcaster.

### ❌ Don't: Create Many Versions Quickly

```python
# ❌ Don't
DocumentUploadedV1
DocumentUploadedV2
DocumentUploadedV3  # Too many versions!
```

**Instead**: Batch related changes into single version increments.

### ❌ Don't: Skip Tests

```python
# ❌ Don't deploy without tests
def test_upcaster():
    pass  # TODO: Write test
```

**Instead**: Write comprehensive tests before deployment.

---

## Rollback Procedure

If an event evolution causes problems:

1. **Identify the Issue**:
   - Check logs for deserialization errors
   - Check monitoring for increased error rates
   - Identify affected event type and version

2. **Immediate Mitigation**:
   - Rollback code deployment
   - Old code continues working (writes V1, reads V1)
   - New V2 events may have been written (investigate impact)

3. **Fix**:
   - Fix upcaster logic
   - Add missing tests
   - Verify in staging

4. **Redeploy**:
   - Deploy fixed version
   - Monitor closely
   - Verify both V1 and V2 events work

---

## Examples

### Example 1: Adding Optional Metadata

**Change**: Add `tags` field to DocumentUploaded.

**Implementation**:
```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    tags: Optional[List[str]] = None  # ✅ Optional
```

**Deployment**: Zero downtime, no upcaster needed.

---

### Example 2: Adding Required User Tracking

**Change**: Add `uploaded_by_user_id` as required field.

**Implementation**:

1. Create upcaster with system user default:
```python
class DocumentUploadedV1ToV2Upcaster:
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            **event_data,
            "version": 2,
            "uploaded_by_user_id": "system",
        }
```

2. Update event:
```python
@dataclass(frozen=True)
class DocumentUploaded(DomainEvent):
    document_id: str
    file_name: str
    uploaded_by_user_id: str  # Required
    version: int = 2
```

**Deployment**: Zero downtime, upcaster handles V1 events.

---

## References

- [ADR 016: Event Versioning Strategy](../decisions/016-event-versioning-strategy.md)
- [Greg Young - Versioning in Event Sourced Systems](https://leanpub.com/esversioning)
- [Martin Fowler - Tolerant Reader](https://martinfowler.com/bliki/TolerantReader.html)
- [Event Store - Schema Evolution](https://developers.eventstore.com/server/v21.10/streams.html#event-versioning)

---

## Revision History

| Date | Changes | Author |
|------|---------|--------|
| 2025-12-13 | Initial version | Engineering Team |
