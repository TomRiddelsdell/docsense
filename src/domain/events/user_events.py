"""Domain events for User aggregate."""

from dataclasses import dataclass, field
from typing import List

from .base import DomainEvent


@dataclass(frozen=True)
class UserRegistered(DomainEvent):
    """Event when a user is registered from Kerberos authentication.
    
    This event is raised when a user authenticates for the first time
    and their account is automatically created.
    """
    
    aggregate_type: str = field(default="User")
    kerberos_id: str = ""
    groups: List[str] = field(default_factory=list)
    display_name: str = ""
    email: str = ""
    initial_roles: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class UserGroupAdded(DomainEvent):
    """Event when a user is added to a group.
    
    Groups are typically synced from the authentication system
    (Kerberos headers) on each login.
    """
    
    aggregate_type: str = field(default="User")
    group: str = ""


@dataclass(frozen=True)
class UserGroupRemoved(DomainEvent):
    """Event when a user is removed from a group.
    
    This occurs when group membership changes in the authentication system.
    """
    
    aggregate_type: str = field(default="User")
    group: str = ""


@dataclass(frozen=True)
class UserRoleGranted(DomainEvent):
    """Event when a role is granted to a user.
    
    Roles control what permissions the user has in the system.
    """
    
    aggregate_type: str = field(default="User")
    role: str = ""


@dataclass(frozen=True)
class UserRoleRevoked(DomainEvent):
    """Event when a role is revoked from a user."""
    
    aggregate_type: str = field(default="User")
    role: str = ""


@dataclass(frozen=True)
class UserDeactivated(DomainEvent):
    """Event when a user account is deactivated.
    
    Deactivated users cannot authenticate or access the system.
    """
    
    aggregate_type: str = field(default="User")
    reason: str = ""


@dataclass(frozen=True)
class UserReactivated(DomainEvent):
    """Event when a deactivated user account is reactivated."""
    
    aggregate_type: str = field(default="User")
