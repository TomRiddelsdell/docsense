from uuid import UUID

from ..base import AIProvider, AnalysisOptions, PolicyRule
from ..provider_factory import ProviderFactory, ProviderType
from .progress_tracker import ProgressTracker, AnalysisStage, ProgressCallback
from .policy_evaluator import PolicyEvaluator
from .feedback_generator import FeedbackGenerator
from .result_aggregator import ResultAggregator, AggregatedResult


class AnalysisEngine:
    
    def __init__(
        self,
        provider_factory: ProviderFactory | None = None,
        default_provider: ProviderType = ProviderType.GEMINI,
    ):
        self._provider_factory = provider_factory or ProviderFactory()
        self._default_provider = default_provider

    async def analyze(
        self,
        document_id: UUID,
        document_content: str,
        policy_rules: list[PolicyRule],
        options: AnalysisOptions | None = None,
        provider_type: ProviderType | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AggregatedResult:
        options = options or AnalysisOptions()
        provider_type = provider_type or self._default_provider
        
        provider = self._provider_factory.get_provider(provider_type)
        
        tracker = ProgressTracker(document_id=document_id, total_steps=4)
        if progress_callback:
            tracker.add_callback(progress_callback)
        
        aggregator = ResultAggregator()
        
        try:
            tracker.start_stage(AnalysisStage.PREPROCESSING, "Preparing document for analysis")
            processed_content = self._preprocess_document(document_content)
            tracker.complete_step("Document preprocessed")
            
            tracker.start_stage(AnalysisStage.ANALYZING, "Analyzing document content")
            analysis_result = await provider.analyze_document(
                content=processed_content,
                policy_rules=policy_rules,
                options=options,
            )
            tracker.complete_step("Document analysis complete")
            
            policy_evaluation = None
            if policy_rules:
                tracker.start_stage(AnalysisStage.EVALUATING_POLICIES, "Evaluating policy compliance")
                evaluator = PolicyEvaluator(provider)
                policy_evaluation = await evaluator.evaluate(
                    document_content=processed_content,
                    policy_rules=policy_rules,
                    options=options,
                )
                tracker.complete_step("Policy evaluation complete")
            else:
                tracker.complete_step("Skipping policy evaluation (no rules)")
            
            feedback_result = None
            if options.include_suggestions and analysis_result.issues:
                tracker.start_stage(AnalysisStage.GENERATING_FEEDBACK, "Generating feedback and suggestions")
                generator = FeedbackGenerator(provider)
                feedback_result = await generator.generate(
                    document_content=processed_content,
                    issues=analysis_result.issues,
                    policy_rules=policy_rules,
                    options=options,
                )
                tracker.complete_step("Feedback generation complete")
            else:
                tracker.complete_step("Skipping feedback generation")
            
            tracker.start_stage(AnalysisStage.AGGREGATING_RESULTS, "Aggregating results")
            aggregated = aggregator.aggregate(
                document_id=document_id,
                analysis_result=analysis_result,
                policy_evaluation=policy_evaluation,
                feedback_result=feedback_result,
            )
            
            tracker.complete()
            
            return aggregated
            
        except Exception as e:
            tracker.fail(str(e))
            return AggregatedResult(
                id=tracker.analysis_id,
                document_id=document_id,
                success=False,
                analysis_result=None,
                policy_evaluation=None,
                feedback_items=[],
                overall_score=0.0,
                total_issues=0,
                critical_issues=0,
                high_issues=0,
                suggestions_generated=0,
                processing_time_ms=0,
                model_used=provider.default_model,
                errors=[str(e)],
            )

    def _preprocess_document(self, content: str) -> str:
        lines = content.split('\n')
        normalized = []
        for line in lines:
            stripped = line.rstrip()
            normalized.append(stripped)
        
        result = []
        prev_empty = False
        for line in normalized:
            is_empty = len(line.strip()) == 0
            if is_empty and prev_empty:
                continue
            result.append(line)
            prev_empty = is_empty
        
        return '\n'.join(result).strip()

    async def quick_analyze(
        self,
        document_id: UUID,
        document_content: str,
        provider_type: ProviderType | None = None,
    ) -> AggregatedResult:
        options = AnalysisOptions(
            include_suggestions=False,
            max_issues=10,
        )
        return await self.analyze(
            document_id=document_id,
            document_content=document_content,
            policy_rules=[],
            options=options,
            provider_type=provider_type,
        )

    async def detailed_analyze(
        self,
        document_id: UUID,
        document_content: str,
        policy_rules: list[PolicyRule],
        provider_type: ProviderType | None = None,
        progress_callback: ProgressCallback | None = None,
    ) -> AggregatedResult:
        options = AnalysisOptions(
            include_suggestions=True,
            max_issues=50,
        )
        return await self.analyze(
            document_id=document_id,
            document_content=document_content,
            policy_rules=policy_rules,
            options=options,
            provider_type=provider_type,
            progress_callback=progress_callback,
        )

    async def get_available_providers(self) -> list[ProviderType]:
        return await self._provider_factory.get_available_providers()
