# Supabase PostgreSQL Connection Error: Root Cause Analysis

## Error Message
```
psycopg2.OperationalError: connection to server at "aws-0-us-east-1.pooler.supabase.com" (44.216.29.125), port 5432 failed:
FATAL: Tenant or user not found
```

## Root Causes

### 1. **Incorrect Connection URL Format (Most Common)**

Supabase provides two types of connection endpoints:
- **Direct Connection**: `db.{project-ref}.supabase.co:5432`
- **Connection Pooler**: `aws-0-{region}.pooler.supabase.com:5432` or `:6543`

The pooler requires a specific username format: `postgres.{project-ref}` NOT just `postgres`.

**Incorrect:**
```
postgresql://postgres:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres
```

**Correct (Transaction Mode - Port 5432):**
```
postgresql://postgres.{project-ref}:password@aws-0-us-east-1.pooler.supabase.com:5432/postgres?sslmode=require
```

**Correct (Session Mode - Port 6543):**
```
postgresql://postgres.{project-ref}:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require
```

**Correct (Direct Connection - No Pooler):**
```
postgresql://postgres:password@db.{project-ref}.supabase.co:5432/postgres?sslmode=require
```

### 2. **Missing Project Reference in Username**

The pooler uses the username format `postgres.{project-ref}` to route connections to the correct tenant. Without the project reference, Supabase cannot identify which database to connect to, resulting in "Tenant or user not found".

**How to find your project reference:**
- Supabase Dashboard → Settings → General → Reference ID
- Or extract from your Supabase URL: `https://{project-ref}.supabase.co`

### 3. **Wrong Port Selection**

Supabase pooler has two modes:
- **Port 5432 (Transaction Mode)**: Best for connection pooling, supports prepared statements
- **Port 6543 (Session Mode)**: Best for serverless, no prepared statements

Using the wrong port with the wrong username format causes authentication failures.

### 4. **Missing SSL Parameters**

Supabase requires SSL connections. Missing `?sslmode=require` can cause connection failures or security warnings.

### 5. **Incorrect Database Password**

The password might be:
- Wrong password set in environment variables
- Password changed in Supabase dashboard but not updated in `.env`
- Password contains special characters that need URL encoding

### 6. **Database Paused or Project Deleted**

Supabase free tier projects pause after inactivity. The error can occur if:
- Project is paused (wake it up in dashboard)
- Project was deleted
- Project is in a different region than expected

### 7. **Environment Variable Mismatch**

Common issues:
- Local `.env` has different values than production
- CI/CD environment variables not set correctly
- `.env` file not loaded (missing `python-dotenv` or wrong path)
- Environment variable name mismatch (`DATABASE_URL` vs `DB_URL`)

### 8. **SQLAlchemy Engine Configuration Issues**

