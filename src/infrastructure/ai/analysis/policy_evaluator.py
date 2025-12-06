from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from ..base import AIProvider, AnalysisOptions, PolicyRule


class ComplianceStatus(Enum):
    COMPLIANT = "compliant"
    PARTIAL = "partial"
    NON_COMPLIANT = "non_compliant"
    NOT_APPLICABLE = "not_applicable"


@dataclass
class ComplianceResult:
    id: UUID
    rule_id: str
    rule_name: str
    status: ComplianceStatus
    evidence: str
    location: str
    gaps: list[str]
    remediation: str
    confidence: float

    @classmethod
    def create(
        cls,
        rule_id: str,
        rule_name: str,
        status: ComplianceStatus,
        evidence: str,
        location: str,
        gaps: list[str],
        remediation: str,
        confidence: float,
    ) -> "ComplianceResult":
        return cls(
            id=uuid4(),
            rule_id=rule_id,
            rule_name=rule_name,
            status=status,
            evidence=evidence,
            location=location,
            gaps=gaps,
            remediation=remediation,
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "status": self.status.value,
            "evidence": self.evidence,
            "location": self.location,
            "gaps": self.gaps,
            "remediation": self.remediation,
            "confidence": self.confidence,
        }


@dataclass
class PolicyEvaluationResult:
    success: bool
    compliance_results: list[ComplianceResult]
    overall_score: float
    critical_gaps: list[str]
    summary: str
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "compliance_results": [r.to_dict() for r in self.compliance_results],
            "overall_score": self.overall_score,
            "critical_gaps": self.critical_gaps,
            "summary": self.summary,
            "errors": self.errors,
        }

    @property
    def compliant_count(self) -> int:
        return sum(1 for r in self.compliance_results if r.status == ComplianceStatus.COMPLIANT)

    @property
    def non_compliant_count(self) -> int:
        return sum(1 for r in self.compliance_results if r.status == ComplianceStatus.NON_COMPLIANT)

    @property
    def partial_count(self) -> int:
        return sum(1 for r in self.compliance_results if r.status == ComplianceStatus.PARTIAL)


class PolicyEvaluator:
    
    def __init__(self, provider: AIProvider):
        self._provider = provider

    async def evaluate(
        self,
        document_content: str,
        policy_rules: list[PolicyRule],
        options: AnalysisOptions | None = None,
    ) -> PolicyEvaluationResult:
        options = options or AnalysisOptions()
        
        try:
            result = await self._provider.analyze_document(
                content=document_content,
                policy_rules=policy_rules,
                options=options,
            )
            
            if not result.success:
                return PolicyEvaluationResult(
                    success=False,
                    compliance_results=[],
                    overall_score=0.0,
                    critical_gaps=[],
                    summary="Policy evaluation failed",
                    errors=result.errors,
                )
            
            compliance_results = self._convert_issues_to_compliance(result.issues, policy_rules)
            overall_score = self._calculate_overall_score(compliance_results, policy_rules)
            critical_gaps = self._identify_critical_gaps(compliance_results)
            
            return PolicyEvaluationResult(
                success=True,
                compliance_results=compliance_results,
                overall_score=overall_score,
                critical_gaps=critical_gaps,
                summary=result.summary,
            )
            
        except Exception as e:
            return PolicyEvaluationResult(
                success=False,
                compliance_results=[],
                overall_score=0.0,
                critical_gaps=[],
                summary="",
                errors=[str(e)],
            )

    def _convert_issues_to_compliance(
        self,
        issues: list,
        policy_rules: list[PolicyRule],
    ) -> list[ComplianceResult]:
        rule_issues: dict[str, list] = {}
        for issue in issues:
            rule_id = issue.rule_id
            if rule_id not in rule_issues:
                rule_issues[rule_id] = []
            rule_issues[rule_id].append(issue)
        
        compliance_results = []
        for rule in policy_rules:
            rule_id = rule.id
            issues_for_rule = rule_issues.get(rule_id, [])
            
            if not issues_for_rule:
                status = ComplianceStatus.COMPLIANT
                evidence = "No issues found for this rule"
                gaps = []
                remediation = "N/A"
                confidence = 0.8
            else:
                critical_issues = [i for i in issues_for_rule if i.severity.value in ("critical", "high")]
                if critical_issues:
                    status = ComplianceStatus.NON_COMPLIANT
                else:
                    status = ComplianceStatus.PARTIAL
                
                evidence = "; ".join([i.original_text for i in issues_for_rule[:3]])
                gaps = [i.description for i in issues_for_rule]
                remediation = "; ".join([i.title for i in issues_for_rule])
                confidence = sum(i.confidence for i in issues_for_rule) / len(issues_for_rule)
            
            result = ComplianceResult.create(
                rule_id=rule_id,
                rule_name=rule.name,
                status=status,
                evidence=evidence,
                location=issues_for_rule[0].location if issues_for_rule else "N/A",
                gaps=gaps,
                remediation=remediation,
                confidence=confidence,
            )
            compliance_results.append(result)
        
        return compliance_results

    def _calculate_overall_score(
        self,
        compliance_results: list[ComplianceResult],
        policy_rules: list[PolicyRule],
    ) -> float:
        if not compliance_results:
            return 1.0
        
        weights = {"MUST": 3.0, "SHOULD": 2.0, "MAY": 1.0}
        rule_weights = {r.id: weights.get(r.requirement_type, 1.0) for r in policy_rules}
        
        total_weight = 0.0
        weighted_score = 0.0
        
        for result in compliance_results:
            weight = rule_weights.get(result.rule_id, 1.0)
            total_weight += weight
            
            if result.status == ComplianceStatus.COMPLIANT:
                weighted_score += weight * 1.0
            elif result.status == ComplianceStatus.PARTIAL:
                weighted_score += weight * 0.5
            elif result.status == ComplianceStatus.NOT_APPLICABLE:
                total_weight -= weight
        
        return weighted_score / total_weight if total_weight > 0 else 1.0

    def _identify_critical_gaps(self, compliance_results: list[ComplianceResult]) -> list[str]:
        critical_gaps = []
        for result in compliance_results:
            if result.status == ComplianceStatus.NON_COMPLIANT:
                for gap in result.gaps[:2]:
                    critical_gaps.append(f"{result.rule_name}: {gap}")
        return critical_gaps[:5]
