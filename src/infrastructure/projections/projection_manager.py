from typing import List, Optional
from uuid import UUID

import asyncpg

from src.domain.events import DomainEvent
from src.infrastructure.projections.base import Projection
from src.infrastructure.persistence.event_store import EventStore


class ProjectionManager:
    def __init__(
        self,
        pool: asyncpg.Pool,
        event_store: EventStore,
        projections: List[Projection]
    ):
        self._pool = pool
        self._event_store = event_store
        self._projections = projections

    async def project(self, event: DomainEvent) -> None:
        for projection in self._projections:
            if projection.can_handle(event):
                await projection.handle(event)

    async def project_all(self, events: List[DomainEvent]) -> None:
        for event in events:
            await self.project(event)

    async def rebuild_all(self, batch_size: int = 100) -> int:
        await self._reset_checkpoints()
        
        position = 0
        total_processed = 0

        while True:
            events = await self._event_store.get_all_events(position, batch_size)
            if not events:
                break

            await self.project_all(events)
            total_processed += len(events)
            position += len(events)

            await self._update_checkpoint("all", None)

        return total_processed

    async def get_checkpoint(self, projection_name: str) -> Optional[UUID]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT last_event_id FROM projection_checkpoints
                WHERE projection_name = $1
                """,
                projection_name
            )
            return row["last_event_id"] if row else None

    async def _update_checkpoint(self, projection_name: str, last_event_id: Optional[UUID]) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO projection_checkpoints (projection_name, last_event_id, last_processed_at)
                VALUES ($1, $2, NOW())
                ON CONFLICT (projection_name) DO UPDATE SET
                    last_event_id = $2,
                    last_processed_at = NOW()
                """,
                projection_name,
                last_event_id
            )

    async def _reset_checkpoints(self) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute("DELETE FROM projection_checkpoints")
