"""User repository for event-sourced User aggregates."""

from typing import Optional, Type, Set
from uuid import UUID, uuid5, NAMESPACE_DNS
import logging

from src.domain.aggregates.user import User
from src.infrastructure.repositories.base import Repository
from src.infrastructure.persistence.event_store import EventStore
from src.infrastructure.persistence.snapshot_store import SnapshotStore

logger = logging.getLogger(__name__)


def kerberos_id_to_uuid(kerberos_id: str) -> UUID:
    """Convert kerberos_id to deterministic UUID for event store.
    
    Uses UUID v5 (name-based with SHA-1 hash) to create a stable UUID
    from the kerberos_id string. Same kerberos_id always produces same UUID.
    
    Args:
        kerberos_id: 6-character Kerberos username
        
    Returns:
        UUID derived from kerberos_id
    """
    return uuid5(NAMESPACE_DNS, f"user.kerberos.{kerberos_id}")


class UserRepository(Repository[User]):
    """Repository for User aggregates using event sourcing.
    
    Supports auto-registration on first authentication via get_or_create_from_auth().
    User aggregate ID is the kerberos_id (6-character string).
    """
    
    def __init__(
        self,
        event_store: EventStore,
        snapshot_store: Optional[SnapshotStore] = None,
        snapshot_threshold: int = 10
    ):
        super().__init__(event_store, snapshot_store, snapshot_threshold)
    
    def _aggregate_type(self) -> Type[User]:
        return User
    
    def _aggregate_type_name(self) -> str:
        return "User"
    
    async def get_by_kerberos_id(self, kerberos_id: str) -> Optional[User]:
        """Get user by Kerberos ID.
        
        Args:
            kerberos_id: 6-character Kerberos username
            
        Returns:
            User aggregate if exists, None otherwise
        """
        # Convert kerberos_id to UUID for event store lookup
        aggregate_uuid = kerberos_id_to_uuid(kerberos_id)
        
        # Use base class get() method with UUID
        return await self.get(aggregate_uuid)
    
    async def get_or_create_from_auth(
        self,
        kerberos_id: str,
        groups: Set[str],
        display_name: str,
        email: str
    ) -> User:
        """Get existing user or auto-register on first authentication.
        
        Implements auto-registration flow:
        1. Try to load existing user from event store
        2. If not found, create new user via User.register()
        3. If found, sync groups if they changed since last login
        4. Save and return user
        
        Args:
            kerberos_id: 6-character Kerberos username
            groups: Set of group names from X-User-Groups header
            display_name: Display name from auth system
            email: Email from auth system
            
        Returns:
            User aggregate (newly created or existing)
        """
        # Try to load existing user
        user = await self.get_by_kerberos_id(kerberos_id)
        
        if user is None:
            # New user - auto-register
            logger.info(f"Auto-registering new user: {kerberos_id}")
            user = User.register(
                kerberos_id=kerberos_id,
                groups=groups,
                display_name=display_name,
                email=email
            )
            await self.save_user(user)
            return user
        
        # Existing user - sync groups if changed
        current_groups = user.groups
        if current_groups != groups:
            logger.info(
                f"Syncing groups for user {kerberos_id}: "
                f"{current_groups} -> {groups}"
            )
            user.sync_groups(groups)
            await self.save_user(user)
        
        return user
    
    async def save_user(self, user: User) -> None:
        """Save user aggregate.
        
        Note: We need to set the aggregate.id to the UUID derived from kerberos_id
        before saving, since the base Repository.save() expects aggregate.id to be set.
        
        Args:
            user: User aggregate to save
        """
        # Set the aggregate ID to the UUID derived from kerberos_id
        # This is required for the event store which uses UUIDs
        user._id = kerberos_id_to_uuid(user.kerberos_id)
        
        # Use base class save() method
        await self.save(user)
