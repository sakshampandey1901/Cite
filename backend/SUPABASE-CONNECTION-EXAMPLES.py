"""
Example code demonstrating production-ready Supabase database connection setup.

This file shows:
1. Environment-safe DB initialization
2. Connection testing on boot
3. Structured error handling
4. Multiple environment support
"""

import logging
import os
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool

# Import our production-ready utilities
from app.core.config import settings
from app.core.database import (
    create_database_engine,
    test_database_connection,
    validate_database_url,
    normalize_database_url,
    DatabaseConnectionError,
    get_connection_info
)

logger = logging.getLogger(__name__)


# ============================================================================
# Example 1: Basic Database Initialization with Validation
# ============================================================================

def example_basic_init():
    """Basic example: Create engine with validation."""
    try:
        # This will validate the URL format and create a properly configured engine
        engine = create_database_engine()
        logger.info("Database engine created successfully")
        return engine
    except DatabaseConnectionError as e:
        logger.error(f"Database configuration error: {e}")
        raise


# ============================================================================
# Example 2: Environment-Aware Initialization
# ============================================================================

def example_environment_aware_init():
    """Initialize database with different behavior per environment."""
    try:
        engine = create_database_engine()
        
        # Test connection
        success, error_msg = test_database_connection(engine)
        
        if not success:
            if settings.ENVIRONMENT == "production":
                # Fail fast in production
                raise DatabaseConnectionError(
                    f"Production database connection failed: {error_msg}"
                )
            else:
                # Warn but continue in development
                logger.warning(f"Database connection failed (non-production): {error_msg}")
                logger.warning("Application will start but database operations will fail")
        
        return engine
    except DatabaseConnectionError as e:
        if settings.ENVIRONMENT == "production":
            raise
        else:
            logger.warning(f"Database error (non-production): {e}")
            # Return a dummy engine that will fail on use
            return None


# ============================================================================
# Example 3: Connection Testing on Application Startup
# ============================================================================

def example_startup_connection_test():
    """Test connection during application startup."""
    logger.info("Testing database connection on startup...")
    
    try:
        engine = create_database_engine()
    except DatabaseConnectionError as e:
        logger.error(f"Failed to create database engine: {e}")
        if settings.ENVIRONMENT == "production":
            raise
        return None
    
    # Test the connection
    success, error_msg = test_database_connection(engine)
    
    if not success:
        error = DatabaseConnectionError(
            f"Startup connection test failed: {error_msg}"
        )
        
        if settings.ENVIRONMENT == "production":
            logger.error("=" * 80)
            logger.error("PRODUCTION: Database connection failed - application will not start")
            logger.error("=" * 80)
            logger.error(str(error))
            raise error
        else:
            logger.warning("=" * 80)
            logger.warning("DEVELOPMENT: Database connection failed - continuing anyway")
            logger.warning("=" * 80)
            logger.warning(str(error))
    
    # Log connection info
    conn_info = get_connection_info(engine)
    logger.info(f"Database connection verified: {conn_info.get('url_masked', 'N/A')}")
    
    return engine


# ============================================================================
# Example 4: Health Check Endpoint
# ============================================================================

def example_health_check(engine) -> dict:
    """
    Create a health check endpoint that tests database connection.
    
    Returns:
        Dictionary with health status
    """
    health_status = {
        "status": "unknown",
        "database": "unknown",
        "error": None
    }
    
    try:
        success, error_msg = test_database_connection(engine)
        
        if success:
            conn_info = get_connection_info(engine)
            health_status.update({
                "status": "healthy",
                "database": "connected",
                "pool_size": conn_info.get("pool_size"),
                "checked_out": conn_info.get("checked_out", 0),
            })
        else:
            health_status.update({
                "status": "unhealthy",
                "database": "disconnected",
                "error": error_msg
            })
    except Exception as e:
        health_status.update({
            "status": "error",
            "database": "error",
            "error": str(e)
        })
    
    return health_status


# ============================================================================
# Example 5: FastAPI Startup Event
# ============================================================================

def example_fastapi_startup():
    """
    Example FastAPI startup event handler.
    
    Use this in your FastAPI app:
    
    @app.on_event("startup")
    async def startup_event():
        example_fastapi_startup()
    """
    logger.info("Starting database initialization...")
    
    # Create engine
    try:
        engine = create_database_engine()
    except DatabaseConnectionError as e:
        if settings.ENVIRONMENT == "production":
            logger.error(f"CRITICAL: Cannot start in production without database: {e}")
            raise
        else:
            logger.warning(f"Database engine creation failed (non-production): {e}")
            return
    
    # Test connection
    success, error_msg = test_database_connection(engine)
    
    if not success:
        error = DatabaseConnectionError(
            f"Database connection failed during startup: {error_msg}"
        )
        
        if settings.ENVIRONMENT == "production":
            logger.error("=" * 80)
            logger.error("PRODUCTION: Database connection failed - application will not start")
            logger.error("=" * 80)
            logger.error(str(error))
            raise error
        else:
            logger.warning("=" * 80)
            logger.warning("DEVELOPMENT: Database connection failed - application will start but DB operations will fail")
            logger.warning("=" * 80)
            logger.warning(str(error))
            return
    
    # Initialize tables (if needed)
    try:
        from app.models.database import Base
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database initialization completed successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database tables: {e}")
        if settings.ENVIRONMENT == "production":
            raise


