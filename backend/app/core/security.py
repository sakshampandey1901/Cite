"""Security utilities for authentication and authorization."""
from datetime import datetime, timedelta
from typing import Optional
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from app.core.config import settings


# Password hashing (bcrypt_sha256 pre-hashes to avoid bcrypt's 72-byte limit)
pwd_context = CryptContext(schemes=["bcrypt_sha256", "bcrypt"], deprecated="auto")


def _legacy_normalize_password(password: str) -> str:
    """
    Legacy normalization for bcrypt limits (72-byte max).

    This preserves historical behavior for existing hashes.
    """
    password_bytes = password.encode("utf-8")
    if len(password_bytes) > 72:
        password_bytes = password_bytes[:72]
    return password_bytes.decode("utf-8", errors="ignore")


def _is_bcrypt_sha256_hash(hashed_password: str) -> bool:
    return hashed_password.startswith("$bcrypt-sha256$")


# HTTP Bearer token scheme
security = HTTPBearer()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against a hash.

    Args:
        plain_password: Plain text password
        hashed_password: Hashed password

    Returns:
        True if password matches
    """
    if _is_bcrypt_sha256_hash(hashed_password):
        return pwd_context.verify(plain_password, hashed_password)
    return pwd_context.verify(_legacy_normalize_password(plain_password), hashed_password)


def verify_password_and_update(plain_password: str, hashed_password: str) -> tuple[bool, Optional[str]]:
    """
    Verify a password and return a replacement hash when upgrading legacy hashes.
    """
    if _is_bcrypt_sha256_hash(hashed_password):
        return pwd_context.verify_and_update(plain_password, hashed_password)

    legacy_password = _legacy_normalize_password(plain_password)
    verified = pwd_context.verify(legacy_password, hashed_password)
    if not verified:
        return False, None
    return True, pwd_context.hash(plain_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.

    Args:
        password: Plain text password

    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.

    Args:
        data: Data to encode in token
        expires_delta: Token expiration time

    Returns:
        Encoded JWT token
    """
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)
    return encoded_jwt


def decode_access_token(token: str) -> dict:
    """
    Decode JWT access token.

    Args:
        token: JWT token

    Returns:
        Decoded token data

    Raises:
        HTTPException: If token is invalid
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user_id(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    """
    Get current user ID from JWT token.

    Args:
        credentials: HTTP authorization credentials

    Returns:
        User ID

    Raises:
        HTTPException: If token is invalid or user not found
    """
    token = credentials.credentials
    payload = decode_access_token(token)

    user_id: str = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user_id


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
