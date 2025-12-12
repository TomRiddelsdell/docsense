"""
Unit tests for projection health API endpoints.

Tests the health monitoring endpoints including:
- Get all projection health
- Get specific projection health
- Get checkpoint
- Get failures
"""

import pytest
from uuid import uuid4
from datetime import datetime
from fastapi.testclient import TestClient
from fastapi import FastAPI
from unittest.mock import AsyncMock, MagicMock, patch

from src.api.routes.projection_health import router, get_failure_tracker
from src.infrastructure.projections.failure_tracking import ProjectionFailureTracker


@pytest.fixture
def mock_failure_tracker():
    """Create a mock ProjectionFailureTracker."""
    tracker = AsyncMock(spec=ProjectionFailureTracker)
    return tracker


@pytest.fixture
def app(mock_failure_tracker):
    """Create test FastAPI app with projection health routes."""
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


class TestGetAllProjectionHealth:
    """Test GET /health/projections endpoint."""
    
    def test_returns_all_projection_health(self, client, mock_failure_tracker):
        """Test that endpoint returns health for all projections."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'DocumentProjection',
                'health_status': 'healthy',
                'total_events_processed': 100,
                'total_failures': 0,
                'active_failures': 0,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': None,
                'lag_seconds': 0
            },
            {
                'projection_name': 'PolicyProjection',
                'health_status': 'degraded',
                'total_events_processed': 50,
                'total_failures': 5,
                'active_failures': 2,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': datetime.utcnow(),
                'lag_seconds': 10
            }
        ]
        
        response = client.get("/health/projections/")
        
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 2
        assert data[0]['projection_name'] == 'DocumentProjection'
        assert data[0]['health_status'] == 'healthy'
        assert data[1]['projection_name'] == 'PolicyProjection'
        assert data[1]['health_status'] == 'degraded'
    
    def test_returns_empty_list_when_no_projections(self, client, mock_failure_tracker):
        """Test that endpoint returns empty list when no projections exist."""
        mock_failure_tracker.get_health_metrics.return_value = []
        
        response = client.get("/health/projections/")
        
        assert response.status_code == 200
        assert response.json() == []
    
    def test_returns_500_on_error(self, client, mock_failure_tracker):
        """Test that endpoint returns 500 on internal error."""
        mock_failure_tracker.get_health_metrics.side_effect = Exception("Database error")
        
        response = client.get("/health/projections/")
        
        assert response.status_code == 500
        assert "Failed to fetch projection health" in response.json()['detail']


class TestGetProjectionHealth:
    """Test GET /health/projections/{projection_name} endpoint."""
    
    def test_returns_specific_projection_health(self, client, mock_failure_tracker):
        """Test that endpoint returns health for specific projection."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'DocumentProjection',
                'health_status': 'healthy',
                'total_events_processed': 100,
                'total_failures': 0,
                'active_failures': 0,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': None,
                'lag_seconds': 0
            }
        ]
        
        response = client.get("/health/projections/DocumentProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['projection_name'] == 'DocumentProjection'
        assert data['health_status'] == 'healthy'
        assert data['total_events_processed'] == 100
    
    def test_returns_404_when_projection_not_found(self, client, mock_failure_tracker):
        """Test that endpoint returns 404 when projection doesn't exist."""
        mock_failure_tracker.get_health_metrics.return_value = []
        
        response = client.get("/health/projections/NonExistentProjection")
        
        assert response.status_code == 404
        assert "not found" in response.json()['detail']


class TestGetProjectionCheckpoint:
    """Test GET /health/projections/{projection_name}/checkpoint endpoint."""
    
    def test_returns_checkpoint(self, client, mock_failure_tracker):
        """Test that endpoint returns checkpoint for projection."""
        event_id = str(uuid4())
        checkpoint_time = datetime.utcnow()
        
        mock_failure_tracker.get_checkpoint.return_value = {
            'projection_name': 'DocumentProjection',
            'last_event_id': event_id,
            'last_event_type': 'DocumentUploaded',
            'last_event_sequence': 42,
            'events_processed': 100,
            'checkpoint_at': checkpoint_time
        }
        
        response = client.get("/health/projections/DocumentProjection/checkpoint")
        
        assert response.status_code == 200
        data = response.json()
        assert data['projection_name'] == 'DocumentProjection'
        assert data['last_event_sequence'] == 42
        assert data['events_processed'] == 100
    
    def test_returns_404_when_no_checkpoint(self, client, mock_failure_tracker):
        """Test that endpoint returns 404 when no checkpoint exists."""
        mock_failure_tracker.get_checkpoint.return_value = None
        
        response = client.get("/health/projections/NewProjection/checkpoint")
        
        assert response.status_code == 404
        assert "No checkpoint found" in response.json()['detail']


class TestGetProjectionFailures:
    """Test GET /health/projections/{projection_name}/failures endpoint."""
    
    def test_returns_unresolved_failures_by_default(self, client, mock_failure_tracker):
        """Test that endpoint returns only unresolved failures by default."""
        # Need to mock the pool access within the endpoint
        with patch.object(mock_failure_tracker, '_pool') as mock_pool:
            conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = conn
            
            conn.fetch.return_value = [
                {
                    'id': str(uuid4()),
                    'event_id': str(uuid4()),
                    'event_type': 'DocumentUploaded',
                    'projection_name': 'DocumentProjection',
                    'error_message': 'Database connection failed',
                    'retry_count': 2,
                    'max_retries': 5,
                    'failed_at': datetime.utcnow(),
                    'next_retry_at': datetime.utcnow(),
                    'resolved_at': None
                }
            ]
            
            response = client.get("/health/projections/DocumentProjection/failures")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['projection_name'] == 'DocumentProjection'
            assert data[0]['resolved_at'] is None
    
    def test_returns_resolved_failures_when_requested(self, client, mock_failure_tracker):
        """Test that endpoint returns resolved failures when requested."""
        with patch.object(mock_failure_tracker, '_pool') as mock_pool:
            conn = AsyncMock()
            mock_pool.acquire.return_value.__aenter__.return_value = conn
            
            conn.fetch.return_value = [
                {
                    'id': str(uuid4()),
                    'event_id': str(uuid4()),
                    'event_type': 'DocumentUploaded',
                    'projection_name': 'DocumentProjection',
                    'error_message': 'Transient error',
                    'retry_count': 1,
                    'max_retries': 5,
                    'failed_at': datetime.utcnow(),
                    'next_retry_at': None,
                    'resolved_at': datetime.utcnow()
                }
            ]
            
            response = client.get("/health/projections/DocumentProjection/failures?include_resolved=true")
            
            assert response.status_code == 200
            data = response.json()
            assert len(data) == 1
            assert data[0]['resolved_at'] is not None


class TestHealthStatusLevels:
    """Test health status level representation."""
    
    def test_healthy_status_zero_failures(self, client, mock_failure_tracker):
        """Test that healthy status is reported with zero active failures."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'healthy',
                'total_events_processed': 1000,
                'total_failures': 5,  # Had failures in past
                'active_failures': 0,  # But none active
                'last_success_at': datetime.utcnow(),
                'last_failure_at': datetime.utcnow(),
                'lag_seconds': 0
            }
        ]
        
        response = client.get("/health/projections/TestProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['health_status'] == 'healthy'
        assert data['active_failures'] == 0
    
    def test_degraded_status_few_failures(self, client, mock_failure_tracker):
        """Test that degraded status is reported with few active failures."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'degraded',
                'total_events_processed': 100,
                'total_failures': 5,
                'active_failures': 5,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': datetime.utcnow(),
                'lag_seconds': 30
            }
        ]
        
        response = client.get("/health/projections/TestProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['health_status'] == 'degraded'
        assert data['active_failures'] > 0
        assert data['active_failures'] < 10
    
    def test_critical_status_many_failures(self, client, mock_failure_tracker):
        """Test that critical status is reported with many active failures."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'critical',
                'total_events_processed': 100,
                'total_failures': 25,
                'active_failures': 25,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': datetime.utcnow(),
                'lag_seconds': 300
            }
        ]
        
        response = client.get("/health/projections/TestProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['health_status'] == 'critical'
        assert data['active_failures'] >= 10


class TestLagReporting:
    """Test projection lag reporting."""
    
    def test_reports_lag_in_seconds(self, client, mock_failure_tracker):
        """Test that lag is reported in seconds."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'healthy',
                'total_events_processed': 100,
                'total_failures': 0,
                'active_failures': 0,
                'last_success_at': datetime.utcnow(),
                'last_failure_at': None,
                'lag_seconds': 42
            }
        ]
        
        response = client.get("/health/projections/TestProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['lag_seconds'] == 42
    
    def test_reports_null_lag_when_unknown(self, client, mock_failure_tracker):
        """Test that null lag is reported when unknown."""
        mock_failure_tracker.get_health_metrics.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'healthy',
                'total_events_processed': 0,
                'total_failures': 0,
                'active_failures': 0,
                'last_success_at': None,
                'last_failure_at': None,
                'lag_seconds': None
            }
        ]
        
        response = client.get("/health/projections/TestProjection")
        
        assert response.status_code == 200
        data = response.json()
        assert data['lag_seconds'] is None
