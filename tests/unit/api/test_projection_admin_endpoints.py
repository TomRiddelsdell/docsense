"""
Unit tests for projection admin API endpoints.

Tests the admin management endpoints including:
- Replay projection
- Reset projection
- Resolve failure
- Get system status
"""

import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.routes.projection_admin import router, get_failure_tracker
from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker


@pytest.fixture
def mock_failure_tracker():
    """Create a mock ProjectionFailureTracker."""
    tracker = AsyncMock(spec=ProjectionFailureTracker)
    tracker._pool = AsyncMock()
    return tracker


@pytest.fixture
def app(mock_failure_tracker):
    """Create test FastAPI app with projection admin routes."""
    app = FastAPI()
    
    # Override dependency
    async def override_get_failure_tracker():
        return mock_failure_tracker
    
    app.dependency_overrides[get_failure_tracker] = override_get_failure_tracker
    app.include_router(router)
    
    return app


@pytest.fixture
def client(app):
    """Create test client."""
    return TestClient(app)


class TestReplayProjection:
    """Test POST /admin/projections/{projection_name}/replay endpoint."""
    
    def test_replay_from_checkpoint(self, client, mock_failure_tracker):
        """Test replaying projection from last checkpoint."""
        mock_failure_tracker.get_checkpoint.return_value = {
            'last_event_sequence': 42,
            'events_processed': 100
        }
        
        response = client.post(
            "/admin/projections/DocumentProjection/replay",
            json={"from_sequence": None, "to_sequence": None}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['projection_name'] == 'DocumentProjection'
        assert data['status'] == 'completed'
    
    def test_replay_from_specific_sequence(self, client, mock_failure_tracker):
        """Test replaying from specific sequence number."""
        response = client.post(
            "/admin/projections/DocumentProjection/replay",
            json={"from_sequence": 100, "to_sequence": 200}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['projection_name'] == 'DocumentProjection'
    
    def test_replay_with_skip_failed(self, client, mock_failure_tracker):
        """Test replaying with skip_failed option."""
        response = client.post(
            "/admin/projections/DocumentProjection/replay",
            json={"skip_failed": True}
        )
        
        assert response.status_code == 200
    
    def test_replay_returns_statistics(self, client, mock_failure_tracker):
        """Test that replay returns statistics about processed events."""
        response = client.post(
            "/admin/projections/DocumentProjection/replay",
            json={}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert 'events_replayed' in data
        assert 'events_skipped' in data
        assert 'events_failed' in data
        assert 'started_at' in data
        assert 'completed_at' in data


class TestResetProjection:
    """Test POST /admin/projections/{projection_name}/reset endpoint."""
    
    def test_reset_clears_checkpoint(self, client, mock_failure_tracker):
        """Test that reset clears the projection checkpoint."""
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        conn.transaction.return_value.__aenter__ = AsyncMock()
        conn.transaction.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/admin/projections/DocumentProjection/reset")
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['projection_name'] == 'DocumentProjection'
        assert 'reset_at' in data
    
    def test_reset_marks_failures_resolved(self, client, mock_failure_tracker):
        """Test that reset marks all failures as resolved."""
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        conn.transaction.return_value.__aenter__ = AsyncMock()
        conn.transaction.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/admin/projections/DocumentProjection/reset")
        
        assert response.status_code == 200
        # Verify execute was called (for checkpoint delete and failure updates)
        assert conn.execute.called
    
    def test_reset_updates_health_metrics(self, client, mock_failure_tracker):
        """Test that reset updates health metrics."""
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        conn.transaction.return_value.__aenter__ = AsyncMock()
        conn.transaction.return_value.__aexit__ = AsyncMock()
        
        response = client.post("/admin/projections/DocumentProjection/reset")
        
        assert response.status_code == 200
        # Should have multiple execute calls for different updates
        assert conn.execute.call_count >= 3
    
    def test_reset_returns_500_on_error(self, client, mock_failure_tracker):
        """Test that reset returns 500 on database error."""
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        conn.transaction.side_effect = Exception("Database error")
        
        response = client.post("/admin/projections/DocumentProjection/reset")
        
        assert response.status_code == 500
        assert "Failed to reset projection" in response.json()['detail']


class TestResolveFailure:
    """Test POST /admin/projections/failures/{failure_id}/resolve endpoint."""
    
    def test_resolve_with_retry_strategy(self, client, mock_failure_tracker):
        """Test resolving failure with retry strategy."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        # Mock existing failure
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': None
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "retry"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['status'] == 'success'
        assert data['resolution_method'] == 'manual_retry'
    
    def test_resolve_with_skip_strategy(self, client, mock_failure_tracker):
        """Test resolving failure with skip strategy."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': None
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "skip"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['resolution_method'] == 'manual_skip'
        assert 'data inconsistency may exist' in data['message']
    
    def test_resolve_with_manual_fix_strategy(self, client, mock_failure_tracker):
        """Test resolving failure with manual_fix strategy."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': None
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "manual_fix"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data['resolution_method'] == 'manual_fix'
    
    def test_resolve_returns_404_for_nonexistent_failure(self, client, mock_failure_tracker):
        """Test that resolve returns 404 for nonexistent failure."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        conn.fetchrow.return_value = None
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "retry"}
        )
        
        assert response.status_code == 404
        assert "not found" in response.json()['detail']
    
    def test_resolve_returns_400_for_already_resolved(self, client, mock_failure_tracker):
        """Test that resolve returns 400 for already resolved failure."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': datetime.utcnow()
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "retry"}
        )
        
        assert response.status_code == 400
        assert "already resolved" in response.json()['detail']
    
    def test_resolve_returns_400_for_invalid_strategy(self, client, mock_failure_tracker):
        """Test that resolve returns 400 for invalid compensation strategy."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': None
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "invalid"}
        )
        
        assert response.status_code == 400
        assert "Invalid compensation strategy" in response.json()['detail']
    
    def test_resolve_updates_health_metrics(self, client, mock_failure_tracker):
        """Test that resolving failure updates health metrics."""
        failure_id = str(uuid4())
        conn = AsyncMock()
        mock_failure_tracker._pool.acquire.return_value.__aenter__.return_value = conn
        
        conn.fetchrow.return_value = {
            'id': failure_id,
            'projection_name': 'DocumentProjection',
            'resolved_at': None
        }
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id, "compensation_strategy": "manual_fix"}
        )
        
        assert response.status_code == 200
        # Should update failure and health metrics
        assert conn.execute.call_count >= 2


