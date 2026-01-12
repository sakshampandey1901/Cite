"""Authentication API endpoints."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from datetime import timedelta

from app.core.security import (
    verify_password_and_update,
    get_password_hash,
    create_access_token,
    get_current_user_id
)
from app.models.database import get_db, User

router = APIRouter(tags=["authentication"])
security = HTTPBearer()


class SignupRequest(BaseModel):
    """Signup request model."""
    email: EmailStr
    password: str

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securepassword123"
            }
        }


class LoginRequest(BaseModel):
    """Login request model."""
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    """Authentication response model."""
    access_token: str
    token_type: str = "bearer"
    user_id: str
    email: str


@router.post("/auth/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(request: SignupRequest, db: Session = Depends(get_db)):
    """
    Create a new user account.

    - **email**: Valid email address
    - **password**: Minimum 8 characters

    Returns access token for immediate use.
    """
    # Validate password length
    if len(request.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )

    # Check if user already exists
    existing_user = db.query(User).filter(User.email == request.email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create new user
    hashed_password = get_password_hash(request.password)
    new_user = User(
        email=request.email,
        hashed_password=hashed_password
    )

    try:
        db.add(new_user)
        db.commit()
        db.refresh(new_user)
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user account"
        )

    # Generate access token
    access_token = create_access_token(
        data={"sub": new_user.id},
        expires_delta=timedelta(days=7)
    )

    return AuthResponse(
        access_token=access_token,
        user_id=new_user.id,
        email=new_user.email
    )


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password.

    - **email**: Registered email address
    - **password**: Account password

    Returns access token valid for 7 days.
    """
    # Find user by email
    user = db.query(User).filter(User.email == request.email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Verify password
    verified, upgraded_hash = verify_password_and_update(request.password, user.hashed_password)
    if not verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if upgraded_hash:
        try:
            user.hashed_password = upgraded_hash
            db.add(user)
            db.commit()
        except Exception:
            db.rollback()

    # Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )

    # Generate access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(days=7)
    )

    return AuthResponse(
        access_token=access_token,
        user_id=user.id,
        email=user.email
    )


@router.get("/auth/me")
async def get_current_user_info(user_id: str = Depends(get_current_user_id), db: Session = Depends(get_db)):
    """
    Get current user information.

    Requires authentication.
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    return {
        "user_id": user.id,
        "email": user.email,
        "created_at": user.created_at.isoformat(),
        "is_active": user.is_active
    }
