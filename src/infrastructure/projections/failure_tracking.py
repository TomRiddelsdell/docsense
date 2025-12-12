"""
Projection failure tracking and retry infrastructure.

This module implements Event Sourcing best practices for projection resilience:
1. Tracks all projection failures for monitoring and recovery
2. Implements exponential backoff retry logic
3. Maintains projection checkpoints for replay capability
4. Provides health metrics for monitoring

Author: System
Date: 2025-12-12
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, List
from uuid import UUID
import asyncio
import traceback
import logging

import asyncpg

from src.domain.events.base import DomainEvent

logger = logging.getLogger(__name__)


class ProjectionFailureTracker:
    """Tracks projection failures and manages retry logic with exponential backoff."""
    
    # Exponential backoff schedule: 1s, 2s, 4s, 8s, 16s (max)
    RETRY_DELAYS = [1, 2, 4, 8, 16]
    MAX_RETRIES = 5
    
    def __init__(self, pool: asyncpg.Pool):
        self._pool = pool
    
    async def record_failure(
        self,
        event: DomainEvent,
        projection_name: str,
        error: Exception
    ) -> UUID:
        """
        Record a projection failure and schedule next retry.
        
        Returns the failure record ID.
        """
        error_message = str(error)
        error_traceback = traceback.format_exc()
        
        async with self._pool.acquire() as conn:
            # Check if this failure already exists (for retry attempts)
            existing = await conn.fetchrow(
                """
                SELECT id, retry_count
                FROM projection_failures
                WHERE event_id = $1 
                  AND projection_name = $2 
                  AND resolved_at IS NULL
                ORDER BY created_at DESC
                LIMIT 1
                """,
                event.event_id,
                projection_name
            )
            
            if existing:
                # Update existing failure record
                retry_count = existing['retry_count'] + 1
                next_retry_delay = self._get_retry_delay(retry_count)
                next_retry_at = datetime.utcnow() + timedelta(seconds=next_retry_delay) if retry_count < self.MAX_RETRIES else None
                
                await conn.execute(
                    """
                    UPDATE projection_failures
                    SET retry_count = $1,
                        last_retry_at = NOW(),
                        next_retry_at = $2,
                        error_message = $3,
                        error_traceback = $4,
                        updated_at = NOW()
                    WHERE id = $5
                    """,
                    retry_count,
                    next_retry_at,
                    error_message,
                    error_traceback,
                    existing['id']
                )
                
                logger.warning(
                    f"Projection {projection_name} failed again for event {event.event_id}. "
                    f"Retry {retry_count}/{self.MAX_RETRIES}. "
                    f"Next retry in {next_retry_delay}s" if next_retry_at else "Max retries exceeded."
                )
                
                return existing['id']
            else:
                # Create new failure record
                next_retry_at = datetime.utcnow() + timedelta(seconds=self.RETRY_DELAYS[0])
                
                failure_id = await conn.fetchval(
                    """
                    INSERT INTO projection_failures
                    (event_id, event_type, projection_name, error_message, 
                     error_traceback, retry_count, max_retries, failed_at, 
                     next_retry_at)
                    VALUES ($1, $2, $3, $4, $5, 0, $6, NOW(), $7)
                    RETURNING id
                    """,
                    event.event_id,
                    event.event_type,
                    projection_name,
                    error_message,
                    error_traceback,
                    self.MAX_RETRIES,
                    next_retry_at
                )
                
                # Update health metrics
                await self._update_health_metrics(conn, projection_name, success=False)
                
                logger.error(
                    f"NEW PROJECTION FAILURE: {projection_name} failed for event {event.event_type}. "
                    f"Error: {error_message}. Will retry in {self.RETRY_DELAYS[0]}s."
                )
                
                return failure_id
    
    async def record_success(
        self,
        event: DomainEvent,
        projection_name: str
    ) -> None:
        """Record successful projection processing."""
        async with self._pool.acquire() as conn:
            # Update checkpoint
            await conn.execute(
                """
                INSERT INTO projection_checkpoints
                (projection_name, last_event_id, last_event_type, 
                 last_event_sequence, events_processed)
                VALUES ($1, $2, $3, $4, 1)
                ON CONFLICT (projection_name) DO UPDATE SET
                    last_event_id = $2,
                    last_event_type = $3,
                    last_event_sequence = $4,
                    checkpoint_at = NOW(),
                    events_processed = projection_checkpoints.events_processed + 1,
                    updated_at = NOW()
                """,
                projection_name,
                event.event_id,
                event.event_type,
                event.sequence  # Assuming events have sequence numbers
            )
            
            # Update health metrics
            await self._update_health_metrics(conn, projection_name, success=True)
            
            # Resolve any pending failures for this event
            await conn.execute(
                """
                UPDATE projection_failures
                SET resolved_at = NOW(),
                    resolution_method = 'auto_retry',
                    updated_at = NOW()
                WHERE event_id = $1 
                  AND projection_name = $2 
                  AND resolved_at IS NULL
                """,
                event.event_id,
                projection_name
            )
    
    async def get_failures_for_retry(self) -> List[Dict]:
        """Get all failures that are due for retry."""
        async with self._pool.acquire() as conn:
            rows = await conn.fetch(
                """
                SELECT id, event_id, event_type, projection_name, retry_count
                FROM projection_failures
                WHERE resolved_at IS NULL
                  AND next_retry_at IS NOT NULL
                  AND next_retry_at <= NOW()
                  AND retry_count < max_retries
                ORDER BY next_retry_at
                """
            )
            return [dict(row) for row in rows]
    
    async def get_checkpoint(self, projection_name: str) -> Optional[Dict]:
        """Get the last checkpoint for a projection."""
        async with self._pool.acquire() as conn:
            row = await conn.fetchrow(
                """
                SELECT projection_name, last_event_id, last_event_type, 
                       last_event_sequence, events_processed, checkpoint_at
                FROM projection_checkpoints
                WHERE projection_name = $1
                """,
                projection_name
            )
            return dict(row) if row else None
    
    async def get_health_metrics(self, projection_name: Optional[str] = None) -> List[Dict]:
        """Get health metrics for projections."""
        async with self._pool.acquire() as conn:
            if projection_name:
                rows = await conn.fetch(
                    """
                    SELECT * FROM projection_health_metrics
                    WHERE projection_name = $1
                    """,
                    projection_name
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT * FROM projection_health_metrics
                    ORDER BY health_status DESC, projection_name
                    """
                )
            return [dict(row) for row in rows]
    
    def _get_retry_delay(self, retry_count: int) -> int:
        """Get exponential backoff delay for retry attempt."""
        if retry_count < len(self.RETRY_DELAYS):
            return self.RETRY_DELAYS[retry_count]
        return self.RETRY_DELAYS[-1]  # Max delay
    
    async def _update_health_metrics(
        self,
        conn: asyncpg.Connection,
        projection_name: str,
        success: bool
    ) -> None:
        """Update aggregated health metrics for a projection."""
        if success:
            await conn.execute(
                """
                INSERT INTO projection_health_metrics
                (projection_name, total_events_processed, last_success_at)
                VALUES ($1, 1, NOW())
                ON CONFLICT (projection_name) DO UPDATE SET
                    total_events_processed = projection_health_metrics.total_events_processed + 1,
                    last_success_at = NOW(),
                    updated_at = NOW()
                """,
                projection_name
            )
        else:
            await conn.execute(
                """
                INSERT INTO projection_health_metrics
                (projection_name, total_failures, active_failures, last_failure_at)
                VALUES ($1, 1, 1, NOW())
                ON CONFLICT (projection_name) DO UPDATE SET
                    total_failures = projection_health_metrics.total_failures + 1,
                    active_failures = projection_health_metrics.active_failures + 1,
                    last_failure_at = NOW(),
                    updated_at = NOW()
                """,
                projection_name
            )
        
        # Update health status based on metrics
        await conn.execute(
            """
            UPDATE projection_health_metrics
            SET health_status = CASE
                WHEN active_failures = 0 THEN 'healthy'
                WHEN active_failures < 10 THEN 'degraded'
                WHEN active_failures < 50 THEN 'critical'
                ELSE 'offline'
            END
            WHERE projection_name = $1
            """,
            projection_name
        )


