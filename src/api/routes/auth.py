"""Authentication API routes."""

import logging
from fastapi import APIRouter, Depends

from src.domain.aggregates.user import User
from src.domain.services.authorization_service import AuthorizationService
from src.api.dependencies.auth import get_current_user
from src.api.dependencies import get_authorization_service
from src.api.schemas.auth import CurrentUserResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.get("/me", response_model=CurrentUserResponse)
async def get_current_user_info(
    user: User = Depends(get_current_user),
    auth_service: AuthorizationService = Depends(get_authorization_service)
) -> CurrentUserResponse:
    """Get current authenticated user information.
    
    Returns the authenticated user's profile including:
    - Kerberos ID and display info
    - Groups from authentication system
    - Assigned roles
    - Computed permissions (based on roles)
    - Account activation status
    
    This endpoint is useful for:
    - Displaying user info in UI header
    - Checking user permissions client-side
    - Debugging authentication issues
    
    Args:
        user: Current authenticated user (from dependency)
        auth_service: Authorization service (from dependency)
        
    Returns:
        CurrentUserResponse with user profile and permissions
    """
    # Get all permissions for user's roles
    permissions = auth_service.get_user_permissions(user)
    
    return CurrentUserResponse(
        kerberos_id=user.kerberos_id,
        display_name=user.display_name,
        email=user.email,
        groups=list(user.groups),
        roles=[role.value for role in user.roles],
        permissions=[perm.value for perm in permissions],
        is_active=user.is_active
    )
