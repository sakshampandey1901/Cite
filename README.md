# Cite - AI-Powered Cognitive Assistant

An AI-powered personal cognitive assistant that learns from your uploaded documents (PDFs, research papers, notes, video transcripts) to provide structured, thinking-aligned guidance during writing and problem-solving.

**Core Philosophy**: Provide structured guidance, not final answers. Help users start, continue, reframe, or unblock their thinking without impersonating them or claiming to "think like" them.

---

## Key Features

### Zero Hallucination Design
- All outputs traceable to uploaded sources
- Explicit uncertainty flagging when sources are insufficient
- No claims beyond provided corpus

### Five Task Modes
1. **START**: Guidance on how to begin approaching a topic
2. **CONTINUE**: Identify logical next steps in existing writing
3. **REFRAME**: Suggest alternative angles consistent with prior reasoning
4. **STUCK DIAGNOSIS**: Explain why progress stalls and suggest paths forward
5. **OUTLINE**: Generate skeletal structure (no prose)

### Retrieval-Augmented Generation (RAG)
- Semantic search across user's document corpus
- Source citation with page numbers and relevance scores
- Hybrid search (semantic + keyword matching)

### Security-First Design
- Input sanitization (SQL injection, XSS prevention)
- User-scoped data isolation
- Rate limiting (10 uploads/hour, 30 assistance requests/hour)
- File type validation and size limits
- Authentication and authorization

### Transparency
- Every suggestion shows source citations
- Rhetorical role labeling (argument, example, background, etc.)
- Relevance scores for each source

---

## Quick Start

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- API Keys: Groq, Pinecone

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd cognitive-assistant

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Edit .env and add your API keys

# Start dependencies
docker-compose up -d

# Run backend
python -m app.main
```

```bash
# Frontend setup (new terminal)
npm install
cp .env.example .env
npm run dev
```


---

## Architecture

### System Overview

```
┌─────────────┐
│   Frontend  │  Vanilla JS (planned: React)
│  (Vite)     │
└──────┬──────┘
       │ HTTP/REST
┌──────▼──────┐
│   FastAPI   │  Python 3.11
│   Backend   │
└──────┬──────┘
       │
   ┌───┴────┬──────────┬──────────┐
   ▼        ▼          ▼          ▼
┌────┐  ┌─────┐  ┌─────────┐  ┌──────┐
│ DB │  │Redis│  │Pinecone │  │ Groq │
│PG  │  │Cache│  │ Vector  │  │ LLM  │
└────┘  └─────┘  └─────────┘  └──────┘
```

### Prompt Layering System

The system uses a 6-layer prompt architecture for safety and determinism:

1. **System Rules** (Immutable): Zero hallucination, no impersonation
2. **Identity & Scope**: Role definition, capabilities
3. **Task Mode**: Specific mode instructions (START, CONTINUE, etc.)
4. **Retrieved Context**: Source chunks with metadata
5. **User Input**: Editor content + mode selection
6. **Output Format**: Mandatory structure enforcement

### Document Processing Pipeline

```
Upload → Validate → Parse → Chunk → Extract Metadata → Embed → Store
                                                              ↓
                                                         Pinecone
