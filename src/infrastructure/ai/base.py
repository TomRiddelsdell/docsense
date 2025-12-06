from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class ProviderType(Enum):
    GEMINI = "gemini"
    OPENAI = "openai"
    CLAUDE = "claude"


class IssueSeverity(Enum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


@dataclass(frozen=True)
class PolicyRule:
    id: str
    name: str
    description: str
    requirement_type: str
    category: str
    validation_criteria: str
    examples: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PolicyRule":
        return cls(
            id=data["id"],
            name=data["name"],
            description=data["description"],
            requirement_type=data.get("requirement_type", "SHOULD"),
            category=data.get("category", "general"),
            validation_criteria=data.get("validation_criteria", ""),
            examples=data.get("examples", []),
        )


@dataclass
class AnalysisOptions:
    include_suggestions: bool = True
    max_issues: int = 50
    severity_threshold: IssueSeverity = IssueSeverity.INFO
    focus_sections: list[str] = field(default_factory=list)
    model_name: str | None = None
    temperature: float = 0.3
    extra_context: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "include_suggestions": self.include_suggestions,
            "max_issues": self.max_issues,
            "severity_threshold": self.severity_threshold.value,
            "focus_sections": self.focus_sections,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "extra_context": self.extra_context,
        }


@dataclass
class Issue:
    id: UUID
    rule_id: str
    severity: IssueSeverity
    title: str
    description: str
    location: str
    original_text: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @classmethod
    def create(
        cls,
        rule_id: str,
        severity: IssueSeverity,
        title: str,
        description: str,
        location: str,
        original_text: str,
        confidence: float,
    ) -> "Issue":
        return cls(
            id=uuid4(),
            rule_id=rule_id,
            severity=severity,
            title=title,
            description=description,
            location=location,
            original_text=original_text,
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "rule_id": self.rule_id,
            "severity": self.severity.value,
            "title": self.title,
            "description": self.description,
            "location": self.location,
            "original_text": self.original_text,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class Suggestion:
    id: UUID
    issue_id: UUID
    suggested_text: str
    explanation: str
    confidence: float
    created_at: datetime = field(default_factory=datetime.utcnow)

    def __post_init__(self):
        if not 0.0 <= self.confidence <= 1.0:
            raise ValueError(f"Confidence must be between 0.0 and 1.0, got {self.confidence}")

    @classmethod
    def create(
        cls,
        issue_id: UUID,
        suggested_text: str,
        explanation: str,
        confidence: float,
    ) -> "Suggestion":
        return cls(
            id=uuid4(),
            issue_id=issue_id,
            suggested_text=suggested_text,
            explanation=explanation,
            confidence=confidence,
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "issue_id": str(self.issue_id),
            "suggested_text": self.suggested_text,
            "explanation": self.explanation,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class AnalysisResult:
    success: bool
    issues: list[Issue]
    suggestions: list[Suggestion]
    summary: str
    processing_time_ms: int
    model_used: str
    token_count: int = 0
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "success": self.success,
            "issues": [issue.to_dict() for issue in self.issues],
            "suggestions": [suggestion.to_dict() for suggestion in self.suggestions],
            "summary": self.summary,
            "processing_time_ms": self.processing_time_ms,
            "model_used": self.model_used,
            "token_count": self.token_count,
            "errors": self.errors,
        }

    @property
    def issue_count(self) -> int:
        return len(self.issues)

    @property
    def critical_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.severity == IssueSeverity.CRITICAL]

    @property
    def high_severity_issues(self) -> list[Issue]:
        return [i for i in self.issues if i.severity in (IssueSeverity.CRITICAL, IssueSeverity.HIGH)]


class AIProvider(ABC):
    
    @property
    @abstractmethod
    def provider_type(self) -> ProviderType:
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        pass

    @property
    @abstractmethod
    def available_models(self) -> list[str]:
        pass

    @abstractmethod
    async def analyze_document(
        self,
        content: str,
        policy_rules: list[PolicyRule],
        options: AnalysisOptions | None = None,
    ) -> AnalysisResult:
        pass

    @abstractmethod
    async def generate_suggestion(
        self,
        issue: Issue,
        document_context: str,
        policy_rule: PolicyRule,
    ) -> Suggestion:
        pass

    @abstractmethod
    async def is_available(self) -> bool:
        pass

    def validate_model(self, model_name: str | None) -> str:
        if model_name is None:
            return self.default_model
        if model_name not in self.available_models:
            raise ValueError(
                f"Model '{model_name}' not available for {self.provider_type.value}. "
                f"Available models: {self.available_models}"
            )
        return model_name
