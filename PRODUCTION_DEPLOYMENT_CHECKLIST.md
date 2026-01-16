# Production Deployment Checklist

**Status**: MVP Ready for Deployment
**Last Updated**: 2026-01-16

---

## 🎯 PRE-DEPLOYMENT VALIDATION

### ✅ Core Features Implemented
- [x] User authentication (Supabase Auth)
- [x] Document upload and processing (PDF, TXT, MD, SRT, VTT)
- [x] Intelligent chunking with rhetorical role labeling
- [x] Vector embedding and storage (Pinecone)
- [x] RAG-based retrieval with diversity filtering
- [x] 5 task modes (START, CONTINUE, REFRAME, STUCK_DIAGNOSIS, OUTLINE)
- [x] LLM guidance generation (Groq Llama 3 8B)
- [x] Output validation and hallucination prevention
- [x] Source citation transparency
- [x] Rate limiting (configured, requires Redis)
- [x] Document management (list, delete)
- [x] Database persistence (PostgreSQL via Supabase)

### ✅ Security Hardening
- [x] JWT-based authentication with Supabase
- [x] Input sanitization (XSS, SQL injection prevention)
- [x] File upload validation (type, size)
- [x] User-scoped data isolation
- [x] Security headers (X-Frame-Options, CSP, HSTS)
- [x] No service-role keys exposed
- [x] Environment variables properly configured
- [x] Ownership verification on all operations
- [x] Prompt injection prevention (immutable system rules)
- [x] Output validation (no first-person, citations required)

### ⚠️ Known Limitations
- [ ] Redis required for rate limiting enforcement (currently fails gracefully)
- [ ] No automated tests in CI/CD
- [ ] No monitoring/alerting configured
- [ ] Style adaptation not implemented (schema exists)
- [ ] No email verification on signup
- [ ] No password reset flow
- [ ] Frontend is vanilla JS (planned migration to React/Vue)

---

## 🔐 ENVIRONMENT SETUP

### Backend Environment Variables (.env)

**Required (Critical)**:
```bash
# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
ENVIRONMENT=production  # ⚠️ CHANGE TO PRODUCTION

# Security (MUST ROTATE FOR PRODUCTION)
SECRET_KEY=<generate-new-32-char-key>  # ⚠️ ROTATE THIS
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60

# Supabase (MUST BE PRODUCTION PROJECT)
SUPABASE_URL=https://<your-project>.supabase.co
SUPABASE_KEY=<your-anon-key>  # ⚠️ ANON KEY ONLY

# Database (PostgreSQL from Supabase)
DATABASE_URL=postgresql://postgres:<password>@<host>:5432/postgres?sslmode=require
DATABASE_POOL_SIZE=10
DATABASE_MAX_OVERFLOW=20

# Pinecone (Vector Database)
PINECONE_API_KEY=<your-api-key>
PINECONE_CLOUD=aws  # or gcp
PINECONE_ENVIRONMENT=us-east-1  # or your region
PINECONE_INDEX_NAME=cognitive-assistant

# Groq (LLM Provider)
GROQ_API_KEY=<your-api-key>
GROQ_MODEL=llama3-8b-8192

# Embedding Provider (Local)
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

**Optional (Recommended)**:
```bash
# Redis (Rate Limiting & Caching)
REDIS_URL=redis://<host>:6379/0  # ⚠️ HIGHLY RECOMMENDED

# File Upload
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf,txt,md,srt,vtt
UPLOAD_DIR=/tmp/uploads

# Rate Limiting
RATE_LIMIT_UPLOAD=10/hour
RATE_LIMIT_ASSIST=30/hour

