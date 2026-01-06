"""
User Management Routes

Endpoints for user authentication and management.
"""

from datetime import datetime, timedelta
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

from nexusflow.config import settings
from nexusflow.db.repository import UserRepository
from nexusflow.models.user import (
    LoginRequest,
    PasswordChange,
    Token,
    TokenData,
    User,
    UserCreate,
    UserRole,
    UserStats,
    UserUpdate,
)

router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Security
security = HTTPBearer(auto_error=False)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash."""
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: timedelta = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.jwt_access_token_expire_minutes)

    to_encode.update({"exp": expire})

    encoded_jwt = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return encoded_jwt


def db_to_model(db_user) -> User:
    """Convert database user to Pydantic model."""
    return User(
        id=UUID(db_user.id),
        email=db_user.email,
        full_name=db_user.full_name,
        role=UserRole(db_user.role),
        is_active=db_user.is_active,
        department=db_user.department,
        teams=db_user.teams or [],
        created_at=db_user.created_at,
        updated_at=db_user.updated_at,
        last_login=db_user.last_login,
        tickets_reviewed=db_user.tickets_reviewed,
        corrections_made=db_user.corrections_made,
        avg_review_time_seconds=db_user.avg_review_time_seconds,
    )


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> User | None:
    """Get the current authenticated user."""
    # Ensure admin exists
    admin_hash = get_password_hash("admin123")
    admin_db = await UserRepository.ensure_admin_exists(admin_hash)

    if not settings.enable_auth:
        return db_to_model(admin_db)

    if not credentials:
        if settings.enable_test_auth_bypass:
            return db_to_model(admin_db)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        )

    try:
        payload = jwt.decode(
            credentials.credentials,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        user_id: str = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")

        token_data = TokenData(user_id=UUID(user_id))
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    db_user = await UserRepository.get(str(token_data.user_id))
    if db_user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return db_to_model(db_user)


async def require_admin(user: User = Depends(get_current_user)) -> User:
    """Require admin role."""
    if user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


class UserListResponse(BaseModel):
    """Response for user list."""

    users: list[User]
    total: int


@router.post("/login", response_model=Token)
async def login(request: LoginRequest):
    """
    Authenticate user and return JWT token.
    """
    db_user = await UserRepository.get_by_email(request.email)

    if not db_user or not verify_password(request.password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
        )

    if not db_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is disabled",
        )

    # Update last login
    await UserRepository.update_login(db_user.id)

    # Create token
    access_token = create_access_token(
        data={"sub": db_user.id, "role": db_user.role},
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        expires_in=settings.jwt_access_token_expire_minutes * 60,
        user=db_to_model(db_user),
    )


@router.post("/register", response_model=User)
async def register(user_data: UserCreate, admin: User = Depends(require_admin)):
    """
    Register a new user (admin only).
    """
    # Check if email exists
    existing = await UserRepository.get_by_email(user_data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    db_user = await UserRepository.create(
        email=user_data.email,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        role=user_data.role.value,
        department=user_data.department,
        teams=user_data.teams,
    )

    return db_to_model(db_user)


@router.get("/me", response_model=User)
async def get_current_user_info(user: User = Depends(get_current_user)):
    """
    Get current user information.
    """
    return user


@router.put("/me", response_model=User)
async def update_current_user(
    update: UserUpdate,
    user: User = Depends(get_current_user),
):
    """
    Update current user information.
    """
    update_data = update.model_dump(exclude_unset=True)

    # Handle password change separately
    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    # Convert role enum
    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value

    db_user = await UserRepository.update(str(user.id), **update_data)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return db_to_model(db_user)


@router.post("/me/change-password")
async def change_password(
    data: PasswordChange,
    user: User = Depends(get_current_user),
):
    """
    Change current user password.
    """
    db_user = await UserRepository.get(str(user.id))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    if not verify_password(data.current_password, db_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    await UserRepository.update(
        str(user.id),
        hashed_password=get_password_hash(data.new_password),
    )

    return {"message": "Password changed successfully"}


@router.get("", response_model=UserListResponse)
async def list_users(admin: User = Depends(require_admin)):
    """
    List all users (admin only).
    """
    db_users = await UserRepository.list()
    users = [db_to_model(u) for u in db_users]

    return UserListResponse(users=users, total=len(users))


@router.get("/{user_id}", response_model=User)
async def get_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
):
    """
    Get a user by ID (admin only).
    """
    db_user = await UserRepository.get(str(user_id))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    return db_to_model(db_user)


@router.put("/{user_id}", response_model=User)
async def update_user(
    user_id: UUID,
    update: UserUpdate,
    admin: User = Depends(require_admin),
):
    """
    Update a user (admin only).
    """
    existing = await UserRepository.get(str(user_id))
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    update_data = update.model_dump(exclude_unset=True)

    if "password" in update_data:
        update_data["hashed_password"] = get_password_hash(update_data.pop("password"))

    if "role" in update_data and update_data["role"]:
        update_data["role"] = update_data["role"].value

    db_user = await UserRepository.update(str(user_id), **update_data)

    return db_to_model(db_user)


@router.delete("/{user_id}")
async def delete_user(
    user_id: UUID,
    admin: User = Depends(require_admin),
):
    """
    Delete a user (admin only).
    """
    existing = await UserRepository.get(str(user_id))
    if not existing:
        raise HTTPException(status_code=404, detail="User not found")

    # Prevent self-deletion
    if str(user_id) == str(admin.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete your own account",
        )

    await UserRepository.delete(str(user_id))

    return {"message": "User deleted", "user_id": str(user_id)}


@router.get("/{user_id}/stats", response_model=UserStats)
async def get_user_stats(
    user_id: UUID,
    current_user: User = Depends(get_current_user),
):
    """
    Get user statistics.
    """
    # Users can view their own stats, admins can view anyone's
    if str(user_id) != str(current_user.id) and current_user.role != UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Not authorized")

    db_user = await UserRepository.get(str(user_id))
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Get correction stats
    from nexusflow.db.repository import HITLCorrectionRepository

    accuracy_rate = await HITLCorrectionRepository.get_accuracy_rate()
    avg_time = await HITLCorrectionRepository.get_avg_review_time()

    return UserStats(
        user_id=user_id,
        total_reviews=db_user.tickets_reviewed,
        corrections_submitted=db_user.corrections_made,
        accuracy_rate=accuracy_rate,
        avg_review_time=avg_time,
        reviews_today=0,  # Would need date filtering
        reviews_this_week=0,
        reviews_this_month=db_user.tickets_reviewed,
    )
