"""Security utilities for authentication and authorization using Supabase."""
import logging
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.supabase_client import get_supabase_client

logger = logging.getLogger(__name__)


# HTTP Bearer token scheme
security = HTTPBearer()


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user ID from Supabase JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User ID from Supabase Auth

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials

    try:
        # Get Supabase client
        supabase = get_supabase_client()
        
        # Verify token with Supabase Auth
        user_response = supabase.auth.get_user(token)

        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_response.user.id

    except ValueError as e:
        # Supabase client configuration error
        logger.error(f"Supabase client error in get_current_user_id: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service is not available",
        )
    except Exception as e:
        logger.warning(f"Token validation failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename to prevent path traversal attacks.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    # Remove directory components
    import os
    filename = os.path.basename(filename)

    # Remove dangerous characters
    dangerous_chars = ['..', '/', '\\', '\x00']
    for char in dangerous_chars:
        filename = filename.replace(char, '')

    # Limit length
    max_length = 255
    if len(filename) > max_length:
        name, ext = os.path.splitext(filename)
        filename = name[:max_length - len(ext)] + ext

    return filename


def validate_file_type(filename: str, allowed_extensions: list) -> bool:
    """
    Validate file type against allowed extensions.

    Args:
        filename: Filename to validate
        allowed_extensions: List of allowed extensions

    Returns:
        True if file type is allowed
    """
    import os
    _, ext = os.path.splitext(filename.lower())
    ext = ext.lstrip('.')
    return ext in allowed_extensions
