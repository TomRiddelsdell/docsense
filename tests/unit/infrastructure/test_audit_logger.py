"""Tests for AuditLogger."""
import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

from src.infrastructure.audit.audit_logger import AuditLogger


@pytest.fixture
def mock_pool():
    """Mock asyncpg pool with proper async context manager support."""
    from unittest.mock import MagicMock
    
    # Create mock connection
    mock_conn = AsyncMock()
    mock_conn.execute = AsyncMock()
    mock_conn.fetch = AsyncMock(return_value=[])
    
    # Create mock context manager
    mock_acquire = MagicMock()
    mock_acquire.__aenter__ = AsyncMock(return_value=mock_conn)
    mock_acquire.__aexit__ = AsyncMock(return_value=None)
    
    # Create mock pool
    pool = MagicMock()
    pool.acquire = MagicMock(return_value=mock_acquire)
    
    # Store mock_conn so tests can access it
    pool._test_conn = mock_conn
    
    return pool


@pytest.fixture
def audit_logger(mock_pool):
    """Create AuditLogger with mocked pool."""
    return AuditLogger(mock_pool)


@pytest.mark.asyncio
async def test_log_access_allowed(audit_logger, mock_pool):
    """Test logging allowed document access."""
    document_id = uuid4()
    user_kerberos_id = "testuser"
    action = "view"
    result = "allowed"
    
    await audit_logger.log_access(
        user_kerberos_id=user_kerberos_id,
        document_id=document_id,
        action=action,
        result=result
    )
    
    # Verify execute was called with correct SQL
    mock_conn = mock_pool._test_conn
    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args
    sql = call_args[0][0]
    
    assert "INSERT INTO access_audit_log" in sql
    # Check that user_kerberos_id and document_id are in the params
    assert user_kerberos_id in call_args[0]
    assert document_id in call_args[0]
    assert action in call_args[0]
    assert result in call_args[0]


@pytest.mark.asyncio
async def test_log_access_denied(audit_logger, mock_pool):
    """Test logging denied document access."""
    document_id = uuid4()
    user_kerberos_id = "testuser"
    action = "edit"
    result = "denied"
    reason = "User does not have CONTRIBUTOR role"
    
    await audit_logger.log_access(
        user_kerberos_id=user_kerberos_id,
        document_id=document_id,
        action=action,
        result=result,
        reason=reason
    )
    
    # Verify execute was called with correct SQL
    mock_conn = mock_pool._test_conn
    mock_conn.execute.assert_called_once()
    call_args = mock_conn.execute.call_args
    sql = call_args[0][0]
    
    assert "INSERT INTO access_audit_log" in sql
    assert user_kerberos_id in call_args[0]
    assert document_id in call_args[0]
    assert action in call_args[0]
    assert result in call_args[0]
    assert reason in call_args[0]


@pytest.mark.asyncio
async def test_get_document_audit_trail(audit_logger, mock_pool):
    """Test retrieving audit trail for a document."""
    document_id = uuid4()
    
    # Mock return data
    mock_records = [
        {
            "id": uuid4(),
            "document_id": document_id,
            "user_kerberos_id": "user1",
            "action": "view",
            "result": "allowed",
            "reason": None,
            "ip_address": "192.168.1.1",
            "occurred_at": datetime.now()
        },
        {
            "id": uuid4(),
            "document_id": document_id,
            "user_kerberos_id": "user2",
            "action": "edit",
            "result": "denied",
            "reason": "Insufficient permissions",
            "ip_address": "192.168.1.2",
            "occurred_at": datetime.now()
        }
    ]
    
    # Configure mock connection
    mock_conn = mock_pool._test_conn
    mock_conn.fetch.return_value = mock_records
    
    # Get audit trail
    entries = await audit_logger.get_document_audit_trail(document_id, limit=10)
    
    # Verify fetch was called correctly
    mock_conn.fetch.assert_called_once()
    call_args = mock_conn.fetch.call_args
    sql = call_args[0][0]
    
    assert "SELECT" in sql
    assert "FROM access_audit_log" in sql
    assert "WHERE document_id = $1" in sql
    assert "ORDER BY occurred_at DESC" in sql
    assert call_args[0][1] == document_id
    assert call_args[0][2] == 10
    
    # Verify returned entries
    assert len(entries) == 2
    assert all(isinstance(e, dict) for e in entries)
    assert entries[0]["user_kerberos_id"] == "user1"
    assert entries[0]["result"] == "allowed"
    assert entries[1]["user_kerberos_id"] == "user2"
    assert entries[1]["result"] == "denied"


