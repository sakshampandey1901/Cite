# Token Authentication Troubleshooting Guide

## Error: "Failed to generate guidance: Could not validate credentials"

This error occurs when the JWT token in your browser is invalid, expired, or from the old authentication system.

---

## 🎯 Quick Fix (2 Minutes)

### Option A: Clear Token & Re-Login (Recommended)

1. **Open Browser Console** (F12 or Right-click → Inspect → Console)

2. **Clear the old token**:
   ```javascript
   localStorage.removeItem('auth_token')
   ```

3. **Refresh the page** (F5 or Cmd+R)

4. **Login/Signup** with the authentication modal that appears

5. **Test the assistance feature** - should work now!

---

### Option B: Quick Token Replacement (For Testing)

If you need to test with a specific token immediately:

1. **Get a valid token** from signup/login response or generate one via:
   ```bash
   cd backend
   python test_auth.py
   ```

2. **Set token in browser console**:
   ```javascript
   localStorage.setItem('auth_token', 'YOUR_TOKEN_HERE')
   ```

3. **Refresh the page**

---

## 🔧 Production-Grade Fix Applied

I've enhanced the frontend to automatically handle token expiration:

### Changes Made

#### 1. [src/services/api.js](src/services/api.js#L86-L93) - Auto-detect 401 Errors

**Added**:
```javascript
// Handle authentication errors (401 Unauthorized)
if (response.status === 401) {
  this.clearToken();
  // Dispatch custom event for auth failure
  window.dispatchEvent(new CustomEvent('auth-failed', {
    detail: { message: 'Session expired. Please login again.' }
  }));
}
```

**What this does**:
- Detects when backend rejects token with 401 Unauthorized
- Automatically clears the invalid token from localStorage
- Triggers app-wide authentication failure event
- Prevents cascading failed requests with same bad token

#### 2. [src/main.js](src/main.js#L12-L15) - Listen for Auth Failures

**Added**:
```javascript
// Listen for authentication failures
window.addEventListener('auth-failed', (e) => {
  this.handleAuthFailure(e.detail.message);
});
```

**Added method**:
```javascript
handleAuthFailure(message) {
  // Show error message
  alert(message || 'Session expired. Please login again.');
  // Show login modal
  this.authModal.show();
  // Hide app content
  document.getElementById('app').style.display = 'none';
}
```

**What this does**:
- Listens for authentication failure events from API service
- Shows user-friendly error message: "Session expired. Please login again."
- Automatically opens the login/signup modal
- Hides app content until re-authenticated
- User can login again without page refresh

---

## 🎨 User Experience Flow

### Before (Current Behavior)
```
User clicks "Generate"
  → Backend returns 401
    → Error shows in output panel: "Failed to generate guidance: Could not validate credentials"
      → User confused, doesn't know what to do
        → User manually navigates to logout button
          → User manually logs back in
```

### After (With Fix Applied)
```
User clicks "Generate"
  → Backend returns 401
    → Token auto-cleared from localStorage
      → Alert: "Session expired. Please login again."
        → Login modal auto-opens
          → User logs in
            → Fresh token saved
              → App ready to use immediately
```

---

## 🧪 Testing the Fix

### Test Scenario 1: Expired Token
```javascript
// In browser console - simulate expired token
localStorage.setItem('auth_token', 'expired.token.here')

// Click "Generate" button
// Expected: Alert → Login modal → Re-authenticate → Works
```

### Test Scenario 2: Invalid Token
```javascript
// In browser console - simulate invalid token
localStorage.setItem('auth_token', 'totally-invalid-token')

// Click "Generate" button
// Expected: Alert → Login modal → Re-authenticate → Works
```

### Test Scenario 3: Missing Token
```javascript
// In browser console - remove token
localStorage.removeItem('auth_token')

// Refresh page
// Expected: Login modal shows immediately on page load
```

---

## 🔍 Debugging Token Issues

### Check Current Token
```javascript
// In browser console
const token = localStorage.getItem('auth_token');
console.log('Current token:', token);

// Decode JWT (doesn't verify signature)
if (token) {
  const payload = JSON.parse(atob(token.split('.')[1]));
  console.log('Token payload:', payload);
  console.log('Expires at:', new Date(payload.exp * 1000));
  console.log('Is expired?', Date.now() > payload.exp * 1000);
}
```

### Verify Backend Recognizes Token
```javascript
// In browser console
const token = localStorage.getItem('auth_token');

fetch('http://localhost:8000/api/v1/health', {
  headers: { 'Authorization': `Bearer ${token}` }
})
.then(r => r.json())
.then(data => console.log('Health check:', data))
.catch(err => console.error('Token invalid:', err));
```

