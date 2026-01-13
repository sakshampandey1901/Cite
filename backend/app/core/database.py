"""Database connection management with validation and health checks."""
import logging
import re
from typing import Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.pool import QueuePool

from app.core.config import settings

logger = logging.getLogger(__name__)


class DatabaseConnectionError(Exception):
    """Raised when database connection fails with actionable error message."""
    pass


def validate_database_url(url: str) -> Tuple[bool, Optional[str]]:
    """
    Validate database URL format and Supabase-specific requirements.
    
    Args:
        url: Database connection URL
        
    Returns:
        Tuple of (is_valid, error_message)
    """
    if not url:
        return False, "DATABASE_URL is empty or not set"
    
    # Check if it's a PostgreSQL URL
    if not url.startswith(("postgresql://", "postgresql+psycopg2://", "postgres://")):
        return True, None  # Allow other database types (e.g., sqlite)
    
    try:
        parsed = urlparse(url)
    except Exception as e:
        return False, f"Invalid URL format: {str(e)}"
    
    # Check for Supabase connection
    is_supabase = "supabase" in parsed.hostname.lower() if parsed.hostname else False
    is_pooler = "pooler" in parsed.hostname.lower() if parsed.hostname else False
    
    if is_supabase and is_pooler:
        # Pooler requires postgres.{project-ref} format
        username = parsed.username or ""
        if not username.startswith("postgres."):
            return False, (
                "Supabase pooler connection requires username format: postgres.{project-ref}\n"
                "Current username: {}\n"
                "Fix: Get connection string from Supabase Dashboard → Settings → Database → Connection string"
            ).format(username)
    
    # Check for SSL requirement (Supabase requires SSL)
    if is_supabase:
        query_params = parse_qs(parsed.query)
        sslmode = query_params.get("sslmode", [None])[0]
        if sslmode not in ("require", "prefer", "allow"):
            # Add sslmode=require if missing
            logger.warning(
                "Supabase connection missing sslmode=require. "
                "This may cause connection failures."
            )
    
    return True, None


def normalize_database_url(url: str) -> str:
    """
    Normalize database URL by ensuring required parameters are present.
    
    Args:
        url: Database connection URL
        
    Returns:
        Normalized URL with required parameters
    """
    if not url or "supabase" not in url.lower():
        return url
    
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Ensure sslmode is set for Supabase
        if "sslmode" not in query_params:
            query_params["sslmode"] = ["require"]
        
        # Rebuild URL
        new_query = urlencode(query_params, doseq=True)
        normalized = urlunparse((
            parsed.scheme,
            parsed.netloc,
            parsed.path,
            parsed.params,
            new_query,
            parsed.fragment
        ))
        
        return normalized
    except Exception as e:
        logger.warning(f"Failed to normalize database URL: {e}")
        return url


def create_database_engine(database_url: Optional[str] = None) -> Engine:
    """
    Create SQLAlchemy engine with production-ready configuration.
    
    Args:
        database_url: Optional database URL (defaults to settings.DATABASE_URL)
        
    Returns:
        Configured SQLAlchemy engine
        
    Raises:
        DatabaseConnectionError: If URL validation fails
    """
    url = database_url or settings.DATABASE_URL
    
    # Validate URL
    is_valid, error_msg = validate_database_url(url)
    if not is_valid:
        raise DatabaseConnectionError(
            f"Invalid database URL configuration:\n{error_msg}\n\n"
            f"Current URL (masked): {_mask_password_in_url(url)}\n\n"
            "To fix:\n"
            "1. Go to Supabase Dashboard → Settings → Database\n"
            "2. Copy 'Connection string' (URI format)\n"
            "3. Ensure it uses format: postgresql://postgres.{project-ref}:password@host:port/db?sslmode=require"
        )
    
    # Normalize URL (add missing parameters)
    normalized_url = normalize_database_url(url)
    
    # Determine if this is a Supabase connection
    is_supabase = "supabase" in normalized_url.lower()
    is_sqlite = "sqlite" in normalized_url.lower()
    
    # Configure engine arguments
    engine_args = {
        "pool_pre_ping": True,  # CRITICAL: Test connections before use
        "echo": False,  # Set to True for SQL debugging
    }
    
    if is_sqlite:
        # SQLite-specific configuration
        engine_args["connect_args"] = {"check_same_thread": False}
    else:
        # PostgreSQL/Supabase configuration
        engine_args.update({
            "poolclass": QueuePool,
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "connect_args": {
                "connect_timeout": 10,  # 10 second connection timeout
            }
        })
        
        # Add SSL mode to connect_args if not in URL
        if is_supabase:
            parsed = urlparse(normalized_url)
            query_params = parse_qs(parsed.query)
            if "sslmode" in query_params:
                engine_args["connect_args"]["sslmode"] = query_params["sslmode"][0]
    
    try:
        engine = create_engine(normalized_url, **engine_args)
        logger.info(f"Database engine created successfully (Supabase: {is_supabase})")
        return engine
    except Exception as e:
        raise DatabaseConnectionError(
            f"Failed to create database engine:\n{str(e)}\n\n"
            f"URL (masked): {_mask_password_in_url(normalized_url)}"
        )


