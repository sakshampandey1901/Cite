# Quick Deployment Guide

**Status**: Production-Ready MVP
**Version**: 0.1.0

---

## 🚀 One-Command Deployment

```bash
./scripts/deploy.sh
```

This script will:
1. Install Python dependencies
2. Download embedding models
3. Initialize database tables
4. Create Pinecone index
5. Setup Redis (optional)
6. Build frontend (optional)
7. Start production server

---

## ✅ Pre-Deployment Checklist

### 1. Environment Configuration

Verify `backend/.env` has production values:

```bash
# Check these are set correctly:
grep "ENVIRONMENT=production" backend/.env
grep "CORS_ORIGINS=https://" backend/.env
```

**Critical**: All credentials have been rotated with new values.

### 2. Update Production Domains

Replace placeholder domains in `backend/.env`:

```bash
# Change from:
CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com

# To your actual domains:
CORS_ORIGINS=https://actual-domain.com,https://www.actual-domain.com
```

### 3. Optional: Enable Monitoring

Add Sentry DSN to `backend/.env`:

```bash
SENTRY_DSN=https://your-sentry-dsn@sentry.io/project-id
```

---

## 📦 Manual Deployment Steps

If you prefer manual control:

### Step 1: Install Dependencies

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### Step 2: Download Models

```bash
python3 scripts/download_models.py
```

### Step 3: Initialize Database

```bash
python3 scripts/init_database.py
```

### Step 4: Create Pinecone Index

```bash
python3 scripts/init_pinecone.py
```

### Step 5: Setup Redis (Optional)

```bash
# macOS
brew install redis
brew services start redis

# Linux (Docker)
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Or run the setup script
./scripts/setup_redis.sh
```

### Step 6: Start Server

```bash
cd backend
source venv/bin/activate

# Development (single worker)
uvicorn app.main:app --host 0.0.0.0 --port 8000

# Production (multi-worker)
gunicorn app.main:app \
  --workers 4 \
  --worker-class uvicorn.workers.UvicornWorker \
  --bind 0.0.0.0:8000 \
  --timeout 120
```

---

## 🧪 Verify Deployment

### 1. Health Check

```bash
curl http://localhost:8000/health
# Expected: {"status":"healthy","service":"cognitive-assistant"}
```

### 2. Database Connection

```bash
curl http://localhost:8000/
# Expected: {"service":"Cognitive Assistant API","version":"0.1.0","status":"operational"}
```

### 3. Test Upload (with auth token)

```bash
# First login to get token
# Then test upload
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test.pdf"
```

---

## 🐳 Docker Deployment

### Build

```bash
cd backend
docker build -t cognitive-assistant:latest .
```

### Run

```bash
docker run -d \
  --name cognitive-assistant \
  -p 8000:8000 \
  --env-file .env \
  cognitive-assistant:latest
```

### With Docker Compose

```bash
docker-compose up -d
```

---

## 🌐 Production Hosting Options

### Option 1: VPS (DigitalOcean, Linode, AWS EC2)

1. Upload code to server
2. Run `./scripts/deploy.sh`
3. Configure Nginx as reverse proxy
4. Setup SSL with Let's Encrypt

### Option 2: Platform-as-a-Service

**Render, Railway, Fly.io**:
1. Connect GitHub repo
2. Set environment variables in dashboard
3. Deploy automatically

**Heroku**:
```bash
# Add Procfile
echo "web: cd backend && gunicorn app.main:app --workers 4 --worker-class uvicorn.workers.UvicornWorker --bind 0.0.0.0:\$PORT" > Procfile

# Deploy
heroku create your-app-name
git push heroku main
```

---

## ⚙️ Production Configuration

### Systemd Service (Linux)

Create `/etc/systemd/system/cognitive-assistant.service`:

```ini
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
  --bind 0.0.0.0:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable cognitive-assistant
sudo systemctl start cognitive-assistant
sudo systemctl status cognitive-assistant
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/cognitive-assistant`:

