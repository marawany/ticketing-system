"""
SQLAlchemy Database Models

Persistent storage models for tickets, users, HITL tasks, and corrections.
"""

from datetime import datetime
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
)
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship


def generate_uuid() -> str:
    return str(uuid4())


class Base(AsyncAttrs, DeclarativeBase):
    """Base class for all models."""

    pass


class TicketDB(Base):
    """Ticket database model."""

    __tablename__ = "tickets"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String(20), default="medium")
    status = Column(String(20), default="new")
    source = Column(String(100), nullable=True)
    customer_id = Column(String(100), nullable=True)
    extra_data = Column(JSON, default=dict)

    # Classification results
    level1_category = Column(String(100), nullable=True)
    level2_category = Column(String(100), nullable=True)
    level3_category = Column(String(100), nullable=True)
    classification_confidence = Column(Float, nullable=True)

    # Processing metadata
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    classified_at = Column(DateTime, nullable=True)
    resolved_at = Column(DateTime, nullable=True)

    # Processing info
    processing_time_ms = Column(Integer, nullable=True)
    assigned_to = Column(String(36), nullable=True)
    resolution = Column(Text, nullable=True)

    # Relationships
    hitl_tasks = relationship("HITLTaskDB", back_populates="ticket")


class UserDB(Base):
    """User database model."""

    __tablename__ = "users"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    email = Column(String(255), unique=True, nullable=False, index=True)
    full_name = Column(String(100), nullable=False)
    hashed_password = Column(String(255), nullable=False)
    role = Column(String(20), default="viewer")
    is_active = Column(Boolean, default=True)
    department = Column(String(100), nullable=True)
    teams = Column(JSON, default=list)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime, nullable=True)

    # Activity tracking
    tickets_reviewed = Column(Integer, default=0)
    corrections_made = Column(Integer, default=0)
    avg_review_time_seconds = Column(Float, nullable=True)

    # Relationships
    hitl_tasks = relationship(
        "HITLTaskDB", back_populates="assigned_user", foreign_keys="HITLTaskDB.assigned_to"
    )
    corrections = relationship("HITLCorrectionDB", back_populates="reviewer")


class HITLTaskDB(Base):
    """HITL Task database model."""

    __tablename__ = "hitl_tasks"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)

    # Original ticket info (denormalized for quick access)
    ticket_title = Column(String(500), nullable=False)
    ticket_description = Column(Text, nullable=False)
    ticket_source = Column(String(100), nullable=True)

    # AI classification (to be reviewed)
    ai_level1 = Column(String(100), nullable=False)
    ai_level2 = Column(String(100), nullable=False)
    ai_level3 = Column(String(100), nullable=False)
    ai_confidence = Column(Float, nullable=False)

    # Reason for HITL routing
    routing_reason = Column(String(500), nullable=False)
    confidence_details = Column(JSON, default=dict)

    # Task metadata
    status = Column(String(20), default="pending")
    priority = Column(String(20), default="normal")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Assignment
    assigned_to = Column(String(36), ForeignKey("users.id"), nullable=True)
    assigned_at = Column(DateTime, nullable=True)

    # Completion
    completed_by = Column(String(36), nullable=True)
    completed_at = Column(DateTime, nullable=True)
    review_time_seconds = Column(Integer, nullable=True)

    # Similar tickets for reference (stored as JSON)
    similar_tickets = Column(JSON, default=list)

    # Relationships
    ticket = relationship("TicketDB", back_populates="hitl_tasks")
    assigned_user = relationship("UserDB", back_populates="hitl_tasks", foreign_keys=[assigned_to])
    correction = relationship("HITLCorrectionDB", back_populates="task", uselist=False)


class HITLCorrectionDB(Base):
    """HITL Correction database model."""

    __tablename__ = "hitl_corrections"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    task_id = Column(String(36), ForeignKey("hitl_tasks.id"), nullable=False)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)
    reviewer_id = Column(String(36), ForeignKey("users.id"), nullable=False)

    # Original AI classification
    original_level1 = Column(String(100), nullable=False)
    original_level2 = Column(String(100), nullable=False)
    original_level3 = Column(String(100), nullable=False)
    original_confidence = Column(Float, nullable=False)

    # Human correction
    corrected_level1 = Column(String(100), nullable=False)
    corrected_level2 = Column(String(100), nullable=False)
    corrected_level3 = Column(String(100), nullable=False)

    # Correction details
    is_correct = Column(Boolean, nullable=False)
    correction_notes = Column(Text, nullable=True)
    confidence_feedback = Column(String(500), nullable=True)

    # Metadata
    submitted_at = Column(DateTime, default=datetime.utcnow)
    review_time_seconds = Column(Integer, nullable=False)

    # Learning signal
    should_update_graph = Column(Boolean, default=True)
    should_retrain_model = Column(Boolean, default=False)

    # Additional context
    tags = Column(JSON, default=list)
    extra_data = Column(JSON, default=dict)

    # Relationships
    task = relationship("HITLTaskDB", back_populates="correction")
    reviewer = relationship("UserDB", back_populates="corrections")


class BatchJobDB(Base):
    """Batch processing job database model."""

    __tablename__ = "batch_jobs"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    batch_id = Column(String(100), unique=True, nullable=False, index=True)

    # Job metadata
    ticket_count = Column(Integer, nullable=False)
    status = Column(String(20), default="pending")
    progress = Column(Integer, default=0)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Results
    successful = Column(Integer, default=0)
    failed = Column(Integer, default=0)
    auto_resolved = Column(Integer, default=0)
    requires_hitl = Column(Integer, default=0)

    # Callback
    callback_url = Column(String(500), nullable=True)

    # Error info
    error = Column(Text, nullable=True)

    # Results data (stored as JSON)
    results = Column(JSON, default=list)


class ClassificationMetricsDB(Base):
    """Classification metrics for analytics."""

    __tablename__ = "classification_metrics"

    id = Column(String(36), primary_key=True, default=generate_uuid)
    ticket_id = Column(String(36), ForeignKey("tickets.id"), nullable=False)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Classification
    level1 = Column(String(100), nullable=False)
    level2 = Column(String(100), nullable=False)
    level3 = Column(String(100), nullable=False)

    # Confidence scores
    graph_confidence = Column(Float, nullable=False)
    vector_confidence = Column(Float, nullable=False)
    llm_confidence = Column(Float, nullable=False)
    final_confidence = Column(Float, nullable=False)
    component_agreement = Column(Float, nullable=False)

    # Routing
    auto_resolved = Column(Boolean, nullable=False)
    requires_hitl = Column(Boolean, nullable=False)

    # Processing
    processing_time_ms = Column(Integer, nullable=False)

    # Later validation
    was_correct = Column(Boolean, nullable=True)  # Filled after HITL review
