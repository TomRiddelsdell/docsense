"""Integration tests for event versioning and upcasting.

Tests the complete event versioning system including:
- Upcasting V1 events to V2
- Mixed version event streams
- Aggregate reconstruction with upcasters
- Backward compatibility
"""

import pytest
from uuid import uuid4
from datetime import datetime
from typing import Dict, Any

from src.infrastructure.persistence.event_upcaster import (
    UpcasterRegistry,
    DocumentUploadedV1ToV2Upcaster,
    DocumentConvertedV1ToV2Upcaster,
    AnalysisStartedV1ToV2Upcaster,
)
from src.domain.events.versions import EVENT_VERSIONS, get_current_version


class TestUpcasters:
    """Test individual upcasters."""
    
    def test_document_uploaded_v1_to_v2_upcaster(self):
        """Test DocumentUploaded V1 → V2 upcasting."""
        upcaster = DocumentUploadedV1ToV2Upcaster()
        
        # V1 event data
        v1_data = {
            "event_type": "DocumentUploaded",
            "version": 1,
            "event_id": str(uuid4()),
            "aggregate_id": str(uuid4()),
            "document_id": "doc-123",
            "file_name": "test.pdf",
            "content_type": "application/pdf",
            "occurred_at": datetime.utcnow().isoformat(),
        }
        
        # Test can_upcast
        assert upcaster.can_upcast("DocumentUploaded", 1) is True
        assert upcaster.can_upcast("DocumentUploaded", 2) is False
        assert upcaster.can_upcast("OtherEvent", 1) is False
        
        # Test upcast
        v2_data = upcaster.upcast(v1_data)
        
        assert v2_data["version"] == 2
        assert v2_data["file_size"] == 0  # Default value
        assert v2_data["uploaded_by_user_id"] == "system"  # Default value
        assert v2_data["document_id"] == "doc-123"  # Preserved
        assert v2_data["file_name"] == "test.pdf"  # Preserved
    
    def test_document_converted_v1_to_v2_upcaster(self):
        """Test DocumentConverted V1 → V2 upcasting."""
        upcaster = DocumentConvertedV1ToV2Upcaster()
        
        v1_data = {
            "event_type": "DocumentConverted",
            "version": 1,
            "document_id": "doc-123",
            "source_format": "pdf",
            "target_format": "markdown",
        }
        
        assert upcaster.can_upcast("DocumentConverted", 1) is True
        
        v2_data = upcaster.upcast(v1_data)
        
        assert v2_data["version"] == 2
        assert v2_data["conversion_duration_ms"] == 0  # Default
        assert v2_data["converter_version"] == "unknown"  # Default
        assert v2_data["source_format"] == "pdf"  # Preserved
    
    def test_analysis_started_v1_to_v2_upcaster(self):
        """Test AnalysisStarted V1 → V2 upcasting."""
        upcaster = AnalysisStartedV1ToV2Upcaster()
        
        v1_data = {
            "event_type": "AnalysisStarted",
            "version": 1,
            "analysis_id": "analysis-123",
            "document_id": "doc-123",
        }
        
        assert upcaster.can_upcast("AnalysisStarted", 1) is True
        
        v2_data = upcaster.upcast(v1_data)
        
        assert v2_data["version"] == 2
        assert v2_data["ai_provider"] == "claude"  # Default
        assert v2_data["estimated_duration_seconds"] == 300  # Default
        assert v2_data["analysis_id"] == "analysis-123"  # Preserved


class TestUpcasterRegistry:
    """Test the upcaster registry."""
    
    def test_registry_applies_single_upcaster(self):
        """Test registry applies a single upcaster."""
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        v1_data = {
            "event_type": "DocumentUploaded",
            "version": 1,
            "document_id": "doc-123",
            "file_name": "test.pdf",
            "content_type": "application/pdf",
        }
        
        v2_data = registry.upcast(v1_data)
        
        assert v2_data["version"] == 2
        assert "file_size" in v2_data
        assert "uploaded_by_user_id" in v2_data
    
    def test_registry_chains_upcasters(self):
        """Test registry chains multiple upcasters (V1 → V2 → V3)."""
        registry = UpcasterRegistry()
        
        # V1 → V2 upcaster
        class V1ToV2Upcaster:
            def can_upcast(self, event_type: str, version: int) -> bool:
                return event_type == "TestEvent" and version == 1
            
            def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
                return {**event_data, "version": 2, "field_v2": "added in v2"}
        
        # V2 → V3 upcaster
        class V2ToV3Upcaster:
            def can_upcast(self, event_type: str, version: int) -> bool:
                return event_type == "TestEvent" and version == 2
            
            def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
                return {**event_data, "version": 3, "field_v3": "added in v3"}
        
        registry.register(V1ToV2Upcaster())
        registry.register(V2ToV3Upcaster())
        
        v1_data = {
            "event_type": "TestEvent",
            "version": 1,
            "field_v1": "original",
        }
        
        v3_data = registry.upcast(v1_data)
        
        assert v3_data["version"] == 3
        assert v3_data["field_v1"] == "original"
        assert v3_data["field_v2"] == "added in v2"
        assert v3_data["field_v3"] == "added in v3"
    
    def test_registry_handles_no_upcasters(self):
        """Test registry returns data unchanged if no upcasters apply."""
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        # Already V2 data
        v2_data = {
            "event_type": "DocumentUploaded",
            "version": 2,
            "document_id": "doc-123",
        }
        
        result = registry.upcast(v2_data)
        
        assert result["version"] == 2
        assert result == v2_data
    
    def test_registry_handles_different_event_types(self):
        """Test registry only applies upcasters for matching event types."""
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        other_event = {
            "event_type": "OtherEvent",
            "version": 1,
            "data": "test",
        }
        
        result = registry.upcast(other_event)
        
        assert result["version"] == 1
        assert result == other_event
    
    def test_registry_prevents_infinite_loops(self):
        """Test registry prevents infinite upcasting loops."""
        registry = UpcasterRegistry()
        
        # Bad upcaster that doesn't increment version
        class BadUpcaster:
            def can_upcast(self, event_type: str, version: int) -> bool:
                return True  # Always applicable (bad!)
            
            def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
                return event_data  # Doesn't change version (bad!)
        
        registry.register(BadUpcaster())
        
        data = {"event_type": "TestEvent", "version": 1}
        
        # Should not infinite loop
        result = registry.upcast(data)
        
        assert result["version"] == 1