@pytest.mark.asyncio
async def test_get_user_audit_trail(audit_logger, mock_pool):
    """Test retrieving audit trail for a user."""
    user_kerberos_id = "testuser"
    
    # Mock return data
    mock_records = [
        {
            "id": uuid4(),
            "document_id": uuid4(),
            "user_kerberos_id": user_kerberos_id,
            "action": "view",
            "result": "allowed",
            "reason": None,
            "ip_address": "192.168.1.1",
            "occurred_at": datetime.now()
        }
    ]
    
    # Configure mock connection
    mock_conn = mock_pool._test_conn
    mock_conn.fetch.return_value = mock_records
    
    # Get audit trail
    entries = await audit_logger.get_user_audit_trail(user_kerberos_id, limit=20)
    
    # Verify fetch was called correctly
    mock_conn.fetch.assert_called_once()
    call_args = mock_conn.fetch.call_args
    sql = call_args[0][0]
    
    assert "SELECT" in sql
    assert "FROM access_audit_log" in sql
    assert "WHERE user_kerberos_id = $1" in sql
    assert "ORDER BY occurred_at DESC" in sql
    assert call_args[0][1] == user_kerberos_id
    assert call_args[0][2] == 20
    
    # Verify returned entries
    assert len(entries) == 1
    assert entries[0]["user_kerberos_id"] == user_kerberos_id


@pytest.mark.asyncio
async def test_get_denied_access_attempts(audit_logger, mock_pool):
    """Test retrieving recent denied access attempts."""
    # Mock return data
    mock_records = [
        {
            "id": uuid4(),
            "document_id": uuid4(),
            "user_kerberos_id": "user1",
            "action": "edit",
            "result": "denied",
            "reason": "Insufficient role",
            "ip_address": "192.168.1.1",
            "occurred_at": datetime.now()
        },
        {
            "id": uuid4(),
            "document_id": uuid4(),
            "user_kerberos_id": "user2",
            "action": "delete",
            "result": "denied",
            "reason": "Not owner",
            "ip_address": "192.168.1.2",
            "occurred_at": datetime.now()
        }
    ]
    
    # Configure mock connection
    mock_conn = mock_pool._test_conn
    mock_conn.fetch.return_value = mock_records
    
    # Get denied attempts
    entries = await audit_logger.get_denied_access_attempts(hours=24, limit=50)
    
    # Verify fetch was called correctly
    mock_conn.fetch.assert_called_once()
    call_args = mock_conn.fetch.call_args
    sql = call_args[0][0]
    
    assert "SELECT" in sql
    assert "FROM access_audit_log" in sql
    assert "WHERE result = 'denied'" in sql
    assert "AND occurred_at >=" in sql
    assert "ORDER BY occurred_at DESC" in sql
    assert call_args[0][1] == 50  # limit parameter
    
    # Verify returned entries
    assert len(entries) == 2
    assert all(e["result"] == "denied" for e in entries)
    assert all(e["reason"] is not None for e in entries)


@pytest.mark.asyncio
async def test_get_audit_trail_empty_results(audit_logger, mock_pool):
    """Test getting audit trail with no results."""
    document_id = uuid4()
    
    # Configure mock connection
    mock_conn = mock_pool._test_conn
    mock_conn.fetch.return_value = []
    
    entries = await audit_logger.get_document_audit_trail(document_id)
    
    assert entries == []
