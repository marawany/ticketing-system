"""
Classification Data Models

Models for classification results, confidence scores, and processing details.
"""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class ClassificationLevel(BaseModel):
    """Represents a single level in the classification hierarchy."""

    level: int = Field(..., ge=1, le=3, description="Classification level (1-3)")
    category: str = Field(..., description="Category name at this level")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score")
    node_id: str | None = Field(None, description="Neo4j node ID")
    description: str | None = None
    examples: list[str] | None = None


class GraphPath(BaseModel):
    """Represents a path through the classification graph."""

    path: list[ClassificationLevel] = Field(..., description="Ordered list of levels")
    total_confidence: float = Field(..., ge=0.0, le=1.0)
    path_weight: float = Field(default=1.0, description="Weight based on historical accuracy")
    traversal_time_ms: int | None = None

    @property
    def full_path_string(self) -> str:
        """Get string representation of the path."""
        return " > ".join([level.category for level in self.path])


class VectorMatch(BaseModel):
    """Represents a similar ticket found via vector search."""

    ticket_id: UUID
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    title: str
    description_snippet: str
    level1_category: str
    level2_category: str
    level3_category: str
    was_correct: bool | None = Field(None, description="Whether this classification was validated")
    matched_at: datetime = Field(default_factory=datetime.utcnow)


class ConfidenceScore(BaseModel):
    """
    Confidence score calculation using ensemble methods.

    Combines graph traversal confidence, vector similarity, and LLM judgment
    using weighted ensemble and calibration techniques.
    """

    # Individual component scores
    graph_confidence: float = Field(..., ge=0.0, le=1.0)
    vector_confidence: float = Field(..., ge=0.0, le=1.0)
    llm_confidence: float = Field(..., ge=0.0, le=1.0)

    # Ensemble weights (learned from historical data)
    graph_weight: float = Field(default=0.35)
    vector_weight: float = Field(default=0.35)
    llm_weight: float = Field(default=0.30)

    # Final scores
    raw_combined_score: float = Field(..., ge=0.0, le=1.0)
    calibrated_score: float = Field(..., ge=0.0, le=1.0, description="After Platt scaling")

    # Agreement metrics
    component_agreement: float = Field(
        ..., ge=0.0, le=1.0, description="Agreement between components"
    )
    entropy: float = Field(..., ge=0.0, description="Prediction entropy")

    # Calibration metadata
    calibration_method: str = Field(default="platt_scaling")
    calibration_temperature: float = Field(default=1.0)

    @property
    def is_high_confidence(self) -> bool:
        """Check if confidence exceeds threshold for auto-resolution."""
        return self.calibrated_score >= 0.7 and self.component_agreement >= 0.6

    @property
    def needs_review(self) -> bool:
        """Check if ticket should be routed to HITL."""
        return self.calibrated_score < 0.5 or self.component_agreement < 0.4


class LLMJudgment(BaseModel):
    """LLM's final judgment on the classification."""

    model_name: str
    classification_path: list[str] = Field(..., description="[level1, level2, level3]")
    confidence: float = Field(..., ge=0.0, le=1.0)
    reasoning: str = Field(..., description="Explanation of the classification decision")
    alternative_paths: list[dict[str, Any]] | None = None
    tokens_used: int = 0
    latency_ms: int = 0


class ClassificationResult(BaseModel):
    """Complete classification result with all processing details."""

    ticket_id: UUID

    # Final classification
    level1_category: str
    level2_category: str
    level3_category: str

    # Full path through hierarchy
    classification_path: GraphPath

    # Supporting evidence
    graph_paths: list[GraphPath] = Field(default_factory=list)
    vector_matches: list[VectorMatch] = Field(default_factory=list)
    llm_judgment: LLMJudgment

    # Confidence assessment
    confidence: ConfidenceScore

    # Processing metadata
    processed_at: datetime = Field(default_factory=datetime.utcnow)
    processing_time_ms: int
    agent_version: str = "1.0.0"

    # Status
    is_auto_resolved: bool = False
    requires_hitl: bool = False
    hitl_reason: str | None = None

    class Config:
        json_schema_extra = {
            "example": {
                "ticket_id": "550e8400-e29b-41d4-a716-446655440000",
                "level1_category": "Technical Support",
                "level2_category": "Authentication",
                "level3_category": "Password Reset Issues",
                "confidence": {
                    "graph_confidence": 0.88,
                    "vector_confidence": 0.91,
                    "llm_confidence": 0.85,
                    "calibrated_score": 0.89,
                    "component_agreement": 0.92,
                },
                "is_auto_resolved": True,
                "requires_hitl": False,
            }
        }


class Classification(BaseModel):
    """Simplified classification model for API responses."""

    ticket_id: UUID
    level1: str
    level2: str
    level3: str
    confidence: float
    auto_resolved: bool
    processed_at: datetime


class BatchClassificationResult(BaseModel):
    """Results from batch classification processing."""

    batch_id: str
    total_tickets: int
    successful: int
    failed: int
    auto_resolved: int
    requires_hitl: int
    results: list[ClassificationResult]
    processing_time_ms: int
    started_at: datetime
    completed_at: datetime
