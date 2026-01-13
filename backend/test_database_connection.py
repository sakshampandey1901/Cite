#!/usr/bin/env python3
"""
Database connection testing utility for Supabase.

This script tests database connections with comprehensive error reporting
and suggestions for fixing common issues.

Usage:
    python test_database_connection.py [DATABASE_URL]
    
    Or set DATABASE_URL environment variable:
    export DATABASE_URL="postgresql://..."
    python test_database_connection.py
"""
import sys
import os
import logging
from typing import Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import (
    validate_database_url,
    normalize_database_url,
    create_database_engine,
    test_database_connection,
    get_connection_info,
    DatabaseConnectionError,
    _mask_password_in_url
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


def print_section(title: str, char: str = "="):
    """Print a formatted section header."""
    print(f"\n{char * 80}")
    print(f"{title}")
    print(f"{char * 80}\n")


def test_connection_url(url: Optional[str] = None) -> bool:
    """
    Test a database connection URL with comprehensive error reporting.
    
    Args:
        url: Database URL to test (defaults to settings.DATABASE_URL)
        
    Returns:
        True if connection successful, False otherwise
    """
    url = url or settings.DATABASE_URL
    
    print_section("Database Connection Test")
    
    # Step 1: Validate URL format
    print("Step 1: Validating URL format...")
    is_valid, error_msg = validate_database_url(url)
    
    if not is_valid:
        print(f"❌ URL validation failed:\n{error_msg}")
        print(f"\nCurrent URL (masked): {_mask_password_in_url(url)}")
        print("\nTo fix:")
        print("1. Go to Supabase Dashboard → Settings → Database")
        print("2. Copy 'Connection string' (URI format)")
        print("3. Ensure it uses format: postgresql://postgres.{project-ref}:password@host:port/db?sslmode=require")
        return False
    
    print("✅ URL format is valid")
    
    # Step 2: Normalize URL
    print("\nStep 2: Normalizing URL (adding missing parameters)...")
    normalized_url = normalize_database_url(url)
    if normalized_url != url:
        print(f"⚠️  URL was normalized (added missing parameters)")
        print(f"   Original: {_mask_password_in_url(url)}")
        print(f"   Normalized: {_mask_password_in_url(normalized_url)}")
    else:
        print("✅ URL is already normalized")
    
    # Step 3: Create engine
    print("\nStep 3: Creating database engine...")
    try:
        engine = create_database_engine(normalized_url)
        print("✅ Engine created successfully")
    except DatabaseConnectionError as e:
        print(f"❌ Engine creation failed:\n{e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error creating engine: {e}")
        return False
    
    # Step 4: Test connection
    print("\nStep 4: Testing database connection...")
    success, error_msg = test_database_connection(engine)
    
    if not success:
        print(f"❌ Connection test failed:\n{error_msg}")
        return False
    
    print("✅ Connection test passed")
    
    # Step 5: Get connection info
    print("\nStep 5: Gathering connection information...")
    try:
        conn_info = get_connection_info(engine)
        print("✅ Connection information:")
        print(f"   URL (masked): {conn_info.get('url_masked', 'N/A')}")
        if 'postgresql_version' in conn_info:
            print(f"   PostgreSQL version: {conn_info['postgresql_version'][:60]}...")
        if conn_info.get('pool_size'):
            print(f"   Pool size: {conn_info.get('pool_size')}")
            print(f"   Checked out: {conn_info.get('checked_out', 0)}")
            print(f"   Overflow: {conn_info.get('overflow', 0)}")
    except Exception as e:
        print(f"⚠️  Could not gather connection info: {e}")
    
    print_section("✅ Connection Test Successful", "=")
    print(f"\nYour database connection is working correctly!")
    print(f"\nUse this URL in your .env file (masked here):")
    print(f"{_mask_password_in_url(normalized_url)}")
    print()
    
    return True


def main():
    """Main entry point for connection testing."""
    # Get URL from command line or environment
    if len(sys.argv) > 1:
        test_url = sys.argv[1]
    else:
        # Try to get from settings
        try:
            test_url = settings.DATABASE_URL
        except Exception as e:
            print(f"❌ Error loading DATABASE_URL from settings: {e}")
            print("\nUsage:")
            print("  python test_database_connection.py [DATABASE_URL]")
            print("\nOr set DATABASE_URL environment variable")
            sys.exit(1)
    
    if not test_url:
        print("❌ No DATABASE_URL provided")
        print("\nUsage:")
        print("  python test_database_connection.py [DATABASE_URL]")
        print("\nOr set DATABASE_URL environment variable")
        sys.exit(1)
    
    # Run test
    success = test_connection_url(test_url)
    
    if not success:
        print_section("Connection Test Failed", "=")
        print("\nTroubleshooting steps:")
        print("1. Verify Supabase project is active (not paused)")
        print("2. Get connection string from: Settings → Database → Connection string")
        print("3. For pooler connections, ensure username is: postgres.{project-ref}")
        print("4. Verify password is correct (reset if needed)")
        print("5. Check IP allowlist settings if enabled")
        print("6. Ensure SSL mode is set: ?sslmode=require")
        print("\nFor detailed analysis, see: SUPABASE-CONNECTION-ANALYSIS.md")
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()
