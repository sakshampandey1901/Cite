# ✅ PDF Upload Issue - FIXED!

## Problem Summary
PDF uploads were failing with "Could not validate credentials" error because:
1. Backend requires JWT authentication for file uploads
2. Frontend had no auth token configured
3. SECRET_KEY was randomly generated on each restart (causing token invalidation)

## Solution Implemented

### 1. Fixed SECRET_KEY Configuration
**Changed**: [backend/app/core/config.py](backend/app/core/config.py)
- Removed random generation of SECRET_KEY
- Now reads SECRET_KEY from .env file (stable across restarts)

**Added**: [backend/.env](backend/.env)

### 2. Restarted Backend Server
Backend is now running with the stable SECRET_KEY:
```bash
cd /Users/saksham/Desktop/Cite/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### 3. Generated Fresh Authentication Token
**Valid for 7 days** (expires January 18, 2026):
```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3Njg3MDM2NTh9.h2edhIlzjZ5Cy1tv283wNwmg6xrM3M2dv9wnpjvlmfg
```

## How to Use (Choose One Method)

### Method 1: Interactive Setup Tool (Easiest)
1. Open [setup-dev-auth.html](setup-dev-auth.html) in your browser
2. Click "Setup Auth Token"
3. The token is now set in localStorage
4. Go to your app and upload a PDF - it works!

### Method 2: Browser Console (Quick)
1. Open your application at http://localhost:5173 (or :3000)
2. Press F12 to open Developer Tools
3. Go to Console tab
4. Paste this:
```javascript
localStorage.setItem('auth_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3Njg3MDM2NTh9.h2edhIlzjZ5Cy1tv283wNwmg6xrM3M2dv9wnpjvlmfg');
```
5. Refresh the page (F5)
6. Upload your PDF!

### Method 3: Command Line Test
```bash
cd ~/Desktop

# Create a test PDF
echo "%PDF-1.4 Test" > test.pdf

# Upload it
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3Njg3MDM2NTh9.h2edhIlzjZ5Cy1tv283wNwmg6xrM3M2dv9wnpjvlmfg" \
  -F "file=@test.pdf"
```

Expected response:
```json
{
  "document_id": "62b637c0-9409-42cf-a51d-be024b4b1227",
  "filename": "test.pdf",
  "status": "ready",
  "created_at": "2026-01-11T02:34:49.111165Z"
}
```

## Verification

✅ Backend running on http://localhost:8000
✅ Health check working: `curl http://localhost:8000/api/v1/health`
✅ File upload tested successfully
✅ Token is valid for 7 days
✅ SECRET_KEY is stable (won't change on restart)

## Files Modified

1. **[backend/app/core/config.py](backend/app/core/config.py)**
   - Removed random SECRET_KEY generation
   - Now requires SECRET_KEY from environment

2. **[backend/.env](backend/.env)**
   - Added SECRET_KEY configuration

3. **[backend/requirements.txt](backend/requirements.txt)**
   - Updated all dependencies to Python 3.13 compatible versions
   - Fixed pymupdf version (1.26.7) with pre-built wheels

4. **Created: [setup-dev-auth.html](setup-dev-auth.html)**
   - Interactive tool to configure authentication
   - Shows token status and expiration
   - Verifies backend connection

5. **Created: [TROUBLESHOOTING.md](TROUBLESHOOTING.md)**
   - Complete troubleshooting guide
   - Authentication options for production

## What Changed Behind the Scenes

### Before (Broken)
```
User uploads PDF → Frontend sends request without token
→ Backend requires auth → Returns 401 Unauthorized
→ Frontend shows "failed"
```

### After (Fixed)
```
User uploads PDF → Frontend includes auth token in request
→ Backend validates token with SECRET_KEY → Accepts upload
→ Processes PDF → Returns success with document_id
→ Frontend shows "ready"
```

## For Your Team

### Development Setup (Other Developers)
When a team member clones the repo:

1. **Install dependencies**:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

2. **Configure .env** (already done in your repo)

3. **Set auth token in browser**:
   - Open setup-dev-auth.html
   - Click "Setup Auth Token"
   - Start working!

### Production Deployment
For production, implement proper authentication:

1. **Add login/signup endpoints**
2. **Create login UI**
3. **Store tokens securely**
4. **Implement token refresh**
5. **Add password reset flow**

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for detailed production auth implementation guide.

## Token Expiration

Current token expires: **January 18, 2026** (7 days from now)

To generate a new token when this one expires:
```bash
cd /Users/saksham/Desktop/Cite/backend
source venv/bin/activate
python3 << 'EOF'
from app.core.security import create_access_token
from datetime import timedelta
token = create_access_token(data={'sub': 'dev-user-123'}, expires_delta=timedelta(days=7))
print(f"localStorage.setItem('auth_token', '{token}');")
EOF
```

## Backend Restart Command

If you need to restart the backend:
```bash
cd /Users/saksham/Desktop/Cite/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Testing Checklist

- [x] Backend running on port 8000
- [x] Health endpoint responding
- [x] SECRET_KEY set in .env
- [x] Auth token generated and working
- [x] PDF upload successful via curl
- [x] Token valid for 7 days
- [x] setup-dev-auth.html created
- [x] Documentation updated

## Support

- **Backend logs**: Check terminal where uvicorn is running
- **Frontend errors**: Press F12 → Console tab
- **Network issues**: Press F12 → Network tab → Check request/response

## Quick Reference

**Backend URL**: http://localhost:8000
**API Docs**: http://localhost:8000/docs (in development mode)
**Health Check**: http://localhost:8000/api/v1/health
**Upload Endpoint**: POST /api/v1/documents/upload

**User ID**: dev-user-123
**Token Expiry**: January 18, 2026

---

**Status**: ✅ RESOLVED
**Fixed**: January 11, 2026
**Tested**: PDF upload working successfully