class TestEventVersionRegistry:
    """Test the event version registry."""
    
    def test_current_versions_defined(self):
        """Test all event types have defined versions."""
        assert EVENT_VERSIONS["DocumentUploaded"] == 2
        assert EVENT_VERSIONS["DocumentConverted"] == 2
        assert EVENT_VERSIONS["AnalysisStarted"] == 2
        assert EVENT_VERSIONS["DocumentDeleted"] == 1
    
    def test_get_current_version(self):
        """Test getting current version for event types."""
        assert get_current_version("DocumentUploaded") == 2
        assert get_current_version("DocumentDeleted") == 1
        assert get_current_version("UnknownEvent") == 1  # Default


@pytest.mark.integration
class TestBackwardCompatibility:
    """Test backward compatibility - new code reads old events."""
    
    def test_v1_events_readable_by_v2_code(self):
        """Test V1 events can be read by current code."""
        # Simulate V1 event from production
        v1_event_data = {
            "event_type": "DocumentUploaded",
            "version": 1,
            "event_id": str(uuid4()),
            "aggregate_id": str(uuid4()),
            "document_id": "doc-production-123",
            "file_name": "production_document.pdf",
            "content_type": "application/pdf",
            "occurred_at": datetime.utcnow().isoformat(),
        }
        
        # Apply upcasting (simulates event store deserialization)
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        v2_event_data = registry.upcast(v1_event_data)
        
        # Verify V1 event was successfully upcasted
        assert v2_event_data["version"] == 2
        assert v2_event_data["document_id"] == "doc-production-123"
        assert v2_event_data["file_size"] == 0
        assert v2_event_data["uploaded_by_user_id"] == "system"
    
    def test_mixed_version_event_stream(self):
        """Test event stream with mixed V1 and V2 events."""
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        # Simulate event stream with V1 and V2 events
        event_stream = [
            {
                "event_type": "DocumentUploaded",
                "version": 1,
                "document_id": "doc-old",
                "file_name": "old.pdf",
                "content_type": "application/pdf",
            },
            {
                "event_type": "DocumentUploaded",
                "version": 2,
                "document_id": "doc-new",
                "file_name": "new.pdf",
                "content_type": "application/pdf",
                "file_size": 2048,
                "uploaded_by_user_id": "user-123",
            },
        ]
        
        # Apply upcasting to all events
        upcasted_events = [registry.upcast(event) for event in event_stream]
        
        # Verify all events are now V2
        assert all(event["version"] == 2 for event in upcasted_events)
        
        # Verify V1 event got defaults
        assert upcasted_events[0]["file_size"] == 0
        assert upcasted_events[0]["uploaded_by_user_id"] == "system"
        
        # Verify V2 event unchanged
        assert upcasted_events[1]["file_size"] == 2048
        assert upcasted_events[1]["uploaded_by_user_id"] == "user-123"


@pytest.mark.integration
class TestTolerantReader:
    """Test tolerant reader pattern - handle missing optional fields."""
    
    def test_missing_optional_fields_handled(self):
        """Test events work with missing optional fields."""
        # Event missing optional fields (acceptable)
        minimal_event = {
            "event_type": "DocumentUploaded",
            "version": 2,
            "document_id": "doc-123",
            "file_name": "test.pdf",
            "content_type": "application/pdf",
            # file_size omitted (optional in some contexts)
        }
        
        registry = UpcasterRegistry()
        result = registry.upcast(minimal_event)
        
        # Should not fail - tolerant reader
        assert result["version"] == 2
        assert result["document_id"] == "doc-123"
    
    def test_extra_fields_preserved(self):
        """Test upcasting preserves extra/unknown fields."""
        event_with_extras = {
            "event_type": "DocumentUploaded",
            "version": 1,
            "document_id": "doc-123",
            "file_name": "test.pdf",
            "content_type": "application/pdf",
            "unknown_field": "should be preserved",
            "metadata": {"key": "value"},
        }
        
        registry = UpcasterRegistry()
        registry.register(DocumentUploadedV1ToV2Upcaster())
        
        result = registry.upcast(event_with_extras)
        
        # Unknown fields preserved
        assert result["unknown_field"] == "should be preserved"
        assert result["metadata"] == {"key": "value"}


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
