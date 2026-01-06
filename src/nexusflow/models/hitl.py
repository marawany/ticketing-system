"""
Human-in-the-Loop (HITL) Data Models

Models for managing human review tasks and corrections.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class HITLStatus(str, Enum):
    """Status of HITL review tasks."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    SKIPPED = "skipped"
    ESCALATED = "escalated"


class HITLPriority(str, Enum):
    """Priority levels for HITL tasks."""

    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class HITLTask(BaseModel):
    """A task requiring human review."""

    id: UUID = Field(default_factory=uuid4)
    ticket_id: UUID

    # Original ticket info
    ticket_title: str
    ticket_description: str
    ticket_source: str | None = None

    # AI classification (to be reviewed)
    ai_level1: str
    ai_level2: str
    ai_level3: str
    ai_confidence: float

    # Reason for HITL routing
    routing_reason: str
    confidence_details: dict[str, float] = Field(default_factory=dict)

    # Task metadata
    status: HITLStatus = Field(default=HITLStatus.PENDING)
    priority: HITLPriority = Field(default=HITLPriority.NORMAL)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Assignment
    assigned_to: UUID | None = None
    assigned_at: datetime | None = None

    # Completion
    completed_by: UUID | None = None
    completed_at: datetime | None = None
    review_time_seconds: int | None = None

    # Similar tickets for reference
    similar_tickets: list[dict[str, Any]] = Field(default_factory=list)

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "ticket_id": "660e8400-e29b-41d4-a716-446655440001",
                "ticket_title": "Payment not processed",
                "ticket_description": "Customer reports payment stuck in pending state",
                "ai_level1": "Billing",
                "ai_level2": "Payments",
                "ai_level3": "Processing Issues",
                "ai_confidence": 0.45,
                "routing_reason": "Low confidence score",
                "status": "pending",
                "priority": "high",
            }
        }


class HITLCorrection(BaseModel):
    """A correction submitted by a human reviewer."""

    id: UUID = Field(default_factory=uuid4)
    task_id: UUID
    ticket_id: UUID
    reviewer_id: UUID

    # Original AI classification
    original_level1: str
    original_level2: str
    original_level3: str
    original_confidence: float

    # Human correction
    corrected_level1: str
    corrected_level2: str
    corrected_level3: str

    # Correction details
    is_correct: bool = Field(..., description="True if AI was correct, False if corrected")
    correction_notes: str | None = None
    confidence_feedback: str | None = Field(None, description="Feedback on confidence calibration")

    # Metadata
    submitted_at: datetime = Field(default_factory=datetime.utcnow)
    review_time_seconds: int

    # Learning signal
    should_update_graph: bool = Field(default=True)
    should_retrain_model: bool = Field(default=False)

    # Additional context
    tags: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "ticket_id": "660e8400-e29b-41d4-a716-446655440001",
                "reviewer_id": "770e8400-e29b-41d4-a716-446655440002",
                "original_level1": "Billing",
                "original_level2": "Payments",
                "original_level3": "Processing Issues",
                "original_confidence": 0.45,
                "corrected_level1": "Technical Support",
                "corrected_level2": "Integration",
                "corrected_level3": "API Errors",
                "is_correct": False,
                "correction_notes": "This is actually an API integration issue, not a billing problem",
                "review_time_seconds": 45,
            }
        }


class HITLTaskCreate(BaseModel):
    """Model for creating a HITL task."""

    ticket_id: UUID
    ticket_title: str
    ticket_description: str
    ticket_source: str | None = None
    ai_level1: str
    ai_level2: str
    ai_level3: str
    ai_confidence: float
    routing_reason: str
    confidence_details: dict[str, float] = Field(default_factory=dict)
    priority: HITLPriority = Field(default=HITLPriority.NORMAL)
    similar_tickets: list[dict[str, Any]] = Field(default_factory=list)


class HITLCorrectionCreate(BaseModel):
    """Model for submitting a HITL correction."""

    task_id: UUID
    corrected_level1: str
    corrected_level2: str
    corrected_level3: str
    is_correct: bool
    correction_notes: str | None = None
    confidence_feedback: str | None = None
    review_time_seconds: int


class HITLStats(BaseModel):
    """Statistics for HITL dashboard."""

    total_pending: int
    total_in_progress: int
    total_completed_today: int
    total_completed_week: int

    avg_review_time_seconds: float
    ai_accuracy_rate: float
    correction_rate: float

    tasks_by_priority: dict[str, int]
    tasks_by_routing_reason: dict[str, int]

    top_correction_categories: list[dict[str, Any]]
    reviewer_leaderboard: list[dict[str, Any]]


class HITLQueueFilters(BaseModel):
    """Filters for HITL task queue."""

    status: list[HITLStatus] | None = None
    priority: list[HITLPriority] | None = None
    assigned_to: UUID | None = None
    unassigned_only: bool = False
    min_confidence: float | None = None
    max_confidence: float | None = None
    created_after: datetime | None = None
    created_before: datetime | None = None
    limit: int = Field(default=50, ge=1, le=200)
    offset: int = Field(default=0, ge=0)
