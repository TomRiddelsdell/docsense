import json
from dataclasses import asdict, fields
from datetime import datetime
from enum import Enum
from typing import Dict, Type, Any
from uuid import UUID

from src.domain.events import (
    DomainEvent,
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
    AnalysisStarted,
    AnalysisCompleted,
    AnalysisFailed,
    AnalysisReset,
    FeedbackSessionCreated,
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
    ChangeModified,
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)
from src.domain.events.user_events import (
    UserRegistered,
    UserGroupAdded,
    UserGroupRemoved,
    UserRoleGranted,
    UserRoleRevoked,
    UserDeactivated,
    UserReactivated,
)


class EventSerializer:
    _event_types: Dict[str, Type[DomainEvent]] = {
        "DocumentUploaded": DocumentUploaded,
        "DocumentConverted": DocumentConverted,
        "DocumentExported": DocumentExported,
        "AnalysisStarted": AnalysisStarted,
        "AnalysisCompleted": AnalysisCompleted,
        "AnalysisFailed": AnalysisFailed,
        "AnalysisReset": AnalysisReset,
        "FeedbackSessionCreated": FeedbackSessionCreated,
        "FeedbackGenerated": FeedbackGenerated,
        "ChangeAccepted": ChangeAccepted,
        "ChangeRejected": ChangeRejected,
        "ChangeModified": ChangeModified,
        "PolicyRepositoryCreated": PolicyRepositoryCreated,
        "PolicyAdded": PolicyAdded,
        "DocumentAssignedToPolicy": DocumentAssignedToPolicy,
        "UserRegistered": UserRegistered,
        "UserGroupAdded": UserGroupAdded,
        "UserGroupRemoved": UserGroupRemoved,
        "UserRoleGranted": UserRoleGranted,
        "UserRoleRevoked": UserRoleRevoked,
        "UserDeactivated": UserDeactivated,
        "UserReactivated": UserReactivated,
    }

    @classmethod
    def register_event_type(cls, event_type: Type[DomainEvent]) -> None:
        cls._event_types[event_type.__name__] = event_type

    def serialize(self, event: DomainEvent) -> Dict[str, Any]:
        data = {}
        for field in fields(event):
            value = getattr(event, field.name)
            if isinstance(value, UUID):
                data[field.name] = str(value)
            elif isinstance(value, datetime):
                data[field.name] = value.isoformat()
            elif isinstance(value, Enum):
                data[field.name] = value.value
            elif isinstance(value, list):
                data[field.name] = self._serialize_list(value)
            elif isinstance(value, dict):
                data[field.name] = self._serialize_dict(value)
            else:
                data[field.name] = value
        return data

    def _serialize_list(self, items: list) -> list:
        result = []
        for item in items:
            if isinstance(item, UUID):
                result.append(str(item))
            elif isinstance(item, datetime):
                result.append(item.isoformat())
            elif isinstance(item, Enum):
                result.append(item.value)
            elif isinstance(item, dict):
                result.append(self._serialize_dict(item))
            else:
                result.append(item)
        return result

    def _serialize_dict(self, d: dict) -> dict:
        result = {}
        for k, v in d.items():
            if isinstance(v, UUID):
                result[k] = str(v)
            elif isinstance(v, datetime):
                result[k] = v.isoformat()
            elif isinstance(v, Enum):
                result[k] = v.value
            elif isinstance(v, list):
                result[k] = self._serialize_list(v)
            elif isinstance(v, dict):
                result[k] = self._serialize_dict(v)
            else:
                result[k] = v
        return result

    def deserialize(self, event_type: str, data: Dict[str, Any]) -> DomainEvent:
        event_class = self._event_types.get(event_type)
        if event_class is None:
            raise ValueError(f"Unknown event type: {event_type}")

        converted_data = {}
        for field in fields(event_class):
            if field.name not in data:
                continue
            value = data[field.name]
            if field.type == UUID or field.type == "UUID":
                converted_data[field.name] = UUID(value) if value else None
            elif field.type == datetime or field.type == "datetime":
                converted_data[field.name] = datetime.fromisoformat(value) if value else None
            else:
                converted_data[field.name] = value

        return event_class(**converted_data)

    def to_json(self, event: DomainEvent) -> str:
        return json.dumps(self.serialize(event))

    def from_json(self, event_type: str, json_str: str) -> DomainEvent:
        data = json.loads(json_str)
        return self.deserialize(event_type, data)
