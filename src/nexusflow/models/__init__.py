"""
NexusFlow Data Models

Pydantic models for tickets, classifications, and system entities.
"""

from nexusflow.models.classification import (
    Classification,
    ClassificationLevel,
    ClassificationResult,
    ConfidenceScore,
    GraphPath,
    LLMJudgment,
    VectorMatch,
)
from nexusflow.models.hitl import (
    HITLCorrection,
    HITLStatus,
    HITLTask,
)
from nexusflow.models.ticket import (
    Ticket,
    TicketBatch,
    TicketCreate,
    TicketPriority,
    TicketStatus,
    TicketUpdate,
)
from nexusflow.models.user import (
    Token,
    TokenData,
    User,
    UserCreate,
    UserRole,
    UserUpdate,
)

__all__ = [
    # Ticket models
    "Ticket",
    "TicketCreate",
    "TicketUpdate",
    "TicketBatch",
    "TicketStatus",
    "TicketPriority",
    # Classification models
    "Classification",
    "ClassificationResult",
    "ClassificationLevel",
    "ConfidenceScore",
    "GraphPath",
    "VectorMatch",
    "LLMJudgment",
    # User models
    "User",
    "UserCreate",
    "UserUpdate",
    "UserRole",
    "Token",
    "TokenData",
    # HITL models
    "HITLTask",
    "HITLCorrection",
    "HITLStatus",
]