def test_database_connection(engine: Engine, timeout: int = 10) -> Tuple[bool, Optional[str]]:
    """
    Test database connection with a simple query.
    
    Args:
        engine: SQLAlchemy engine
        timeout: Connection timeout in seconds
        
    Returns:
        Tuple of (success, error_message)
    """
    try:
        with engine.connect() as conn:
            # Simple query to test connection
            result = conn.execute(text("SELECT 1"))
            result.fetchone()
            
            # Get database version for logging
            try:
                version_result = conn.execute(text("SELECT version()"))
                version = version_result.fetchone()[0]
                logger.info(f"Database connection successful. PostgreSQL version: {version[:50]}...")
            except Exception:
                pass  # Version query is optional
            
            return True, None
    except OperationalError as e:
        error_str = str(e)
        
        # Provide specific error messages for common issues
        if "Tenant or user not found" in error_str:
            return False, (
                "Connection failed: Tenant or user not found\n\n"
                "This usually means:\n"
                "1. Missing project reference in username (should be postgres.{project-ref} for pooler)\n"
                "2. Incorrect password\n"
                "3. Database paused - check Supabase dashboard\n\n"
                "Fix:\n"
                "1. Go to Supabase Dashboard → Settings → Database\n"
                "2. Copy the 'Connection string' (URI format)\n"
                "3. Ensure username format: postgres.{project-ref} for pooler connections\n"
                "4. Verify password is correct\n"
                "5. Check if database is paused and wake it up if needed"
            )
        elif "password authentication failed" in error_str.lower():
            return False, (
                "Connection failed: Password authentication failed\n\n"
                "This means the password is incorrect.\n\n"
                "Fix:\n"
                "1. Go to Supabase Dashboard → Settings → Database\n"
                "2. Click 'Reset Database Password'\n"
                "3. Copy the new password\n"
                "4. Update DATABASE_URL in your .env file"
            )
        elif "connection refused" in error_str.lower() or "could not connect" in error_str.lower():
            return False, (
                "Connection failed: Could not connect to database server\n\n"
                "This usually means:\n"
                "1. Database is paused - wake it up in Supabase dashboard\n"
                "2. Incorrect hostname or port\n"
                "3. Network/firewall blocking connection\n"
                "4. IP allowlist restrictions\n\n"
                "Fix:\n"
                "1. Check Supabase dashboard - is project active?\n"
                "2. Verify connection string from Settings → Database\n"
                "3. Check IP allowlist settings if enabled"
            )
        else:
            return False, f"Connection failed: {error_str}"
    except SQLAlchemyError as e:
        return False, f"Database error: {str(e)}"
    except Exception as e:
        return False, f"Unexpected error: {str(e)}"


def _mask_password_in_url(url: str) -> str:
    """Mask password in database URL for logging."""
    try:
        parsed = urlparse(url)
        if parsed.password:
            masked_netloc = parsed.netloc.replace(
                f":{parsed.password}@",
                ":***@"
            )
            return urlunparse((
                parsed.scheme,
                masked_netloc,
                parsed.path,
                parsed.params,
                parsed.query,
                parsed.fragment
            ))
    except Exception:
        pass
    return url.replace("://", "://***:***@") if "://" in url else "***"


def get_connection_info(engine: Engine) -> dict:
    """
    Get connection information for debugging.
    
    Args:
        engine: SQLAlchemy engine
        
    Returns:
        Dictionary with connection information
    """
    info = {
        "url_masked": _mask_password_in_url(str(engine.url)),
        "pool_size": getattr(engine.pool, "size", None),
        "checked_out": getattr(engine.pool, "checkedout", None),
        "overflow": getattr(engine.pool, "overflow", None),
    }
    
    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            info["postgresql_version"] = result.fetchone()[0]
    except Exception:
        pass
    
    return info
