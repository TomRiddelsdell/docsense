from dataclasses import dataclass
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

import asyncpg


@dataclass
class PolicyRepositoryView:
    id: UUID
    name: str
    description: Optional[str]
    policy_count: int
    document_count: int
    created_at: datetime
    updated_at: datetime


@dataclass
class PolicyView:
    id: UUID
    repository_id: UUID
    name: str
    description: Optional[str]
    requirement_type: str
    created_at: datetime
    updated_at: datetime


class PolicyQueries:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_repository_by_id(self, repository_id: UUID) -> Optional[PolicyRepositoryView]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, name, description, policy_count, document_count,
                       created_at, updated_at
                FROM policy_repository_views
                WHERE id = $1
                """,
                repository_id
            )

        if row is None:
            return None

        return PolicyRepositoryView(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            policy_count=row["policy_count"],
            document_count=row["document_count"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def list_repositories(
        self,
        limit: int = 50,
        offset: int = 0
    ) -> List[PolicyRepositoryView]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, name, description, policy_count, document_count,
                       created_at, updated_at
                FROM policy_repository_views
                ORDER BY created_at DESC
                LIMIT $1 OFFSET $2
                """,
                limit,
                offset
            )

        return [
            PolicyRepositoryView(
                id=row["id"],
                name=row["name"],
                description=row["description"],
                policy_count=row["policy_count"],
                document_count=row["document_count"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

    async def get_policies_by_repository(
        self,
        repository_id: UUID,
        requirement_type: Optional[str] = None
    ) -> List[PolicyView]:
        query = """
            SELECT id, repository_id, name, description, requirement_type,
                   created_at, updated_at
            FROM policy_views
            WHERE repository_id = $1
        """
        params: List[Any] = [repository_id]

        if requirement_type:
            query += " AND requirement_type = $2"
            params.append(requirement_type)

        query += " ORDER BY created_at ASC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            PolicyView(
                id=row["id"],
                repository_id=row["repository_id"],
                name=row["name"],
                description=row["description"],
                requirement_type=row["requirement_type"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

    async def count_repositories(self) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval("SELECT COUNT(*) FROM policy_repository_views")
