# Quick Start - Supabase Auth Setup

## 🚀 Get Started in 5 Minutes

### 1. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Get Supabase Credentials

1. Go to [https://app.supabase.com](https://app.supabase.com)
2. Create a new project (or use existing)
3. Go to **Settings** → **API**
4. Copy your credentials:
   - **Project URL**
   - **anon public key**

### 3. Configure Environment

Create `backend/.env`:

```bash
# Supabase
SUPABASE_URL=https://xxxxx.supabase.co
SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...

# Database (from Supabase Settings → Database)
DATABASE_URL=postgresql://postgres:your-password@db.xxxxx.supabase.co:5432/postgres

# Security
SECRET_KEY=your-secret-key-change-this

# LLM & Vector DB (your existing keys)
GROQ_API_KEY=your-groq-key
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX_NAME=cognitive-assistant
```

### 4. Enable Email Auth in Supabase

1. Go to **Authentication** → **Providers**
2. Enable **Email**
3. Save

### 5. Run Migrations

```bash
cd backend
alembic upgrade head
```

If alembic fails, manually update:
```sql
ALTER TABLE users ALTER COLUMN hashed_password DROP NOT NULL;
ALTER TABLE users ALTER COLUMN hashed_password SET DEFAULT '';
```

### 6. Start Backend

```bash
cd backend
uvicorn app.main:app --reload
```

### 7. Test It!

**Signup:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

**Login:**
```bash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "password123"}'
```

---

## ✅ What's Different?

| Before | After |
|--------|-------|
| Manual bcrypt hashing | Supabase handles it |
| Custom JWT generation | Supabase manages tokens |
| 400 Bad Request errors | Fixed automatically |
| ~300 lines of auth code | ~100 lines |
| Security risks | Production-ready |

---

## 🔧 Troubleshooting

**"SUPABASE_URL not set"**
→ Add it to `backend/.env`

**"User already registered"**
→ Email exists. Use different email or delete from Supabase dashboard

**"Could not validate credentials"**
→ Check you're using the **anon key**, not service role key

**Token expired**
→ Tokens expire after 1 hour. Re-login to get fresh token

---

## 📚 Full Documentation

See [SUPABASE-AUTH-MIGRATION.md](SUPABASE-AUTH-MIGRATION.md) for detailed explanation.

---

## 🎯 Key Changes

1. **No more bcrypt in code** - Supabase handles all password hashing
2. **Tokens from Supabase** - JWT generation automated
3. **Local DB sync** - Users synced to local DB for app data only
4. **Validation automatic** - Password rules enforced by Supabase
5. **Production ready** - Battle-tested auth system

That's it! Your authentication is now powered by Supabase. 🎉
