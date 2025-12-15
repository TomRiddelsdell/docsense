"""Authentication API schemas."""

from typing import List, Set
from pydantic import BaseModel, Field, ConfigDict


class CurrentUserResponse(BaseModel):
    """Response model for GET /auth/me endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "kerberos_id": "jsmith",
                "display_name": "John Smith",
                "email": "john.smith@example.com",
                "groups": ["equity-trading", "risk-mgmt"],
                "roles": ["contributor"],
                "permissions": ["view", "edit", "share", "analyze", "export"],
                "is_active": True
            }
        }
    )
    
    kerberos_id: str = Field(..., description="6-character Kerberos username")
    display_name: str = Field(..., description="User's display name")
    email: str = Field(..., description="User's email address")
    groups: List[str] = Field(..., description="Groups user belongs to")
    roles: List[str] = Field(..., description="Roles assigned to user")
    permissions: List[str] = Field(..., description="Permissions user has")
    is_active: bool = Field(..., description="Whether user account is active")


class ShareDocumentRequest(BaseModel):
    """Request model for POST /documents/{id}/share endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "groups": ["equity-trading", "risk-mgmt"]
            }
        }
    )
    
    groups: List[str] = Field(..., description="Groups to share document with")


class ShareDocumentResponse(BaseModel):
    """Response model for POST /documents/{id}/share endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "visibility": "group",
                "shared_with_groups": ["equity-trading", "risk-mgmt"]
            }
        }
    )
    
    document_id: str = Field(..., description="Document ID")
    visibility: str = Field(..., description="Document visibility level")
    shared_with_groups: List[str] = Field(..., description="Groups document is shared with")


class MakePrivateResponse(BaseModel):
    """Response model for POST /documents/{id}/make-private endpoint."""
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "document_id": "123e4567-e89b-12d3-a456-426614174000",
                "visibility": "private",
                "shared_with_groups": []
            }
        }
    )
    
    document_id: str = Field(..., description="Document ID")
    visibility: str = Field(..., description="Document visibility level (private)")
    shared_with_groups: List[str] = Field(..., description="Groups document is shared with (empty)")
