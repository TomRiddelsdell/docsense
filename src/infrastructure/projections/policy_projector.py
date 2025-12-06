from typing import List, Type

import asyncpg

from src.domain.events import (
    DomainEvent,
    PolicyRepositoryCreated,
    PolicyAdded,
    DocumentAssignedToPolicy,
)
from src.infrastructure.projections.base import Projection


class PolicyProjection(Projection):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def handles(self) -> List[Type[DomainEvent]]:
        return [
            PolicyRepositoryCreated,
            PolicyAdded,
            DocumentAssignedToPolicy,
        ]

    async def handle(self, event: DomainEvent) -> None:
        if isinstance(event, PolicyRepositoryCreated):
            await self._handle_created(event)
        elif isinstance(event, PolicyAdded):
            await self._handle_policy_added(event)
        elif isinstance(event, DocumentAssignedToPolicy):
            await self._handle_document_assigned(event)

    async def _handle_created(self, event: PolicyRepositoryCreated) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO policy_repository_views
                (id, name, description, created_at)
                VALUES ($1, $2, $3, $4)
                ON CONFLICT (id) DO UPDATE SET
                    name = $2,
                    description = $3,
                    updated_at = NOW()
                """,
                event.aggregate_id,
                event.name,
                event.description,
                event.occurred_at
            )

    async def _handle_policy_added(self, event: PolicyAdded) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO policy_views
                (id, repository_id, name, description, requirement_type, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    name = $3,
                    description = $4,
                    requirement_type = $5,
                    updated_at = NOW()
                """,
                event.policy_id,
                event.aggregate_id,
                event.policy_name,
                event.policy_content,
                event.requirement_type,
                event.occurred_at
            )
            await conn.execute(
                """
                UPDATE policy_repository_views
                SET policy_count = policy_count + 1, updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )

    async def _handle_document_assigned(self, event: DocumentAssignedToPolicy) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE policy_repository_views
                SET document_count = document_count + 1, updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )
            await conn.execute(
                """
                UPDATE document_views
                SET policy_repository_id = $1, updated_at = NOW()
                WHERE id = $2
                """,
                event.aggregate_id,
                event.document_id
            )
