"""User aggregate for authentication and authorization."""

from typing import List, Set

from ..events.base import DomainEvent
from ..events.user_events import (
    UserDeactivated,
    UserGroupAdded,
    UserGroupRemoved,
    UserReactivated,
    UserRegistered,
    UserRoleGranted,
    UserRoleRevoked,
)
from ..value_objects.user_role import UserRole
from .base import Aggregate


class User(Aggregate):
    """User aggregate representing an authenticated user.
    
    Users are identified by their Kerberos ID (6-character string)
    and belong to groups provided by the authentication system.
    Users have roles that determine their permissions in the system.
    
    Attributes:
        _kerberos_id: 6-character Kerberos identifier
        _groups: Set of group names the user belongs to
        _roles: Set of UserRole enums
        _display_name: Human-readable name
        _email: User's email address
        _is_active: Whether the account is active
    """
    
    def __init__(self, kerberos_id: str, aggregate_id=None):
        """Initialize User aggregate.
        
        Args:
            kerberos_id: 6-character Kerberos identifier
            aggregate_id: Optional UUID for the aggregate (generated from kerberos_id if not provided)
        """
        # If aggregate_id not provided, use kerberos_id (will be converted to UUID by repository)
        super().__init__(aggregate_id if aggregate_id is not None else kerberos_id)
        self._kerberos_id = kerberos_id
        self._groups: Set[str] = set()
        self._roles: Set[UserRole] = {UserRole.VIEWER}
        self._display_name: str = ""
        self._email: str = ""
        self._is_active: bool = True
    
    @property
    def kerberos_id(self) -> str:
        """Get the user's Kerberos ID."""
        return self._kerberos_id
    
    @property
    def groups(self) -> Set[str]:
        """Get the user's groups."""
        return self._groups.copy()
    
    @property
    def roles(self) -> Set[UserRole]:
        """Get the user's roles."""
        return self._roles.copy()
    
    @property
    def display_name(self) -> str:
        """Get the user's display name."""
        return self._display_name
    
    @property
    def email(self) -> str:
        """Get the user's email."""
        return self._email
    
    @property
    def is_active(self) -> bool:
        """Check if the user account is active."""
        return self._is_active
    
    @classmethod
    def register(
        cls,
        kerberos_id: str,
        groups: List[str],
        display_name: str = "",
        email: str = "",
        aggregate_id=None
    ) -> "User":
        """Register a new user from Kerberos authentication.
        
        Args:
            kerberos_id: 6-character Kerberos identifier
            groups: List of group names
            display_name: Human-readable name
            email: User's email address
            
        Returns:
            New User aggregate instance
            
        Raises:
            ValueError: If kerberos_id is not 6 characters
        """
        if len(kerberos_id) != 6:
            raise ValueError(
                f"Kerberos ID must be 6 characters, got {len(kerberos_id)}: '{kerberos_id}'"
            )
        
        user = cls(kerberos_id, aggregate_id=aggregate_id)
        user._apply_event(UserRegistered(
            aggregate_id=user.id,  # Use the aggregate's ID (will be UUID if provided, kerberos_id otherwise)
            kerberos_id=kerberos_id,
            groups=groups,
            display_name=display_name,
            email=email,
            initial_roles=[]  # No default role - must be explicitly granted
        ))
        return user
    
    def add_to_group(self, group: str) -> None:
        """Add user to a group.
        
        Args:
            group: Group name to add
        """
        if group not in self._groups:
            self._apply_event(UserGroupAdded(
                aggregate_id=self.id,
                group=group
            ))
    
    def remove_from_group(self, group: str) -> None:
        """Remove user from a group.
        
        Args:
            group: Group name to remove
        """
        if group in self._groups:
            self._apply_event(UserGroupRemoved(
                aggregate_id=self.id,
                group=group
            ))
    
    def sync_groups(self, new_groups: List[str]) -> None:
        """Synchronize user's groups with authentication system.
        
        This compares current groups with new groups and raises
        appropriate events for additions and removals.
        
        Args:
            new_groups: Current groups from authentication system
        """
        current = self._groups
        new = set(new_groups)
        
        # Add new groups
        for group in new - current:
            self.add_to_group(group)
        
        # Remove old groups
        for group in current - new:
            self.remove_from_group(group)
    
    def grant_role(self, role: UserRole) -> None:
        """Grant a role to the user.
        
        Args:
            role: Role to grant
        """
        if role not in self._roles:
            self._apply_event(UserRoleGranted(
                aggregate_id=self.id,
                role=role.value
            ))
    
    def revoke_role(self, role: UserRole) -> None:
        """Revoke a role from the user.
        
        Args:
            role: Role to revoke
        """
        if role in self._roles:
            self._apply_event(UserRoleRevoked(
                aggregate_id=self.id,
                role=role.value
            ))
    
    def has_role(self, role: UserRole) -> bool:
        """Check if user has a specific role.
        
        ADMIN role implies all permissions, so always returns True
        for admins regardless of the role being checked.
        
        Args:
            role: Role to check
            
        Returns:
            True if user has the role or is an ADMIN
        """
        return role in self._roles or UserRole.ADMIN in self._roles
    
    def in_group(self, group: str) -> bool:
        """Check if user is in a specific group.
        
        Args:
            group: Group name to check
            
        Returns:
            True if user is in the group
        """
        return group in self._groups
    
    def deactivate(self, reason: str = "") -> None:
        """Deactivate the user account.
        
        Args:
            reason: Optional reason for deactivation
        """
        if self._is_active:
            self._apply_event(UserDeactivated(
                aggregate_id=self.id,
                reason=reason
            ))
    
    def reactivate(self) -> None:
        """Reactivate a deactivated user account."""
        if not self._is_active:
            self._apply_event(UserReactivated(
                aggregate_id=self.id
            ))
    
    def _when(self, event: DomainEvent) -> None:
        """Apply events to aggregate state.
        
        Args:
            event: Domain event to apply
        """
        match event:
            case UserRegistered():
                self._kerberos_id = event.kerberos_id
                self._groups = set(event.groups)
                self._roles = {UserRole.from_string(r) for r in event.initial_roles}
                self._display_name = event.display_name
                self._email = event.email
                self._is_active = True
            
            case UserGroupAdded():
                self._groups.add(event.group)
            
            case UserGroupRemoved():
                self._groups.discard(event.group)
            
            case UserRoleGranted():
                self._roles.add(UserRole.from_string(event.role))
            
            case UserRoleRevoked():
                self._roles.discard(UserRole.from_string(event.role))
            
            case UserDeactivated():
                self._is_active = False
            
            case UserReactivated():
                self._is_active = True
