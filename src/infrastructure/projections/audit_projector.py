from typing import List, Type
import json

import asyncpg

from src.domain.events import DomainEvent
from src.infrastructure.projections.base import Projection


class AuditProjection(Projection):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def handles(self) -> List[Type[DomainEvent]]:
        return []

    def can_handle(self, event: DomainEvent) -> bool:
        return True

    async def handle(self, event: DomainEvent) -> None:
        details = {
            "event_type": event.event_type,
            "aggregate_type": event.aggregate_type,
        }

        if hasattr(event, 'uploaded_by'):
            user_id = event.uploaded_by
        elif hasattr(event, 'initiated_by'):
            user_id = event.initiated_by
        elif hasattr(event, 'exported_by'):
            user_id = event.exported_by
        elif hasattr(event, 'accepted_by'):
            user_id = event.accepted_by
        elif hasattr(event, 'rejected_by'):
            user_id = event.rejected_by
        elif hasattr(event, 'modified_by'):
            user_id = event.modified_by
        elif hasattr(event, 'created_by'):
            user_id = event.created_by
        elif hasattr(event, 'assigned_by'):
            user_id = event.assigned_by
        else:
            user_id = None

        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_log_views
                (id, event_type, aggregate_id, aggregate_type, document_id, user_id, details, timestamp)
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
                """,
                event.event_id,
                event.event_type,
                event.aggregate_id,
                event.aggregate_type,
                event.aggregate_id if event.aggregate_type == "Document" else None,
                user_id,
                json.dumps(details),
                event.occurred_at
            )
