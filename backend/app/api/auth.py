"""Authentication API endpoints using Supabase Auth."""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.supabase_client import supabase
from app.core.security import get_current_user_id
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
    Create a new user account using Supabase Auth.

    - **email**: Valid email address
    - **password**: Minimum 8 characters (enforced by Supabase)

    Returns access token for immediate use.
    """
    try:
        # Supabase handles password validation and hashing automatically
        auth_response = supabase.auth.sign_up({
            "email": request.email,
            "password": request.password
        })

        if not auth_response.user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create user account"
            )

        user_id = auth_response.user.id

        # Check if session was created (email confirmation may be required)
        if not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email confirmation required. Please check your email or disable email confirmation in Supabase dashboard (Settings > Auth > Email Provider > Disable 'Enable email confirmations')"
            )

        access_token = auth_response.session.access_token
        if not access_token:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to generate access token"
            )

        # Sync user to local database for application data (documents, etc.)
        existing_user = db.query(User).filter(User.id == user_id).first()
        if not existing_user:
            new_user = User(
                id=user_id,
                email=request.email,
                hashed_password=""  # Managed by Supabase Auth
            )
            try:
                db.add(new_user)
                db.commit()
                db.refresh(new_user)
            except Exception:
                db.rollback()
                # Continue even if local sync fails - auth still succeeded

        return AuthResponse(
            access_token=access_token,
            user_id=user_id,
            email=request.email
        )

    except Exception as e:
        error_message = str(e)

        # Handle common Supabase Auth errors
        if "already registered" in error_message.lower() or "already exists" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
        elif "password" in error_message.lower() and "short" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        elif "invalid" in error_message.lower() and "email" in error_message.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format"
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {error_message}"
            )


@router.post("/auth/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    """
    Login with email and password using Supabase Auth.

    - **email**: Registered email address
    - **password**: Account password

    Returns access token managed by Supabase.
    """
    try:
        # Supabase handles password verification and hashing automatically
        auth_response = supabase.auth.sign_in_with_password({
            "email": request.email,
            "password": request.password
        })

        if not auth_response.user or not auth_response.session:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = auth_response.user.id
        access_token = auth_response.session.access_token

        # Check local user status
        user = db.query(User).filter(User.id == user_id).first()
        if user and not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )

        # Sync user to local database if not exists
        if not user:
            new_user = User(
                id=user_id,
                email=request.email,
                hashed_password=""  # Managed by Supabase Auth
            )
            try:
                db.add(new_user)
                db.commit()
            except Exception:
                db.rollback()

        return AuthResponse(
            access_token=access_token,
            user_id=user_id,
            email=request.email
        )

    except HTTPException:
        raise
    except Exception as e:
        error_message = str(e)

        # Handle common Supabase Auth errors
        if "invalid" in error_message.lower() and ("credentials" in error_message.lower() or "login" in error_message.lower()):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication error: {error_message}"
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
