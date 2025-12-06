from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg


@dataclass
class FeedbackView:
    id: UUID
    document_id: UUID
    section_id: Optional[str]
    status: str
    category: Optional[str]
    severity: Optional[str]
    original_text: Optional[str]
    suggestion: str
    explanation: Optional[str]
    confidence_score: Optional[float]
    policy_reference: Optional[str]
    rejection_reason: Optional[str]
    processed_at: Optional[datetime]
    created_at: datetime


class FeedbackQueries:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_by_id(self, feedback_id: UUID) -> Optional[FeedbackView]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT id, document_id, section_id, status, category, severity,
                       original_text, suggestion, explanation, confidence_score,
                       policy_reference, rejection_reason, processed_at, created_at
                FROM feedback_views
                WHERE id = $1
                """,
                feedback_id
            )

        if row is None:
            return None

        return self._row_to_view(row)

    async def get_by_document(
        self,
        document_id: UUID,
        status: Optional[str] = None
    ) -> List[FeedbackView]:
        query = """
            SELECT id, document_id, section_id, status, category, severity,
                   original_text, suggestion, explanation, confidence_score,
                   policy_reference, rejection_reason, processed_at, created_at
            FROM feedback_views
            WHERE document_id = $1
        """
        params = [document_id]

        if status:
            query += " AND status = $2"
            params.append(status)

        query += " ORDER BY created_at ASC"

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [self._row_to_view(row) for row in rows]

    async def get_pending_by_document(self, document_id: UUID) -> List[FeedbackView]:
        return await self.get_by_document(document_id, status="pending")

    async def count_by_document(
        self,
        document_id: UUID,
        status: Optional[str] = None
    ) -> int:
        query = "SELECT COUNT(*) FROM feedback_views WHERE document_id = $1"
        params = [document_id]

        if status:
            query += " AND status = $2"
            params.append(status)

        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *params)

    async def count_pending(self, document_id: UUID) -> int:
        return await self.count_by_document(document_id, status="pending")

    def _row_to_view(self, row: asyncpg.Record) -> FeedbackView:
        return FeedbackView(
            id=row["id"],
            document_id=row["document_id"],
            section_id=row["section_id"],
            status=row["status"],
            category=row["category"],
            severity=row["severity"],
            original_text=row["original_text"],
            suggestion=row["suggestion"],
            explanation=row["explanation"],
            confidence_score=float(row["confidence_score"]) if row["confidence_score"] else None,
            policy_reference=row["policy_reference"],
            rejection_reason=row["rejection_reason"],
            processed_at=row["processed_at"],
            created_at=row["created_at"]
        )