Problems with engine setup:
- Missing `pool_pre_ping=True` (doesn't detect stale connections)
- Pool size too large for Supabase limits
- Missing connection timeout settings
- Not handling connection errors gracefully

### 9. **IP Allowlist Restrictions**

If IP allowlist is enabled in Supabase:
- Your server's IP might not be whitelisted
- CI/CD runner IPs might not be whitelisted
- Dynamic IPs (home networks) change and break connections

## Supabase Connection URL Format Explained

### Direct Connection (No Pooler)
```
postgresql://[user]:[password]@db.[project-ref].supabase.co:5432/postgres?sslmode=require
```

**Components:**
- `postgresql://` - Protocol
- `[user]` - Usually `postgres` (direct connection)
- `[password]` - Database password from Supabase dashboard
- `db.[project-ref].supabase.co` - Direct database hostname
- `5432` - Standard PostgreSQL port
- `postgres` - Default database name
- `?sslmode=require` - SSL requirement

**Use when:**
- Long-lived connections
- Need prepared statements
- Running migrations
- Local development

### Connection Pooler - Transaction Mode (Port 5432)
```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:5432/postgres?sslmode=require
```

**Components:**
- `postgres.[project-ref]` - **CRITICAL**: Must include project reference
- `aws-0-[region].pooler.supabase.com` - Pooler hostname (region-specific)
- `5432` - Transaction mode port
- Supports prepared statements
- Better for connection pooling

**Use when:**
- Production applications
- Need connection pooling
- Want prepared statement support

### Connection Pooler - Session Mode (Port 6543)
```
postgresql://postgres.[project-ref]:[password]@aws-0-[region].pooler.supabase.com:6543/postgres?sslmode=require
```

**Components:**
- `6543` - Session mode port
- No prepared statements
- Better for serverless functions

**Use when:**
- Serverless environments (AWS Lambda, Vercel)
- Short-lived connections
- Don't need prepared statements

## SQLAlchemy Engine Best Practices for Supabase

### Required Configuration

```python
from sqlalchemy import create_engine
from sqlalchemy.pool import QueuePool

engine = create_engine(
    database_url,
    # Connection Pooling
    poolclass=QueuePool,
    pool_size=5,  # Supabase recommends 5-10 for pooler
    max_overflow=10,  # Total connections = pool_size + max_overflow
    
    # Connection Health
    pool_pre_ping=True,  # CRITICAL: Tests connections before use
    
    # Timeouts
    connect_args={
        "connect_timeout": 10,  # 10 second connection timeout
        "sslmode": "require"  # If not in URL
    },
    
    # Performance
    echo=False,  # Set to True for SQL debugging
    future=True,  # Use SQLAlchemy 2.0 style
)
```

### Why Each Setting Matters

1. **`pool_pre_ping=True`**: 
   - Tests connections before use
   - Detects stale connections from pooler
   - Prevents "connection closed" errors

2. **`pool_size=5`**:
   - Supabase pooler has connection limits
   - Too many connections = "too many connections" errors
   - Start small, increase if needed

3. **`max_overflow=10`**:
   - Allows temporary connection bursts
   - Total max = pool_size + max_overflow = 15

4. **`connect_timeout=10`**:
   - Fails fast if database is unreachable
   - Prevents hanging connections

5. **`sslmode=require`**:
   - Supabase requires SSL
   - Prevents connection errors

## Environment-Safe Configuration Strategy

### 1. Validate DATABASE_URL Format

Check for:
- Contains `supabase` (Supabase connection)
- Contains `pooler` (pooler connection) → must have `postgres.{project-ref}` format
- Contains `sslmode=require` or add it
- Valid PostgreSQL URL format

### 2. Test Connection on Startup

- Attempt connection during application startup
- Fail fast with clear error messages
- Don't start server if database is unreachable (production)
- Allow graceful degradation in development

### 3. Environment Detection

- `ENVIRONMENT=production` → Fail fast on DB errors
- `ENVIRONMENT=development` → Warn but allow startup
- `ENVIRONMENT=test` → Use test database or mock

### 4. Structured Error Messages

Instead of:
```
❌ Connection failed
```

Provide:
```
❌ Database connection failed
   Error: Tenant or user not found
   URL: postgresql://postgres:***@aws-0-us-east-1.pooler.supabase.com:5432/postgres
   
   Possible causes:
   1. Missing project reference in username (should be postgres.{project-ref})
   2. Incorrect password
   3. Database paused - check Supabase dashboard
   4. Wrong connection URL format
   
   Fix:
   - Get connection string from: Settings → Database → Connection string
   - Use Session mode (port 6543) or Transaction mode (port 5432)
   - Ensure username format: postgres.{project-ref}
```

## Debugging Checklist

### Step 1: Verify Supabase Project Status
- [ ] Go to https://app.supabase.com
- [ ] Check if project is active (not paused)
- [ ] Note your project reference ID
- [ ] Check region (us-east-1, us-west-1, etc.)

### Step 2: Get Correct Connection String
- [ ] Go to Settings → Database
- [ ] Copy "Connection string" (URI format)
- [ ] Verify it includes `postgres.{project-ref}` for pooler
- [ ] Check if using pooler or direct connection

### Step 3: Verify Environment Variables
- [ ] Check `.env` file exists and is loaded
- [ ] Verify `DATABASE_URL` matches Supabase dashboard
- [ ] Check for typos or extra spaces
- [ ] Ensure password is URL-encoded if it has special chars

### Step 4: Test Connection Locally
```bash
# Test with psql
psql "postgresql://postgres.{project-ref}:password@aws-0-us-east-1.pooler.supabase.com:6543/postgres?sslmode=require"

# Test with Python
python backend/test_db_connection.py
```

### Step 5: Check SQLAlchemy Configuration
- [ ] `pool_pre_ping=True` is set
- [ ] Pool size is reasonable (5-10)
- [ ] SSL mode is required
- [ ] Connection timeout is set

### Step 6: Verify Network Access
- [ ] Check if IP allowlist is enabled
- [ ] Add your IP to allowlist if needed
- [ ] For CI/CD, add runner IPs or disable allowlist

### Step 7: Check Application Logs
- [ ] Look for connection errors in startup logs
- [ ] Check for environment variable loading errors
- [ ] Verify database URL is being used correctly

## Production Deployment Checklist

### Pre-Deployment
- [ ] Connection string tested in staging environment
- [ ] Environment variables set in deployment platform
- [ ] Database password is secure and not hardcoded
- [ ] Connection pooling limits are appropriate

### Deployment
- [ ] Application fails fast if DB connection fails
- [ ] Health check endpoint tests DB connection
- [ ] Monitoring alerts on DB connection failures
- [ ] Logs include connection status

### Post-Deployment
- [ ] Verify connection pool metrics
- [ ] Check for connection errors in logs
- [ ] Monitor connection count vs limits
- [ ] Test failover scenarios
