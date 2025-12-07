"""Shared fixtures for end-to-end integration tests."""
import os
import pytest
import asyncio
from typing import AsyncGenerator
from uuid import uuid4

import asyncpg
from httpx import AsyncClient, ASGITransport

from src.api.main import create_app
from src.api.dependencies import Container, get_settings


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def db_pool():
    settings = get_settings()
    if not settings.database_url:
        pytest.skip("DATABASE_URL not set")
    
    pool = await asyncpg.create_pool(
        settings.database_url,
        min_size=2,
        max_size=5,
    )
    yield pool
    await pool.close()


@pytest.fixture(autouse=True)
async def reset_container():
    Container._instance = None
    Container._pool = None
    yield
    if Container._instance:
        await Container._instance.close()
    Container._instance = None
    Container._pool = None


@pytest.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_markdown_file():
    content = b"""# Trading Algorithm Specification

## Overview
This document describes a momentum-based trading algorithm for equities.

## Entry Conditions
- RSI crosses above 30
- Price is above the 200-day moving average
- Volume is at least 1.5x average

## Exit Conditions
- RSI crosses below 70
- Stop loss triggered at 2%
- Take profit at 5%

## Risk Parameters
- Maximum position size: 5% of portfolio
- Maximum daily loss: 2%
- Maximum drawdown: 10%
"""
    return content


@pytest.fixture
def sample_pdf_content():
    return b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\ntrailer\n<< /Root 1 0 R >>\n%%EOF"


@pytest.fixture
def sample_policy_data():
    return {
        "name": f"Test Policy Repository {uuid4().hex[:8]}",
        "description": "Test policy repository for E2E tests",
    }


@pytest.fixture
def sample_policy_rule():
    return {
        "name": "Entry/Exit Conditions Required",
        "description": "Trading documents must specify clear entry and exit conditions",
        "requirement_type": "MUST",
        "validation_rules": ["entry_conditions", "exit_conditions"],
    }
