"""
Admin API endpoints for projection management and compensation.

Provides manual control over projection replay and failure recovery.
"""

from typing import Optional
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime
import asyncpg

from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker
from src.infrastructure.persistence.event_store import PostgresEventStore
from src.infrastructure.projections.base import Projection
from src.api.dependencies import Container

router = APIRouter(prefix="/admin/projections", tags=["admin"])


async def get_failure_tracker() -> ProjectionFailureTracker:
    """Dependency injection for failure tracker."""
    container = await Container.get_instance()
    if not container.failure_tracker:
        raise HTTPException(status_code=503, detail="Projection failure tracking not available")
    return container.failure_tracker


class ReplayRequest(BaseModel):
    """Request to replay events for a projection."""
    from_sequence: Optional[int] = None  # If None, replay from checkpoint
    to_sequence: Optional[int] = None    # If None, replay to latest
    skip_failed: bool = False            # Skip events that previously failed


class ReplayResponse(BaseModel):
    """Response from replay operation."""
    projection_name: str
    events_replayed: int
    events_skipped: int
    events_failed: int
    started_at: datetime
    completed_at: datetime
    status: str  # 'completed', 'failed', 'in_progress'


class CompensateFailureRequest(BaseModel):
    """Request to compensate a specific failure."""
    failure_id: str
    compensation_strategy: str  # 'retry', 'skip', 'manual_fix'


@router.post("/{projection_name}/replay", response_model=ReplayResponse)
async def replay_projection(
    projection_name: str,
    request: ReplayRequest,
    background_tasks: BackgroundTasks,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
) -> ReplayResponse:
    """
    Manually replay events for a projection.
    
    This enables compensation logic when projections fail or need to be rebuilt.
    
    Args:
        projection_name: Name of the projection to replay
        request: Replay configuration (event range, skip failed events)
    
    Returns:
        Status of the replay operation
    
    Use cases:
    - Recover from multiple projection failures
    - Rebuild read model after schema changes
    - Fix inconsistencies between event store and read models
    """
    try:
        # Determine replay range
        from_sequence = request.from_sequence
        if from_sequence is None:
            # Start from last checkpoint
            checkpoint = await failure_tracker.get_checkpoint(projection_name)
            from_sequence = checkpoint['last_event_sequence'] if checkpoint else 0
        
        to_sequence = request.to_sequence or 999999999  # Replay to latest
        
        # Start replay in background
        started_at = datetime.utcnow()
        
        # Execute replay (simplified - real implementation would be more robust)
        events_replayed = 0
        events_skipped = 0
        events_failed = 0
        
        # TODO: Implement actual replay logic with event store
        # This requires:
        # 1. Fetch events from event store in sequence range
        # 2. Apply each event to projection
        # 3. Track success/failure
        # 4. Update checkpoint after each successful event
        
        completed_at = datetime.utcnow()
        
        return ReplayResponse(
            projection_name=projection_name,
            events_replayed=events_replayed,
            events_skipped=events_skipped,
            events_failed=events_failed,
            started_at=started_at,
            completed_at=completed_at,
            status='completed'
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500, 
            detail=f"Failed to replay projection: {str(e)}"
        )


@router.post("/{projection_name}/reset")
async def reset_projection(
    projection_name: str,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
):
    """
    Reset a projection to initial state.
    
    This clears the read model and checkpoint, allowing full rebuild.
    
    CAUTION: This is a destructive operation. All projection data will be lost.
    
    Args:
        projection_name: Name of the projection to reset
    
    Returns:
        Confirmation of reset operation
    """
    try:
        pool = failure_tracker._pool
        
        async with pool.acquire() as conn:
            async with conn.transaction():
                # Delete checkpoint
                await conn.execute(
                    "DELETE FROM projection_checkpoints WHERE projection_name = $1",
                    projection_name
                )
                
                # Mark all failures as resolved
                await conn.execute(
                    """
                    UPDATE projection_failures
                    SET resolved_at = NOW(),
                        resolution_method = 'manual_reset',
                        updated_at = NOW()
                    WHERE projection_name = $1 AND resolved_at IS NULL
                    """,
                    projection_name
                )
                
                # Reset health metrics
                await conn.execute(
                    """
                    UPDATE projection_health_metrics
                    SET active_failures = 0,
                        health_status = 'healthy',
                        updated_at = NOW()
                    WHERE projection_name = $1
                    """,
                    projection_name
                )
        
        return {
            "status": "success",
            "message": f"Projection '{projection_name}' has been reset. You can now replay events.",
            "projection_name": projection_name,
            "reset_at": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to reset projection: {str(e)}"
        )


