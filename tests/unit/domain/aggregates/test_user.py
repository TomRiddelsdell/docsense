"""Tests for User aggregate."""

import pytest

from src.domain.aggregates.user import User
from src.domain.events.user_events import (
    UserDeactivated,
    UserGroupAdded,
    UserGroupRemoved,
    UserReactivated,
    UserRegistered,
    UserRoleGranted,
    UserRoleRevoked,
)
from src.domain.value_objects.user_role import UserRole


class TestUserAggregate:
    """Tests for User aggregate behavior."""
    
    def test_register_creates_user_with_valid_kerberos_id(self):
        """Test that register creates a user with valid 6-character Kerberos ID."""
        user = User.register(
            kerberos_id="jsmith",
            groups=["equity-trading", "risk-mgmt"],
            display_name="John Smith",
            email="john.smith@example.com"
        )
        
        assert user.kerberos_id == "jsmith"
        assert user.display_name == "John Smith"
        assert user.email == "john.smith@example.com"
        assert user.groups == {"equity-trading", "risk-mgmt"}
        assert user.is_active is True
        assert len(user.pending_events) == 1
        
        event = user.pending_events[0]
        assert isinstance(event, UserRegistered)
        assert event.kerberos_id == "jsmith"
        assert event.groups == ["equity-trading", "risk-mgmt"]
        assert event.display_name == "John Smith"
        assert event.email == "john.smith@example.com"
        assert event.initial_roles == []  # No default role
    
    def test_register_rejects_invalid_kerberos_id(self):
        """Test that register raises ValueError for non-6-character Kerberos ID."""
        with pytest.raises(ValueError, match="Kerberos ID must be 6 characters"):
            User.register(kerberos_id="short", groups=[])
        
        with pytest.raises(ValueError, match="Kerberos ID must be 6 characters"):
            User.register(kerberos_id="toolongid", groups=[])
    
    def test_add_to_group(self):
        """Test adding user to a group."""
        user = User.register(kerberos_id="jsmith", groups=["group1"])
        user.clear_pending_events()
        
        user.add_to_group("group2")
        
        assert "group2" in user.groups
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserGroupAdded)
        assert event.group == "group2"
    
    def test_add_to_group_idempotent(self):
        """Test adding user to same group twice is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=["group1"])
        user.clear_pending_events()
        
        user.add_to_group("group1")
        
        # No new event should be raised
        assert len(user.pending_events) == 0
    
    def test_remove_from_group(self):
        """Test removing user from a group."""
        user = User.register(kerberos_id="jsmith", groups=["group1", "group2"])
        user.clear_pending_events()
        
        user.remove_from_group("group1")
        
        assert "group1" not in user.groups
        assert "group2" in user.groups
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserGroupRemoved)
        assert event.group == "group1"
    
    def test_remove_from_group_idempotent(self):
        """Test removing user from non-member group is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=["group1"])
        user.clear_pending_events()
        
        user.remove_from_group("group2")
        
        # No event should be raised
        assert len(user.pending_events) == 0
    
    def test_sync_groups_adds_new_groups(self):
        """Test sync_groups adds newly assigned groups."""
        user = User.register(kerberos_id="jsmith", groups=["group1"])
        user.clear_pending_events()
        
        user.sync_groups(["group1", "group2", "group3"])
        
        assert user.groups == {"group1", "group2", "group3"}
        assert len(user.pending_events) == 2
        # Should have added group2 and group3
        group_adds = [e for e in user.pending_events if isinstance(e, UserGroupAdded)]
        assert len(group_adds) == 2
        added_groups = {e.group for e in group_adds}
        assert added_groups == {"group2", "group3"}
    
    def test_sync_groups_removes_old_groups(self):
        """Test sync_groups removes groups user is no longer in."""
        user = User.register(kerberos_id="jsmith", groups=["group1", "group2", "group3"])
        user.clear_pending_events()
        
        user.sync_groups(["group1"])
        
        assert user.groups == {"group1"}
        assert len(user.pending_events) == 2
        # Should have removed group2 and group3
        group_removes = [e for e in user.pending_events if isinstance(e, UserGroupRemoved)]
        assert len(group_removes) == 2
        removed_groups = {e.group for e in group_removes}
        assert removed_groups == {"group2", "group3"}
    
    def test_grant_role(self):
        """Test granting a role to user."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.clear_pending_events()
        
        user.grant_role(UserRole.ADMIN)
        
        assert UserRole.ADMIN in user.roles
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserRoleGranted)
        assert event.role == UserRole.ADMIN.value
    
    def test_grant_role_idempotent(self):
        """Test granting same role twice is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.grant_role(UserRole.ADMIN)
        user.clear_pending_events()
        
        user.grant_role(UserRole.ADMIN)
        
        # No new event
        assert len(user.pending_events) == 0
    
    def test_revoke_role(self):
        """Test revoking a role from user."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.grant_role(UserRole.ADMIN)
        user.clear_pending_events()
        
        user.revoke_role(UserRole.ADMIN)
        
        assert UserRole.ADMIN not in user.roles
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserRoleRevoked)
        assert event.role == UserRole.ADMIN.value
    
    def test_revoke_role_idempotent(self):
        """Test revoking non-held role is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.clear_pending_events()
        
        user.revoke_role(UserRole.ADMIN)
        
        # No event
        assert len(user.pending_events) == 0
    
    def test_has_role_returns_true_for_held_role(self):
        """Test has_role returns True for roles user has."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.grant_role(UserRole.CONTRIBUTOR)
        
        # User has CONTRIBUTOR role after granting
        assert user.has_role(UserRole.CONTRIBUTOR) is True
        assert user.has_role(UserRole.ADMIN) is False
    
    def test_has_role_admin_implies_all_roles(self):
        """Test has_role returns True for any role if user is ADMIN."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.grant_role(UserRole.ADMIN)
        
        # Admin has all roles
        assert user.has_role(UserRole.VIEWER) is True
        assert user.has_role(UserRole.CONTRIBUTOR) is True
        assert user.has_role(UserRole.ADMIN) is True
        assert user.has_role(UserRole.AUDITOR) is True
    
    def test_in_group_returns_true_for_member_group(self):
        """Test in_group returns True for groups user belongs to."""
        user = User.register(kerberos_id="jsmith", groups=["equity-trading"])
        
        assert user.in_group("equity-trading") is True
        assert user.in_group("fixed-income") is False
    
    def test_deactivate_user(self):
        """Test deactivating a user account."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.clear_pending_events()
        
        user.deactivate(reason="User left company")
        
        assert user.is_active is False
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserDeactivated)
        assert event.reason == "User left company"
    
    def test_deactivate_idempotent(self):
        """Test deactivating already inactive user is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.deactivate()
        user.clear_pending_events()
        
        user.deactivate()
        
        # No new event
        assert len(user.pending_events) == 0
    
    def test_reactivate_user(self):
        """Test reactivating a deactivated user account."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.deactivate()
        user.clear_pending_events()
        
        user.reactivate()
        
        assert user.is_active is True
        assert len(user.pending_events) == 1
        event = user.pending_events[0]
        assert isinstance(event, UserReactivated)
    
    def test_reactivate_idempotent(self):
        """Test reactivating already active user is idempotent."""
        user = User.register(kerberos_id="jsmith", groups=[])
        user.clear_pending_events()
        
        user.reactivate()
        
        # No new event
        assert len(user.pending_events) == 0
    
    def test_reconstitute_from_events(self):
        """Test rebuilding user from event history."""
        events = [
            UserRegistered(
                aggregate_id="jsmith",
                kerberos_id="jsmith",
                groups=["group1"],
                display_name="John Smith",
                email="john@example.com",
                initial_roles=[UserRole.CONTRIBUTOR.value]
            ),
            UserGroupAdded(
                aggregate_id="jsmith",
                group="group2"
            ),
            UserRoleGranted(
                aggregate_id="jsmith",
                role=UserRole.ADMIN.value
            ),
        ]
        
        user = User.reconstitute(events)
        
        assert user.kerberos_id == "jsmith"
        assert user.display_name == "John Smith"
        assert user.email == "john@example.com"
        assert user.groups == {"group1", "group2"}
        assert UserRole.CONTRIBUTOR in user.roles
        assert UserRole.ADMIN in user.roles
        assert user.version == 3
        assert len(user.pending_events) == 0


class TestUserRole:
    """Tests for UserRole enum."""
    
    def test_user_role_values(self):
        """Test UserRole enum has expected values."""
        assert UserRole.VIEWER.value == "viewer"
        assert UserRole.CONTRIBUTOR.value == "contributor"
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.AUDITOR.value == "auditor"
    
    def test_from_string_valid(self):
        """Test from_string converts valid strings to roles."""
        assert UserRole.from_string("viewer") == UserRole.VIEWER
        assert UserRole.from_string("CONTRIBUTOR") == UserRole.CONTRIBUTOR
        assert UserRole.from_string("Admin") == UserRole.ADMIN
    
    def test_from_string_invalid(self):
        """Test from_string raises ValueError for invalid strings."""
        with pytest.raises(ValueError, match="Invalid role 'invalid'"):
            UserRole.from_string("invalid")
