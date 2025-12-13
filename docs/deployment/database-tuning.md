# Database Connection Pool Tuning Guide

**Author**: System Documentation
**Date**: 2025-12-13
**Applies To**: PostgreSQL with asyncpg
**Related**: [Environment Variables](./environment-variables.md), [Production Deployment](./production-deployment.md)

## Overview

This guide provides recommendations for tuning database connection pool settings for optimal performance, reliability, and resource utilization.

## Connection Pool Basics

The application uses **asyncpg** for PostgreSQL connections with a connection pool managed by `asyncpg.create_pool()`. The pool maintains a set of reusable database connections to:

1. **Reduce latency**: Reuse existing connections instead of creating new ones
2. **Limit resources**: Prevent exhausting database or application resources
3. **Improve throughput**: Handle concurrent requests efficiently

## Configuration Parameters

### DB_POOL_MIN_SIZE

**Description**: Minimum number of connections to keep open in the pool at all times.

**Default**: 5
**Valid Range**: 1-50 (enforced by validation)
**Environment Variable**: `DB_POOL_MIN_SIZE`

**Purpose**:
- Ensures connections are ready immediately for requests
- Reduces latency for initial requests after idle periods
- Keeps connections "warm" to avoid PostgreSQL startup overhead

**Recommendations**:
- **Development**: 2-5 connections (low resource usage)
- **Staging**: 5-10 connections (balance testing and resources)
- **Production (Low Traffic)**: 5-10 connections
- **Production (Medium Traffic)**: 10-20 connections
- **Production (High Traffic)**: 15-30 connections

**Warning**: Setting above 100 triggers a warning - very high minimum size wastes resources.

### DB_POOL_MAX_SIZE

**Description**: Maximum number of connections allowed in the pool.

**Default**: 20
**Valid Range**: 1-100 (enforced by validation)
**Environment Variable**: `DB_POOL_MAX_SIZE`

**Purpose**:
- Limits total connections to prevent database overload
- Controls application memory usage (each connection uses RAM)
- Prevents "connection storm" during traffic spikes

**Recommendations**:
- **Development**: 10-20 connections (sufficient for local dev)
- **Staging**: 20-50 connections (testing under load)
- **Production (Low Traffic)**: 20-30 connections (<100 concurrent users)
- **Production (Medium Traffic)**: 30-60 connections (100-1000 concurrent users)
- **Production (High Traffic)**: 60-100 connections (>1000 concurrent users)

**Warning**: Setting above 500 triggers a warning - this is rarely needed and consumes significant resources.

### Validation Rules

The application enforces the following validation rules at startup:

1. ✅ **Both must be >= 1**: At least one connection required
2. ✅ **MIN_SIZE <= MAX_SIZE**: Minimum cannot exceed maximum
3. ⚠️ **MIN_SIZE > 100**: Warning - very high, wastes resources
4. ⚠️ **MAX_SIZE > 500**: Warning - rarely needed, high memory usage

## Sizing Guidelines

### Formula-Based Approach

A good starting point for sizing the pool:

```
MIN_SIZE = number_of_application_instances * 5
MAX_SIZE = number_of_application_instances * 20
```

**Example**: 3 application instances
- MIN_SIZE = 3 * 5 = 15
- MAX_SIZE = 3 * 20 = 60

### Load-Based Approach

Size based on expected concurrent requests:

```
MAX_SIZE = (average_concurrent_requests * 1.5) / number_of_instances
MIN_SIZE = MAX_SIZE * 0.25
```

**Example**: 200 concurrent requests, 4 instances
- MAX_SIZE = (200 * 1.5) / 4 = 75
- MIN_SIZE = 75 * 0.25 = 19

### Resource-Based Approach

Consider database and application resource limits:

**PostgreSQL max_connections** (default: 100):
- Reserve 10-20 connections for admin/monitoring
- Divide remaining by number of application instances
- Set MAX_SIZE below this limit

**Application memory**:
- Each connection uses ~5-10MB RAM
- Factor into container/pod memory limits

**Example**: PostgreSQL max_connections=100, 4 app instances
- Available for apps: 100 - 15 (admin) = 85
- Per instance: 85 / 4 = ~21
- Set MAX_SIZE = 20 (with safety margin)

## Performance Tuning

### Symptoms of Poor Configuration

#### Pool Too Small (MIN_SIZE or MAX_SIZE too low)

**Symptoms**:
- High connection acquisition latency
- Frequent "waiting for connection" log messages
- Request timeouts under load
- Poor throughput during traffic spikes

**Solution**: Increase MAX_SIZE incrementally (e.g., +10-20)

#### Pool Too Large (MAX_SIZE too high)

