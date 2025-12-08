from uuid import UUID

from ..base import AIProvider, AnalysisOptions, PolicyRule
from ..provider_factory import ProviderFactory, ProviderType
from .progress_tracker import ProgressTracker, AnalysisStage, ProgressCallback
from .policy_evaluator import PolicyEvaluator
from .feedback_generator import FeedbackGenerator
from .result_aggregator import ResultAggregator, AggregatedResult
from .analysis_log import AnalysisLogStore


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
        
        log_store = AnalysisLogStore.get_instance()
        log = log_store.create_log(document_id)
        
        try:
            log.info("initialization", f"Starting analysis with {provider_type.value} provider", {
                "provider": provider_type.value,
                "model": provider.default_model,
                "include_suggestions": options.include_suggestions,
                "max_issues": options.max_issues,
                "policy_rules_count": len(policy_rules),
            })
            
            tracker.start_stage(AnalysisStage.PREPROCESSING, "Preparing document for analysis")
            log.info("preprocessing", "Preprocessing document content", {
                "original_length": len(document_content),
            })
            processed_content = self._preprocess_document(document_content)
            log.info("preprocessing", "Document preprocessed successfully", {
                "processed_length": len(processed_content),
                "reduction_pct": round((1 - len(processed_content) / max(len(document_content), 1)) * 100, 1),
            })
            tracker.complete_step("Document preprocessed")
            
            tracker.start_stage(AnalysisStage.ANALYZING, "Analyzing document content")
            log.info("analysis", "Sending document to AI for analysis", {
                "content_preview": processed_content[:200] + "..." if len(processed_content) > 200 else processed_content,
            })
            analysis_result = await provider.analyze_document(
                content=processed_content,
                policy_rules=policy_rules,
                options=options,
            )
            log.info("analysis", "AI analysis complete", {
                "issues_found": len(analysis_result.issues) if analysis_result.issues else 0,
                "suggestions_count": len(analysis_result.suggestions) if analysis_result.suggestions else 0,
            })
            if analysis_result.raw_response:
                log.info("ai_response", "Raw AI model response:", {
                    "response": analysis_result.raw_response[:4000] if len(analysis_result.raw_response) > 4000 else analysis_result.raw_response,
                    "truncated": len(analysis_result.raw_response) > 4000,
                    "total_length": len(analysis_result.raw_response),
                })
            if analysis_result.issues:
                for i, issue in enumerate(analysis_result.issues[:5]):
                    log.debug("analysis", f"Issue {i+1}: {issue.title if hasattr(issue, 'title') else str(issue)[:100]}", {
                        "severity": issue.severity.value if hasattr(issue, 'severity') else "unknown",
                    })
                if len(analysis_result.issues) > 5:
                    log.debug("analysis", f"... and {len(analysis_result.issues) - 5} more issues")
            tracker.complete_step("Document analysis complete")
            
            policy_evaluation = None
            if policy_rules:
                tracker.start_stage(AnalysisStage.EVALUATING_POLICIES, "Evaluating policy compliance")
                log.info("policy_evaluation", f"Evaluating against {len(policy_rules)} policy rules")
                evaluator = PolicyEvaluator(provider)
                policy_evaluation = await evaluator.evaluate(
                    document_content=processed_content,
                    policy_rules=policy_rules,
                    options=options,
                )
                log.info("policy_evaluation", "Policy evaluation complete", {
                    "overall_score": policy_evaluation.overall_score if policy_evaluation else 0,
                    "compliance_results_count": len(policy_evaluation.compliance_results) if policy_evaluation else 0,
                    "critical_gaps": len(policy_evaluation.critical_gaps) if policy_evaluation else 0,
                })
                tracker.complete_step("Policy evaluation complete")
            else:
                log.info("policy_evaluation", "Skipping policy evaluation (no rules defined)")
                tracker.complete_step("Skipping policy evaluation (no rules)")
            
            feedback_result = None
            if options.include_suggestions and analysis_result.issues:
                tracker.start_stage(AnalysisStage.GENERATING_FEEDBACK, "Generating feedback and suggestions")
                log.info("feedback", f"Generating feedback for {len(analysis_result.issues)} issues")
                generator = FeedbackGenerator(provider)
                feedback_result = await generator.generate(
                    document_content=processed_content,
                    issues=analysis_result.issues,
                    policy_rules=policy_rules,
                    options=options,
                )
                log.info("feedback", "Feedback generation complete", {
                    "feedback_items_count": len(feedback_result.feedback_items) if feedback_result else 0,
                })
                tracker.complete_step("Feedback generation complete")
            else:
                reason = "suggestions disabled" if not options.include_suggestions else "no issues found"
                log.info("feedback", f"Skipping feedback generation ({reason})")
                tracker.complete_step("Skipping feedback generation")
            
            tracker.start_stage(AnalysisStage.AGGREGATING_RESULTS, "Aggregating results")
            log.info("aggregation", "Aggregating all analysis results")
            aggregated = aggregator.aggregate(
                document_id=document_id,
                analysis_result=analysis_result,
                policy_evaluation=policy_evaluation,
                feedback_result=feedback_result,
            )
            
            log.info("complete", "Analysis completed successfully", {
                "overall_score": aggregated.overall_score,
                "total_issues": aggregated.total_issues,
                "critical_issues": aggregated.critical_issues,
                "high_issues": aggregated.high_issues,
                "suggestions_generated": aggregated.suggestions_generated,
            })
            log.complete("completed")
            
            tracker.complete()
            
            return aggregated
            
        except Exception as e:
            log.error("error", f"Analysis failed: {str(e)}", {
                "error_type": type(e).__name__,
            })
            log.complete("failed")
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
