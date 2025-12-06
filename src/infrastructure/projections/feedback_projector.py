from typing import List, Type

import asyncpg

from src.domain.events import (
    DomainEvent,
    FeedbackGenerated,
    ChangeAccepted,
    ChangeRejected,
    ChangeModified,
)
from src.infrastructure.projections.base import Projection


class FeedbackProjection(Projection):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def handles(self) -> List[Type[DomainEvent]]:
        return [
            FeedbackGenerated,
            ChangeAccepted,
            ChangeRejected,
            ChangeModified,
        ]

    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, FeedbackGenerated):
            await self._handle_generated(event)
        elif isinstance(event, ChangeAccepted):
            await self._handle_accepted(event)
        elif isinstance(event, ChangeRejected):
            await self._handle_rejected(event)
        elif isinstance(event, ChangeModified):
            await self._handle_modified(event)

    async def _handle_generated(self, event: FeedbackGenerated) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO feedback_views
                (id, document_id, section_id, status, category, severity,
                 original_text, suggestion, explanation, confidence_score,
                 policy_reference, created_at)
                VALUES ($1, $2, $3, 'pending', $4, $5, $6, $7, $8, $9, $10, $11)
                ON CONFLICT (id) DO NOTHING
                """,
                event.feedback_id,
                event.aggregate_id,
                event.section_reference,
                'improvement',
                'info',
                '',
                event.suggested_change,
                event.issue_description,
                event.confidence_score,
                event.policy_reference,
                event.occurred_at
            )

    async def _handle_accepted(self, event: ChangeAccepted) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE feedback_views
                SET status = 'accepted', processed_at = $2
                WHERE id = $1
                """,
                event.feedback_id,
                event.occurred_at
            )

    async def _handle_rejected(self, event: ChangeRejected) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE feedback_views
                SET status = 'rejected', 
                    rejection_reason = $2,
                    processed_at = $3
                WHERE id = $1
                """,
                event.feedback_id,
                event.rejection_reason,
                event.occurred_at
            )

    async def _handle_modified(self, event: ChangeModified) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE feedback_views
                SET status = 'modified',
                    suggestion = $2,
                    processed_at = $3
                WHERE id = $1
                """,
                event.feedback_id,
                event.modified_change,
                event.occurred_at
            )
