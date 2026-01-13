#!/usr/bin/env python3
"""Test Supabase Auth integration."""
import sys
from app.core.supabase_client import supabase

def test_signup():
    """Test user signup."""
    print("=" * 60)
    print("Testing Supabase Auth - Signup")
    print("=" * 60)

    test_email = "testuser456@gmail.com"
    test_password = "SecurePassword123!"

    try:
        result = supabase.auth.sign_up({
            "email": test_email,
            "password": test_password
        })

        print(f"✅ User created successfully")
        print(f"   User ID: {result.user.id if result.user else 'None'}")
        print(f"   Email: {result.user.email if result.user else 'None'}")

        if result.session:
            print(f"✅ Session created")
            print(f"   Access Token: {result.session.access_token[:50]}...")
            print(f"   Token Type: {result.session.token_type}")
            print("\n✅ READY TO USE - Backend will work!")
            return True
        else:
            print(f"❌ No session created")
            print(f"\n⚠️  ACTION REQUIRED:")
            print(f"   1. Go to: https://app.supabase.com/project/bwixygkmogchzhjuhivt/auth/providers")
            print(f"   2. Click on 'Email' provider")
            print(f"   3. Find 'Enable email confirmations' toggle")
            print(f"   4. DISABLE it (turn OFF)")
            print(f"   5. Click 'Save'")
            print(f"   6. Run this test again")
            return False

    except Exception as e:
        error_msg = str(e)
        print(f"❌ Error: {error_msg}")

        if "already registered" in error_msg.lower() or "already exists" in error_msg.lower():
            print(f"\n✅ Good news: This error means Auth is working!")
            print(f"   (User already exists from previous test)")
            print(f"\nTrying to login instead...")
            return test_login(test_email, test_password)

        return False

def test_login(email, password):
    """Test user login."""
    print("\n" + "=" * 60)
    print("Testing Supabase Auth - Login")
    print("=" * 60)

    try:
        result = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })

        print(f"✅ Login successful")
        print(f"   User ID: {result.user.id if result.user else 'None'}")

        if result.session:
            print(f"✅ Session created")
            print(f"   Access Token: {result.session.access_token[:50]}...")
            print("\n✅ READY TO USE - Backend will work!")
            return True
        else:
            print(f"❌ No session - email confirmation required")
            return False

    except Exception as e:
        print(f"❌ Login error: {str(e)}")
        return False

def main():
    """Run auth tests."""
    print("\n🔐 Supabase Auth Integration Test\n")

    success = test_signup()

    print("\n" + "=" * 60)
    if success:
        print("✅ ALL TESTS PASSED - Backend is ready!")
        print("\nYou can now:")
        print("  1. Start backend: cd backend && uvicorn app.main:app --reload")
        print("  2. Test signup: curl -X POST http://localhost:8000/api/v1/auth/signup \\")
        print("                    -H 'Content-Type: application/json' \\")
        print("                    -d '{\"email\":\"user@example.com\",\"password\":\"pass123\"}'")
    else:
        print("❌ TESTS FAILED - See instructions above")
        print("\nAfter fixing, run: python test_auth.py")
    print("=" * 60 + "\n")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