**Symptoms**:
- High memory usage
- Database running out of connections
- Slow query performance (too many concurrent queries)
- Out of memory errors

**Solution**: Decrease MAX_SIZE and optimize queries

#### MIN_SIZE Too High

**Symptoms**:
- High idle resource usage
- Memory waste when traffic is low
- Slow application startup

**Solution**: Reduce MIN_SIZE to 25-30% of MAX_SIZE

### Monitoring Metrics

Monitor these metrics to tune pool settings:

**Application Metrics**:
- `pool_active_connections`: Currently in use
- `pool_idle_connections`: Available for use
- `pool_wait_time`: Time waiting for connection
- `pool_acquisition_count`: Total connections acquired

**Database Metrics** (PostgreSQL):
```sql
-- Current connections by state
SELECT state, COUNT(*)
FROM pg_stat_activity
WHERE datname = 'your_database'
GROUP BY state;

-- Connections by application
SELECT application_name, COUNT(*)
FROM pg_stat_activity
WHERE datname = 'your_database'
GROUP BY application_name;
```

**Ideal Ratios**:
- Active connections: 50-80% of MAX_SIZE during peak load
- Idle connections: ~MIN_SIZE during low traffic
- Wait time: <10ms average, <100ms p99

## Production Recommendations

### Small Application (<10 req/sec)

```bash
DB_POOL_MIN_SIZE=5
DB_POOL_MAX_SIZE=20
```

**Rationale**: Sufficient for low traffic, minimal resource usage

### Medium Application (10-100 req/sec)

```bash
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=50
```

**Rationale**: Handles traffic spikes, good balance of resources

### Large Application (100-1000 req/sec)

```bash
DB_POOL_MIN_SIZE=20
DB_POOL_MAX_SIZE=80
```

**Rationale**: High throughput, handles sustained load

### Very Large Application (>1000 req/sec)

```bash
DB_POOL_MIN_SIZE=30
DB_POOL_MAX_SIZE=100
```

**Rationale**: Maximum concurrency, requires careful database tuning

**Note**: For very large applications, consider:
- Read replicas for read-heavy workloads
- Connection pooler (PgBouncer) for >100 connections
- Horizontal scaling with load balancer

## Environment-Specific Settings

### Development

**Goal**: Fast startup, low resource usage, easy debugging

```bash
ENVIRONMENT=development
DB_POOL_MIN_SIZE=2
DB_POOL_MAX_SIZE=10
```

**Why**:
- Minimal connections for single developer
- Faster application startup
- Lower memory footprint

### Staging

**Goal**: Simulate production, load testing capable

```bash
ENVIRONMENT=staging
DB_POOL_MIN_SIZE=10
DB_POOL_MAX_SIZE=40
```

**Why**:
- Sufficient for load testing
- Similar to production behavior
- Can test connection limits

### Production

**Goal**: Optimal performance, high availability, resource efficient

```bash
ENVIRONMENT=production
DB_POOL_MIN_SIZE=15
DB_POOL_MAX_SIZE=60
```

**Why**:
- Handles traffic spikes
- Keeps connections ready
- Balanced resource usage

## Advanced Topics

### Connection Lifecycle

```
1. Pool Initialization
   - MIN_SIZE connections created immediately
   - Connections tested with simple query

2. Connection Acquisition (from pool)
   - Check for idle connection
   - If none available and pool < MAX_SIZE, create new
   - If pool at MAX_SIZE, wait (with timeout)

3. Connection Release (back to pool)
   - Connection returned to idle state
   - Kept alive if pool >= MIN_SIZE
   - Closed if pool > MIN_SIZE (scaling down)

4. Connection Health Checks
   - Periodic health checks on idle connections
   - Failed connections removed and replaced
```

### Timeout Settings

Related to connection pool:

**Connection Timeout**: How long to wait for a connection from the pool
```python
# In asyncpg.create_pool()
timeout=10  # 10 seconds default
```

**Command Timeout**: How long a query can run
```python
# In asyncpg.create_pool()
command_timeout=120  # 120 seconds default
```

**Recommendation**:
- Connection timeout: 10-30 seconds
- Command timeout: 60-300 seconds (depends on query complexity)

### Connection Pooling vs PgBouncer

**Use Application Pool** (asyncpg) when:
- < 100 total connections needed
- Single application instance or few instances
- Simple deployment

**Use PgBouncer** when:
- > 100 total connections needed
- Many microservices accessing same database
- Need transaction pooling or session pooling
- Want to reduce PostgreSQL overhead

### Database Configuration

Ensure PostgreSQL is configured to handle your connection pool:

```ini
# postgresql.conf
max_connections = 200  # Total allowed connections
shared_buffers = 4GB   # 25% of RAM
effective_cache_size = 12GB  # 75% of RAM
work_mem = 16MB        # Per connection work memory
```

