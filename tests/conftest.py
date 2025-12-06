import pytest
from uuid import uuid4
from datetime import datetime, timezone


@pytest.fixture
def sample_uuid():
    return uuid4()


@pytest.fixture
def sample_datetime():
    return datetime.now(timezone.utc)


@pytest.fixture
def sample_document_data():
    return {
        "filename": "trading_algorithm_spec.pdf",
        "content": b"sample content bytes",
        "content_type": "application/pdf",
        "title": "Trading Algorithm Specification",
        "uploaded_by": "user@example.com"
    }


@pytest.fixture
def sample_markdown_content():
    return """# Trading Algorithm Specification

## Overview
This document describes the momentum-based trading algorithm.

## Entry Conditions
- RSI crosses above 30
- Price above 200-day moving average

## Exit Conditions  
- RSI crosses below 70
- Stop loss at 2%
"""


@pytest.fixture
def sample_sections():
    return [
        {"heading": "Overview", "content": "This document describes...", "level": 2},
        {"heading": "Entry Conditions", "content": "RSI crosses above 30...", "level": 2},
        {"heading": "Exit Conditions", "content": "RSI crosses below 70...", "level": 2}
    ]


@pytest.fixture
def sample_feedback_data():
    return {
        "section": "Entry Conditions",
        "issue": "Missing specific RSI threshold duration",
        "suggestion": "Specify how long RSI must remain above 30 before triggering entry",
        "original_text": "RSI crosses above 30",
        "suggested_text": "RSI crosses above 30 and remains above for 2 consecutive bars",
        "confidence": 0.85,
        "policy_reference": "SEC-001"
    }


@pytest.fixture
def sample_policy_data():
    return {
        "name": "SEC Index Publishing",
        "description": "Requirements for SEC index methodology documents",
        "jurisdiction": "US",
        "policies": [
            {
                "name": "Entry/Exit Conditions Required",
                "description": "Document must specify clear entry and exit conditions",
                "requirement_type": "MUST",
                "validation_rules": []
            }
        ]
    }
