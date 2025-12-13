from fastapi import APIRouter, Depends, HTTPException
from typing import Optional, Dict, Any
from pydantic import BaseModel
import logging

from src.api.dependencies import Container

router = APIRouter()
logger = logging.getLogger(__name__)


class DatabasePoolMetrics(BaseModel):
    """Database connection pool metrics."""
    min_size: int
    max_size: int
    current_size: int
    active_connections: int
    idle_connections: int


class HealthResponse(BaseModel):
    """Overall health status response."""
    status: str
    version: str
    database: Optional[Dict[str, Any]] = None


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Basic health check endpoint.

    Returns:
        HealthResponse: Application health status
    """
    return HealthResponse(
        status="healthy",
        version="1.0.0"
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
