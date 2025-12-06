from dataclasses import dataclass
from typing import List, Dict, Any

from src.domain.value_objects import RequirementType


@dataclass
class ComplianceResult:
    is_compliant: bool
    confidence: float
    requirement_type: RequirementType
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
        threshold = self._get_threshold_for_requirement_type(requirement_type)
        is_compliant = confidence >= threshold
        
        return ComplianceResult(
            is_compliant=is_compliant,
            confidence=confidence,
            requirement_type=requirement_type,
            explanation=f"Found {matches}/{len(keywords)} key terms (threshold: {threshold})",
        )

    def _get_threshold_for_requirement_type(self, requirement_type: RequirementType) -> float:
        if requirement_type == RequirementType.MUST:
            return 0.8
        elif requirement_type == RequirementType.SHOULD:
            return 0.5
        elif requirement_type == RequirementType.MAY:
            return 0.3
        return 0.5

    def identify_issues(
        self,
        document_content: str,
        policy_rules: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        issues = []
        for rule in policy_rules:
            req_type = rule.get("type", RequirementType.SHOULD)
            if isinstance(req_type, str):
                req_type = RequirementType(req_type.upper())
            result = self.check_requirement(
                document_content=document_content,
                policy_rule=rule["rule"],
                requirement_type=req_type,
            )
            if not result.is_compliant:
                issues.append({
                    "rule": rule["rule"],
                    "requirement_type": result.requirement_type.value,
                    "confidence": result.confidence,
                    "explanation": result.explanation,
                    "severity": self._get_severity(result.requirement_type),
                })
        return issues

    def _get_severity(self, requirement_type: RequirementType) -> str:
        if requirement_type == RequirementType.MUST:
            return "HIGH"
        elif requirement_type == RequirementType.SHOULD:
            return "MEDIUM"
        return "LOW"

    def _extract_keywords(self, rule: str) -> List[str]:
        stop_words = {"must", "should", "may", "have", "contain", "include", "the", "a", "an"}
        words = rule.lower().split()
        return [w for w in words if w not in stop_words and len(w) > 2]
