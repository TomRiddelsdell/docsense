"""User queries for read model access."""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import asyncpg


@dataclass
class UserView:
    """Read model view for a user."""
    
    kerberos_id: str
    display_name: str
    email: str
    groups: List[str]
    roles: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class UserQueries:
    """Query service for user read models.
    
    Provides fast read access to user data from the users table.
    This is the read side of CQRS for User aggregates.
    """
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def get_by_kerberos_id(self, kerberos_id: str) -> Optional[UserView]:
        """Get user by Kerberos ID.
        
        Args:
            kerberos_id: 6-character Kerberos username
            
        Returns:
            UserView if found, None otherwise
        """
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT 
                    kerberos_id, display_name, email, groups, roles,
                    is_active, created_at, updated_at
                FROM users
                WHERE kerberos_id = $1
                """,
                kerberos_id
            )
        
        if row is None:
            return None
        
        return UserView(
            kerberos_id=row["kerberos_id"],
            display_name=row["display_name"],
            email=row["email"],
            groups=list(row["groups"]) if row["groups"] else [],
            roles=list(row["roles"]) if row["roles"] else [],
            is_active=row["is_active"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
    
    async def search_users(
        self,
        query: Optional[str] = None,
        active_only: bool = True,
        limit: int = 50
    ) -> List[UserView]:
        """Search for users.
        
        Searches across kerberos_id, display_name, and email fields.
        
        Args:
            query: Optional search term (searches kerberos_id, name, email)
            active_only: Only return active users
            limit: Maximum number of results
            
        Returns:
            List of matching UserView objects
        """
        async with self._pool.acquire() as conn:
            if query:
                # Search with query term
                rows = await conn.fetch(
                    """
                    SELECT 
                        kerberos_id, display_name, email, groups, roles,
                        is_active, created_at, updated_at
                    FROM users
                    WHERE ($1 = TRUE AND is_active = TRUE OR $1 = FALSE)
                    AND (
                        kerberos_id ILIKE $2
                        OR display_name ILIKE $2
                        OR email ILIKE $2
                    )
                    ORDER BY display_name
                    LIMIT $3
                    """,
                    active_only,
                    f"%{query}%",
                    limit
                )
            else:
                # Get all users (with optional active filter)
                rows = await conn.fetch(
                    """
                    SELECT 
                        kerberos_id, display_name, email, groups, roles,
                        is_active, created_at, updated_at
                    FROM users
                    WHERE ($1 = TRUE AND is_active = TRUE OR $1 = FALSE)
                    ORDER BY display_name
                    LIMIT $2
                    """,
                    active_only,
                    limit
                )
        
        return [
            UserView(
                kerberos_id=row["kerberos_id"],
                display_name=row["display_name"],
                email=row["email"],
                groups=list(row["groups"]) if row["groups"] else [],
                roles=list(row["roles"]) if row["roles"] else [],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
    
    async def get_users_by_group(
        self,
        group: str,
        active_only: bool = True,
        limit: int = 100
    ) -> List[UserView]:
        """Get all users in a specific group.
        
        Uses GIN index on groups array for fast lookups.
        
        Args:
            group: Group name to filter by
            active_only: Only return active users
            limit: Maximum number of results
            
        Returns:
            List of UserView objects in the group
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    kerberos_id, display_name, email, groups, roles,
                    is_active, created_at, updated_at
                FROM users
                WHERE $2 = ANY(groups)
                AND ($1 = TRUE AND is_active = TRUE OR $1 = FALSE)
                ORDER BY display_name
                LIMIT $3
                """,
                active_only,
                group,
                limit
            )
        
        return [
            UserView(
                kerberos_id=row["kerberos_id"],
                display_name=row["display_name"],
                email=row["email"],
                groups=list(row["groups"]) if row["groups"] else [],
                roles=list(row["roles"]) if row["roles"] else [],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
    
    async def get_users_by_role(
        self,
        role: str,
        active_only: bool = True,
        limit: int = 100
    ) -> List[UserView]:
        """Get all users with a specific role.
        
        Args:
            role: Role name to filter by (viewer, contributor, admin, auditor)
            active_only: Only return active users
            limit: Maximum number of results
            
        Returns:
            List of UserView objects with the role
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    kerberos_id, display_name, email, groups, roles,
                    is_active, created_at, updated_at
                FROM users
                WHERE $2 = ANY(roles)
                AND ($1 = TRUE AND is_active = TRUE OR $1 = FALSE)
                ORDER BY display_name
                LIMIT $3
                """,
                active_only,
                role,
                limit
            )
        
        return [
            UserView(
                kerberos_id=row["kerberos_id"],
                display_name=row["display_name"],
                email=row["email"],
                groups=list(row["groups"]) if row["groups"] else [],
                roles=list(row["roles"]) if row["roles"] else [],
                is_active=row["is_active"],
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]
