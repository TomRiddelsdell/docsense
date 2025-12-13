"""Event upcasting system for schema evolution.

This module provides the infrastructure for evolving event schemas over time
without requiring data migration. Upcasters transform old event versions to
current versions at read time.

Key Principles:
- Events in storage remain immutable
- Upcasting happens at deserialization time
- Multiple upcasters can chain (V1 → V2 → V3)
- Upcasters are pure functions (no side effects)
"""

from typing import Dict, Any, List, Protocol, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)


class EventUpcaster(Protocol):
    """Protocol for event upcasters.
    
    Upcasters transform old event versions to newer versions,
    allowing schema evolution without data migration.
    """
    
    def can_upcast(self, event_type: str, version: int) -> bool:
        """Check if this upcaster can handle the given event type and version.
        
        Args:
            event_type: The event type (e.g., "DocumentUploaded")
            version: The current version of the event
            
        Returns:
            True if this upcaster can transform this event
        """
        ...
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform the event data to the next version.
        
        Args:
            event_data: The event data at the current version
            
        Returns:
            The event data at the next version
            
        Raises:
            ValueError: If the event cannot be upcasted
        """
        ...


class UpcasterRegistry:
    """Registry for event upcasters.
    
    Manages upcasters and applies them in sequence to transform
    events from old versions to current versions.
    """
    
    def __init__(self):
        self._upcasters: List[EventUpcaster] = []
    
    def register(self, upcaster: EventUpcaster) -> None:
        """Register an upcaster.
        
        Args:
            upcaster: The upcaster to register
        """
        self._upcasters.append(upcaster)
        logger.info(f"Registered upcaster: {upcaster.__class__.__name__}")
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Apply all applicable upcasters to the event data.
        
        Upcasters are applied in sequence until no more upcasters
        can be applied. This allows chaining (V1 → V2 → V3).
        
        Args:
            event_data: The event data (must include 'event_type' and 'version')
            
        Returns:
            The upcasted event data at the current version
            
        Raises:
            ValueError: If event_data is missing required fields
        """
        if 'event_type' not in event_data:
            raise ValueError("event_data must include 'event_type'")
        
        event_type = event_data['event_type']
        version = event_data.get('version', 1)
        original_version = version
        
        # Apply upcasters in sequence
        max_iterations = 10  # Prevent infinite loops
        iterations = 0
        
        while iterations < max_iterations:
            applied = False
            
            for upcaster in self._upcasters:
                if upcaster.can_upcast(event_type, version):
                    logger.debug(
                        f"Upcasting {event_type} from V{version} using "
                        f"{upcaster.__class__.__name__}"
                    )
                    event_data = upcaster.upcast(event_data)
                    version = event_data.get('version', version + 1)
                    applied = True
                    break  # Try from beginning with new version
            
            if not applied:
                break  # No more upcasters applicable
            
            iterations += 1
        
        if iterations >= max_iterations:
            logger.warning(
                f"Reached max upcasting iterations for {event_type}. "
                f"Possible infinite loop?"
            )
        
        if version != original_version:
            logger.info(
                f"Upcasted {event_type} from V{original_version} to V{version}"
            )
        
        return event_data


# Example upcasters for DocumentUploaded event

class DocumentUploadedV1ToV2Upcaster:
    """Upcast DocumentUploaded from V1 to V2.
    
    V2 adds:
    - file_size: int - Size of uploaded file in bytes
    - uploaded_by_user_id: str - User who uploaded the document
    """
    
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentUploaded" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add new required fields with sensible defaults."""
        return {
            **event_data,
            "version": 2,
            "file_size": 0,  # Default for historical events (unknown)
            "uploaded_by_user_id": "system",  # System user for historical events
        }


class DocumentConvertedV1ToV2Upcaster:
    """Upcast DocumentConverted from V1 to V2.
    
    V2 adds:
    - conversion_duration_ms: int - Time taken for conversion
    - converter_version: str - Version of converter used
    """
    
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "DocumentConverted" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add conversion metadata with defaults."""
        return {
            **event_data,
            "version": 2,
            "conversion_duration_ms": 0,  # Unknown for historical events
            "converter_version": "unknown",  # Unknown for historical events
        }


class AnalysisStartedV1ToV2Upcaster:
    """Upcast AnalysisStarted from V1 to V2.
    
    V2 adds:
    - ai_provider: str - Which AI provider is being used
    - estimated_duration_seconds: int - Estimated time for analysis
    """
    
    def can_upcast(self, event_type: str, version: int) -> bool:
        return event_type == "AnalysisStarted" and version == 1
    
    def upcast(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """Add AI provider metadata with defaults."""
        return {
            **event_data,
            "version": 2,
            "ai_provider": "claude",  # Default to Claude
            "estimated_duration_seconds": 300,  # Default 5 minutes
        }


# Factory function to create a registry with all upcasters

def create_upcaster_registry() -> UpcasterRegistry:
    """Create and populate the upcaster registry.
    
    Returns:
        A registry with all registered upcasters
    """
    registry = UpcasterRegistry()
    
    # Register all upcasters
    registry.register(DocumentUploadedV1ToV2Upcaster())
    registry.register(DocumentConvertedV1ToV2Upcaster())
    registry.register(AnalysisStartedV1ToV2Upcaster())
    
    return registry
