# Quick Fix Guide: Supabase Connection Error

## The Problem
```
psycopg2.OperationalError: connection to server failed:
FATAL: Tenant or user not found
```

## The Solution (3 Steps)

### Step 1: Get Correct Connection String

1. Go to [Supabase Dashboard](https://app.supabase.com)
2. Select your project
3. Go to **Settings** → **Database**
4. Find **Connection string** section
5. Copy the **URI** format (not JDBC)

**It should look like:**
```
postgresql://postgres.{project-ref}:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

**Important:** For pooler connections, username MUST be `postgres.{project-ref}`, not just `postgres`

### Step 2: Update Your .env File

```bash
# In backend/.env
DATABASE_URL=postgresql://postgres.{project-ref}:your-password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

Replace:
- `{project-ref}` with your actual project reference ID
- `your-password` with your database password

### Step 3: Test the Connection

```bash
cd backend
python test_database_connection.py
```

If it shows ✅, you're done! If it shows ❌, see troubleshooting below.

## Common Issues

### Issue 1: "Missing project reference in username"

**Problem:** Using `postgres` instead of `postgres.{project-ref}`

**Fix:** Get connection string from Supabase Dashboard (it has the correct format)

### Issue 2: "Password authentication failed"

**Problem:** Wrong password

**Fix:**
1. Go to Supabase Dashboard → Settings → Database
2. Click "Reset Database Password"
3. Copy new password
4. Update DATABASE_URL in .env

### Issue 3: "Database paused"

**Problem:** Supabase free tier project paused after inactivity

**Fix:**
1. Go to Supabase Dashboard
2. Click "Restore" or "Resume" on your project

### Issue 4: "Connection refused"

**Problem:** Wrong hostname or port

**Fix:** Use the exact connection string from Supabase Dashboard

## Verify It Works

Start your application:
```bash
cd backend
python -m uvicorn app.main:app --reload
```

You should see:
```
INFO: Database connection verified: postgresql://postgres.***@...
INFO: ✅ Database initialization completed successfully
```

## What Changed in the Code

The codebase now:
- ✅ Validates database URL format automatically
- ✅ Tests connection on startup
- ✅ Shows clear error messages with fix instructions
- ✅ Fails fast in production (won't start if DB is down)
- ✅ Warns but continues in development

## Need More Help?

- **Detailed Analysis:** See `SUPABASE-CONNECTION-ANALYSIS.md`
- **Code Examples:** See `SUPABASE-CONNECTION-EXAMPLES.py`
- **Full Summary:** See `SUPABASE-CONNECTION-FIX-SUMMARY.md`
