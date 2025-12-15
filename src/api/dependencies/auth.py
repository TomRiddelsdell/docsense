"""Authentication dependencies for FastAPI."""

import logging
from typing import Callable

from fastapi import Depends, HTTPException, Request, status

from src.domain.aggregates.user import User
from src.domain.value_objects.user_role import UserRole
from src.infrastructure.repositories.user_repository import UserRepository
from src.api.dependencies import get_user_repository

logger = logging.getLogger(__name__)


async def get_current_user(
    request: Request,
    user_repo: UserRepository = Depends(get_user_repository)
) -> User:
    """Get current authenticated user from request state.
    
    Extracts Kerberos ID from request.state (set by KerberosAuthMiddleware),
    auto-registers user if first login, and returns User aggregate.
    
    Args:
        request: FastAPI request with state.kerberos_id set by middleware
        user_repo: UserRepository for loading/creating users
        
    Returns:
        User aggregate for authenticated user
        
    Raises:
        HTTPException 401: If no Kerberos ID in request state (not authenticated)
        HTTPException 403: If user account is deactivated
    """
    # Check if Kerberos ID is present (set by middleware)
    kerberos_id = getattr(request.state, "kerberos_id", None)
    if not kerberos_id:
        logger.warning(f"Unauthenticated request to {request.url.path}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. X-User-Kerberos header missing.",
            headers={"WWW-Authenticate": "Kerberos"},
        )
    
    # Get user groups and profile from request state
    user_groups = getattr(request.state, "user_groups", set())
    display_name = getattr(request.state, "display_name", kerberos_id)
    email = getattr(request.state, "email", f"{kerberos_id}@example.com")
    
    # Get or create user (auto-register on first authentication)
    try:
        user = await user_repo.get_or_create_from_auth(
            kerberos_id=kerberos_id,
            groups=user_groups,
            display_name=display_name,
            email=email
        )
    except Exception as e:
        logger.error(f"Failed to get/create user {kerberos_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to load user information"
        )
    
    # Check if user is active
    if not user.is_active:
        logger.warning(f"Inactive user attempted access: {kerberos_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User account is deactivated"
        )
    
    logger.debug(
        f"Authenticated user: {user.kerberos_id}, "
        f"groups={user.groups}, roles={user.roles}"
    )
    
    return user


def require_role(role: UserRole) -> Callable:
    """Dependency factory to require a specific role.
    
    Returns a dependency function that checks if the current user
    has the specified role. Raises 403 if user lacks the role.
    
    Args:
        role: UserRole to require
        
    Returns:
        Dependency function that validates role
        
    Example:
        @router.get("/admin/users")
        async def list_users(user: User = Depends(require_admin)):
            ...
    """
    async def _require_role(user: User = Depends(get_current_user)) -> User:
        if not user.has_role(role):
            logger.warning(
                f"User {user.kerberos_id} lacks required role: {role.value}"
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{role.value}' required for this operation"
            )
        return user
    
    return _require_role


# Convenience dependencies for common roles
require_admin = require_role(UserRole.ADMIN)
require_contributor = require_role(UserRole.CONTRIBUTOR)
require_viewer = require_role(UserRole.VIEWER)
require_auditor = require_role(UserRole.AUDITOR)
