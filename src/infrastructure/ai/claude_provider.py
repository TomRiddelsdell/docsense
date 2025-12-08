import asyncio
import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import litellm

logger = logging.getLogger(__name__)

AI_RESPONSES_DIR = Path("data/ai_responses")

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
        "claude-sonnet-4-5",
        "claude-haiku-4-5",
        "claude-opus-4-5",
    ]
    DEFAULT_MODEL = "claude-sonnet-4-5"
    REQUEST_TIMEOUT = 240

    def __init__(self, rate_limiter: RateLimiter | None = None):
        self._rate_limiter = rate_limiter
        
        base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
        if base_url:
            os.environ["ANTHROPIC_BASE_URL"] = base_url
            api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
        else:
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
                if api_key:
                    os.environ["ANTHROPIC_API_KEY"] = api_key
        
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
            
            raw_response = ""
            if message.choices and len(message.choices) > 0:
                raw_response = message.choices[0].message.content or ""
            
            logger.info(f"Raw AI response length: {len(raw_response)}")
            logger.debug(f"Raw AI response (first 2000 chars): {raw_response[:2000]}")
            
            self._save_ai_response(raw_response, model, "document_analysis")
            
            result_text = self._extract_json(raw_response)
            logger.info(f"Extracted JSON length: {len(result_text)}")
            logger.debug(f"Extracted JSON (first 2000 chars): {result_text[:2000]}")
            
            result_data = json.loads(result_text or "{}")
            logger.info(f"Parsed issues count: {len(result_data.get('issues', []))}")
            
            issues = self._parse_issues(result_data.get("issues", []))
            suggestions = []
            
            if options.include_suggestions:
                suggestions = self._parse_suggestions(result_data.get("suggestions", []), issues)
            
            token_count = 0
            if message.usage:
                token_count = (message.usage.prompt_tokens or 0) + (message.usage.completion_tokens or 0)
            
            return AnalysisResult(
                success=True,
                issues=issues,
                suggestions=suggestions,
                summary=result_data.get("summary", "Analysis completed"),
                processing_time_ms=processing_time,
                model_used=model,
                token_count=token_count,
                raw_response=raw_response,
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
        base_url = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_BASE_URL")
        if base_url:
            os.environ["ANTHROPIC_BASE_URL"] = base_url
            api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            if api_key:
                os.environ["ANTHROPIC_API_KEY"] = api_key
        
        litellm_model = f"anthropic/{model}"
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]
        
        response = litellm.completion(
            model=litellm_model,
            messages=messages,
            max_tokens=max_tokens,
            timeout=self.REQUEST_TIMEOUT,
            num_retries=2,
        )
        
        return response

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
            if message.choices and len(message.choices) > 0:
                result_text = message.choices[0].message.content or ""
            
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
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                api_key = os.environ.get("AI_INTEGRATIONS_ANTHROPIC_API_KEY")
            return bool(api_key)
        except Exception:
            return False

    def _save_ai_response(self, response: str, model: str, operation: str) -> None:
        try:
            AI_RESPONSES_DIR.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"{operation}_{model}_{timestamp}.txt"
            filepath = AI_RESPONSES_DIR / filename
            filepath.write_text(response)
            logger.info(f"Saved AI response to: {filepath}")
        except Exception as e:
            logger.error(f"Failed to save AI response: {e}")

    def _extract_json(self, text: str) -> str:
        text = text.strip()
        
        # Log first 500 chars of raw response to understand format
        logger.info(f"_extract_json: First 500 chars: {text[:500]}")
        logger.info(f"_extract_json: Last 500 chars: {text[-500:]}")
        
        # Try to find JSON in code blocks first (most reliable)
        import re
        
        # Look for ```json ... ``` blocks anywhere in the text
        json_block_match = re.search(r'```json\s*([\s\S]*?)```', text)
        if json_block_match:
            json_text = json_block_match.group(1).strip()
            logger.info(f"Found JSON in code block, length: {len(json_text)}")
            try:
                json.loads(json_text)
                return json_text
            except json.JSONDecodeError as e:
                logger.info(f"JSON code block parse failed: {e}, trying repair")
                repaired = self._repair_truncated_json(json_text)
                try:
                    json.loads(repaired)
                    return repaired
                except json.JSONDecodeError:
                    pass
        else:
            logger.info("No ```json block found")
        
        # Look for ``` ... ``` blocks (without json marker)
        code_block_match = re.search(r'```\s*([\s\S]*?)```', text)
        if code_block_match:
            block_text = code_block_match.group(1).strip()
            logger.info(f"Found code block, starts with: {block_text[:100] if block_text else 'empty'}")
            if block_text.startswith('{'):
                logger.info(f"Found JSON in unmarked code block, length: {len(block_text)}")
                try:
                    json.loads(block_text)
                    return block_text
                except json.JSONDecodeError as e:
                    logger.info(f"Unmarked code block JSON parse failed: {e}")
                    repaired = self._repair_truncated_json(block_text)
                    try:
                        json.loads(repaired)
                        return repaired
                    except json.JSONDecodeError:
                        pass
        else:
            logger.info("No code block found at all")
        
        # Fall back to finding JSON object directly in text
        # Look for the LAST occurrence of {"issues" which is likely the complete JSON
        issues_match = re.search(r'\{[^{}]*"issues"\s*:', text)
        if issues_match:
            start_idx = issues_match.start()
            logger.info(f"Found 'issues' key at position {start_idx}")
        else:
            start_idx = text.find("{")
            logger.info(f"No 'issues' key found, first brace at: {start_idx}")
        
        if start_idx == -1:
            logger.warning("No JSON object found in response")
            return "{}"
        
        # Extract balanced JSON from start_idx
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
            extracted = text[start_idx:end_idx + 1]
            logger.debug(f"Extracted balanced JSON, length: {len(extracted)}")
            return extracted
        
        # If braces not balanced, try to repair
        json_text = text[start_idx:]
        logger.debug(f"Braces unbalanced (count={brace_count}), attempting repair")
        json_text = self._repair_truncated_json(json_text)
        return json_text

    def _repair_truncated_json(self, text: str) -> str:
        if not text:
            return "{}"
        
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            pass
        
        in_string = False
        escape_next = False
        brace_count = 0
        bracket_count = 0
        
        for char in text:
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
            elif char == "[":
                bracket_count += 1
            elif char == "]":
                bracket_count -= 1
        
        if in_string:
            text = text + '"'
        
        text = text + "]" * bracket_count
        text = text + "}" * brace_count
        
        try:
            json.loads(text)
            return text
        except json.JSONDecodeError:
            return "{}"

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