# ============================================================================
# Example 6: Manual URL Validation
# ============================================================================

def example_validate_url(url: str) -> bool:
    """Validate a database URL before using it."""
    is_valid, error_msg = validate_database_url(url)
    
    if not is_valid:
        logger.error(f"Invalid database URL: {error_msg}")
        logger.error(f"URL (masked): {url.replace('://', '://***:***@')}")
        return False
    
    logger.info("Database URL is valid")
    return True


# ============================================================================
# Example 7: URL Normalization
# ============================================================================

def example_normalize_url(url: str) -> str:
    """Normalize a database URL (add missing parameters)."""
    normalized = normalize_database_url(url)
    
    if normalized != url:
        logger.info(f"URL was normalized:")
        logger.info(f"  Original: {url.replace('://', '://***:***@')}")
        logger.info(f"  Normalized: {normalized.replace('://', '://***:***@')}")
    
    return normalized


# ============================================================================
# Example 8: Connection Pool Monitoring
# ============================================================================

def example_monitor_pool(engine):
    """Monitor connection pool status."""
    conn_info = get_connection_info(engine)
    
    logger.info("Connection Pool Status:")
    logger.info(f"  Pool size: {conn_info.get('pool_size', 'N/A')}")
    logger.info(f"  Checked out: {conn_info.get('checked_out', 0)}")
    logger.info(f"  Overflow: {conn_info.get('overflow', 0)}")
    
    # Check if pool is near capacity
    pool_size = conn_info.get('pool_size', 0)
    checked_out = conn_info.get('checked_out', 0)
    
    if pool_size > 0:
        utilization = (checked_out / pool_size) * 100
        if utilization > 80:
            logger.warning(f"Connection pool utilization is high: {utilization:.1f}%")


# ============================================================================
# Example 9: Error Handling in Database Operations
# ============================================================================

def example_safe_db_operation(engine):
    """Example of safe database operation with error handling."""
    SessionLocal = sessionmaker(bind=engine)
    
    try:
        db = SessionLocal()
        try:
            # Your database operation here
            result = db.execute(text("SELECT 1"))
            result.fetchone()
            db.commit()
            logger.info("Database operation successful")
        except Exception as e:
            db.rollback()
            logger.error(f"Database operation failed: {e}")
            raise
        finally:
            db.close()
    except DatabaseConnectionError as e:
        logger.error(f"Database connection error: {e}")
        # Handle connection errors (retry, fallback, etc.)
        raise
    except Exception as e:
        logger.error(f"Unexpected database error: {e}")
        raise


# ============================================================================
# Example 10: CI/CD Environment Setup
# ============================================================================

def example_cicd_setup():
    """
    Example for CI/CD environments.
    
    In CI/CD, you want to:
    1. Fail fast if DATABASE_URL is not set
    2. Validate the URL format
    3. Test connection before running tests
    """
    # Get DATABASE_URL from environment
    database_url = os.getenv("DATABASE_URL")
    
    if not database_url:
        raise ValueError(
            "DATABASE_URL environment variable is required in CI/CD environment"
        )
    
    # Validate URL
    is_valid, error_msg = validate_database_url(database_url)
    if not is_valid:
        raise ValueError(f"Invalid DATABASE_URL in CI/CD: {error_msg}")
    
    # Create engine
    try:
        engine = create_database_engine(database_url)
    except DatabaseConnectionError as e:
        raise ValueError(f"Cannot create database engine in CI/CD: {e}")
    
    # Test connection (fail fast)
    success, error_msg = test_database_connection(engine)
    if not success:
        raise ConnectionError(f"Database connection test failed in CI/CD: {error_msg}")
    
    logger.info("✅ CI/CD database connection verified")
    return engine


if __name__ == "__main__":
    # Example usage
    logging.basicConfig(level=logging.INFO)
    
    print("=" * 80)
    print("Supabase Database Connection Examples")
    print("=" * 80)
    
    # Example: Basic initialization
    print("\n1. Basic Initialization:")
    try:
        engine = example_basic_init()
        print("   ✅ Success")
    except Exception as e:
        print(f"   ❌ Failed: {e}")
    
    # Example: Connection testing
    print("\n2. Connection Testing:")
    try:
        engine = create_database_engine()
        success, error_msg = test_database_connection(engine)
        if success:
            print("   ✅ Connection test passed")
        else:
            print(f"   ❌ Connection test failed: {error_msg}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
    
    # Example: Health check
    print("\n3. Health Check:")
    try:
        engine = create_database_engine()
        health = example_health_check(engine)
        print(f"   Status: {health['status']}")
        print(f"   Database: {health['database']}")
    except Exception as e:
        print(f"   ❌ Error: {e}")
