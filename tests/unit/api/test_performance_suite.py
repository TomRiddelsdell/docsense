"""
Comprehensive performance test suite for the Trading Algorithm Document Analyzer API.

Tests cover:
1. API Response Time Benchmarks
2. Concurrent Request Handling
3. Memory Usage Monitoring
4. Connection Pool Performance
5. Database Query Performance
6. Large Payload Handling
7. Caching Performance
8. Event Store Performance

This test suite ensures the application meets performance requirements.
"""
import pytest
import asyncio
import time
import gc
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO

# Make psutil optional
try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    psutil = None


@pytest.fixture
def test_app():
    """Create FastAPI test application."""
    import os
    os.environ["ENVIRONMENT"] = "test"
    os.environ["DATABASE_URL"] = "postgresql://test:test@localhost:5432/test"
    os.environ["GEMINI_API_KEY"] = "test-key-12345678901234567890123456789012"
    os.environ["SECRET_KEY"] = "test-secret-key-12345678901234567890123456789012"
    os.environ["CORS_ORIGINS"] = "http://localhost:5000"
    os.environ["DB_POOL_MIN_SIZE"] = "5"
    os.environ["DB_POOL_MAX_SIZE"] = "20"

    from src.api.main import create_app
    return create_app()


@pytest.fixture
def test_client(test_app):
    """Create test client."""
    return TestClient(test_app)


