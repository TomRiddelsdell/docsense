from dataclasses import dataclass
from typing import List, Dict, Any

from src.domain.value_objects import RequirementType


@dataclass
class ComplianceResult:
    is_compliant: bool
    confidence: float
    explanation: str = ""


class ComplianceChecker:
    def check_requirement(
        self,
        document_content: str,
        policy_rule: str,
        requirement_type: RequirementType,
    ) -> ComplianceResult:
        keywords = self._extract_keywords(policy_rule)
        matches = sum(1 for kw in keywords if kw.lower() in document_content.lower())
        
        confidence = min(1.0, matches / max(1, len(keywords)))
        is_compliant = confidence > 0.5
        
        return ComplianceResult(
            is_compliant=is_compliant,
            confidence=confidence,
            explanation=f"Found {matches}/{len(keywords)} key terms",
        )

    def identify_issues(
        self,
        document_content: str,
        policy_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        issues = []
        for rule in policy_rules:
            result = self.check_requirement(
                document_content=document_content,
                policy_rule=rule["rule"],
                requirement_type=rule["type"],
            )
            if not result.is_compliant:
                issues.append({
                    "rule": rule["rule"],
                    "requirement_type": rule["type"],
                    "confidence": result.confidence,
                    "explanation": result.explanation,
                })
        return issues

    def _extract_keywords(self, rule: str) -> List[str]:
        stop_words = {"must", "should", "may", "have", "contain", "include", "the", "a", "an"}
        words = rule.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 2]
