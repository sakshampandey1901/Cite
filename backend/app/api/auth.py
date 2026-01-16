"""Authentication API endpoints using Supabase Auth."""
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.supabase_client import get_supabase_client
from app.core.security import get_current_user_id
from app.models.database import get_db, User

logger = logging.getLogger(__name__)

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
        # Get Supabase client (with error handling)
        try:
            supabase = get_supabase_client()
        except ValueError as e:
            logger.error(f"Supabase client configuration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not properly configured. Please contact support."
            )
        except Exception as e:
            logger.error(f"Failed to get Supabase client: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable. Please try again later."
            )
        
        # Supabase handles password validation and hashing automatically
        try:
            auth_response = supabase.auth.sign_up({
                "email": request.email,
                "password": request.password
            })
        except Exception as supabase_error:
            error_str = str(supabase_error).lower()
            logger.warning(f"Supabase signup error: {supabase_error}")
            
            # Handle network/connection errors
            if "network" in error_str or "connection" in error_str or "timeout" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to connect to authentication service. Please check your internet connection and try again."
                )
            # Re-raise to be handled by outer exception handler
            raise

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

    except HTTPException:
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        error_message = str(e).lower()
        logger.error(f"Signup error: {e}", exc_info=True)

        # Handle common Supabase Auth errors
        if "already registered" in error_message or "already exists" in error_message or "user already registered" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered. Please use a different email or try logging in."
            )
        elif "password" in error_message and ("short" in error_message or "minimum" in error_message):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password must be at least 8 characters long"
            )
        elif "invalid" in error_message and "email" in error_message:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid email format. Please enter a valid email address."
            )
        elif "network" in error_message or "connection" in error_message or "timeout" in error_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to connect to authentication service. Please check your internet connection and try again."
            )
        else:
            # Don't expose internal error details in production
            if settings.ENVIRONMENT == "development":
                detail = f"Authentication error: {str(e)}"
            else:
                detail = "An error occurred during signup. Please try again or contact support if the problem persists."
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
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
        # Get Supabase client (with error handling)
        try:
            supabase = get_supabase_client()
        except ValueError as e:
            logger.error(f"Supabase client configuration error: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is not properly configured. Please contact support."
            )
        except Exception as e:
            logger.error(f"Failed to get Supabase client: {e}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service is temporarily unavailable. Please try again later."
            )
        
        # Supabase handles password verification and hashing automatically
        try:
            auth_response = supabase.auth.sign_in_with_password({
                "email": request.email,
                "password": request.password
            })
        except Exception as supabase_error:
            error_str = str(supabase_error).lower()
            logger.warning(f"Supabase login error: {supabase_error}")
            
            # Handle network/connection errors
            if "network" in error_str or "connection" in error_str or "timeout" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Unable to connect to authentication service. Please check your internet connection and try again."
                )
            # Re-raise to be handled by outer exception handler
            raise

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
        # Re-raise HTTP exceptions (already properly formatted)
        raise
    except Exception as e:
        error_message = str(e).lower()
        logger.error(f"Login error: {e}", exc_info=True)

        # Handle common Supabase Auth errors
        if "invalid" in error_message and ("credentials" in error_message or "login" in error_message or "password" in error_message):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password. Please check your credentials and try again.",
                headers={"WWW-Authenticate": "Bearer"},
            )
        elif "network" in error_message or "connection" in error_message or "timeout" in error_message:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Unable to connect to authentication service. Please check your internet connection and try again."
            )
        else:
            # Don't expose internal error details in production
            if settings.ENVIRONMENT == "development":
                detail = f"Authentication error: {str(e)}"
            else:
                detail = "An error occurred during login. Please try again or contact support if the problem persists."
            
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=detail
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