### Test Signup Flow
```bash
# Using curl
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"securepass123"}'

# Response should include:
# {
#   "access_token": "eyJ...",
#   "token_type": "bearer",
#   "user_id": "...",
#   "email": "test@example.com"
# }
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Email confirmation required"
**Symptom**: Signup succeeds but no token returned

**Solution**: Disable email confirmation in Supabase
```
1. Go to: https://app.supabase.com/project/YOUR_PROJECT/auth/providers
2. Click "Email" provider
3. Disable "Enable email confirmations"
4. Save
```

See [FIX-SUPABASE-AUTH.md](FIX-SUPABASE-AUTH.md) for details.

### Issue 2: Token works once then fails
**Symptom**: First request works, subsequent fail

**Cause**: Token not persisting in localStorage

**Solution**: Check if browser has localStorage disabled
```javascript
// Test localStorage
try {
  localStorage.setItem('test', 'value');
  localStorage.removeItem('test');
  console.log('✅ localStorage working');
} catch (e) {
  console.error('❌ localStorage blocked:', e);
}
```

### Issue 3: CORS errors
**Symptom**: Browser console shows CORS policy error

**Solution**: Backend CORS already configured for localhost:5173
```python
# backend/app/main.py already has:
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

If frontend runs on different port, update `allow_origins`.

### Issue 4: Token format issues
**Symptom**: Token exists but backend rejects it

**Verification**: Check token format
```javascript
// Valid JWT format: xxxxx.yyyyy.zzzzz (3 parts separated by dots)
const token = localStorage.getItem('auth_token');
const parts = token.split('.');
console.log('Token parts:', parts.length); // Should be 3

// Each part should be base64-encoded
parts.forEach((part, i) => {
  try {
    const decoded = atob(part);
    console.log(`Part ${i} decoded OK`);
  } catch (e) {
    console.error(`Part ${i} invalid base64`);
  }
});
```

---

## 📊 Token Lifecycle

```
1. User Signup/Login
   ↓
2. Backend validates credentials with Supabase Auth
   ↓
3. Supabase generates JWT token
   ↓
4. Backend returns token in response
   ↓
5. Frontend saves to localStorage: localStorage.setItem('auth_token', token)
   ↓
6. Frontend includes in requests: Authorization: Bearer {token}
   ↓
7. Backend validates token with Supabase Auth
   ↓
8. If valid → Request succeeds
   If invalid/expired → 401 Unauthorized → Auto-logout flow
```

---

## 🔐 Security Best Practices

### Current Implementation (Good)
✅ Tokens stored in localStorage (acceptable for SPA)
✅ HTTPS required in production (configured in backend)
✅ HTTPOnly cookies not used (localStorage is standard for SPAs)
✅ Tokens validated server-side with Supabase Auth
✅ 401 errors trigger immediate token clearance

### Future Enhancements
- **Token Refresh**: Implement refresh token flow for long-lived sessions
- **Token Expiry Check**: Validate token expiry client-side before requests
- **Secure Storage**: Consider storing tokens in memory for sensitive apps
- **Multi-tab Sync**: Sync auth state across browser tabs using BroadcastChannel API

---

## 📝 Related Documentation

- [FIX-SUPABASE-AUTH.md](FIX-SUPABASE-AUTH.md) - Email confirmation issue
- [SUPABASE-QUICK-START.md](SUPABASE-QUICK-START.md) - Setup guide
- [PINECONE-METADATA-FIX.md](PINECONE-METADATA-FIX.md) - Document upload fix

---

## ✅ Verification Checklist

After applying fixes, verify:

- [ ] Frontend automatically detects 401 errors
- [ ] Invalid token cleared from localStorage
- [ ] Login modal appears on auth failure
- [ ] User can re-authenticate without refresh
- [ ] Fresh token allows successful requests
- [ ] Document upload works with valid token
- [ ] Assistance generation works with valid token
- [ ] Logout clears token properly

---

## 🆘 Still Having Issues?

If authentication still fails after trying these solutions:

1. **Check backend logs**:
   ```bash
   # Backend should show detailed auth errors
   tail -f /var/folders/.../tasks/[backend-task-id].output
   ```

2. **Verify Supabase credentials** in `backend/.env`:
   ```bash
   cat backend/.env | grep SUPABASE
   ```

3. **Test backend directly** with curl:
   ```bash
   # Get token first
   TOKEN=$(curl -X POST http://localhost:8000/api/v1/auth/login \
     -H "Content-Type: application/json" \
     -d '{"email":"your@email.com","password":"yourpass"}' \
     | jq -r '.access_token')

   # Test assistance endpoint
   curl -X POST http://localhost:8000/api/v1/assist \
     -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"mode":"START","editor_content":"test","additional_context":null}'
   ```

4. **Check browser network tab**:
   - Open DevTools → Network tab
   - Click "Generate" button
   - Look for `/assist` request
   - Check if Authorization header is present
   - Check response status and body
