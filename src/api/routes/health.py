from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from src.api.dependencies import Container

router = APIRouter()
logger = logging.getLogger(__name__)


class DependencyStatus(BaseModel):
    """Status of a single dependency."""
    status: str  # healthy, degraded, unhealthy
    message: Optional[str] = None
    details: Optional[Dict[str, Any]] = None


class DatabasePoolMetrics(BaseModel):
    """Database connection pool metrics."""
    min_size: int
    max_size: int
    current_size: int
    active_connections: int
    idle_connections: int


class HealthResponse(BaseModel):
    """Overall health status response."""
    status: str  # healthy, degraded, unhealthy
    version: str
    dependencies: Dict[str, DependencyStatus]


@router.get("/health", response_model=HealthResponse)
async def health_check(
    container: Container = Depends(Container.get_instance)
) -> HealthResponse:
    """
    Comprehensive health check endpoint with dependency status.

    Checks:
    - Database connectivity and pool status
    - Event store accessibility
    - Overall application health

    Returns:
        HealthResponse: Application health status with dependency details
    """
    dependencies = {}
    overall_healthy = True
    degraded = False

    # Check database
    try:
        pool = container.pool

        if not pool:
            dependencies["database"] = DependencyStatus(
                status="unhealthy",
                message="Database pool not initialized"
            )
            overall_healthy = False
        else:
            # Get pool metrics
            pool_size = pool.get_size()
            pool_min_size = pool.get_min_size()
            pool_max_size = pool.get_max_size()
            pool_idle_size = pool.get_idle_size()
            active_connections = pool_size - pool_idle_size

            # Test connectivity
            try:
                async with pool.acquire() as conn:
                    await conn.fetchval("SELECT 1")
                    db_connected = True
            except Exception as e:
                logger.error(f"Database connectivity test failed: {e}")
                db_connected = False

            # Determine status
            utilization = (active_connections / pool_max_size) * 100 if pool_max_size > 0 else 0

            if not db_connected:
                status = "unhealthy"
                message = "Database connection failed"
                overall_healthy = False
            elif utilization > 90:
                status = "degraded"
                message = "Connection pool nearly exhausted"
                degraded = True
            elif utilization > 70:
                status = "degraded"
                message = "High connection pool utilization"
                degraded = True
            else:
                status = "healthy"
                message = "Database operational"

            dependencies["database"] = DependencyStatus(
                status=status,
                message=message,
                details={
                    "connected": db_connected,
                    "pool_size": pool_size,
                    "active_connections": active_connections,
                    "idle_connections": pool_idle_size,
                    "utilization_percent": round(utilization, 1),
                }
            )

    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        dependencies["database"] = DependencyStatus(
            status="unhealthy",
            message=f"Health check error: {str(e)}"
        )
        overall_healthy = False

    # Check event store
    try:
        event_store = container.event_store
        if event_store:
            # Try to query event store
            try:
                # Simple query to verify event store is accessible
                async with container.pool.acquire() as conn:
                    count = await conn.fetchval("SELECT COUNT(*) FROM events")
                dependencies["event_store"] = DependencyStatus(
                    status="healthy",
                    message="Event store operational",
                    details={"total_events": count}
                )
            except Exception as e:
                logger.error(f"Event store check failed: {e}")
                dependencies["event_store"] = DependencyStatus(
                    status="unhealthy",
                    message="Event store query failed"
                )
                overall_healthy = False
        else:
            dependencies["event_store"] = DependencyStatus(
                status="unhealthy",
                message="Event store not initialized"
            )
            overall_healthy = False
    except Exception as e:
        logger.error(f"Event store health check failed: {e}", exc_info=True)
        dependencies["event_store"] = DependencyStatus(
            status="unhealthy",
            message=f"Health check error: {str(e)}"
        )
        overall_healthy = False

    # Determine overall status
    if not overall_healthy:
        overall_status = "unhealthy"
    elif degraded:
        overall_status = "degraded"
    else:
        overall_status = "healthy"

    return HealthResponse(
        status=overall_status,
        version="1.0.0",
        dependencies=dependencies
    )


@router.get("/health/database")
async def database_health_check(
    container: Container = Depends(Container.get_instance)
) -> Dict[str, Any]:
    """
    Detailed database health check including connection pool metrics.

    Returns:
        dict: Database health status and pool metrics
    """
    try:
        pool = container.pool

        if not pool:
            return {
                "status": "unhealthy",
                "message": "Database pool not initialized",
                "connected": False
            }

        # Get pool metrics
        pool_size = pool.get_size()
        pool_min_size = pool.get_min_size()
        pool_max_size = pool.get_max_size()
        pool_idle_size = pool.get_idle_size()

        # Calculate active connections
        active_connections = pool_size - pool_idle_size

        # Test database connectivity
        try:
            async with pool.acquire() as conn:
                # Simple query to verify connection works
                version = await conn.fetchval("SELECT version()")
                db_connected = True

                # Get current database connection count
                total_connections = await conn.fetchval(
                    """
                    SELECT count(*)
                    FROM pg_stat_activity
                    WHERE datname = current_database()
                    """
                )
        except Exception as e:
            logger.error(f"Database connectivity test failed: {e}")
            db_connected = False
            version = None
            total_connections = None

        # Determine pool status
        utilization = (active_connections / pool_max_size) * 100 if pool_max_size > 0 else 0

        if utilization > 90:
            pool_status = "critical"  # Pool nearly exhausted
        elif utilization > 70:
            pool_status = "warning"   # High utilization
        else:
            pool_status = "healthy"

        overall_status = "healthy" if db_connected and pool_status in ["healthy", "warning"] else "unhealthy"

        return {
            "status": overall_status,
            "pool": {
                "status": pool_status,
                "min_size": pool_min_size,
                "max_size": pool_max_size,
                "current_size": pool_size,
                "active_connections": active_connections,
                "idle_connections": pool_idle_size,
                "utilization_percent": round(utilization, 1),
            },
            "database": {
                "connected": db_connected,
                "version": version.split(" on ")[0] if version else None,  # Clean up version string
                "total_connections": total_connections,
            }
        }

    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Health check failed: {str(e)}"
        )