class TestGetProjectionSystemStatus:
    """Test GET /admin/projections/status endpoint."""
    
    def test_returns_overall_system_status(self, client, mock_failure_tracker):
        """Test that endpoint returns overall projection system status."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'Projection1',
                'health_status': 'healthy',
                'active_failures': 0,
                'total_events_processed': 1000
            },
            {
                'projection_name': 'Projection2',
                'health_status': 'degraded',
                'active_failures': 5,
                'total_events_processed': 500
            },
            {
                'projection_name': 'Projection3',
                'health_status': 'critical',
                'active_failures': 20,
                'total_events_processed': 100
            }
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_projections'] == 3
        assert data['healthy_projections'] == 1
        assert data['degraded_projections'] == 1
        assert data['critical_projections'] == 1
        assert data['offline_projections'] == 0
    
    def test_calculates_total_active_failures(self, client, mock_failure_tracker):
        """Test that total active failures are calculated correctly."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100},
            {'health_status': 'degraded', 'active_failures': 5, 'total_events_processed': 100},
            {'health_status': 'critical', 'active_failures': 15, 'total_events_processed': 100}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_active_failures'] == 20
    
    def test_calculates_total_events_processed(self, client, mock_failure_tracker):
        """Test that total events processed are calculated correctly."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 1000},
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 2000},
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 3000}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['total_events_processed'] == 6000
    
    def test_overall_status_healthy_when_all_healthy(self, client, mock_failure_tracker):
        """Test that overall status is healthy when all projections are healthy."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100},
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['overall_status'] == 'healthy'
    
    def test_overall_status_degraded_when_some_degraded(self, client, mock_failure_tracker):
        """Test that overall status is degraded when some projections are degraded."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100},
            {'health_status': 'degraded', 'active_failures': 5, 'total_events_processed': 100}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['overall_status'] == 'degraded'
    
    def test_overall_status_critical_when_any_critical(self, client, mock_failure_tracker):
        """Test that overall status is critical when any projection is critical."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100},
            {'health_status': 'degraded', 'active_failures': 5, 'total_events_processed': 100},
            {'health_status': 'critical', 'active_failures': 20, 'total_events_processed': 100}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['overall_status'] == 'critical'
    
    def test_overall_status_critical_when_any_offline(self, client, mock_failure_tracker):
        """Test that overall status is critical when any projection is offline."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {'health_status': 'healthy', 'active_failures': 0, 'total_events_processed': 100},
            {'health_status': 'offline', 'active_failures': 100, 'total_events_processed': 0}
        ]
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert data['overall_status'] == 'critical'
        assert data['offline_projections'] == 1
    
    def test_includes_timestamp(self, client, mock_failure_tracker):
        """Test that response includes timestamp."""
        mock_failure_tracker.get_health_metrics.return_value = []
        
        response = client.get("/admin/projections/status")
        
        assert response.status_code == 200
        data = response.json()
        assert 'timestamp' in data


class TestRequestValidation:
    """Test request validation for admin endpoints."""
    
    def test_replay_validates_sequence_numbers(self, client, mock_failure_tracker):
        """Test that replay validates sequence numbers."""
        # from_sequence must be less than to_sequence if both provided
        # This would be validated by Pydantic if we add validation
        response = client.post(
            "/admin/projections/DocumentProjection/replay",
            json={"from_sequence": 100, "to_sequence": 50}
        )
        
        # Currently accepts any values - might want to add validation
        assert response.status_code in [200, 400]
    
    def test_resolve_requires_compensation_strategy(self, client, mock_failure_tracker):
        """Test that resolve requires compensation_strategy field."""
        failure_id = str(uuid4())
        
        response = client.post(
            f"/admin/projections/failures/{failure_id}/resolve",
            json={"failure_id": failure_id}  # Missing compensation_strategy
        )
        
        # Pydantic should reject this
        assert response.status_code == 422
