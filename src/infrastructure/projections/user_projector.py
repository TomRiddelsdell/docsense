"""User projection for maintaining users read model."""

import logging
from typing import List, Type

import asyncpg

from src.domain.events import DomainEvent
from src.domain.events.user_events import (
    UserRegistered,
    UserGroupAdded,
    UserGroupRemoved,
    UserRoleGranted,
    UserRoleRevoked,
    UserDeactivated,
    UserReactivated,
)
from src.infrastructure.projections.base import Projection

logger = logging.getLogger(__name__)


class UserProjection(Projection):
    """Projection that maintains the users read model table.
    
    Handles User aggregate events and updates the users table
    for fast query access. The users table is the read model
    for authenticated user information.
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    def handles(self) -> List[Type[DomainEvent]]:
        """Return list of event types this projection handles."""
        return [
            UserRegistered,
            UserGroupAdded,
            UserGroupRemoved,
            UserRoleGranted,
            UserRoleRevoked,
            UserDeactivated,
            UserReactivated,
        ]
    
    async def handle(self, event: DomainEvent) -> None:
        """Handle a domain event and update read model."""
        logger.info(
            f"UserProjection handling event: {event.event_type}, "
            f"aggregate_id: {event.aggregate_id}"
        )
        
        if isinstance(event, UserRegistered):
            await self._handle_registered(event)
        elif isinstance(event, UserGroupAdded):
            await self._handle_group_added(event)
        elif isinstance(event, UserGroupRemoved):
            await self._handle_group_removed(event)
        elif isinstance(event, UserRoleGranted):
            await self._handle_role_granted(event)
        elif isinstance(event, UserRoleRevoked):
            await self._handle_role_revoked(event)
        elif isinstance(event, UserDeactivated):
            await self._handle_deactivated(event)
        elif isinstance(event, UserReactivated):
            await self._handle_reactivated(event)
        
        logger.info(
            f"UserProjection successfully handled event: {event.event_type}"
        )
    
    async def _handle_registered(self, event: UserRegistered) -> None:
        """Handle UserRegistered event - insert new user."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO users 
                (kerberos_id, display_name, email, groups, roles, is_active, created_at, updated_at)
                VALUES ($1, $2, $3, $4, $5, TRUE, $6, $6)
                ON CONFLICT (kerberos_id) DO UPDATE
                SET 
                    display_name = EXCLUDED.display_name,
                    email = EXCLUDED.email,
                    groups = EXCLUDED.groups,
                    roles = EXCLUDED.roles,
                    updated_at = EXCLUDED.updated_at
                """,
                event.kerberos_id,
                event.display_name,
                event.email,
                event.groups,
                event.initial_roles,
                event.occurred_at,
            )
    
    async def _handle_group_added(self, event: UserGroupAdded) -> None:
        """Handle UserGroupAdded event - add group to user's groups array."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    groups = array_append(groups, $2),
                    updated_at = $3
                WHERE kerberos_id = $1
                AND NOT ($2 = ANY(groups))
                """,
                event.aggregate_id,
                event.group,
                event.occurred_at,
            )
    
    async def _handle_group_removed(self, event: UserGroupRemoved) -> None:
        """Handle UserGroupRemoved event - remove group from user's groups array."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    groups = array_remove(groups, $2),
                    updated_at = $3
                WHERE kerberos_id = $1
                """,
                event.aggregate_id,
                event.group,
                event.occurred_at,
            )
    
    async def _handle_role_granted(self, event: UserRoleGranted) -> None:
        """Handle UserRoleGranted event - add role to user's roles array."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    roles = array_append(roles, $2),
                    updated_at = $3
                WHERE kerberos_id = $1
                AND NOT ($2 = ANY(roles))
                """,
                event.aggregate_id,
                event.role,
                event.occurred_at,
            )
    
    async def _handle_role_revoked(self, event: UserRoleRevoked) -> None:
        """Handle UserRoleRevoked event - remove role from user's roles array."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    roles = array_remove(roles, $2),
                    updated_at = $3
                WHERE kerberos_id = $1
                """,
                event.aggregate_id,
                event.role,
                event.occurred_at,
            )
    
    async def _handle_deactivated(self, event: UserDeactivated) -> None:
        """Handle UserDeactivated event - set is_active to FALSE."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    is_active = FALSE,
                    updated_at = $2
                WHERE kerberos_id = $1
                """,
                event.aggregate_id,
                event.occurred_at,
            )
    
    async def _handle_reactivated(self, event: UserReactivated) -> None:
        """Handle UserReactivated event - set is_active to TRUE."""
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                UPDATE users
                SET 
                    is_active = TRUE,
                    updated_at = $2
                WHERE kerberos_id = $1
                """,
                event.aggregate_id,
                event.occurred_at,
            )
