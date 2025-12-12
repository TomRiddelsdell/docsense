"""
Unit tests for ProjectionFailureTracker.

Tests the core failure tracking logic including:
- Recording failures
- Exponential backoff calculation
- Success recording
- Checkpoint management
- Health metrics updates
"""

import pytest
from datetime import datetime, timedelta
from uuid import uuid4
from unittest.mock import AsyncMock, MagicMock, patch

from src.infrastructure.projections.failure_tracking import (
    ProjectionFailureTracker,
    RetryableProjectionPublisher
)
from src.domain.events.document_events import DocumentUploaded


@pytest.fixture
def mock_conn():
    """Create a mock database connection."""
    return AsyncMock()


@pytest.fixture
def mock_pool(mock_conn):
    """Create a mock asyncpg pool with connection."""
    pool = MagicMock()
    
    # Create async context manager
    async_context = AsyncMock()
    async_context.__aenter__ = AsyncMock(return_value=mock_conn)
    async_context.__aexit__ = AsyncMock(return_value=None)
    
    # Setup pool.acquire() to return the async context manager
    pool.acquire = MagicMock(return_value=async_context)
    
    return pool


@pytest.fixture
def failure_tracker(mock_pool):
    """Create ProjectionFailureTracker with mock pool."""
    return ProjectionFailureTracker(mock_pool)


@pytest.fixture
def sample_event():
    """Create a sample domain event for testing."""
    event = DocumentUploaded(
        aggregate_id=str(uuid4()),
        filename="test.pdf",
        original_format="pdf",
        file_size=1024,
        uploaded_by="test-user",
        storage_path="/tmp/test.pdf"
    )
    event.event_id = uuid4()
    event.sequence = 1
    event.occurred_at = datetime.utcnow()
    return event


class TestExponentialBackoff:
    """Test exponential backoff delay calculation."""
    
    def test_first_retry_delay(self, failure_tracker):
        """Test that first retry has 1 second delay."""
        assert failure_tracker._get_retry_delay(0) == 1
    
    def test_second_retry_delay(self, failure_tracker):
        """Test that second retry has 2 second delay."""
        assert failure_tracker._get_retry_delay(1) == 2
    
    def test_third_retry_delay(self, failure_tracker):
        """Test that third retry has 4 second delay."""
        assert failure_tracker._get_retry_delay(2) == 4
    
    def test_fourth_retry_delay(self, failure_tracker):
        """Test that fourth retry has 8 second delay."""
        assert failure_tracker._get_retry_delay(3) == 8
    
    def test_fifth_retry_delay(self, failure_tracker):
        """Test that fifth retry has 16 second delay."""
        assert failure_tracker._get_retry_delay(4) == 16
    
    def test_max_delay_cap(self, failure_tracker):
        """Test that delay is capped at 16 seconds."""
        assert failure_tracker._get_retry_delay(5) == 16
        assert failure_tracker._get_retry_delay(10) == 16
        assert failure_tracker._get_retry_delay(100) == 16


class TestRecordFailure:
    """Test failure recording functionality."""
    
    @pytest.mark.asyncio
    async def test_first_failure_creates_new_record(self, failure_tracker, sample_event, mock_conn):
        """Test that first failure creates a new database record."""
        # Mock no existing failure
        mock_conn.fetchrow.return_value = None
        mock_conn.fetchval.return_value = uuid4()
        
        error = Exception("Database connection failed")
        projection_name = "TestProjection"
        
        failure_id = await failure_tracker.record_failure(sample_event, projection_name, error)
        
        # Verify failure was recorded
        assert failure_id is not None
        
        # Verify database insert was called
        assert mock_conn.fetchval.called
        insert_call = mock_conn.fetchval.call_args
        assert insert_call is not None
        
        # Check SQL contains correct table
        sql = insert_call[0][0]
        assert "INSERT INTO projection_failures" in sql
    
    @pytest.mark.asyncio
    async def test_subsequent_failure_updates_retry_count(self, failure_tracker, sample_event, mock_conn):
        """Test that subsequent failures increment retry count."""
        # Mock existing failure
        existing_id = uuid4()
        mock_conn.fetchrow.return_value = {'id': existing_id, 'retry_count': 1}
        
        error = Exception("Database connection failed")
        projection_name = "TestProjection"
        
        failure_id = await failure_tracker.record_failure(sample_event, projection_name, error)
        
        # Should return existing failure ID
        assert failure_id == existing_id
        
        # Verify update was called
        assert mock_conn.execute.called
        update_call = conn.execute.call_args
        sql = update_call[0][0]
        assert "UPDATE projection_failures" in sql
        
        # Verify retry_count was incremented
        retry_count = update_call[0][1]
        assert retry_count == 2
    
    @pytest.mark.asyncio
    async def test_next_retry_scheduled_with_exponential_backoff(self, failure_tracker, sample_event, mock_conn):
        """Test that next retry is scheduled with correct delay."""
        # Using mock_conn fixture
        conn.fetchrow.return_value = None
        conn.fetchval.return_value = uuid4()
        
        error = Exception("Test error")
        projection_name = "TestProjection"
        
        before_time = datetime.utcnow()
        await failure_tracker.record_failure(sample_event, projection_name, error)
        after_time = datetime.utcnow()
        
        # Verify insert was called with next_retry_at
        insert_call = conn.fetchval.call_args[0]
        next_retry_at = insert_call[-1]
        
        # Should be scheduled ~1 second in future (first retry)
        assert next_retry_at > before_time
        assert next_retry_at < after_time + timedelta(seconds=2)
    
    @pytest.mark.asyncio
    async def test_max_retries_stops_scheduling(self, failure_tracker, sample_event, mock_conn):
        """Test that retries stop after max attempts."""
        existing_id = uuid4()
        # Using mock_conn fixture
        conn.fetchrow.return_value = {'id': existing_id, 'retry_count': 4}  # At max
        
        error = Exception("Permanent failure")
        projection_name = "TestProjection"
        
        await failure_tracker.record_failure(sample_event, projection_name, error)
        
        # Verify next_retry_at is None (no more retries)
        update_call = conn.execute.call_args[0]
        next_retry_at = update_call[2]
        assert next_retry_at is None