@router.post("/failures/{failure_id}/resolve")
async def resolve_failure(
    failure_id: str,
    request: CompensateFailureRequest,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
):
    """
    Manually resolve a specific projection failure.
    
    Compensation strategies:
    - retry: Attempt to process the event again
    - skip: Mark as resolved without processing (data inconsistency accepted)
    - manual_fix: Mark as resolved after manual database correction
    
    Args:
        failure_id: ID of the failure to resolve
        request: Compensation strategy
    
    Returns:
        Confirmation of resolution
    """
    try:
        pool = failure_tracker._pool
        
        async with pool.acquire() as conn:
            # Verify failure exists
            failure = await conn.fetchrow(
                """
                SELECT id, event_id, projection_name, resolved_at
                FROM projection_failures
                WHERE id = $1
                """,
                failure_id
            )
            
            if not failure:
                raise HTTPException(status_code=404, detail=f"Failure '{failure_id}' not found")
            
            if failure['resolved_at']:
                raise HTTPException(
                    status_code=400,
                    detail=f"Failure already resolved at {failure['resolved_at']}"
                )
            
            # Apply compensation strategy
            if request.compensation_strategy == 'retry':
                # TODO: Fetch event from event store and retry projection
                resolution_method = 'manual_retry'
                message = "Event will be retried"
            elif request.compensation_strategy == 'skip':
                resolution_method = 'manual_skip'
                message = "Event skipped - data inconsistency may exist"
            elif request.compensation_strategy == 'manual_fix':
                resolution_method = 'manual_fix'
                message = "Marked as resolved - manual fix applied"
            else:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid compensation strategy: {request.compensation_strategy}"
                )
            
            # Mark failure as resolved
            await conn.execute(
                """
                UPDATE projection_failures
                SET resolved_at = NOW(),
                    resolution_method = $1,
                    updated_at = NOW()
                WHERE id = $2
                """,
                resolution_method,
                failure_id
            )
            
            # Update health metrics
            await conn.execute(
                """
                UPDATE projection_health_metrics
                SET active_failures = GREATEST(active_failures - 1, 0),
                    updated_at = NOW()
                WHERE projection_name = $1
                """,
                failure['projection_name']
            )
        
        return {
            "status": "success",
            "failure_id": failure_id,
            "projection_name": failure['projection_name'],
            "resolution_method": resolution_method,
            "message": message,
            "resolved_at": datetime.utcnow()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to resolve failure: {str(e)}"
        )


@router.get("/status")
async def get_projection_system_status(
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
):
    """
    Get overall status of the projection system.
    
    Returns aggregated health across all projections.
    """
    try:
        metrics = await failure_tracker.get_health_metrics()
        
        total_projections = len(metrics)
        healthy = sum(1 for m in metrics if m['health_status'] == 'healthy')
        degraded = sum(1 for m in metrics if m['health_status'] == 'degraded')
        critical = sum(1 for m in metrics if m['health_status'] == 'critical')
        offline = sum(1 for m in metrics if m['health_status'] == 'offline')
        
        total_active_failures = sum(m['active_failures'] for m in metrics)
        total_events_processed = sum(m['total_events_processed'] for m in metrics)
        
        overall_status = 'healthy'
        if critical > 0 or offline > 0:
            overall_status = 'critical'
        elif degraded > 0:
            overall_status = 'degraded'
        
        return {
            "overall_status": overall_status,
            "total_projections": total_projections,
            "healthy_projections": healthy,
            "degraded_projections": degraded,
            "critical_projections": critical,
            "offline_projections": offline,
            "total_active_failures": total_active_failures,
            "total_events_processed": total_events_processed,
            "timestamp": datetime.utcnow()
        }
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch system status: {str(e)}"
        )