```nginx
upstream backend {
    server 127.0.0.1:8000;
}

server {
    listen 443 ssl http2;
    server_name api.yourdomain.com;

    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;

    client_max_body_size 50M;

    location / {
        proxy_pass http://backend;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

Enable:

```bash
sudo ln -s /etc/nginx/sites-available/cognitive-assistant /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

---

## 📊 Monitoring

### Check Logs

```bash
# Systemd service
journalctl -u cognitive-assistant -f

# Docker
docker logs -f cognitive-assistant

# Direct
tail -f /var/log/cognitive-assistant.log
```

### Sentry (Error Tracking)

Errors are automatically reported to Sentry if `SENTRY_DSN` is configured.

### Health Monitoring

Set up external monitoring:
- UptimeRobot: https://uptimerobot.com
- Pingdom: https://pingdom.com

Check endpoint: `https://api.yourdomain.com/health`

---

## 🔒 Security Checklist

Before going live:

- [ ] `ENVIRONMENT=production` in backend/.env
- [ ] New `SECRET_KEY` generated (not the development one)
- [ ] Production Supabase project (not development)
- [ ] Production Pinecone API key
- [ ] Production Groq API key
- [ ] `CORS_ORIGINS` set to actual domains only
- [ ] SSL/TLS certificate installed
- [ ] Firewall configured (only ports 80, 443, 22 open)
- [ ] Redis password protected (if exposed)
- [ ] Database connection uses SSL
- [ ] `.env` file has `600` permissions
- [ ] Sentry configured for error tracking

---

## 📝 Post-Deployment

### 1. Test Core Flows

- [ ] User signup/login
- [ ] Document upload (PDF, TXT)
- [ ] AI assistance generation
- [ ] Document deletion
- [ ] Source citations display

### 2. Monitor Performance

- [ ] Response times <3s
- [ ] No 500 errors
- [ ] Database queries optimized
- [ ] Memory usage stable

### 3. Setup Backups

- [ ] Database backups (Supabase auto-backup enabled)
- [ ] Document source files archived
- [ ] Environment configuration backed up

---

## 🆘 Troubleshooting

### Database Connection Failed

```bash
# Test connection
python3 scripts/init_database.py
```

Check:
- DATABASE_URL is correct
- Network access to Supabase
- SSL mode is `require`

### Pinecone Initialization Failed

```bash
# Test Pinecone
python3 scripts/init_pinecone.py
```

Check:
- PINECONE_API_KEY is valid
- PINECONE_ENVIRONMENT matches your project
- Index doesn't already exist with different config

### Redis Not Running

```bash
# Check Redis
redis-cli ping
```

If Redis is not available, rate limiting will be disabled (gracefully).

### Groq API Errors

Check:
- GROQ_API_KEY is valid
- Not exceeding free tier limits (14,400 req/day)
- Prompt is properly formatted (fixed in latest code)

---

## 📈 Scaling

When you outgrow single instance:

1. **Load Balancer**: Nginx/HAProxy + multiple backend instances
2. **Redis**: Move to managed Redis (Upstash, Redis Cloud)
3. **Database**: Enable read replicas
4. **Pinecone**: Upgrade to serverless or pod-based
5. **Monitoring**: Add DataDog/New Relic

---

## 💰 Cost Management

Monitor usage:
- Groq dashboard: https://console.groq.com
- Pinecone dashboard: https://app.pinecone.io
- Supabase dashboard: https://app.supabase.com

Free tier limits:
- Groq: 14,400 requests/day (supports ~480 users)
- Pinecone: 100,000 vectors (~200 users at 500 vectors/user)
- Supabase: 500MB storage (~5,000 users)

See [ACTUAL_COST_ANALYSIS.md](ACTUAL_COST_ANALYSIS.md) for detailed breakdown.

---

## 🎯 Success Metrics

Track in first 30 days:
- 99%+ uptime
- <3s average response time
- <5% error rate
- Zero security incidents
- 50+ active users

---

For detailed deployment instructions, see [PRODUCTION_DEPLOYMENT_CHECKLIST.md](PRODUCTION_DEPLOYMENT_CHECKLIST.md)

For known limitations, see [KNOWN_LIMITATIONS_AND_ROADMAP.md](KNOWN_LIMITATIONS_AND_ROADMAP.md)
