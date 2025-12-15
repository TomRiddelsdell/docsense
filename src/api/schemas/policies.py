from datetime import datetime
from typing import Optional, List
from uuid import UUID

from pydantic import BaseModel, Field, ConfigDict


class ValidationRuleCreate(BaseModel):
    rule_type: str = Field(..., pattern="^(section_required|content_pattern|format_check|ai_evaluation)$")
    pattern: str
    error_message: Optional[str] = None


class ValidationRule(ValidationRuleCreate):
    id: UUID


class PolicyCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    requirement_type: str = Field(..., pattern="^(must|should|may)$")
    validation_rules: Optional[List[ValidationRuleCreate]] = None
    ai_prompt_template: Optional[str] = None


class PolicyUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=2000)
    requirement_type: Optional[str] = Field(None, pattern="^(must|should|may)$")
    validation_rules: Optional[List[ValidationRuleCreate]] = None
    ai_prompt_template: Optional[str] = None


class PolicyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    repository_id: UUID
    name: str
    description: Optional[str] = None
    requirement_type: str
    validation_rules: Optional[List[ValidationRule]] = None
    ai_prompt_template: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class PolicyListResponse(BaseModel):
    policies: List[PolicyResponse]
    total: int


class PolicyRepositoryCreate(BaseModel):
    name: str = Field(..., max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class PolicyRepositoryUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = Field(None, max_length=1000)


class PolicyRepositorySummary(BaseModel):
    id: UUID
    name: str


class PolicyRepositoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: UUID
    name: str
    description: Optional[str] = None
    policy_count: int = 0
    document_count: int = 0
    created_at: datetime
    updated_at: datetime


class PolicyRepositoryListResponse(BaseModel):
    repositories: List[PolicyRepositoryResponse]
    total: int


class RequirementCounts(BaseModel):
    total: int
    passed: int
    failed: int


class ComplianceViolation(BaseModel):
    policy_id: UUID
    policy_name: str
    requirement_type: str
    message: str
    section_reference: Optional[str] = None


class ComplianceStatusResponse(BaseModel):
    document_id: UUID
    policy_repository: Optional[PolicyRepositorySummary] = None
    status: str
    must_requirements: Optional[RequirementCounts] = None
    should_requirements: Optional[RequirementCounts] = None
    violations: Optional[List[ComplianceViolation]] = None
    checked_at: datetime