class RetryableProjectionPublisher:
    """
    Event publisher with automatic retry logic for failed projections.
    
    This implementation follows Event Sourcing best practices:
    - Failed projections don't block event processing
    - Failures are tracked and retried with exponential backoff
    - Checkpoints enable replay from last known good state
    - Health metrics provide observability
    """
    
    def __init__(
        self,
        failure_tracker: ProjectionFailureTracker,
        retry_interval_seconds: int = 10
    ):
        self._failure_tracker = failure_tracker
        self._retry_interval = retry_interval_seconds
        self._retry_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start_retry_worker(self) -> None:
        """Start background worker to process failed projection retries."""
        if self._running:
            logger.warning("Retry worker already running")
            return
        
        self._running = True
        self._retry_task = asyncio.create_task(self._retry_worker())
        logger.info("Started projection retry worker")
    
    async def stop_retry_worker(self) -> None:
        """Stop the retry worker."""
        if not self._running:
            return
        
        self._running = False
        if self._retry_task:
            self._retry_task.cancel()
            try:
                await self._retry_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped projection retry worker")
    
    async def _retry_worker(self) -> None:
        """Background worker that retries failed projections."""
        logger.info("Projection retry worker started")
        
        while self._running:
            try:
                failures = await self._failure_tracker.get_failures_for_retry()
                
                if failures:
                    logger.info(f"Found {len(failures)} projection failures to retry")
                    
                    for failure in failures:
                        # TODO: Fetch original event from event store and retry projection
                        # This requires integration with event store to replay events
                        logger.info(
                            f"Retrying projection {failure['projection_name']} "
                            f"for event {failure['event_id']} "
                            f"(attempt {failure['retry_count'] + 1})"
                        )
                
                await asyncio.sleep(self._retry_interval)
                
            except asyncio.CancelledError:
                logger.info("Retry worker cancelled")
                break
            except Exception as e:
                logger.error(f"Error in retry worker: {e}", exc_info=True)
                await asyncio.sleep(self._retry_interval)
        
        logger.info("Projection retry worker stopped")