class TestRecordSuccess:
    """Test success recording functionality."""
    
    @pytest.mark.asyncio
    async def test_success_updates_checkpoint(self, failure_tracker, sample_event, mock_conn):
        """Test that success updates projection checkpoint."""
        # Using mock_conn fixture
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Verify checkpoint update was called
        assert mock_conn.execute.called
        
        # Check that INSERT ON CONFLICT was used
        first_call = conn.execute.call_args_list[0][0]
        sql = first_call[0]
        assert "INSERT INTO projection_checkpoints" in sql
        assert "ON CONFLICT" in sql
    
    @pytest.mark.asyncio
    async def test_success_resolves_pending_failures(self, failure_tracker, sample_event, mock_conn):
        """Test that success resolves pending failures for the event."""
        # Using mock_conn fixture
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Should call execute at least twice (checkpoint + resolve)
        assert mock_conn.execute.call_count >= 2
        
        # Check that failures were resolved
        resolve_call = None
        for call in conn.execute.call_args_list:
            sql = call[0][0]
            if "UPDATE projection_failures" in sql and "resolved_at" in sql:
                resolve_call = call
                break
        
        assert resolve_call is not None
    
    @pytest.mark.asyncio
    async def test_success_updates_health_metrics(self, failure_tracker, sample_event, mock_conn):
        """Test that success updates health metrics."""
        # Using mock_conn fixture
        projection_name = "TestProjection"
        
        await failure_tracker.record_success(sample_event, projection_name)
        
        # Check health metrics were updated
        health_update_call = None
        for call in conn.execute.call_args_list:
            sql = call[0][0]
            if "projection_health_metrics" in sql:
                health_update_call = call
                break
        
        assert health_update_call is not None


class TestGetFailuresForRetry:
    """Test retrieving failures due for retry."""
    
    @pytest.mark.asyncio
    async def test_returns_failures_due_now(self, failure_tracker, mock_conn):
        """Test that only failures with next_retry_at <= NOW are returned."""
        # Using mock_conn fixture
        
        # Mock failures due for retry
        conn.fetch.return_value = [
            {
                'id': uuid4(),
                'event_id': uuid4(),
                'event_type': 'DocumentUploaded',
                'projection_name': 'TestProjection',
                'retry_count': 1
            }
        ]
        
        failures = await failure_tracker.get_failures_for_retry()
        
        assert len(failures) == 1
        assert failures[0]['event_type'] == 'DocumentUploaded'
        
        # Verify query filters correctly
        fetch_call = conn.fetch.call_args[0]
        sql = fetch_call[0]
        assert "next_retry_at <= NOW()" in sql
        assert "resolved_at IS NULL" in sql


class TestGetCheckpoint:
    """Test checkpoint retrieval."""
    
    @pytest.mark.asyncio
    async def test_returns_checkpoint_if_exists(self, failure_tracker, mock_conn):
        """Test that checkpoint is returned if it exists."""
        # Using mock_conn fixture
        
        expected_checkpoint = {
            'projection_name': 'TestProjection',
            'last_event_id': uuid4(),
            'last_event_type': 'DocumentUploaded',
            'last_event_sequence': 42,
            'events_processed': 100,
            'checkpoint_at': datetime.utcnow()
        }
        conn.fetchrow.return_value = expected_checkpoint
        
        checkpoint = await failure_tracker.get_checkpoint('TestProjection')
        
        assert checkpoint is not None
        assert checkpoint['last_event_sequence'] == 42
        assert checkpoint['events_processed'] == 100
    
    @pytest.mark.asyncio
    async def test_returns_none_if_no_checkpoint(self, failure_tracker, mock_conn):
        """Test that None is returned if no checkpoint exists."""
        # Using mock_conn fixture
        conn.fetchrow.return_value = None
        
        checkpoint = await failure_tracker.get_checkpoint('NonExistentProjection')
        
        assert checkpoint is None


