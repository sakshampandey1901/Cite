# 🚀 Quick Start Guide - PDF Upload Fix

## The Issue is NOW FIXED! ✅

Your PDF upload was failing because:
1. Backend was running with wrong Python (system instead of venv)
2. No authentication token was set in the browser

## How to Use Right Now

### Step 1: Set Authentication Token

**Open** [debug-upload.html](debug-upload.html) in your browser and click "Set Development Token"

OR paste this in your browser console (F12):
```javascript
localStorage.setItem('auth_token', 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3Njg3MDM2NTh9.h2edhIlzjZ5Cy1tv283wNwmg6xrM3M2dv9wnpjvlmfg');
```

### Step 2: Upload Your PDF

The backend is now running correctly. Just upload your PDF in the app - it will work!

## Backend is Running

✅ Backend URL: http://localhost:8000
✅ Using correct Python from venv
✅ Token valid until: January 18, 2026

## If Backend Stops

To restart the backend:
```bash
cd /Users/saksham/Desktop/Cite/backend
./start-backend.sh
```

Or manually:
```bash
cd /Users/saksham/Desktop/Cite/backend
source venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Debug Tools

1. **[debug-upload.html](debug-upload.html)** - Upload debugger with detailed logs
2. **[setup-dev-auth.html](setup-dev-auth.html)** - Token setup and verification
3. **Backend logs**: `tail -f /tmp/backend.log`

## Verification

Test the upload works:
```bash
cd ~/Desktop
echo "%PDF-1.4 Test" > test.pdf

curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJkZXYtdXNlci0xMjMiLCJleHAiOjE3Njg3MDM2NTh9.h2edhIlzjZ5Cy1tv283wNwmg6xrM3M2dv9wnpjvlmfg" \
  -F "file=@test.pdf"
```

Expected: `{"document_id":"...","filename":"test.pdf","status":"ready"...}`

## What Was Fixed

1. ✅ **SECRET_KEY** - Now stable in [backend/.env](backend/.env:22)
2. ✅ **Backend Process** - Running with correct venv Python
3. ✅ **Auth Token** - Fresh 7-day token generated
4. ✅ **Startup Script** - [start-backend.sh](backend/start-backend.sh) for easy restart

## Files Created

- **[debug-upload.html](debug-upload.html)** - Interactive upload debugger
- **[setup-dev-auth.html](setup-dev-auth.html)** - Token setup tool
- **[backend/start-backend.sh](backend/start-backend.sh)** - Backend startup script
- **[FIXED-AUTH-ISSUE.md](FIXED-AUTH-ISSUE.md)** - Detailed fix documentation
- **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** - Complete troubleshooting guide

## Common Issues

### "Could not validate credentials"
**Cause**: Old token or backend using wrong SECRET_KEY
**Fix**: Use debug-upload.html to set fresh token

### "Connection refused"
**Cause**: Backend not running
**Fix**: Run `./backend/start-backend.sh`

### "CORS error"
**Cause**: Frontend URL not in CORS_ORIGINS
**Fix**: Check [backend/.env](backend/.env) has your frontend URL

## For Production

This is a development setup. For production, implement:
1. Login/signup endpoints
2. User authentication UI
3. Password management
4. Token refresh mechanism

See [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for production auth guide.

---

**Status**: ✅ Working
**Token Valid**: 7 days (until Jan 18, 2026)
**Backend**: Running on port 8000 with venv Python

**Try uploading a PDF now - it should work!** 🎉