```

---

## Security Features

### Input Validation
- File type whitelist (PDF, TXT, MD, SRT, VTT only)
- File size limits (50MB default)
- Filename sanitization (path traversal prevention)
- SQL injection pattern detection
- XSS pattern detection

### Authentication & Authorization
- JWT token-based authentication
- User-scoped data isolation (users cannot access others' documents)
- Ownership verification on all operations

### Prompt Security
- Immutable system rules
- Output validation (first-person detection, citation requirements)
- Hallucination prevention through mandatory source citation

### Rate Limiting
- 10 document uploads per hour per user
- 30 assistance requests per hour per user

---

## Usage

### 1. Upload Documents

Click the **+** button in the Sources panel and upload:
- Research papers (PDF)
- Lecture notes (TXT, MD)
- Video transcripts (SRT, VTT)

### 2. Select a Task Mode

Choose from:
- **START**: "How do I begin writing about X?"
- **CONTINUE**: "What comes next in my argument?"
- **REFRAME**: "What's an alternative angle?"
- **STUCK DIAGNOSIS**: "Why am I stuck?"
- **OUTLINE**: "Give me a skeletal structure"

### 3. Request Assistance

1. (Optional) Write some context in the editor
2. Click **Generate**
3. Review guidance in the Assistant Output panel
4. Check Context Sources to see which documents were cited

---

## Evaluation Framework

The system is evaluated on:

1. **Structural Similarity** (40%): Does output match user's typical structure?
2. **Reasoning-Path Alignment** (30%): Does approach match user's patterns?
3. **Failure-Mode Alignment** (15%): Does it correctly identify uncertainty?
4. **Continuation Plausibility** (10%): Would this be a logical next step?
5. **Preference Consistency** (5%): Cross-session consistency

### Success Metrics
- Retrieval Quality: Top-5 hit rate > 85%
- User Satisfaction: 4+ stars
- Safety: Zero hallucination incidents
- Performance: p95 < 3s
- Uptime: 99.5%

---

## API Documentation

### POST /api/v1/documents/upload
Upload a document for processing.

**Request:**
```bash
curl -X POST http://localhost:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@document.pdf"
```

**Response:**
```json
{
  "document_id": "uuid",
  "filename": "document.pdf",
  "status": "ready",
  "created_at": "2024-01-10T12:00:00"
}
```

### POST /api/v1/assist
Request cognitive assistance.

**Request:**
```json
{
  "mode": "START",
  "editor_content": "I want to write about cognitive tools",
  "additional_context": null
}
```

**Response:**
```json
{
  "guidance": "## START Guidance\n\n### 1. Likely Next Move\n...",
  "sources": [
    {
      "source": "cognitive_science.pdf",
      "page": 12,
      "content_type": "research_paper",
      "rhetorical_role": "argument",
      "similarity_score": 0.89,
      "content_preview": "..."
    }
  ],
  "mode": "START",
  "metadata": {
    "retrieval_time_ms": 120,
    "generation_time_ms": 1800,
    "source_count": 3
  }
}
```

See [ARCHITECTURE.md](ARCHITECTURE.md) for complete API specification.

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

### Manual Testing
1. Upload a test PDF
2. Try all 5 task modes
3. Verify source citations
4. Test invalid file uploads (should reject .exe, .sh, etc.)
5. Test large files (should reject > 50MB)

---

## MVP Scope

### Included
- PDF/text document processing
- 5 task modes
- Vector-based semantic search
- Source citation with transparency
- Input validation and security
- Rate limiting

### Not Included (Post-MVP)
- User registration/login system (auth stub only)
- Video transcript processing (manual .srt upload only)
- Real-time collaboration
- Mobile app
- OCR for scanned documents
- Advanced style adaptation

---

## Project Structure

```
.
├── backend/
│   ├── app/
│   │   ├── api/              # API routes
│   │   ├── core/             # Config, security
│   │   ├── models/           # Schemas, DB models
│   │   ├── services/         # Business logic
│   │   │   ├── document_processor.py
│   │   │   ├── vector_store.py
│   │   │   ├── prompt_builder.py
│   │   │   └── llm_service.py
│   │   └── main.py
│   ├── tests/
│   ├── requirements.txt
│   ├── Dockerfile
│   └── docker-compose.yml
├── src/
│   ├── components/
│   ├── services/
│   │   └── api.js
│   └── main.js
├── ARCHITECTURE.md           # Detailed architecture
├── IMPLEMENTATION_GUIDE.md   # Deployment guide
└── README.md                 # This file
```

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python 3.11)
- **LLM**: Groq (Llama 3 8B)
- **Embeddings**: Hugging Face `all-MiniLM-L6-v2` (local)
- **Vector DB**: Pinecone
- **Database**: PostgreSQL 15
- **Cache**: Redis 7
- **Document Parsing**: PyMuPDF, python-docx

### Frontend
- **Framework**: Vanilla JS (Vite)
- **Planned**: React/Vue migration

### Infrastructure
- **Containerization**: Docker
- **Deployment**: Cloud-agnostic (AWS/GCP/Azure)

---

## Contributing

### Development Workflow
1. Create feature branch
2. Implement with tests
3. Run test suite
4. Submit PR

### Code Standards
- Python: PEP 8, type hints
- JavaScript: ES6+, ESLint
- Security: OWASP Top 10 compliance
- Testing: pytest for backend

---

## Troubleshooting

See [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md#troubleshooting) for detailed troubleshooting.

**Common issues:**
- Missing API keys → Add to `backend/.env`
- CORS errors → Check `CORS_ORIGINS` setting
- Database connection failed → Ensure PostgreSQL is running
- File upload fails → Check file type and size

---

## License

[Specify your license]

---

## Acknowledgments

- **Groq** for LLM inference
- **Hugging Face** for local text embeddings
- **Pinecone** for vector database

---

## Documentation

- [ARCHITECTURE.md](ARCHITECTURE.md) - Detailed system architecture
- [IMPLEMENTATION_GUIDE.md](IMPLEMENTATION_GUIDE.md) - Deployment and usage guide

---

## Contact

[Add contact information]