class TestGetHealthMetrics:
    """Test health metrics retrieval."""
    
    @pytest.mark.asyncio
    async def test_returns_all_metrics_when_no_name(self, failure_tracker, mock_conn):
        """Test that all metrics are returned when no projection name specified."""
        # Using mock_conn fixture
        
        conn.fetch.return_value = [
            {
                'projection_name': 'Projection1',
                'health_status': 'healthy',
                'total_events_processed': 100,
                'total_failures': 0,
                'active_failures': 0
            },
            {
                'projection_name': 'Projection2',
                'health_status': 'degraded',
                'total_events_processed': 50,
                'total_failures': 5,
                'active_failures': 2
            }
        ]
        
        metrics = await failure_tracker.get_health_metrics()
        
        assert len(metrics) == 2
        assert metrics[0]['projection_name'] == 'Projection1'
        assert metrics[1]['health_status'] == 'degraded'
    
    @pytest.mark.asyncio
    async def test_returns_specific_metric_when_name_provided(self, failure_tracker, mock_conn):
        """Test that specific metric is returned when projection name provided."""
        # Using mock_conn fixture
        
        conn.fetch.return_value = [
            {
                'projection_name': 'TestProjection',
                'health_status': 'healthy',
                'total_events_processed': 100,
                'total_failures': 0,
                'active_failures': 0
            }
        ]
        
        metrics = await failure_tracker.get_health_metrics('TestProjection')
        
        assert len(metrics) == 1
        assert metrics[0]['projection_name'] == 'TestProjection'


class TestRetryWorker:
    """Test background retry worker."""
    
    @pytest.mark.asyncio
    async def test_worker_starts_and_stops(self, failure_tracker):
        """Test that retry worker can be started and stopped."""
        publisher = RetryableProjectionPublisher(failure_tracker, retry_interval_seconds=0.1)
        
        # Start worker
        await publisher.start_retry_worker()
        assert publisher._running is True
        assert publisher._retry_task is not None
        
        # Stop worker
        await publisher.stop_retry_worker()
        assert publisher._running is False
    
    @pytest.mark.asyncio
    async def test_worker_prevents_duplicate_start(self, failure_tracker):
        """Test that worker prevents starting twice."""
        publisher = RetryableProjectionPublisher(failure_tracker, retry_interval_seconds=0.1)
        
        await publisher.start_retry_worker()
        
        # Try to start again - should not raise error
        await publisher.start_retry_worker()
        
        await publisher.stop_retry_worker()
    
    @pytest.mark.asyncio
    async def test_worker_processes_due_failures(self, failure_tracker, mock_conn):
        """Test that worker processes failures that are due."""
        # Using mock_conn fixture
        
        # Mock failures due for retry
        conn.fetch.return_value = [
            {
                'id': uuid4(),
                'event_id': uuid4(),
                'event_type': 'DocumentUploaded',
                'projection_name': 'TestProjection',
                'retry_count': 1
            }
        ]
        
        publisher = RetryableProjectionPublisher(failure_tracker, retry_interval_seconds=0.1)
        
        await publisher.start_retry_worker()
        
        # Give worker time to process
        import asyncio
        await asyncio.sleep(0.2)
        
        await publisher.stop_retry_worker()
        
        # Verify get_failures_for_retry was called
        assert mock_conn.fetch.called


class TestHealthMetricsCalculation:
    """Test health status calculation logic."""
    
    @pytest.mark.asyncio
    async def test_health_status_healthy_with_zero_failures(self, failure_tracker, mock_conn):
        """Test that status is 'healthy' with 0 active failures."""
        # Using mock_conn fixture
        
        # The health status is calculated in database
        # We're testing that the update logic is called correctly
        await failure_tracker._update_health_metrics(conn, "TestProjection", success=True)
        
        # Verify update query was executed
        assert mock_conn.execute.call_count >= 2  # Insert/update + status update
    
    @pytest.mark.asyncio
    async def test_health_status_degraded_with_few_failures(self, failure_tracker, mock_conn):
        """Test that status calculation logic handles degraded state."""
        # Using mock_conn fixture
        
        await failure_tracker._update_health_metrics(conn, "TestProjection", success=False)
        
        # Verify health metrics update was called
        assert mock_conn.execute.called
        
        # Check that status calculation query was executed
        status_update_call = None
        for call in conn.execute.call_args_list:
            if len(call[0]) > 0:
                sql = call[0][0]
                if "health_status = CASE" in sql:
                    status_update_call = call
                    break
        
        assert status_update_call is not None
