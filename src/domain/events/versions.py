"""Event version registry.

This module maintains the current version of each event type.
Use this to track schema evolution over time.

When incrementing an event version:
1. Update the version number here
2. Create an upcaster in event_upcaster.py
3. Add tests for the upcaster
4. Document the change in the event class
"""

# Event version registry
# Format: "EventTypeName": current_version
EVENT_VERSIONS = {
    # Document Events
    "DocumentUploaded": 2,  # V2: Added file_size, uploaded_by_user_id
    "DocumentConverted": 2,  # V2: Added conversion_duration_ms, converter_version
    "DocumentDeleted": 1,
    "DocumentMetadataUpdated": 1,
    
    # Analysis Events
    "AnalysisStarted": 2,  # V2: Added ai_provider, estimated_duration_seconds
    "AnalysisCompleted": 1,
    "AnalysisFailed": 1,
    "AnalysisIssueDetected": 1,
    "AnalysisProgressUpdated": 1,
    
    # Feedback Events
    "FeedbackProvided": 1,
    "FeedbackStatusUpdated": 1,
    "FeedbackCommentAdded": 1,
    
    # Policy Events
    "PolicyRepositoryCreated": 1,
    "PolicyAdded": 1,
    "PolicyUpdated": 1,
    "PolicyRemoved": 1,
    "PolicyRepositoryActivated": 1,
    "PolicyRepositoryDeactivated": 1,
}


def get_current_version(event_type: str) -> int:
    """Get the current version of an event type.
    
    Args:
        event_type: The event type name
        
    Returns:
        The current version number (defaults to 1 if not found)
    """
    return EVENT_VERSIONS.get(event_type, 1)


def get_all_versions() -> dict:
    """Get all event versions.
    
    Returns:
        Dictionary of event type to current version
    """
    return EVENT_VERSIONS.copy()


# Version history documentation
# Use this to track major changes over time

VERSION_HISTORY = {
    "DocumentUploaded": {
        1: "Initial version",
        2: "Added file_size and uploaded_by_user_id fields (2025-12-13)",
    },
    "DocumentConverted": {
        1: "Initial version",
        2: "Added conversion_duration_ms and converter_version fields (2025-12-13)",
    },
    "AnalysisStarted": {
        1: "Initial version",
        2: "Added ai_provider and estimated_duration_seconds fields (2025-12-13)",
    },
}


def get_version_history(event_type: str) -> dict:
    """Get the version history for an event type.
    
    Args:
        event_type: The event type name
        
    Returns:
        Dictionary of version to description
    """
    return VERSION_HISTORY.get(event_type, {1: "Initial version"})