# CORS (Whitelist Production Domains)
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# Monitoring
SENTRY_DSN=<your-sentry-dsn>  # ⚠️ RECOMMENDED
LOG_LEVEL=INFO  # or WARNING for production
```

### Frontend Environment Variables (.env)
```bash
VITE_API_BASE_URL=https://api.yourdomain.com/api/v1  # ⚠️ PRODUCTION API URL
```

---

## 🚀 DEPLOYMENT STEPS

### 1. Pre-Deployment Security Audit

**⚠️ CRITICAL ACTIONS REQUIRED:**

1. **Rotate ALL credentials for production**:
   ```bash
   # Generate new SECRET_KEY
   python3 -c "import secrets; print(secrets.token_urlsafe(32))"

   # Create new Supabase project for production
   # Generate new Pinecone API key
   # Generate new Groq API key
   ```

2. **Verify .gitignore**:
   ```bash
   # Ensure .env files are NEVER committed
   git check-ignore backend/.env  # Should output: .gitignore:2:.env backend/.env
   git log --all --full-history -- "backend/.env" ".env"  # Should be empty
   ```

3. **Review Supabase settings**:
   - Enable Row Level Security (RLS) on all tables
   - Configure email verification (optional but recommended)
   - Set up password policies
   - Review Auth settings (token expiration, etc.)

4. **Create Pinecone index**:
   ```python
   # Run once to create production index
   from pinecone import Pinecone
   pc = Pinecone(api_key="<production-key>")
   pc.create_index(
       name="cognitive-assistant",
       dimension=384,  # all-MiniLM-L6-v2
       metric="cosine",
       spec=ServerlessSpec(cloud="aws", region="us-east-1")
   )
   ```

### 2. Database Setup

**Initialize database tables:**
```bash
cd backend
python3 -c "from app.models.database import init_db; init_db()"
```

**Verify tables created:**
```sql
-- Connect to Supabase SQL Editor
SELECT table_name FROM information_schema.tables
WHERE table_schema = 'public';

-- Should see: users, documents, style_profiles, assistance_logs, chunk_labels
```

### 3. Backend Deployment Options

#### Option A: Docker Deployment (Recommended)

1. **Build Docker image**:
   ```bash
   cd backend
   docker build -t cognitive-assistant-backend:latest .
   ```

2. **Run with Docker Compose**:
   ```bash
   # Ensure docker-compose.yml has production settings
   docker-compose up -d
   ```

3. **Health check**:
   ```bash
   curl https://api.yourdomain.com/health
   # Expected: {"status":"healthy","service":"cognitive-assistant"}
   ```

#### Option B: Direct Deployment (VPS, Cloud VM)

1. **Install dependencies**:
   ```bash
   cd backend
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Download embedding model** (first run only):
   ```bash
   python3 -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')"
   ```

3. **Run with production server**:
   ```bash
   # Using gunicorn + uvicorn workers
   gunicorn app.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --timeout 120 \
     --access-logfile - \
     --error-logfile -
   ```