**Calculate max_connections**:
```
max_connections = (total_app_instances * MAX_SIZE) + 20 (admin/monitoring)
```

## Troubleshooting

### Error: "Pool is full, waiting for connection"

**Cause**: All connections in use, reached MAX_SIZE

**Solutions**:
1. Increase MAX_SIZE if database can handle it
2. Optimize slow queries to release connections faster
3. Add read replicas for read-heavy workloads
4. Use caching to reduce database queries

### Error: "Too many connections"

**Cause**: PostgreSQL max_connections exceeded

**Solutions**:
1. Reduce MAX_SIZE across all application instances
2. Increase PostgreSQL max_connections
3. Implement PgBouncer connection pooling
4. Use connection multiplexing

### Error: "Connection timed out"

**Cause**: Took too long to acquire connection from pool

**Solutions**:
1. Increase connection timeout setting
2. Increase MAX_SIZE if pool exhaustion is common
3. Check for connection leaks (connections not returned)
4. Investigate slow queries blocking connections

### Warning: "Pool min size is very high"

**Cause**: MIN_SIZE > 100

**Solutions**:
1. Reduce MIN_SIZE to 25-30% of MAX_SIZE
2. Check if this is intentional for your use case
3. Consider if resources could be better utilized

### Warning: "Pool max size is very high"

**Cause**: MAX_SIZE > 500

**Solutions**:
1. Verify this is intentional
2. Check database can handle this many connections
3. Consider PgBouncer instead of large pool
4. Review if queries can be optimized to need fewer connections

## Monitoring and Alerts

### Recommended Alerts

**Critical Alerts**:
- Pool acquisition failures > 0
- Average wait time > 1 second
- Connection timeouts > 0

**Warning Alerts**:
- Active connections > 80% of MAX_SIZE for >5 minutes
- Average wait time > 100ms
- Idle connections < MIN_SIZE

**Info Alerts**:
- Pool size changes
- Connection errors
- Slow queries blocking connections

### Health Check Endpoint

The application exposes pool metrics at `/health/database`:

```json
{
  "status": "healthy",
  "pool": {
    "min_size": 10,
    "max_size": 50,
    "current_size": 35,
    "active_connections": 28,
    "idle_connections": 7,
    "wait_queue_size": 0,
    "total_acquisitions": 125840,
    "average_acquisition_time_ms": 5.2
  },
  "database": {
    "connected": true,
    "version": "PostgreSQL 14.5",
    "current_connections": 42
  }
}
```

## Testing Pool Configuration

### Load Testing

Test your pool configuration under load:

```bash
# Using Apache Bench
ab -n 10000 -c 100 http://localhost:8000/api/v1/documents

# Using wrk
wrk -t12 -c400 -d30s http://localhost:8000/api/v1/documents
```

**What to monitor**:
- Request latency (p50, p95, p99)
- Connection pool utilization
- Database connection count
- Error rate

**Expected results with good config**:
- p95 latency < 200ms
- Pool utilization 50-80% of MAX_SIZE
- Zero connection timeouts
- Zero pool exhaustion errors

### Gradual Load Increase

```bash
# Start with low concurrency
ab -n 1000 -c 10 http://localhost:8000/api/v1/documents

# Gradually increase
ab -n 1000 -c 50 http://localhost:8000/api/v1/documents
ab -n 1000 -c 100 http://localhost:8000/api/v1/documents
ab -n 1000 -c 200 http://localhost:8000/api/v1/documents
```

**Goal**: Find the concurrency level where:
- Latency starts increasing significantly
- Connection pool reaches MAX_SIZE
- Errors start appearing

This is your application's capacity limit with current pool settings.

## Best Practices

1. ✅ **Start Conservative**: Begin with default values, increase as needed
2. ✅ **Monitor First**: Collect metrics before making changes
3. ✅ **Tune Iteratively**: Make small adjustments, measure impact
4. ✅ **Document Changes**: Record why you changed settings
5. ✅ **Test Under Load**: Validate changes with realistic traffic
6. ✅ **Set Alerts**: Know when pool is struggling
7. ✅ **Plan for Growth**: Review settings quarterly
8. ✅ **Coordinate with DBA**: Ensure database can handle pool size

## References

- [asyncpg Documentation](https://magicstack.github.io/asyncpg/)
- [PostgreSQL Connection Management](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Database Connection Pooling Best Practices](https://www.postgresql.org/docs/current/runtime-config-connection.html)
- [Environment Variables Documentation](./environment-variables.md)

---

*Last Updated: 2025-12-13*
*Next Review: Quarterly or when traffic patterns change significantly*
