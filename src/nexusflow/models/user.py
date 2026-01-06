"""
User Data Models

Models for user management, authentication, and authorization.
"""

from datetime import datetime
from enum import Enum
from uuid import UUID, uuid4

from pydantic import BaseModel, EmailStr, Field


class UserRole(str, Enum):
    """User roles for authorization."""

    ADMIN = "admin"
    OPERATOR = "operator"
    REVIEWER = "reviewer"
    VIEWER = "viewer"


class UserBase(BaseModel):
    """Base user model with common fields."""

    email: EmailStr = Field(..., description="User email address")
    full_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = Field(default=UserRole.VIEWER)
    is_active: bool = Field(default=True)
    department: str | None = None
    teams: list[str] = Field(default_factory=list)


class UserCreate(UserBase):
    """Model for creating a new user."""

    password: str = Field(..., min_length=8, description="User password")


class UserUpdate(BaseModel):
    """Model for updating an existing user."""

    email: EmailStr | None = None
    full_name: str | None = Field(None, min_length=1, max_length=100)
    role: UserRole | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8)
    department: str | None = None
    teams: list[str] | None = None


class User(UserBase):
    """Full user model with all fields."""

    id: UUID = Field(default_factory=uuid4)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    last_login: datetime | None = None

    # Activity tracking
    tickets_reviewed: int = Field(default=0)
    corrections_made: int = Field(default=0)
    avg_review_time_seconds: float | None = None

    class Config:
        from_attributes = True
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440000",
                "email": "user@example.com",
                "full_name": "John Doe",
                "role": "operator",
                "is_active": True,
                "department": "Customer Support",
                "teams": ["tier1", "escalations"],
            }
        }


class UserInDB(User):
    """User model with hashed password for database storage."""

    hashed_password: str


class Token(BaseModel):
    """JWT token response model."""

    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: User


class TokenData(BaseModel):
    """Data extracted from JWT token."""

    user_id: UUID | None = None
    email: str | None = None
    role: UserRole | None = None
    scopes: list[str] = Field(default_factory=list)


class LoginRequest(BaseModel):
    """User login request."""

    email: EmailStr
    password: str


class PasswordChange(BaseModel):
    """Password change request."""

    current_password: str
    new_password: str = Field(..., min_length=8)


class UserStats(BaseModel):
    """User statistics for dashboard."""

    user_id: UUID
    total_reviews: int
    corrections_submitted: int
    accuracy_rate: float
    avg_review_time: float
    reviews_today: int
    reviews_this_week: int
    reviews_this_month: int
