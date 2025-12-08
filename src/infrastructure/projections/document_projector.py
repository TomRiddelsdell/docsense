import logging
from typing import List, Type, Any
import json
from enum import Enum

import asyncpg

logger = logging.getLogger(__name__)

from src.domain.events import (
    DomainEvent,
    DocumentUploaded,
    DocumentConverted,
    DocumentExported,
    AnalysisStarted,
    AnalysisCompleted,
    AnalysisFailed,
    AnalysisReset,
)
from src.infrastructure.projections.base import Projection


def serialize_for_json(obj: Any) -> Any:
    """Convert objects to JSON-serializable format, handling enums."""
    if isinstance(obj, Enum):
        return obj.value
    elif isinstance(obj, dict):
        return {k: serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_for_json(item) for item in obj]
    return obj


class DocumentProjection(Projection):
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool

    def handles(self) -> List[Type[DomainEvent]]:
        return [
            DocumentUploaded,
            DocumentConverted,
            DocumentExported,
            AnalysisStarted,
            AnalysisCompleted,
            AnalysisFailed,
            AnalysisReset,
        ]

    async def handle(self, event: DomainEvent) -> None:
        logger.info(f"DocumentProjection handling event: {event.event_type}, aggregate_id: {event.aggregate_id}")
        try:
            if isinstance(event, DocumentUploaded):
                await self._handle_uploaded(event)
            elif isinstance(event, DocumentConverted):
                await self._handle_converted(event)
            elif isinstance(event, AnalysisStarted):
                await self._handle_analysis_started(event)
            elif isinstance(event, AnalysisCompleted):
                await self._handle_analysis_completed(event)
            elif isinstance(event, AnalysisFailed):
                await self._handle_analysis_failed(event)
            elif isinstance(event, AnalysisReset):
                await self._handle_analysis_reset(event)
            elif isinstance(event, DocumentExported):
                await self._handle_exported(event)
            logger.info(f"DocumentProjection successfully handled event: {event.event_type}")
        except Exception as e:
            logger.exception(f"DocumentProjection failed to handle event {event.event_type}: {e}")

    async def _handle_uploaded(self, event: DocumentUploaded) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO document_views 
                (id, title, original_format, original_filename, status, created_at)
                VALUES ($1, $2, $3, $4, $5, $6)
                ON CONFLICT (id) DO UPDATE SET
                    title = $2,
                    original_format = $3,
                    original_filename = $4,
                    status = $5,
                    updated_at = NOW()
                """,
                event.aggregate_id,
                event.filename,
                event.original_format,
                event.filename,
                "uploaded",
                event.occurred_at
            )

    async def _handle_converted(self, event: DocumentConverted) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'converted', updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )
            await conn.execute(
                """
                INSERT INTO document_contents
                (document_id, version, markdown_content, sections, metadata)
                VALUES ($1, 1, $2, $3, $4)
                ON CONFLICT (document_id, version) DO UPDATE SET
                    markdown_content = $2,
                    sections = $3,
                    metadata = $4
                """,
                event.aggregate_id,
                event.markdown_content,
                json.dumps(serialize_for_json(event.sections)),
                json.dumps(serialize_for_json(event.metadata))
            )

    async def _handle_analysis_started(self, event: AnalysisStarted) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'analyzing', 
                    policy_repository_id = $2,
                    updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id,
                event.policy_repository_id
            )
            await conn.execute(
                """
                INSERT INTO analysis_session_views
                (id, document_id, status, model_provider, started_at)
                VALUES ($1, $2, 'in_progress', $3, $4)
                """,
                event.event_id,
                event.aggregate_id,
                event.ai_model,
                event.occurred_at
            )

    async def _handle_analysis_completed(self, event: AnalysisCompleted) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'analyzed', 
                    compliance_status = CASE 
                        WHEN $2 >= 0.9 THEN 'compliant'
                        WHEN $2 >= 0.5 THEN 'partial'
                        ELSE 'non_compliant'
                    END,
                    updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id,
                event.compliance_score
            )
            await conn.execute(
                """
                UPDATE analysis_session_views
                SET status = 'completed',
                    feedback_count = $2,
                    completed_at = NOW()
                WHERE document_id = $1 AND status = 'in_progress'
                """,
                event.aggregate_id,
                event.findings_count
            )

    async def _handle_analysis_failed(self, event: AnalysisFailed) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'failed', updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )
            await conn.execute(
                """
                UPDATE analysis_session_views
                SET status = 'failed',
                    error_message = $2,
                    completed_at = NOW()
                WHERE document_id = $1 AND status = 'in_progress'
                """,
                event.aggregate_id,
                event.error_message
            )

    async def _handle_analysis_reset(self, event: AnalysisReset) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'converted', updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )

    async def _handle_exported(self, event: DocumentExported) -> None:
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE document_views
                SET status = 'exported', 
                    version = version + 1,
                    updated_at = NOW()
                WHERE id = $1
                """,
                event.aggregate_id
            )
