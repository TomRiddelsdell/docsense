"""Event handler for automatic semantic IR curation after document conversion."""

import logging
from typing import Optional
import json
from uuid import UUID

from src.domain.events.document_events import DocumentConverted
from src.domain.events.base import DomainEvent
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.semantic.ai_curator import SemanticIRCurator
from src.infrastructure.semantic import IRBuilder
from src.application.services.event_publisher import EventPublisher
from src.infrastructure.persistence.postgres_connection import PostgresConnection
from src.infrastructure.ai.analysis.analysis_log import AnalysisLogStore, LogLevel

logger = logging.getLogger(__name__)


class SemanticCurationEventHandler:
    """
    Event handler that triggers AI curation when a document is converted.

    This implements the async background curation pattern (Option 2):
    1. Document is uploaded and converted with rule-based extraction
    2. DocumentConverted event is emitted
    3. This handler triggers AI curation in the background
    4. Enhanced semantic IR is saved back to the database
    """

    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher,
        db_connection: PostgresConnection,
        ai_curator: Optional[SemanticIRCurator] = None,
        enabled: bool = True,
    ):
        """
        Initialize the curation event handler.

        Args:
            document_repository: Repository for loading/saving documents
            event_publisher: Event publisher for emitting curation events
            db_connection: Database connection for direct semantic_ir table updates
            ai_curator: AI curator (defaults to new instance)
            enabled: Whether curation is enabled (allows disabling for testing)
        """
        self._documents = document_repository
        self._publisher = event_publisher
        self._db = db_connection
        self._curator = ai_curator or SemanticIRCurator()
        self._enabled = enabled

    async def handle(self, event: DomainEvent) -> None:
        """Handle DocumentConverted events."""
        if not isinstance(event, DocumentConverted):
            return

        if not self._enabled:
            logger.info(f"Semantic IR curation disabled, skipping for document {event.aggregate_id}")
            return

        logger.info(f"Triggering semantic IR curation for document {event.aggregate_id}")

        # Get or create analysis log for this document
        log_store = AnalysisLogStore.get_instance()
        # Handle both string and UUID types for aggregate_id
        doc_uuid = event.aggregate_id if isinstance(event.aggregate_id, UUID) else UUID(event.aggregate_id)
        analysis_log = log_store.get_or_create_log(doc_uuid)
        analysis_log.info("semantic_curation", "Starting AI-powered semantic IR curation")

        try:
            # Get semantic IR from database
            analysis_log.info("semantic_curation", "Retrieving semantic IR from database")
            async with self._db.pool.acquire() as conn:
                row = await conn.fetchrow(
                    "SELECT semantic_ir FROM semantic_ir WHERE document_id = $1",
                    event.aggregate_id
                )

            if not row or not row['semantic_ir']:
                analysis_log.warning("semantic_curation", "No semantic IR found, skipping curation")
                logger.warning(f"No semantic IR found for document {event.aggregate_id}, skipping curation")
                return

            # Deserialize semantic IR
            analysis_log.info("semantic_curation", "Deserializing semantic IR")
            from src.domain.value_objects.semantic_ir import DocumentIR
            semantic_ir_data = json.loads(row['semantic_ir'])
            semantic_ir = DocumentIR.from_dict(semantic_ir_data)
            markdown = event.markdown_content

            # Run AI curation
            logger.info(f"Starting AI curation for document {event.aggregate_id}")
            original_def_count = len(semantic_ir.definitions)

            analysis_log.info(
                "semantic_curation",
                f"Running AI curation with Claude",
                {
                    "original_definition_count": original_def_count,
                    "provider": "claude"
                }
            )

            enhanced_ir = await self._curator.curate(
                ir=semantic_ir,
                markdown=markdown,
                provider_type="claude"
            )

            new_def_count = len(enhanced_ir.definitions)
            definitions_added = max(0, new_def_count - original_def_count)
            definitions_removed = max(0, original_def_count - new_def_count)

            logger.info(
                f"AI curation complete for document {event.aggregate_id}: "
                f"added={definitions_added}, removed={definitions_removed}"
            )

            analysis_log.info(
                "semantic_curation",
                "AI curation completed successfully",
                {
                    "definitions_added": definitions_added,
                    "definitions_removed": definitions_removed,
                    "final_definition_count": new_def_count,
                }
            )

            # Save enhanced IR back to database
            analysis_log.info("semantic_curation", "Saving enhanced semantic IR to database")
            serialized_ir = enhanced_ir.to_dict()
            async with self._db.pool.acquire() as conn:
                await conn.execute(
                    """
                    UPDATE semantic_ir
                    SET semantic_ir = $1, updated_at = NOW()
                    WHERE document_id = $2
                    """,
                    json.dumps(serialized_ir),
                    event.aggregate_id
                )

            # Load document and emit success event
            document = await self._documents.get(event.aggregate_id)
            if document:
                document.complete_ir_curation(
                    definitions_added=definitions_added,
                    definitions_removed=definitions_removed,
                    validation_issues_found=0,
                    curation_metadata={
                        "provider": "claude",
                        "original_definitions": original_def_count,
                        "final_definitions": new_def_count,
                    }
                )

                events = list(document.pending_events)
                await self._documents.save(document)

                if events:
                    await self._publisher.publish_all(events)

            logger.info(f"Semantic IR curation completed successfully for document {event.aggregate_id}")
            analysis_log.info("semantic_curation", "Semantic IR curation pipeline completed")

        except Exception as e:
            logger.error(f"Semantic IR curation failed for document {event.aggregate_id}: {e}", exc_info=True)
            analysis_log.error(
                "semantic_curation",
                f"AI curation failed: {str(e)}",
                {"error_type": type(e).__name__}
            )

            # Try to emit failure event
            try:
                document = await self._documents.get(event.aggregate_id)
                if document:
                    document.fail_ir_curation(error_message=str(e))
                    events = list(document.pending_events)
                    await self._documents.save(document)
                    if events:
                        await self._publisher.publish_all(events)
            except Exception as inner_e:
                logger.error(f"Failed to emit curation failure event: {inner_e}")
                analysis_log.error(
                    "semantic_curation",
                    f"Failed to emit failure event: {str(inner_e)}"
                )
