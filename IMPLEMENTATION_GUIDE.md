# Implementation Guide

This guide explains how to deploy and run the AI-powered cognitive assistant system.

---

## Prerequisites

### Required Software
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15+
- Redis 7+

### Required API Keys
- **Groq API Key**: For LLM inference (https://console.groq.com)
- **Embedding Model**: Local Hugging Face model (no API key required)
- **Pinecone API Key**: For vector database (https://www.pinecone.io)

---

## Quick Start (Development)

### 1. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment template
cp .env.example .env

# Edit .env and add your API keys
nano .env

# Start dependencies using Docker Compose
docker-compose up -d postgres redis

# Run backend
python -m app.main
```

The backend API will be available at `http://localhost:8000`

### 2. Frontend Setup

```bash
# From project root
npm install

# Copy environment template
cp .env.example .env

# Start development server
npm run dev
```

The frontend will be available at `http://localhost:5173`

---

## Configuration

### Backend Environment Variables

Edit `backend/.env`:

```bash
# Required - Add your API keys
GROQ_API_KEY=grq_xxxxx
GROQ_MODEL=llama3-8b-8192
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
PINECONE_API_KEY=xxxxx

# Database (use defaults for local development)
DATABASE_URL=postgresql://cognitive_user:cognitive_pass@localhost:5432/cognitive_assistant
REDIS_URL=redis://localhost:6379/0

# Security (generate a secure key for production)
SECRET_KEY=your-secret-key-change-this-in-production

# File Upload
MAX_FILE_SIZE_MB=50
ALLOWED_EXTENSIONS=pdf,txt,md,srt,vtt

# Rate Limiting
RATE_LIMIT_UPLOAD=10/hour
RATE_LIMIT_ASSIST=30/hour
```

### Frontend Environment Variables

Edit `.env`:

```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Usage

### 1. Upload Documents

1. Click the **+** button in the Sources panel
2. Select a PDF, text file, or subtitle file (.srt/.vtt)
3. Wait for processing to complete (status will change to "ready")

**Supported file types:**
- PDF documents (.pdf)
- Plain text (.txt)
- Markdown (.md)
- Subtitle files (.srt, .vtt)

### 2. Select Task Mode

Choose one of five modes:

- **START**: Get guidance on how to begin writing about a topic
- **CONTINUE**: Identify logical next steps in existing writing
- **REFRAME**: Explore alternative angles or perspectives
- **STUCK DIAGNOSIS**: Understand why you're blocked and how to proceed
- **OUTLINE**: Generate a skeletal structure for your writing

### 3. Request Assistance

1. (Optional) Write some context in the editor
2. Click **Generate (Mode Name)**
3. Review the guidance in the Assistant Output panel
4. Check Context Sources to see which documents were used

---

## Architecture Overview

### Backend Components

```
backend/
├── app/
│   ├── api/          # API routes
│   ├── core/         # Config, security
│   ├── models/       # Pydantic schemas, DB models
│   ├── services/     # Business logic
│   │   ├── document_processor.py   # PDF/text parsing
│   │   ├── vector_store.py         # Pinecone integration
│   │   ├── prompt_builder.py       # Prompt layering
│   │   └── llm_service.py          # Groq LLM
│   └── main.py       # FastAPI app
└── tests/            # Security & evaluation tests
```

### Frontend Components

```
src/
├── components/
│   ├── KnowledgeBase.js      # Document management
│   ├── ModeSelector.js       # Task mode selection
│   ├── OutputPanel.js        # Guidance display
│   └── TransparencyPanel.js  # Source citations
├── services/
│   └── api.js                # Backend API client
└── main.js                   # App initialization
```

---

## Security Features

### Input Validation
- File type whitelist enforcement
- File size limits (50MB default)
- SQL injection pattern sanitization
- XSS pattern sanitization
- Path traversal prevention

### Authentication
- JWT token-based authentication
- User-scoped data isolation
- Ownership verification for all operations

### Rate Limiting
- 10 uploads per hour per user
- 30 assistance requests per hour per user

### Prompt Security
- Immutable system rules layer
- Output validation to prevent hallucination
- First-person perspective detection
- Citation requirement enforcement

---

## Testing

### Run Security Tests

```bash
cd backend
pytest tests/test_security.py -v
```

### Run Evaluation Tests

```bash
pytest tests/test_evaluation.py -v
```

### Manual Testing Checklist

- [ ] Upload a PDF document
- [ ] Verify document appears in Sources panel
- [ ] Select START mode
- [ ] Generate guidance with empty editor
- [ ] Verify guidance includes source citations
- [ ] Verify guidance follows required structure
- [ ] Write some text in editor
- [ ] Select CONTINUE mode
- [ ] Verify guidance incorporates editor content
- [ ] Test all 5 modes
- [ ] Verify source citations are accurate
- [ ] Test file upload validation (try .exe file - should fail)

---

## Troubleshooting

### Backend won't start

**Error: Missing API keys**
- Solution: Add required API keys to `backend/.env`

**Error: Database connection failed**
- Solution: Ensure PostgreSQL is running (`docker-compose up -d postgres`)

**Error: Redis connection failed**
- Solution: Ensure Redis is running (`docker-compose up -d redis`)

### Frontend can't connect to backend

**Error: CORS error**
- Solution: Verify `CORS_ORIGINS` in `backend/.env` includes your frontend URL

**Error: 401 Unauthorized**
- Solution: Authentication not yet implemented in MVP. For testing, you can bypass auth by modifying the routes.

### Document upload fails

**Error: File too large**
- Solution: Reduce file size or increase `MAX_FILE_SIZE_MB` in backend config

**Error: Unsupported file type**
- Solution: Only PDF, TXT, MD, SRT, VTT files are supported

### Guidance generation fails

**Error: No relevant sources**
- Solution: Upload documents related to your query topic

**Error: Groq API error**
- Solution: Verify API key and check rate limits

---

## Production Deployment

### Docker Deployment

```bash
cd backend
docker-compose up -d
```

This will start:
- PostgreSQL database
- Redis cache
- FastAPI backend

### Environment-Specific Configuration

**Production checklist:**
- [ ] Generate secure `SECRET_KEY` (32+ characters)
- [ ] Set `ENVIRONMENT=production`
- [ ] Disable API docs (`docs_url=None`)
- [ ] Enable HTTPS only
- [ ] Configure proper CORS origins
- [ ] Set up monitoring (Sentry DSN)
- [ ] Configure database backups
- [ ] Set up rate limiting with Redis
- [ ] Review and restrict file upload limits
- [ ] Enable database connection pooling

### Scaling Considerations

**Horizontal Scaling:**
- Backend API: Stateless, can scale horizontally behind load balancer
- Vector DB: Pinecone is managed and auto-scales
- Database: Use read replicas for read-heavy workloads

**Performance Optimization:**
- Enable Redis caching for frequently accessed documents
- Use CDN for frontend assets
- Implement request batching for multiple document uploads
- Consider async processing for large documents

---

## Monitoring & Logging

### Health Check Endpoint

```bash
curl http://localhost:8000/api/v1/health
```

Expected response:
```json
{
  "status": "healthy",
  "service": "cognitive-assistant"
}
```

### Logs

Backend logs include:
- Request/response timing
- Error traces
- Authentication events
- Document processing status

View logs:
```bash
docker-compose logs -f api
```

---

## Evaluation Metrics

### Retrieval Quality
- **Target**: Top-5 hit rate > 85%
- **Measure**: Manually verify that top 5 retrieved chunks are relevant

### User Satisfaction
- **Target**: 4+ stars on guidance quality
- **Measure**: User feedback survey

### Safety
- **Target**: Zero hallucination incidents
- **Measure**: User reports + automated validation

### Performance
- **Target**: p95 response time < 3s
- **Measure**: Request timing logs

### Uptime
- **Target**: 99.5% availability
- **Measure**: Health check monitoring

---

## MVP Limitations

The current MVP does **not** include:

1. User registration/login (authentication stub only)
2. Real-time collaboration
3. Video transcript processing (only manual .srt upload)
4. Advanced style adaptation (basic pattern matching only)
5. Mobile app
6. OCR for scanned documents
7. Multi-language support

These features are planned for post-MVP releases.

---

## Support & Contribution

### Reporting Issues
- Check existing issues first
- Provide detailed reproduction steps
- Include error logs and configuration (sanitize API keys!)

### Development Workflow
1. Create feature branch from `main`
2. Implement changes with tests
3. Run test suite: `pytest tests/ -v`
4. Submit pull request with description

---

## License

[Specify your license here]

---

## Acknowledgments

This system uses:
- **Groq (Llama 3 8B)** for guidance generation
- **Hugging Face all-MiniLM-L6-v2** for semantic search
- **Pinecone** for vector storage
- **FastAPI** for backend framework
- **Vanilla JS** for frontend (planned migration to React)
