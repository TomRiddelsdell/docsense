"""Audit logging infrastructure for Phase 13.

Records all document access attempts (successful and denied) for security audit trail.
Implements requirements from ADR-021 for complete access logging.
"""

import logging
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

import asyncpg

logger = logging.getLogger(__name__)


class AuditLogger:
    """Service for logging document access attempts.
    
    Logs all access attempts to the access_audit_log table for security
    audit trail and compliance requirements.
    
    Logged information:
    - User identity (Kerberos ID)
    - Document accessed
    - Action performed (view, edit, share, delete)
    - Result (allowed, denied)
    - Reason for denial (if denied)
    - IP address and user agent
    - Timestamp
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        """Initialize audit logger with database connection pool.
        
        Args:
            db_pool: PostgreSQL connection pool
        """
        self._pool = db_pool
    
    async def log_access(
        self,
        user_kerberos_id: str,
        document_id: UUID,
        action: str,
        result: str,
        reason: Optional[str] = None,
        ip_address: Optional[str] = None,
        user_agent: Optional[str] = None,
    ) -> None:
        """Log a document access attempt.
        
        Args:
            user_kerberos_id: User's Kerberos ID
            document_id: UUID of document accessed
            action: Action performed (view, edit, share, delete, export, download)
            result: Result of access (allowed, denied)
            reason: Reason for denial (if denied)
            ip_address: Client IP address
            user_agent: Client user agent string
        """
        try:
            async with self._pool.acquire() as conn:
                await conn.execute(
                    """
                    INSERT INTO access_audit_log (
                        id,
                        user_kerberos_id,
                        document_id,
                        action,
                        result,
                        reason,
                        ip_address,
                        user_agent,
                        occurred_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    """,
                    uuid4(),
                    user_kerberos_id,
                    document_id,
                    action,
                    result,
                    reason,
                    ip_address,
                    user_agent,
                    datetime.utcnow(),
                )
            
            logger.debug(
                f"Audit log: user={user_kerberos_id}, document={document_id}, "
                f"action={action}, result={result}"
            )
        except Exception as e:
            # Log but don't fail the request if audit logging fails
            logger.error(f"Failed to write audit log: {e}", exc_info=True)
    
    async def get_document_audit_trail(
        self,
        document_id: UUID,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """Get audit trail for a specific document.
        
        Args:
            document_id: UUID of document
            limit: Maximum number of records to return
            offset: Offset for pagination
            
        Returns:
            List of audit log entries
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    user_kerberos_id,
                    document_id,
                    action,
                    result,
                    reason,
                    ip_address,
                    occurred_at
                FROM access_audit_log
                WHERE document_id = $1
                ORDER BY occurred_at DESC
                LIMIT $2 OFFSET $3
                """,
                document_id,
                limit,
                offset,
            )
            
            return [dict(row) for row in rows]
    
    async def get_user_audit_trail(
        self,
        user_kerberos_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> list[dict]:
        """Get audit trail for a specific user.
        
        Args:
            user_kerberos_id: User's Kerberos ID
            limit: Maximum number of records to return
            offset: Offset for pagination
            
        Returns:
            List of audit log entries
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    user_kerberos_id,
                    document_id,
                    action,
                    result,
                    reason,
                    ip_address,
                    occurred_at
                FROM access_audit_log
                WHERE user_kerberos_id = $1
                ORDER BY occurred_at DESC
                LIMIT $2 OFFSET $3
                """,
                user_kerberos_id,
                limit,
                offset,
            )
            
            return [dict(row) for row in rows]
    
    async def get_denied_access_attempts(
        self,
        hours: int = 24,
        limit: int = 100
    ) -> list[dict]:
        """Get recent denied access attempts for security monitoring.
        
        Args:
            hours: Number of hours to look back
            limit: Maximum number of records to return
            
        Returns:
            List of denied access attempts
        """
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT 
                    id,
                    user_kerberos_id,
                    document_id,
                    action,
                    reason,
                    ip_address,
                    occurred_at
                FROM access_audit_log
                WHERE result = 'denied'
                  AND occurred_at >= NOW() - INTERVAL '%s hours'
                ORDER BY occurred_at DESC
                LIMIT $1
                """,
                limit,
            )
            
            return [dict(row) for row in rows]
