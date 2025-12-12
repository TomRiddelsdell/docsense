"""
Projection health monitoring API endpoints.

Provides observability into projection status, failures, and lag.
"""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from datetime import datetime
import asyncpg

from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker
from src.api.dependencies import Container

router = APIRouter(prefix="/health/projections", tags=["health"])


async def get_failure_tracker() -> ProjectionFailureTracker:
    """Dependency injection for failure tracker."""
    container = await Container.get_instance()
    if not container.failure_tracker:
        raise HTTPException(status_code=503, detail="Projection failure tracking not available")
    return container.failure_tracker


class ProjectionHealthResponse(BaseModel):
    """Health status for a single projection."""
    projection_name: str
    health_status: str  # healthy, degraded, critical, offline
    total_events_processed: int
    total_failures: int
    active_failures: int
    last_success_at: Optional[datetime]
    last_failure_at: Optional[datetime]
    lag_seconds: Optional[int]


class ProjectionCheckpointResponse(BaseModel):
    """Checkpoint information for a projection."""
    projection_name: str
    last_event_id: str
    last_event_type: str
    last_event_sequence: int
    events_processed: int
    checkpoint_at: datetime


class ProjectionFailureResponse(BaseModel):
    """Details of a projection failure."""
    id: str
    event_id: str
    event_type: str
    projection_name: str
    error_message: str
    retry_count: int
    max_retries: int
    failed_at: datetime
    next_retry_at: Optional[datetime]
    resolved_at: Optional[datetime]


@router.get("/", response_model=List[ProjectionHealthResponse])
async def get_all_projection_health(
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
) -> List[ProjectionHealthResponse]:
    """
    Get health status for all projections.
    
    Returns aggregated metrics including:
    - Health status (healthy, degraded, critical, offline)
    - Event processing counts
    - Failure counts
    - Processing lag
    """
    try:
        metrics = await failure_tracker.get_health_metrics()
        return [ProjectionHealthResponse(**m) for m in metrics]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projection health: {str(e)}")


@router.get("/{projection_name}", response_model=ProjectionHealthResponse)
async def get_projection_health(
    projection_name: str,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
) -> ProjectionHealthResponse:
    """
    Get health status for a specific projection.
    
    Args:
        projection_name: Name of the projection (e.g., 'DocumentProjection')
    
    Returns:
        Detailed health metrics for the projection
    """
    try:
        metrics = await failure_tracker.get_health_metrics(projection_name)
        if not metrics:
            raise HTTPException(status_code=404, detail=f"Projection '{projection_name}' not found")
        return ProjectionHealthResponse(**metrics[0])
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch projection health: {str(e)}")


@router.get("/{projection_name}/checkpoint", response_model=ProjectionCheckpointResponse)
async def get_projection_checkpoint(
    projection_name: str,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
) -> ProjectionCheckpointResponse:
    """
    Get the last checkpoint for a projection.
    
    Checkpoints track the last successfully processed event,
    enabling replay from last known good state.
    
    Args:
        projection_name: Name of the projection
    
    Returns:
        Checkpoint information including last processed event
    """
    try:
        checkpoint = await failure_tracker.get_checkpoint(projection_name)
        if not checkpoint:
            raise HTTPException(status_code=404, detail=f"No checkpoint found for projection '{projection_name}'")
        return ProjectionCheckpointResponse(**checkpoint)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch checkpoint: {str(e)}")


@router.get("/{projection_name}/failures", response_model=List[ProjectionFailureResponse])
async def get_projection_failures(
    projection_name: str,
    include_resolved: bool = False,
    failure_tracker: ProjectionFailureTracker = Depends(get_failure_tracker)
) -> List[ProjectionFailureResponse]:
    """
    Get failure history for a projection.
    
    Args:
        projection_name: Name of the projection
        include_resolved: Include resolved failures in results (default: False)
    
    Returns:
        List of projection failures with retry information
    """
    try:
        # Get pool from failure_tracker
        pool = failure_tracker._pool
        
        async with pool.acquire() as conn:
            if include_resolved:
                rows = await conn.fetch(
                    """
                    SELECT id, event_id, event_type, projection_name, 
                           error_message, retry_count, max_retries,
                           failed_at, next_retry_at, resolved_at
                    FROM projection_failures
                    WHERE projection_name = $1
                    ORDER BY failed_at DESC
                    LIMIT 100
                    """,
                    projection_name
                )
            else:
                rows = await conn.fetch(
                    """
                    SELECT id, event_id, event_type, projection_name,
                           error_message, retry_count, max_retries,
                           failed_at, next_retry_at, resolved_at
                    FROM projection_failures
                    WHERE projection_name = $1 AND resolved_at IS NULL
                    ORDER BY failed_at DESC
                    """,
                    projection_name
                )
        
        return [ProjectionFailureResponse(**dict(row)) for row in rows]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch failures: {str(e)}")
