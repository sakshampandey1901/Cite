#!/usr/bin/env python3
"""Initialize database tables for production deployment."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from app.models.database import init_db, engine
from app.core.database import test_database_connection, get_connection_info
from app.core.config import settings

def init_database():
    """Initialize database tables and verify connection."""
    print("=" * 60)
    print("Database Initialization")
    print("=" * 60)

    # Test connection
    print("\n1. Testing database connection...")
    success, error_msg = test_database_connection(engine)

    if not success:
        print(f"❌ Database connection failed:")
        print(error_msg)
        print("\nTroubleshooting:")
        print("1. Verify DATABASE_URL is correct in .env")
        print("2. Check network connectivity to Supabase")
        print("3. Ensure SSL mode is 'require' for Supabase")
        print("4. Verify database user has necessary permissions")
        return False

    # Show connection info
    conn_info = get_connection_info(engine)
    print(f"✅ Connected to: {conn_info.get('url_masked', 'N/A')}")

    # Initialize tables
    print("\n2. Creating database tables...")
    try:
        init_db()
        print("✅ Database tables created successfully")

        print("\nCreated tables:")
        print("  - users")
        print("  - documents")
        print("  - chunk_labels")
        print("  - style_profiles")
        print("  - assistance_logs")

        print("\n" + "=" * 60)
        print("✅ Database initialization complete!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error creating tables: {e}")
        print("\nTroubleshooting:")
        print("1. Check database user has CREATE TABLE permissions")
        print("2. Verify no table naming conflicts")
        print("3. Review error message above for details")
        return False

if __name__ == "__main__":
    success = init_database()
    sys.exit(0 if success else 1)