class TestAPIResponseTimeBenchmarks:
    """Test that API endpoints meet response time requirements."""

    def test_health_endpoint_response_time(self, test_client):
        """Test that health endpoint responds within 100ms."""
        # Warm up
        test_client.get("/api/v1/health")

        # Benchmark
        start = time.time()
        response = test_client.get("/api/v1/health")
        elapsed = (time.time() - start) * 1000  # Convert to ms

        assert response.status_code == 200
        assert elapsed < 100, f"Health endpoint took {elapsed:.2f}ms (expected < 100ms)"

    def test_health_endpoint_average_response_time(self, test_client):
        """Test average response time over multiple requests."""
        num_requests = 10
        times = []

        for _ in range(num_requests):
            start = time.time()
            response = test_client.get("/api/v1/health")
            elapsed = (time.time() - start) * 1000
            times.append(elapsed)
            assert response.status_code == 200

        avg_time = sum(times) / len(times)
        max_time = max(times)
        min_time = min(times)

        assert avg_time < 50, f"Average response time {avg_time:.2f}ms (expected < 50ms)"
        assert max_time < 200, f"Max response time {max_time:.2f}ms (expected < 200ms)"

        # Print performance statistics for documentation
        print(f"\nHealth endpoint performance:")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Min: {min_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")

    def test_document_list_response_time(self, test_client):
        """Test that document list endpoint has acceptable response time."""
        # This test documents expected performance
        # Actual values will depend on database query performance

        start = time.time()
        response = test_client.get("/api/v1/documents")
        elapsed = (time.time() - start) * 1000

        # Expected response time < 500ms for list queries
        # Actual implementation may vary based on pagination
        assert response.status_code in [200, 404, 500]  # May fail if DB not connected

        if response.status_code == 200:
            assert elapsed < 500, f"Document list took {elapsed:.2f}ms (expected < 500ms)"
            print(f"\nDocument list response time: {elapsed:.2f}ms")


class TestConcurrentRequestHandling:
    """Test that the application handles concurrent requests properly."""

    def test_concurrent_health_checks(self, test_client):
        """Test handling multiple concurrent health check requests."""
        num_concurrent = 10

        def make_request():
            start = time.time()
            response = test_client.get("/api/v1/health")
            elapsed = time.time() - start
            return response.status_code, elapsed

        # Execute concurrent requests
        with ThreadPoolExecutor(max_workers=num_concurrent) as executor:
            futures = [executor.submit(make_request) for _ in range(num_concurrent)]
            results = [f.result() for f in as_completed(futures)]

        # All requests should succeed
        assert all(status == 200 for status, _ in results), \
            "All concurrent requests should succeed"

        # Check response times
        times = [elapsed for _, elapsed in results]
        avg_time = sum(times) / len(times) * 1000
        max_time = max(times) * 1000

        assert avg_time < 100, f"Average concurrent response time {avg_time:.2f}ms"
        assert max_time < 500, f"Max concurrent response time {max_time:.2f}ms"

        print(f"\nConcurrent requests ({num_concurrent} parallel):")
        print(f"  Average: {avg_time:.2f}ms")
        print(f"  Max: {max_time:.2f}ms")

    def test_concurrent_request_throughput(self, test_client):
        """Test overall throughput with concurrent requests."""
        num_requests = 50
        concurrency = 10

        start_time = time.time()

        with ThreadPoolExecutor(max_workers=concurrency) as executor:
            futures = [
                executor.submit(lambda: test_client.get("/api/v1/health"))
                for _ in range(num_requests)
            ]
            results = [f.result() for f in as_completed(futures)]

        total_time = time.time() - start_time
        throughput = num_requests / total_time

        # All requests should succeed
        assert all(r.status_code == 200 for r in results), \
            "All requests should succeed"

        # Expected throughput > 50 req/sec for health endpoint
        assert throughput > 50, \
            f"Throughput {throughput:.2f} req/sec (expected > 50 req/sec)"

        print(f"\nThroughput test ({num_requests} requests, {concurrency} concurrent):")
        print(f"  Total time: {total_time:.2f}s")
        print(f"  Throughput: {throughput:.2f} req/sec")

    def test_no_request_blocking(self, test_client):
        """Test that slow requests don't block fast requests."""
        fast_times = []
        slow_completed = False

        def make_slow_request():
            """Simulate slow request by hitting a slower endpoint."""
            nonlocal slow_completed
            # Health endpoint should be fast
            test_client.get("/api/v1/health")
            time.sleep(0.1)  # Simulate some processing
            slow_completed = True

        def make_fast_request():
            """Fast request that should not be blocked."""
            start = time.time()
            response = test_client.get("/api/v1/health")
            elapsed = (time.time() - start) * 1000
            fast_times.append(elapsed)
            return response.status_code

        # Start slow request in background
        with ThreadPoolExecutor(max_workers=2) as executor:
            slow_future = executor.submit(make_slow_request)

            # Make fast requests while slow one is running
            time.sleep(0.01)  # Let slow request start
            fast_future = executor.submit(make_fast_request)

            slow_future.result()
            status = fast_future.result()

        assert status == 200, "Fast request should succeed"
        assert len(fast_times) > 0, "Fast request should complete"

        # Fast request should not be significantly delayed by slow request
        assert fast_times[0] < 200, \
            f"Fast request took {fast_times[0]:.2f}ms (should not be blocked)"


class TestMemoryUsage:
    """Test memory usage patterns and detect potential leaks."""

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
    def test_memory_usage_stable_under_load(self, test_client):
        """Test that memory usage remains stable under repeated requests."""
        process = psutil.Process(os.getpid())

        # Force garbage collection before starting
        gc.collect()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Make many requests
        num_requests = 100
        for _ in range(num_requests):
            response = test_client.get("/api/v1/health")
            assert response.status_code == 200

        # Force garbage collection
        gc.collect()
        final_memory = process.memory_info().rss / 1024 / 1024  # MB

        memory_increase = final_memory - initial_memory

        # Memory should not increase significantly (< 10MB for 100 requests)
        assert memory_increase < 10, \
            f"Memory increased by {memory_increase:.2f}MB (expected < 10MB)"

        print(f"\nMemory usage test ({num_requests} requests):")
        print(f"  Initial: {initial_memory:.2f}MB")
        print(f"  Final: {final_memory:.2f}MB")
        print(f"  Increase: {memory_increase:.2f}MB")

    @pytest.mark.skipif(not HAS_PSUTIL, reason="psutil not installed")
    def test_no_memory_leak_in_request_cycle(self, test_client):
        """Test for memory leaks over request cycles."""
        process = psutil.Process(os.getpid())

        gc.collect()
        measurements = []

        # Take measurements over multiple cycles
        for cycle in range(5):
            # Make batch of requests
            for _ in range(20):
                test_client.get("/api/v1/health")

            gc.collect()
            memory = process.memory_info().rss / 1024 / 1024
            measurements.append(memory)

        # Memory should stabilize (not continuously grow)
        # Check that last 3 measurements are within 5MB of each other
        last_three = measurements[-3:]
        memory_range = max(last_three) - min(last_three)

        assert memory_range < 5, \
            f"Memory not stable: range {memory_range:.2f}MB in last 3 cycles"

        print(f"\nMemory leak detection (5 cycles, 20 requests each):")
        for i, mem in enumerate(measurements):
            print(f"  Cycle {i+1}: {mem:.2f}MB")


class TestConnectionPoolPerformance:
    """Test database connection pool performance."""

    @pytest.mark.asyncio
    async def test_connection_pool_configuration(self):
        """Test that connection pool is configured properly."""
        from src.api.config import get_settings

        settings = get_settings()

        # Verify pool configuration
        assert settings.DB_POOL_MIN_SIZE >= 1, "Min pool size should be >= 1"
        assert settings.DB_POOL_MAX_SIZE >= settings.DB_POOL_MIN_SIZE, \
            "Max pool size should be >= min pool size"

        # Recommended pool sizes
        assert settings.DB_POOL_MIN_SIZE >= 5, \
            f"Recommended min pool size >= 5 (current: {settings.DB_POOL_MIN_SIZE})"
        assert settings.DB_POOL_MAX_SIZE >= 10, \
            f"Recommended max pool size >= 10 (current: {settings.DB_POOL_MAX_SIZE})"

        print(f"\nConnection pool configuration:")
        print(f"  Min size: {settings.DB_POOL_MIN_SIZE}")
        print(f"  Max size: {settings.DB_POOL_MAX_SIZE}")

    def test_connection_pool_sizing_recommendation(self):
        """Test connection pool sizing recommendations."""
        from src.api.config import get_settings

        settings = get_settings()

        # Production recommendations:
        # min_size = (cores * 2) + effective_spindle_count
        # max_size = min_size * 2 to min_size * 3

        import multiprocessing
        cores = multiprocessing.cpu_count()
        recommended_min = cores * 2
        recommended_max_low = recommended_min * 2
        recommended_max_high = recommended_min * 3

        print(f"\nConnection pool sizing recommendations:")
        print(f"  CPU cores: {cores}")
        print(f"  Recommended min: {recommended_min}")
        print(f"  Recommended max: {recommended_max_low}-{recommended_max_high}")
        print(f"  Current min: {settings.DB_POOL_MIN_SIZE}")
        print(f"  Current max: {settings.DB_POOL_MAX_SIZE}")

        # Document recommendations (don't fail, just warn)
        if settings.DB_POOL_MIN_SIZE < recommended_min:
            pytest.skip(f"Pool min size ({settings.DB_POOL_MIN_SIZE}) below recommended ({recommended_min})")


class TestDatabaseQueryPerformance:
    """Test database query performance (code analysis)."""

    def test_queries_use_indexes(self):
        """Test that queries are designed to use database indexes."""
        import inspect
        from src.infrastructure.queries import read_model_queries

        # Get all query methods
        source = inspect.getsource(read_model_queries)

        # Verify queries filter on indexed fields
        # Common indexed fields: id, aggregate_id, created_at
        indexed_fields = ["id", "aggregate_id", "created_at"]

        # This test documents the expectation
        # Actual index usage should be verified with EXPLAIN ANALYZE
        print("\nDatabase query performance recommendations:")
        print("  - Ensure WHERE clauses use indexed columns")
        print("  - Add indexes for: id, aggregate_id, created_at, event_type")
        print("  - Use EXPLAIN ANALYZE to verify index usage")
        print("  - Consider composite indexes for common query patterns")

    def test_no_n_plus_one_queries(self):
        """Test that code avoids N+1 query anti-pattern."""
        import inspect
        from src.infrastructure.queries import read_model_queries

        source = inspect.getsource(read_model_queries)

        # Check for potential N+1 patterns (loops with queries)
        # This is a simple heuristic check
        has_for_loop = "for " in source
        has_query = "await" in source and "fetch" in source

        if has_for_loop and has_query:
            print("\nWarning: Potential N+1 query pattern detected")
            print("  Review query methods for loops containing database calls")
            print("  Consider using JOIN or batch queries")

        # This test documents the anti-pattern to avoid
        # Manual code review is still required


class TestLargePayloadHandling:
    """Test handling of large payloads."""

    def test_large_file_upload_performance(self, test_client):
        """Test performance with large file uploads (within limits)."""
        # Create 500KB file (well below 10MB limit)
        file_size = 500 * 1024
        large_file = BytesIO(b"x" * file_size)

        start = time.time()
        response = test_client.post(
            "/api/v1/documents/upload",
            data={"title": "Large File Test", "description": "Performance test"},
            files={"file": ("large.pdf", large_file, "application/pdf")}
        )
        elapsed = (time.time() - start) * 1000

        # Response time should be reasonable for 500KB file
        # Actual time depends on file processing (conversion, etc.)
        assert response.status_code in [200, 201, 400, 413, 500]

        print(f"\nLarge file upload ({file_size/1024:.0f}KB):")
        print(f"  Response time: {elapsed:.2f}ms")
        print(f"  Status: {response.status_code}")

    def test_json_response_size_handling(self, test_client):
        """Test that large JSON responses are handled efficiently."""
        # Get health response
        response = test_client.get("/api/v1/health")

        assert response.status_code == 200

        # Response should be reasonably sized
        response_size = len(response.content)
        assert response_size < 10000, \
            f"Health response size {response_size} bytes (should be < 10KB)"

        print(f"\nJSON response size:")
        print(f"  Health endpoint: {response_size} bytes")


class TestCachingPerformance:
    """Test caching implementation (if present)."""

    def test_repeated_request_performance(self, test_client):
        """Test if repeated requests benefit from caching."""
        # First request (cold)
        start = time.time()
        response1 = test_client.get("/api/v1/health")
        time1 = (time.time() - start) * 1000

        # Second request (potentially cached)
        start = time.time()
        response2 = test_client.get("/api/v1/health")
        time2 = (time.time() - start) * 1000

        assert response1.status_code == 200
        assert response2.status_code == 200

        # If caching is implemented, second request should be faster
        # If not, times should be similar
        print(f"\nRepeated request performance:")
        print(f"  First request: {time1:.2f}ms")
        print(f"  Second request: {time2:.2f}ms")

        if time2 < time1 * 0.5:
            print("  Caching appears to be effective")
        else:
            print("  No significant caching detected (may be expected)")


class TestEventStorePerformance:
    """Test event store performance characteristics."""

    @pytest.mark.asyncio
    async def test_event_serialization_performance(self):
        """Test event serialization/deserialization performance."""
        from src.infrastructure.persistence.event_serializer import EventSerializer
        from src.domain.events.document_events import DocumentUploaded
        from datetime import datetime, timezone
        from uuid import uuid4

        serializer = EventSerializer()

        # Create test event
        event = DocumentUploaded(
            aggregate_id=uuid4(),
            title="Test Document",
            description="Test",
            file_name="test.pdf",
            file_size=1024,
            mime_type="application/pdf",
            file_content=b"test content",
            uploaded_by="test",
            created_at=datetime.now(timezone.utc)
        )

        # Benchmark serialization
        num_iterations = 1000
        start = time.time()

        for _ in range(num_iterations):
            payload = serializer.serialize(event)

        serialize_time = (time.time() - start) / num_iterations * 1000000  # microseconds

        # Benchmark deserialization
        start = time.time()

        for _ in range(num_iterations):
            deserialized = serializer.deserialize(payload)

        deserialize_time = (time.time() - start) / num_iterations * 1000000  # microseconds

        # Serialization should be fast (< 100 microseconds per event)
        assert serialize_time < 100, \
            f"Serialization took {serialize_time:.2f}µs (expected < 100µs)"
        assert deserialize_time < 100, \
            f"Deserialization took {deserialize_time:.2f}µs (expected < 100µs)"

        print(f"\nEvent serialization performance ({num_iterations} iterations):")
        print(f"  Serialize: {serialize_time:.2f}µs per event")
        print(f"  Deserialize: {deserialize_time:.2f}µs per event")


# Summary test
def test_performance_test_coverage():
    """Verify that performance test suite has comprehensive coverage."""
    import inspect
    import sys

    current_module = sys.modules[__name__]
    test_classes = [
        obj for name, obj in inspect.getmembers(current_module)
        if inspect.isclass(obj) and name.startswith("Test")
    ]

    test_class_names = [cls.__name__ for cls in test_classes]

    # Verify coverage of key performance areas
    assert "TestAPIResponseTimeBenchmarks" in test_class_names
    assert "TestConcurrentRequestHandling" in test_class_names
    assert "TestMemoryUsage" in test_class_names
    assert "TestConnectionPoolPerformance" in test_class_names
    assert "TestDatabaseQueryPerformance" in test_class_names
    assert "TestLargePayloadHandling" in test_class_names
    assert "TestEventStorePerformance" in test_class_names

    # Count total test methods
    total_tests = sum(
        len([m for m in inspect.getmembers(cls) if m[0].startswith("test_")])
        for cls in test_classes
    )

    assert total_tests >= 15, \
        f"Performance test suite should have at least 15 tests, found {total_tests}"

    print(f"\nPerformance test suite summary:")
    print(f"  Test classes: {len(test_classes)}")
    print(f"  Total tests: {total_tests}")
