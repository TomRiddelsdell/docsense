import asyncio
import json
import os
import re
import time
from typing import Any

from anthropic import Anthropic

from .base import (
    AIProvider,
    AnalysisOptions,
    AnalysisResult,
    Issue,
    IssueSeverity,
    PolicyRule,
    ProviderType,
    Suggestion,
)
from .rate_limiter import RateLimiter
from .prompts.base import PromptContext
from .prompts.document_analysis import DocumentAnalysisPrompt
from .prompts.suggestion_generation import SuggestionGenerationPrompt


class ClaudeProvider(AIProvider):
    
    AVAILABLE_MODELS = [
        "claude-sonnet-4-20250514",
        "claude-3-5-sonnet-20241022",
        "claude-3-5-haiku-20241022",
    ]
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    REQUEST_TIMEOUT = 120

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self._rate_limiter = rate_limiter
        api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
        base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
        
        self._client = Anthropic(
            api_key=api_key,
            base_url=base_url
        )
        self._analysis_prompt = DocumentAnalysisPrompt()
        self._suggestion_prompt = SuggestionGenerationPrompt()

    @property
    def provider_type(self) -> ProviderType:
        return ProviderType.CLAUDE

    @property
    def default_model(self) -> str:
        return self.DEFAULT_MODEL

    @property
    def available_models(self) -> list[str]:
        return self.AVAILABLE_MODELS.copy()

    async def analyze_document(
        self,
        content: str,
        policy_rules: list[PolicyRule],
        options: AnalysisOptions | None = None,
    ) -> AnalysisResult:
        options = options or AnalysisOptions()
        model = self.validate_model(options.model_name)
        
        start_time = time.time()
        
        try:
            if self._rate_limiter:
                await self._rate_limiter.acquire(estimated_tokens=len(content) // 4)
            
            context = PromptContext(
                document_content=content,
                policy_rules=[self._policy_rule_to_dict(r) for r in policy_rules],
                max_issues=options.max_issues,
                include_suggestions=options.include_suggestions,
                section_focus=options.focus_sections,
                extra_context=options.extra_context,
            )
            
            user_prompt = self._analysis_prompt.render(context)
            system_prompt = self._analysis_prompt.get_system_prompt()
            
            message = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_messages_create,
                    model,
                    system_prompt,
                    user_prompt,
                    8192,
                ),
                timeout=self.REQUEST_TIMEOUT,
            )
            
            processing_time = int((time.time() - start_time) * 1000)
            
            result_text = ""
            if message.content and message.content[0].type == "text":
                result_text = message.content[0].text
            
            result_text = self._extract_json(result_text)
            result_data = json.loads(result_text or "{}")
            
            issues = self._parse_issues(result_data.get("issues", []))
            suggestions = []
            
            if options.include_suggestions:
                suggestions = self._parse_suggestions(result_data.get("suggestions", []), issues)
            
            token_count = 0
            if message.usage:
                token_count = message.usage.input_tokens + message.usage.output_tokens
            
            return AnalysisResult(
                success=True,
                issues=issues,
                suggestions=suggestions,
                summary=result_data.get("summary", "Analysis completed"),
                processing_time_ms=processing_time,
                model_used=model,
                token_count=token_count,
            )
            
        except asyncio.TimeoutError:
            processing_time = int((time.time() - start_time) * 1000)
            return AnalysisResult(
                success=False,
                issues=[],
                suggestions=[],
                summary="",
                processing_time_ms=processing_time,
                model_used=model,
                errors=["Request timed out"],
            )
        except Exception as e:
            processing_time = int((time.time() - start_time) * 1000)
            return AnalysisResult(
                success=False,
                issues=[],
                suggestions=[],
                summary="",
                processing_time_ms=processing_time,
                model_used=model,
                errors=[str(e)],
            )
        finally:
            if self._rate_limiter:
                self._rate_limiter.release()

    def _call_messages_create(
        self,
        model: str,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int,
    ):
        return self._client.messages.create(
            model=model,
            max_tokens=max_tokens,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )

    async def generate_suggestion(
        self,
        issue: Issue,
        document_context: str,
        policy_rule: PolicyRule,
    ) -> Suggestion:
        if self._rate_limiter:
            await self._rate_limiter.acquire(estimated_tokens=1000)
        
        try:
            context = PromptContext(
                document_content=document_context,
                policy_rules=[self._policy_rule_to_dict(policy_rule)],
                issue_data=issue.to_dict(),
            )
            
            user_prompt = self._suggestion_prompt.render(context)
            system_prompt = self._suggestion_prompt.get_system_prompt()
            
            message = await asyncio.wait_for(
                asyncio.to_thread(
                    self._call_messages_create,
                    self.default_model,
                    system_prompt,
                    user_prompt,
                    2048,
                ),
                timeout=self.REQUEST_TIMEOUT,
            )
            
            result_text = ""
            if message.content and message.content[0].type == "text":
                result_text = message.content[0].text
            
            result_text = self._extract_json(result_text)
            result_data = json.loads(result_text or "{}")
            
            return Suggestion.create(
                issue_id=issue.id,
                suggested_text=result_data.get("suggested_text", ""),
                explanation=result_data.get("explanation", ""),
                confidence=result_data.get("confidence", 0.7),
            )
            
        finally:
            if self._rate_limiter:
                self._rate_limiter.release()

    async def is_available(self) -> bool:
        try:
            api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
            return bool(api_key and base_url)
        except Exception:
            return False

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if "```" in text:
            text = text.split("```")[0]
        
        text = text.strip()
        
        start_idx = text.find("{")
        if start_idx == -1:
            return "{}"
        
        brace_count = 0
        end_idx = start_idx
        in_string = False
        escape_next = False
        
        for i, char in enumerate(text[start_idx:], start=start_idx):
            if escape_next:
                escape_next = False
                continue
            if char == "\\":
                escape_next = True
                continue
            if char == '"' and not escape_next:
                in_string = not in_string
                continue
            if in_string:
                continue
            if char == "{":
                brace_count += 1
            elif char == "}":
                brace_count -= 1
                if brace_count == 0:
                    end_idx = i
                    break
        
        if brace_count == 0 and end_idx > start_idx:
            return text[start_idx:end_idx + 1]
        
        return text[start_idx:]

    def _policy_rule_to_dict(self, rule: PolicyRule) -> dict[str, Any]:
        return {
            "id": rule.id,
            "name": rule.name,
            "description": rule.description,
            "requirement_type": rule.requirement_type,
            "category": rule.category,
            "validation_criteria": rule.validation_criteria,
            "examples": rule.examples,
        }

    def _parse_issues(self, issues_data: list[dict[str, Any]]) -> list[Issue]:
        issues = []
        for data in issues_data:
            try:
                severity = IssueSeverity(data.get("severity", "medium"))
                issue = Issue.create(
                    rule_id=data.get("rule_id", "unknown"),
                    severity=severity,
                    title=data.get("title", ""),
                    description=data.get("description", ""),
                    location=data.get("location", ""),
                    original_text=data.get("original_text", ""),
                    confidence=float(data.get("confidence", 0.7)),
                )
                issues.append(issue)
            except (ValueError, KeyError):
                continue
        return issues

    def _parse_suggestions(
        self,
        suggestions_data: list[dict[str, Any]],
        issues: list[Issue],
    ) -> list[Suggestion]:
        suggestions = []
        for data in suggestions_data:
            try:
                issue_index = data.get("issue_index", 0)
                if issue_index < len(issues):
                    suggestion = Suggestion.create(
                        issue_id=issues[issue_index].id,
                        suggested_text=data.get("suggested_text", ""),
                        explanation=data.get("explanation", ""),
                        confidence=float(data.get("confidence", 0.7)),
                    )
                    suggestions.append(suggestion)
            except (ValueError, KeyError, IndexError):
                continue
        return suggestions
