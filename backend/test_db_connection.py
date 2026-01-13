#!/usr/bin/env python3
"""Test database connection with different URL formats."""
import sys
import os
from sqlalchemy import create_engine, text

def test_connection(url, name):
    """Test a database connection URL."""
    print(f"\n{'='*60}")
    print(f"Testing: {name}")
    print(f"URL: {url.replace(url.split(':')[2].split('@')[0], '***PASSWORD***')}")
    print('='*60)

    try:
        engine = create_engine(url, echo=False)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()[0]
            print(f"✅ SUCCESS!")
            print(f"   PostgreSQL: {version[:50]}...")
            return True
    except Exception as e:
        print(f"❌ FAILED: {str(e)[:200]}")
        return False

if __name__ == "__main__":
    project_id = "bwixygkmogchzhjuhivt"

    # Get password from user or .env
    if len(sys.argv) > 1:
        password = sys.argv[1]
    else:
        password = os.getenv('DB_PASSWORD', 'saksham100_')

    print(f"Testing with password: {password[:3]}{'*' * (len(password) - 3)}")
    print(f"Project ID: {project_id}")

    # Test different formats
    formats = [
        (
            f"postgresql://postgres:{password}@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require",
            "Session Mode (Port 5432) - Simple Format"
        ),
        (
            f"postgresql://postgres.{project_id}:{password}@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require",
            "Session Mode (Port 6543) - Project Format"
        ),
        (
            f"postgresql://postgres.{project_id}:{password}@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require",
            "Transaction Mode (Port 5432) - Project Format"
        ),
    ]

    success = False
    for url, name in formats:
        if test_connection(url, name):
            success = True
            print(f"\n{'='*60}")
            print(f"✅ USE THIS URL IN YOUR .env FILE:")
            print(f"{'='*60}")
            print(url.replace(password, '[YOUR-PASSWORD]'))
            print('='*60)
            break

    if not success:
        print(f"\n{'='*60}")
        print("❌ ALL FORMATS FAILED")
        print('='*60)
        print("\nPossible issues:")
        print("1. Incorrect password - check Supabase Dashboard")
        print("2. Database paused - wake it up in Dashboard")
        print("3. IP allowlist - check Settings > Database > Connection pooling")
        print("\nTo get correct credentials:")
        print(f"1. Go to: https://app.supabase.com/project/{project_id}/settings/database")
        print("2. Look for 'Connection string' section")
        print("3. Copy the Session mode connection string")
        print("\nOr reset password:")
        print(f"1. Go to: https://app.supabase.com/project/{project_id}/settings/database")
        print("2. Click 'Reset Database Password'")
        print("3. Copy new password and update .env")
        sys.exit(1)
