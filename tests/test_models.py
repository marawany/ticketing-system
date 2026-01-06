"""Tests for Pydantic models."""

import pytest
from uuid import uuid4
from datetime import datetime

from nexusflow.models.ticket import (
    Ticket,
    TicketCreate,
    TicketStatus,
    TicketPriority,
)
from nexusflow.models.classification import (
    ClassificationLevel,
    ConfidenceScore,
    GraphPath,
)
from nexusflow.models.user import User, UserRole


class TestTicketModels:
    """Test ticket models."""
    
    def test_ticket_create(self):
        """Test creating a ticket."""
        ticket = TicketCreate(
            title="Test ticket",
            description="Test description",
            priority=TicketPriority.HIGH,
        )
        
        assert ticket.title == "Test ticket"
        assert ticket.description == "Test description"
        assert ticket.priority == TicketPriority.HIGH
    
    def test_ticket_defaults(self):
        """Test ticket default values."""
        ticket = TicketCreate(
            title="Test",
            description="Test",
        )
        
        assert ticket.priority == TicketPriority.MEDIUM
        assert ticket.source is None
        assert ticket.metadata == {}
    
    def test_full_ticket(self):
        """Test full ticket model."""
        ticket = Ticket(
            title="Test",
            description="Test description",
            level1_category="Technical Support",
            level2_category="Authentication",
            level3_category="Password Reset Issues",
            classification_confidence=0.92,
        )
        
        assert ticket.status == TicketStatus.NEW
        assert ticket.level1_category == "Technical Support"
        assert ticket.classification_confidence == 0.92


class TestClassificationModels:
    """Test classification models."""
    
    def test_classification_level(self):
        """Test classification level model."""
        level = ClassificationLevel(
            level=1,
            category="Technical Support",
            confidence=0.85,
        )
        
        assert level.level == 1
        assert level.category == "Technical Support"
        assert level.confidence == 0.85
    
    def test_confidence_score(self):
        """Test confidence score model."""
        score = ConfidenceScore(
            graph_confidence=0.88,
            vector_confidence=0.91,
            llm_confidence=0.85,
            raw_combined_score=0.88,
            calibrated_score=0.87,
            component_agreement=0.92,
            entropy=0.3,
        )
        
        assert score.is_high_confidence == True
        assert score.needs_review == False
    
    def test_confidence_needs_review(self):
        """Test confidence score requiring review."""
        score = ConfidenceScore(
            graph_confidence=0.4,
            vector_confidence=0.3,
            llm_confidence=0.5,
            raw_combined_score=0.4,
            calibrated_score=0.35,
            component_agreement=0.3,
            entropy=0.8,
        )
        
        assert score.is_high_confidence == False
        assert score.needs_review == True
    
    def test_graph_path(self):
        """Test graph path model."""
        path = GraphPath(
            path=[
                ClassificationLevel(level=1, category="Tech", confidence=0.9),
                ClassificationLevel(level=2, category="Auth", confidence=0.85),
                ClassificationLevel(level=3, category="Password", confidence=0.8),
            ],
            total_confidence=0.85,
        )
        
        assert path.full_path_string == "Tech > Auth > Password"
        assert len(path.path) == 3


class TestUserModels:
    """Test user models."""
    
    def test_user_creation(self):
        """Test user model."""
        user = User(
            email="test@example.com",
            full_name="Test User",
            role=UserRole.OPERATOR,
        )
        
        assert user.email == "test@example.com"
        assert user.role == UserRole.OPERATOR
        assert user.is_active == True
    
    def test_user_defaults(self):
        """Test user default values."""
        user = User(
            email="test@example.com",
            full_name="Test",
        )
        
        assert user.role == UserRole.VIEWER
        assert user.teams == []
        assert user.tickets_reviewed == 0

