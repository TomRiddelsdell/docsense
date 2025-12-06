from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from uuid import UUID

import asyncpg


@dataclass
class DocumentView:
    id: UUID
    title: str
    description: Optional[str]
    status: str
    version: int
    original_format: Optional[str]
    original_filename: Optional[str]
    policy_repository_id: Optional[UUID]
    compliance_status: Optional[str]
    created_at: datetime
    updated_at: datetime


@dataclass
class DocumentDetailView:
    id: UUID
    title: str
    description: Optional[str]
    status: str
    version: int
    original_format: Optional[str]
    markdown_content: Optional[str]
    sections: Optional[list]
    metadata: Optional[dict]
    policy_repository_id: Optional[UUID]
    compliance_status: Optional[str]
    created_at: datetime
    updated_at: datetime


class DocumentQueries:
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    async def get_by_id(self, document_id: UUID) -> Optional[DocumentDetailView]:
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT d.id, d.title, d.description, d.status, d.version,
                       d.original_format, d.policy_repository_id, d.compliance_status,
                       d.created_at, d.updated_at,
                       c.markdown_content, c.sections, c.metadata
                FROM document_views d
                LEFT JOIN document_contents c ON d.id = c.document_id
                WHERE d.id = $1
                ORDER BY c.version DESC
                LIMIT 1
                """,
                document_id
            )

        if row is None:
            return None

        import json
        sections = json.loads(row["sections"]) if row["sections"] else None
        metadata = json.loads(row["metadata"]) if row["metadata"] else None

        return DocumentDetailView(
            id=row["id"],
            title=row["title"],
            description=row["description"],
            status=row["status"],
            version=row["version"],
            original_format=row["original_format"],
            markdown_content=row["markdown_content"],
            sections=sections,
            metadata=metadata,
            policy_repository_id=row["policy_repository_id"],
            compliance_status=row["compliance_status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"]
        )

    async def list_all(
        self,
        status: Optional[str] = None,
        policy_repository_id: Optional[UUID] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[DocumentView]:
        query = """
            SELECT id, title, description, status, version, original_format,
                   original_filename, policy_repository_id, compliance_status,
                   created_at, updated_at
            FROM document_views
            WHERE 1=1
        """
        params = []
        param_count = 0

        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)

        if policy_repository_id:
            param_count += 1
            query += f" AND policy_repository_id = ${param_count}"
            params.append(policy_repository_id)

        query += f" ORDER BY created_at DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([limit, offset])

        async with self._pool.acquire() as conn:
            rows = await conn.fetch(query, *params)

        return [
            DocumentView(
                id=row["id"],
                title=row["title"],
                description=row["description"],
                status=row["status"],
                version=row["version"],
                original_format=row["original_format"],
                original_filename=row["original_filename"],
                policy_repository_id=row["policy_repository_id"],
                compliance_status=row["compliance_status"],
                created_at=row["created_at"],
                updated_at=row["updated_at"]
            )
            for row in rows
        ]

    async def count(
        self,
        status: Optional[str] = None,
        policy_repository_id: Optional[UUID] = None
    ) -> int:
        query = "SELECT COUNT(*) FROM document_views WHERE 1=1"
        params = []
        param_count = 0

        if status:
            param_count += 1
            query += f" AND status = ${param_count}"
            params.append(status)

        if policy_repository_id:
            param_count += 1
            query += f" AND policy_repository_id = ${param_count}"
            params.append(policy_repository_id)

        async with self._pool.acquire() as conn:
            return await conn.fetchval(query, *params)