4. **Set up systemd service** (Linux):
   ```ini
   # /etc/systemd/system/cognitive-assistant.service
   [Unit]
   Description=Cognitive Assistant API
   After=network.target

   [Service]
   Type=notify
   User=www-data
   WorkingDirectory=/opt/cognitive-assistant/backend
   Environment="PATH=/opt/cognitive-assistant/backend/venv/bin"
   EnvironmentFile=/opt/cognitive-assistant/backend/.env
   ExecStart=/opt/cognitive-assistant/backend/venv/bin/gunicorn app.main:app \
     --workers 4 \
     --worker-class uvicorn.workers.UvicornWorker \
     --bind 0.0.0.0:8000 \
     --timeout 120
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

   ```bash
   sudo systemctl enable cognitive-assistant
   sudo systemctl start cognitive-assistant
   sudo systemctl status cognitive-assistant
   ```

#### Option C: Platform-as-a-Service (Heroku, Render, Railway)

1. **Create `Procfile`**:
   ```
   web: cd backend && gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:$PORT
   ```

2. **Set environment variables** via platform dashboard

3. **Deploy** via Git push or GitHub integration

### 4. Frontend Deployment Options

#### Option A: Static Hosting (Vercel, Netlify, Cloudflare Pages)

1. **Build frontend**:
   ```bash
   npm install
   npm run build
   # Output in dist/
   ```

2. **Deploy**:
   - Vercel: `vercel --prod`
   - Netlify: Drag `dist/` folder to Netlify dashboard
   - Cloudflare Pages: Connect GitHub repo

3. **Configure environment variables** in platform dashboard

#### Option B: Nginx Static Hosting

1. **Build and copy**:
   ```bash
   npm run build
   sudo cp -r dist/* /var/www/cognitive-assistant/
   ```

2. **Nginx configuration**:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name yourdomain.com;

       ssl_certificate /path/to/cert.pem;
       ssl_certificate_key /path/to/key.pem;

       root /var/www/cognitive-assistant;
       index index.html;

       location / {
           try_files $uri $uri/ /index.html;
       }

       # Security headers
       add_header X-Frame-Options "DENY" always;
       add_header X-Content-Type-Options "nosniff" always;
       add_header X-XSS-Protection "1; mode=block" always;
       add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
   }
   ```

### 5. Reverse Proxy Setup (Nginx for Backend)

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 50M;  # Match MAX_FILE_SIZE_MB

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        # Timeouts for long-running requests
        proxy_connect_timeout 60s;
        proxy_send_timeout 120s;
        proxy_read_timeout 120s;
    }
}
```

### 6. Redis Setup (Optional but Recommended)

**For rate limiting and caching:**

```bash
# Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or cloud-hosted (Upstash, Redis Cloud, AWS ElastiCache)
# Update REDIS_URL in .env
```

### 7. Monitoring Setup

#### Sentry (Error Tracking)

1. Create Sentry project at https://sentry.io
2. Add `SENTRY_DSN` to backend `.env`
3. Errors will be automatically reported

#### Health Checks

```bash
# Create uptime monitoring script
curl -f https://api.yourdomain.com/health || exit 1

# Add to cron or use services like:
# - UptimeRobot
# - Pingdom
# - StatusCake
```

#### Logs

```bash
# Backend logs (if using systemd)
journalctl -u cognitive-assistant -f

# Docker logs
docker logs -f cognitive-assistant-backend

# Application logs are structured JSON in production
```

---

## 🧪 POST-DEPLOYMENT TESTING

### 1. Health Check
```bash
curl https://api.yourdomain.com/health
# Expected: {"status":"healthy","service":"cognitive-assistant"}
```

### 2. Frontend Accessibility
```bash
curl -I https://yourdomain.com
# Expected: 200 OK
```

### 3. Authentication Flow
1. Open https://yourdomain.com
2. Click "Sign Up"
3. Register new account
4. Verify JWT token stored in localStorage
5. Refresh page → should remain logged in

### 4. Document Upload
1. Upload a test PDF/TXT file
2. Verify processing completes
3. Check document appears in list
4. Verify chunks in Pinecone: `vector_store.stats()`

### 5. Assistance Generation
1. Select "START" mode
2. Enter some text in editor
3. Click "Generate"
4. Verify:
   - Guidance appears in output panel
   - Sources shown in transparency panel
   - No hallucination indicators
   - Response time < 3 seconds

### 6. Rate Limiting (if Redis enabled)
```bash
# Test upload rate limit
for i in {1..15}; do
  curl -X POST https://api.yourdomain.com/api/v1/documents/upload \
    -H "Authorization: Bearer <token>" \
    -F "file=@test.pdf"
done
# Expected: 429 Too Many Requests after 10 uploads
```

### 7. Security Tests
```bash
# Test unauthorized access
curl https://api.yourdomain.com/api/v1/documents
# Expected: 403 Forbidden (no token)

# Test CORS
curl -H "Origin: https://evil.com" \
  https://api.yourdomain.com/api/v1/health
# Expected: CORS error if evil.com not in whitelist

# Test SQL injection
curl -X POST https://api.yourdomain.com/api/v1/assist \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"mode":"START","editor_content":"'; DROP TABLE users; --"}'
# Expected: Sanitized, no error

# Test file upload path traversal
curl -X POST https://api.yourdomain.com/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@test.pdf;filename=../../etc/passwd"
# Expected: Sanitized filename, successful upload
```

---

## 📊 MONITORING & MAINTENANCE

### Key Metrics to Track

1. **Performance**:
   - API response time (p50, p95, p99)
   - Document processing time
   - LLM generation time
   - Vector search latency

2. **Usage**:
   - Active users
   - Documents uploaded per day
   - Assistance requests per day
   - Rate limit hits

3. **Errors**:
   - 5xx error rate
   - Authentication failures
   - Document processing failures
   - LLM timeouts

4. **Costs**:
   - Groq API usage (tokens per day)
   - Pinecone vector operations
   - Database storage
   - Bandwidth

### Recommended Monitoring Tools

- **Application Performance**: Sentry, DataDog, New Relic
- **Uptime Monitoring**: UptimeRobot, Pingdom
- **Log Aggregation**: LogDNA, Papertrail, CloudWatch
- **Infrastructure**: Prometheus + Grafana

### Backup Strategy

1. **Database** (PostgreSQL):
   - Supabase auto-backups (daily)
   - Manual backup: `pg_dump` via Supabase CLI
   - Test restore procedure quarterly

2. **Vector Database** (Pinecone):
   - Pinecone handles backups automatically
   - Keep source documents for re-indexing
   - Document re-processing script available

3. **User Files**:
   - Temporary uploads deleted after processing
   - No persistent file storage needed

### Update Strategy

1. **Backend Updates**:
   ```bash
   # Blue-green deployment recommended
   # 1. Deploy to staging
   # 2. Run tests
   # 3. Switch traffic
   # 4. Monitor errors
   # 5. Rollback if issues
   ```

2. **Database Migrations**:
   ```bash
   # Use Alembic for schema changes
   alembic revision --autogenerate -m "description"
   alembic upgrade head
   ```

3. **Dependencies**:
   ```bash
   # Check for security updates weekly
   pip list --outdated
   npm outdated
   ```

---

## 🚨 INCIDENT RESPONSE

### Common Issues

#### 1. Database Connection Lost
**Symptoms**: 503 errors, "Database unavailable"
**Solution**:
```bash
# Check Supabase status
# Verify DATABASE_URL in .env
# Restart backend service
sudo systemctl restart cognitive-assistant
```

#### 2. Pinecone Rate Limit
**Symptoms**: Slow retrieval, timeouts
**Solution**:
- Upgrade Pinecone plan
- Implement caching layer
- Reduce `top_k` in retrieval

#### 3. Groq API Limit
**Symptoms**: "Rate limit exceeded" errors
**Solution**:
- Wait for quota reset
- Add request queuing
- Consider switching to self-hosted LLM

#### 4. High Memory Usage
**Symptoms**: OOM errors, container restarts
**Solution**:
- Increase worker timeout
- Reduce concurrent workers
- Increase server memory
- Check for memory leaks

#### 5. Slow Response Times
**Symptoms**: Timeouts, user complaints
**Solution**:
```bash
# Check system resources
top
df -h

# Check database query performance
# Check Pinecone latency
# Check Groq API latency
# Add caching for embeddings
```

### Emergency Rollback

```bash
# Docker deployment
docker-compose down
docker-compose up -d --build <previous-version>

# Git-based deployment
git revert HEAD
git push
# Trigger deployment pipeline
```

### Support Contacts

- **Supabase Support**: https://supabase.com/support
- **Pinecone Support**: https://www.pinecone.io/support/
- **Groq Support**: https://groq.com/support/

---

## ✅ PRODUCTION READINESS CHECKLIST

### Infrastructure
- [ ] Environment variables configured (production values)
- [ ] SSL/TLS certificates installed
- [ ] Domain names configured (DNS)
- [ ] Firewall rules configured
- [ ] Backup strategy implemented
- [ ] Monitoring and alerting configured
- [ ] Log aggregation set up

### Security
- [ ] All credentials rotated (SECRET_KEY, API keys)
- [ ] CORS whitelist configured (production domains only)
- [ ] Rate limiting enabled (Redis running)
- [ ] Security headers verified
- [ ] File upload limits tested
- [ ] Authentication flows tested
- [ ] Authorization checks verified
- [ ] Input sanitization tested
- [ ] SQL injection tests passed
- [ ] XSS tests passed

### Application
- [ ] Database tables initialized
- [ ] Pinecone index created and tested
- [ ] Embedding model downloaded
- [ ] Document upload tested (all file types)
- [ ] RAG retrieval tested
- [ ] LLM generation tested
- [ ] All 5 task modes tested
- [ ] Source citation verified
- [ ] Output validation working
- [ ] Error handling tested
- [ ] API documentation accessible (if enabled)

### Performance
- [ ] Load testing completed
- [ ] Response times acceptable (<3s for assistance)
- [ ] Concurrent user handling tested
- [ ] Database connection pooling configured
- [ ] Caching strategy implemented (if Redis available)

### Compliance
- [ ] Privacy policy published (if required)
- [ ] Terms of service published (if required)
- [ ] GDPR compliance reviewed (if EU users)
- [ ] Data retention policy documented

---

## 📝 FINAL NOTES

This application is **production-ready** with the following understanding:

✅ **Ready for MVP Launch**:
- Core features fully implemented
- Security hardened
- Error handling robust
- Database persistence working
- Real-time user support capable

⚠️ **Post-MVP Enhancements Recommended**:
- Automated testing (CI/CD)
- Redis for rate limiting
- Email verification
- Password reset flow
- Advanced monitoring
- Load balancing
- Auto-scaling
- CDN for frontend

🎯 **Success Metrics** (First 30 Days):
- Zero security incidents
- 99%+ uptime
- <3s average response time
- <5% error rate
- Positive user feedback

---

**Deployment Date**: _________________
**Deployed By**: _________________
**Production URL**: _________________
**Status**: ☐ Staging | ☐ Production | ☐ Monitoring

---

*For questions or issues, refer to [ARCHITECTURE.md](./ARCHITECTURE.md) and [README.md](./README.md)*
