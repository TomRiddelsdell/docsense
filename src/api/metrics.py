"""
Application metrics using Prometheus.

This module defines all metrics tracked by the application:
- Performance metrics (request duration, database latency)
- Business metrics (documents processed, analyses completed)
- System metrics (database pool utilization, error rates)
"""
from prometheus_client import Counter, Histogram, Gauge, Info
from typing import Dict

# ============================================================================
# Application Info
# ============================================================================

app_info = Info('docsense_app', 'Trading Algorithm Document Analyzer application info')
app_info.info({
    'version': '1.0.0',
    'environment': 'production'  # Will be updated from settings
})


# ============================================================================
# HTTP Request Metrics
# ============================================================================

http_requests_total = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status_code']
)

http_request_duration_seconds = Histogram(
    'http_request_duration_seconds',
    'HTTP request duration in seconds',
    ['method', 'endpoint'],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0]
)

http_requests_in_progress = Gauge(
    'http_requests_in_progress',
    'Number of HTTP requests currently in progress',
    ['method', 'endpoint']
)


# ============================================================================
# Business Metrics
# ============================================================================

documents_uploaded_total = Counter(
    'documents_uploaded_total',
    'Total number of documents uploaded',
    ['status']  # success, failed
)

documents_converted_total = Counter(
    'documents_converted_total',
    'Total number of documents converted to markdown',
    ['status']  # success, failed
)

analyses_completed_total = Counter(
    'analyses_completed_total',
    'Total number of document analyses completed',
    ['status']  # success, failed
)

feedback_generated_total = Counter(
    'feedback_generated_total',
    'Total number of feedback items generated',
    ['category']  # clarity, completeness, compliance, risk_mgmt, backtesting
)

chat_messages_total = Counter(
    'chat_messages_total',
    'Total number of chat messages processed',
    ['direction']  # user, assistant
)


# ============================================================================
# Event Store Metrics
# ============================================================================

events_appended_total = Counter(
    'events_appended_total',
    'Total number of events appended to event store',
    ['event_type', 'status']  # success, failed
)

events_loaded_total = Counter(
    'events_loaded_total',
    'Total number of events loaded from event store',
    ['aggregate_type']
)

event_store_operation_duration_seconds = Histogram(
    'event_store_operation_duration_seconds',
    'Event store operation duration in seconds',
    ['operation'],  # append, load, get_all
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)


# ============================================================================
# Projection Metrics
# ============================================================================

projection_events_processed_total = Counter(
    'projection_events_processed_total',
    'Total number of events processed by projections',
    ['projection_name', 'event_type', 'status']  # success, failed, skipped
)

projection_lag_seconds = Gauge(
    'projection_lag_seconds',
    'Projection lag behind event stream in seconds',
    ['projection_name']
)


# ============================================================================
# Database Metrics
# ============================================================================

db_pool_size = Gauge(
    'db_pool_size',
    'Current database connection pool size'
)

db_pool_active_connections = Gauge(
    'db_pool_active_connections',
    'Number of active database connections'
)

db_pool_idle_connections = Gauge(
    'db_pool_idle_connections',
    'Number of idle database connections'
)

db_query_duration_seconds = Histogram(
    'db_query_duration_seconds',
    'Database query duration in seconds',
    ['query_type'],  # read, write, transaction
    buckets=[0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0]
)


# ============================================================================
# AI Provider Metrics
# ============================================================================

ai_requests_total = Counter(
    'ai_requests_total',
    'Total number of AI provider requests',
    ['provider', 'operation', 'status']  # gemini/claude/openai, analyze/feedback/chat, success/failed
)

ai_request_duration_seconds = Histogram(
    'ai_request_duration_seconds',
    'AI provider request duration in seconds',
    ['provider', 'operation'],
    buckets=[0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0]
)

ai_tokens_used_total = Counter(
    'ai_tokens_used_total',
    'Total number of AI tokens consumed',
    ['provider', 'token_type']  # prompt, completion
)


# ============================================================================
# Error Metrics
# ============================================================================

errors_total = Counter(
    'errors_total',
    'Total number of errors',
    ['error_type', 'component']  # validation/domain/infrastructure/api, component_name
)

unhandled_exceptions_total = Counter(
    'unhandled_exceptions_total',
    'Total number of unhandled exceptions',
    ['exception_type']
)


# ============================================================================
# Helper Functions
# ============================================================================

def update_database_pool_metrics(
    pool_size: int,
    active: int,
    idle: int
) -> None:
    """Update database pool metrics."""
    db_pool_size.set(pool_size)
    db_pool_active_connections.set(active)
    db_pool_idle_connections.set(idle)


def get_metrics_summary() -> Dict[str, any]:
    """Get a summary of key metrics for health checks."""
    return {
        'http_requests_total': http_requests_total._value.get(),
        'documents_uploaded_total': documents_uploaded_total._value.get(),
        'analyses_completed_total': analyses_completed_total._value.get(),
        'events_appended_total': events_appended_total._value.get(),
        'errors_total': errors_total._value.get(),
    }
