from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class Parameter(BaseModel):
    id: str = Field(..., description="Unique identifier for the parameter")
    name: str = Field(..., description="Parameter name")
    description: Optional[str] = Field(None, description="Parameter description")
    type: str = Field(..., description="Parameter type (e.g., numeric, percentage, text)")
    value: Optional[str] = Field(None, description="Parameter value if specified")
    dependencies: list[str] = Field(default_factory=list, description="IDs of parameters this depends on")
    section: Optional[str] = Field(None, description="Document section where parameter is found")


class ParametersResponse(BaseModel):
    document_id: UUID
    parameters: list[Parameter]
    total: int
