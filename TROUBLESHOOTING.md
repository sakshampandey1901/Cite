# Troubleshooting Guide: PDF Upload Issue

## Problem
When uploading a PDF file, you're seeing:
- Error message about "localhost failing"
- Message about "application/pdf"
- Date "2026-01-11"
- Status "failed"

## Root Cause
The backend API requires **JWT authentication** for the upload endpoint, but the frontend doesn't have an authentication token configured. This causes the upload request to fail with a 401 Unauthorized error.

## Quick Fix (Development)

### Database Connection Issues
If you see `could not translate host name` or `connection refused` in the logs:
1. **Check your connection string** in `.env`:
   - Hostname format: `db.lzzwzkcdlxglxxgjnoyg.supabase.co` (Make sure the project ID is correct)
   - Username: Usually `postgres` (not `postgress`!)
   - Password: Your specific database password
2. **Verify Supabase Status**:
   - If using Supabase, ensure your project is **not paused**. Paused projects have their DNS records removed.
3. **Network**:
   - Ensure your firewall isn't blocking port 5432.

### Option 1: Set Authentication Token in Browser

1. **Open your application** in the browser (http://localhost:5173 or http://localhost:3000)

2. **Open Browser Console** (Press F12 or Right-click → Inspect → Console)

3. **Paste this code** in the console:

```javascript
// Set development authentication token
localStorage.setItem('auth_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3NjgxODQ1NDh9.uJwuCaPg0PLNcIr39WZPZ42oEmuuxydXLfcg6ewpFqE');
console.log('✅ Development token set! Refresh the page and try uploading again.');
```

4. **Refresh the page** (F5)

5. **Try uploading your PDF again** - it should now work!

### Option 2: Test with curl

To verify the backend is working correctly, test with curl:

```bash
# Create a test PDF file
echo "%PDF-1.4 Test" > test.pdf

# Upload with authentication
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3NjgxODQ1NDh9.uJwuCaPg0PLNcIr39WZPZ42oEmuuxydXLfcg6ewpFqE" \
  -F "file=@test.pdf"
```

Expected response:
```json
{
  "document_id": "uuid-here",
  "filename": "test.pdf",
  "status": "ready",
  "created_at": 1736563200
}
```

## Understanding the Error

### What's Happening:

1. **Frontend** tries to upload PDF to `/api/v1/documents/upload`
2. **Backend** checks for authentication token (JWT)
3. **No token found** → Returns 401 Unauthorized
4. **Frontend** catches error and displays "failed" status

### Why Authentication is Required:

The backend uses JWT tokens for security:
- Prevents unauthorized uploads
- Associates documents with specific users
- Implements user-scoped data isolation

## Permanent Fix (For Production)

You need to implement a proper authentication flow. Here are your options:

### Option A: Add Login/Signup UI (Recommended)

Create authentication endpoints and UI:

1. **Add auth routes to backend** ([backend/app/api/auth.py](backend/app/api/auth.py)):
```python
from fastapi import APIRouter, HTTPException
from app.core.security import create_access_token, get_password_hash, verify_password

router = APIRouter()

@router.post("/auth/login")
async def login(email: str, password: str):
    # Verify credentials (check database)
    # For now, accept any login in development
    token = create_access_token(data={"sub": email})
    return {"access_token": token, "token_type": "bearer"}

@router.post("/auth/signup")
async def signup(email: str, password: str):
    # Create user in database
    hashed = get_password_hash(password)
    # Save to DB...
    token = create_access_token(data={"sub": email})
    return {"access_token": token, "token_type": "bearer"}
```

2. **Add login form to frontend**
3. **Store token after successful login**
4. **Include token in all API requests** (already implemented in api.js)

### Option B: Disable Auth for Development (Quick but Insecure)

**⚠️ WARNING: Only for local development, NEVER for production!**

Modify [backend/app/api/routes.py](backend/app/api/routes.py:34):

```python
# Change line 34 from:
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id)  # <-- This requires auth
):

# To:
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = "dev-user-123"  # <-- Hardcoded for dev only
):
```

Then restart the backend server.

### Option C: Use Environment-Based Auth Bypass

Add conditional auth for development:

1. **Create a dev-only dependency** in [backend/app/core/security.py](backend/app/core/security.py):

```python
from app.core.config import settings

async def get_current_user_id_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """Get user ID with optional auth bypass for development."""

    # Development mode: allow bypass
    if settings.ENVIRONMENT == "development":
        if not credentials:
            return "dev-user-default"

    # Production mode: require auth
    return await get_current_user_id(credentials)
```

2. **Update routes to use optional auth**

## Checking Logs

To see detailed error messages from the backend:

```bash
# Check backend logs (in the terminal where backend is running)
# Look for lines with "POST /api/v1/documents/upload"
# You should see 401 Unauthorized errors
```

## Verifying the Fix

After applying Option 1 (setting the token):

1. Open browser console (F12)
2. Upload a PDF file
3. Check the **Network tab**:
   - Find the request to `/api/v1/documents/upload`
   - Check **Request Headers** → Should see: `Authorization: Bearer eyJhbG...`
   - Check **Response** → Should be 200 OK with document_id

## Next Steps

For a production-ready solution:

1. **Implement user authentication**:
   - Signup/Login pages
   - Password reset
   - Email verification

2. **Add database tables for users**:
   - Use Alembic migrations
   - Store hashed passwords
   - Link documents to users

3. **Implement refresh tokens**:
   - Short-lived access tokens
   - Long-lived refresh tokens
   - Auto-refresh before expiration

4. **Add OAuth providers** (optional):
   - Google Sign-In
   - GitHub OAuth
   - Magic link authentication

## Common Issues

### "Token expired" error
**Solution**: Generate a new token using the Python command above

### "CORS error"
**Solution**: Check that frontend URL is in [backend/.env](backend/.env) CORS_ORIGINS

### "File too large" error
**Solution**: Check MAX_FILE_SIZE_MB in [backend/.env](backend/.env) (default: 50MB)

### "File type not allowed" error
**Solution**: Check ALLOWED_EXTENSIONS in [backend/.env](backend/.env)

## Testing Checklist

- [ ] Backend server running on http://localhost:8000
- [ ] Frontend server running on http://localhost:5173 or :3000
- [ ] Auth token set in localStorage
- [ ] PDF file is valid and under 50MB
- [ ] Browser console shows no CORS errors
- [ ] Network tab shows 200 OK response

---

**Development Token Valid Until**: January 11, 2026 (24 hours)

**Need Help?** Check the browser console and backend logs for detailed error messages.