"""
Ticket Data Models

Core models for ticket representation and management.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class TicketStatus(str, Enum):
    """Ticket processing status."""

    NEW = "new"
    PROCESSING = "processing"
    CLASSIFIED = "classified"
    RESOLVED = "resolved"
    PENDING_REVIEW = "pending_review"
    ESCALATED = "escalated"
    CLOSED = "closed"


class TicketPriority(str, Enum):
    """Ticket priority levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class TicketBase(BaseModel):
    """Base ticket model with common fields."""

    title: str = Field(..., min_length=1, max_length=500, description="Ticket title")
    description: str = Field(..., min_length=1, description="Ticket description")
    priority: TicketPriority = Field(default=TicketPriority.MEDIUM)
    source: str | None = Field(default=None, description="Ticket source system")
    customer_id: str | None = Field(default=None, description="Customer identifier")
    metadata: dict[str, Any] = Field(default_factory=dict)


class TicketCreate(TicketBase):
    """Model for creating a new ticket."""

    pass


class TicketUpdate(BaseModel):
    """Model for updating an existing ticket."""

    title: str | None = Field(None, min_length=1, max_length=500)
    description: str | None = Field(None, min_length=1)
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    metadata: dict[str, Any] | None = None


class Ticket(TicketBase):
    """Full ticket model with all fields."""

    id: UUID = Field(default_factory=uuid4)
    status: TicketStatus = Field(default=TicketStatus.NEW)

    # Classification results
    level1_category: str | None = None
    level2_category: str | None = None
    level3_category: str | None = None
    classification_confidence: float | None = None

    # Processing metadata
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    classified_at: datetime | None = None
    resolved_at: datetime | None = None

    # Processing info
    processing_time_ms: int | None = None
    assigned_to: str | None = None
    resolution: str | None = None

    # Embeddings (not exposed in API, used internally)
    embedding: list[float] | None = Field(default=None, exclude=True)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "title": "Cannot access email after password reset",
                "description": "User reports being unable to login to email after resetting password yesterday. Error message shows 'invalid credentials'.",
                "priority": "high",
                "status": "classified",
                "level1_category": "Technical Support",
                "level2_category": "Authentication",
                "level3_category": "Password Reset Issues",
                "classification_confidence": 0.92,
                "source": "email",
                "customer_id": "CUST-12345",
            }
        }


class TicketBatch(BaseModel):
    """Model for batch ticket processing."""

    tickets: list[TicketCreate] = Field(..., min_length=1, max_length=1000)
    batch_id: str | None = None
    priority_override: TicketPriority | None = None
    callback_url: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "tickets": [
                    {"title": "Ticket 1", "description": "Description 1", "priority": "medium"},
                    {"title": "Ticket 2", "description": "Description 2", "priority": "high"},
                ],
                "batch_id": "BATCH-001",
                "callback_url": "https://api.example.com/webhooks/nexusflow",
            }
        }


class TicketSearchQuery(BaseModel):
    """Model for ticket search queries."""

    query: str = Field(..., min_length=1, description="Search query text")
    limit: int = Field(default=10, ge=1, le=100)
    status_filter: list[TicketStatus] | None = None
    priority_filter: list[TicketPriority] | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None
    include_resolved: bool = False
