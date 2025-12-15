import logging
from uuid import UUID

from .base import CommandHandler
from src.domain.commands import StartAnalysis, CancelAnalysis
from src.domain.aggregates.document import Document
from src.domain.exceptions.document_exceptions import DocumentNotFound
from src.domain.exceptions.policy_exceptions import PolicyRepositoryNotFound
from src.infrastructure.repositories.document_repository import DocumentRepository
from src.infrastructure.repositories.policy_repository import PolicyRepositoryRepository
from src.infrastructure.ai.provider_factory import ProviderFactory
from src.infrastructure.ai.analysis.engine import AnalysisEngine
from src.infrastructure.ai.base import PolicyRule, AnalysisOptions
from src.application.services.event_publisher import EventPublisher

logger = logging.getLogger(__name__)

# Import metrics (will be None if not in API context)
try:
    from src.api.metrics import analyses_completed_total
    METRICS_AVAILABLE = True
except ImportError:
    METRICS_AVAILABLE = False
    logger.debug("Metrics not available - running outside API context")


class StartAnalysisHandler(CommandHandler[StartAnalysis, UUID]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        policy_repository: PolicyRepositoryRepository,
        event_publisher: EventPublisher,
        provider_factory: ProviderFactory | None = None,
    ):
        self._documents = document_repository
        self._policies = policy_repository
        self._publisher = event_publisher
        self._provider_factory = provider_factory or ProviderFactory()

    async def handle(self, command: StartAnalysis) -> UUID:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        policy_repo = await self._policies.get(command.policy_repository_id)
        if policy_repo is None:
            raise PolicyRepositoryNotFound(repository_id=command.policy_repository_id)

        document.start_analysis(
            policy_repository_id=command.policy_repository_id,
            ai_model=command.ai_model,
            initiated_by=command.initiated_by
        )

        events = list(document.pending_events)
        await self._documents.save(document)

        if events:
            await self._publisher.publish_all(events)

        try:
            policy_rules = [
                PolicyRule(
                    id=str(p.get("policy_id", "")),
                    name=p.get("policy_name", ""),
                    description=p.get("policy_content", ""),
                    requirement_type=p.get("requirement_type", "SHOULD"),
                    category=p.get("category", "general"),
                    validation_criteria=p.get("validation_criteria", ""),
                    examples=p.get("examples", []),
                )
                for p in policy_repo.policies
            ]

            from src.infrastructure.ai.base import ProviderType
            
            provider_type = ProviderType.CLAUDE
            if command.ai_model:
                try:
                    provider_type = ProviderType(command.ai_model)
                except ValueError:
                    provider_type = ProviderType.CLAUDE
            
            engine = AnalysisEngine(
                provider_factory=self._provider_factory,
                default_provider=provider_type,
            )
            
            options = AnalysisOptions(
                include_suggestions=True,
                max_issues=50,
            )
            
            logger.info(f"Starting AI analysis for document {command.document_id} with provider {provider_type.value}")
            result = await engine.analyze(
                document_id=command.document_id,
                document_content=document.markdown_content,
                policy_rules=policy_rules,
                options=options,
                provider_type=provider_type,
            )
            logger.info(f"Analysis completed: success={result.success}, issues={result.total_issues}")

            if result.success:
                findings = []
                if result.analysis_result:
                    findings = [issue.to_dict() for issue in result.analysis_result.issues]

                document.complete_analysis(
                    findings_count=result.total_issues,
                    compliance_score=result.overall_score,
                    findings=findings,
                    processing_time_ms=result.processing_time_ms,
                )

                # Track successful analysis
                if METRICS_AVAILABLE:
                    analyses_completed_total.labels(status="success").inc()
            else:
                error_msg = "; ".join(result.errors) if result.errors else "Unknown analysis error"
                document.fail_analysis(reason=error_msg)
                logger.error(f"Analysis failed for document {command.document_id}: {error_msg}")

                # Track failed analysis
                if METRICS_AVAILABLE:
                    analyses_completed_total.labels(status="failed").inc()

            completion_events = list(document.pending_events)
            await self._documents.save(document)

            if completion_events:
                await self._publisher.publish_all(completion_events)

        except Exception as e:
            logger.exception(f"Analysis error for document {command.document_id}: {e}")
            try:
                document.fail_analysis(reason=str(e))
                failure_events = list(document.pending_events)
                await self._documents.save(document)
                if failure_events:
                    await self._publisher.publish_all(failure_events)
            except Exception as save_error:
                logger.exception(f"Failed to save failure state: {save_error}")

        return command.document_id


class CancelAnalysisHandler(CommandHandler[CancelAnalysis, bool]):
    def __init__(
        self,
        document_repository: DocumentRepository,
        event_publisher: EventPublisher
    ):
        self._documents = document_repository
        self._publisher = event_publisher

    async def handle(self, command: CancelAnalysis) -> bool:
        document = await self._documents.get(command.document_id)
        if document is None:
            raise DocumentNotFound(document_id=command.document_id)

        return True
