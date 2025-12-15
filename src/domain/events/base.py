from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4


@dataclass(frozen=True)
class DomainEvent:
    aggregate_id: UUID
    event_id: UUID = field(default_factory=uuid4)
    occurred_at: datetime = field(default_factory=datetime.utcnow)
    aggregate_type: str = field(default="")
    version: int = field(default=1)
    sequence: Optional[int] = field(default=None)  # Populated by EventStore from database

    @property
    def event_type(self) -> str:
        return self.__class__.__name__
