"""Pytest configuration and fixtures."""

import pytest
import asyncio
from typing import Generator


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_ticket():
    """Sample ticket data for testing."""
    return {
        "title": "Cannot reset password after account lockout",
        "description": "I've been trying to reset my password but the reset link keeps expiring. This started after my account was locked due to failed login attempts.",
        "priority": "high",
    }


@pytest.fixture
def sample_tickets_batch():
    """Sample batch of tickets for testing."""
    return [
        {
            "title": "Payment failed but money deducted",
            "description": "My card was charged but the payment shows as failed",
            "priority": "critical",
        },
        {
            "title": "Need to upgrade subscription",
            "description": "Want to change from starter to pro plan",
            "priority": "medium",
        },
        {
            "title": "API returning 500 errors",
            "description": "Getting intermittent 500 errors from the /users endpoint",
            "priority": "high",
        },
    ]


@pytest.fixture
def sample_classification_result():
    """Sample classification result for testing."""
    return {
        "ticket_id": "test-123",
        "classification": {
            "level1": "Technical Support",
            "level2": "Authentication",
            "level3": "Password Reset Issues",
        },
        "confidence": {
            "graph_confidence": 0.88,
            "vector_confidence": 0.91,
            "llm_confidence": 0.85,
            "calibrated_score": 0.89,
            "component_agreement": 0.92,
        },
        "routing": {
            "requires_hitl": False,
            "hitl_reason": None,
            "auto_resolved": True,
        },
        "processing": {
            "time_ms": 234,
            "timestamp": "2024-01-15T10:30:00Z",
        },
    }


@pytest.fixture
def classification_hierarchy():
    """Sample classification hierarchy."""
    return {
        "Technical Support": {
            "Authentication": [
                "Password Reset Issues",
                "Two-Factor Authentication",
                "SSO Integration Problems",
            ],
            "Performance": [
                "Slow Response Time",
                "Timeout Errors",
            ],
        },
        "Billing & Payments": {
            "Invoicing": [
                "Missing Invoice",
                "Incorrect Amount",
            ],
            "Payment Processing": [
                "Failed Transactions",
                "Refund Requests",
            ],
        },
    }

