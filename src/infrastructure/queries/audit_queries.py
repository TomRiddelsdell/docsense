from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any
from uuid import UUID

import asyncpg
import json


@dataclass
class AuditLogView:
    id: UUID
    event_type: str
    aggregate_id: Optional[UUID]
    aggregate_type: Optional[str]
    document_id: Optional[UUID]
    user_id: Optional[str]
    details: Dict[str, Any]
    timestamp: datetime


class AuditQueries:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_by_id(self, audit_id: UUID) -> Optional[AuditLogView]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, event_type, aggregate_id, aggregate_type, document_id,
                       user_id, details, timestamp
                FROM audit_log_views
                WHERE id = $1
                """,
                audit_id
            )

        if row is None:
            return None

        return self._row_to_view(row)

    async def get_by_document(
        self,
        document_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogView]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, event_type, aggregate_id, aggregate_type, document_id,
                       user_id, details, timestamp
                FROM audit_log_views
                WHERE document_id = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
                """,
                document_id,
                limit,
                offset
            )

        return [self._row_to_view(row) for row in rows]

    async def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[AuditLogView]:
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, event_type, aggregate_id, aggregate_type, document_id,
                       user_id, details, timestamp
                FROM audit_log_views
                WHERE user_id = $1
                ORDER BY timestamp DESC
                LIMIT $2 OFFSET $3
                """,
                user_id,
                limit,
                offset
            )

        return [self._row_to_view(row) for row in rows]

    async def get_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        event_type: Optional[str] = None
    ) -> List[AuditLogView]:
        query = """
            SELECT id, event_type, aggregate_id, aggregate_type, document_id,
                   user_id, details, timestamp
            FROM audit_log_views
            WHERE 1=1
        """
        params = []
        param_count = 0

        if event_type:
            param_count += 1
            query += f" AND event_type = ${param_count}"
            params.append(event_type)

        query += f" ORDER BY timestamp DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_view(row) for row in rows]

    async def count_by_document(self, document_id: UUID) -> int:
        async with self._pool.acquire() as conn:
            return await conn.fetchval(
                "SELECT COUNT(*) FROM audit_log_views WHERE document_id = $1",
                document_id
            )

    def _row_to_view(self, row: asyncpg.Record) -> AuditLogView:
        details = row["details"]
        if isinstance(details, str):
            details = json.loads(details)

        return AuditLogView(
            id=row["id"],
            event_type=row["event_type"],
            aggregate_id=row["aggregate_id"],
            aggregate_type=row["aggregate_type"],
            document_id=row["document_id"],
            user_id=row["user_id"],
            details=details,
            timestamp=row["timestamp"]
        )
