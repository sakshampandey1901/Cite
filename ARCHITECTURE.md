# Cognitive Assistant System Architecture

## System Overview

A RAG-based AI assistant that provides thinking-aligned guidance by reasoning from user-uploaded documents (PDFs, research papers, notes, video transcripts).

## Core Principles

1. **Zero hallucination tolerance**: All outputs traceable to sources or labeled as methodological guidance
2. **Explicit separation of concerns**: Clear boundaries between system rules, identity, style, sources, and tasks
3. **Security-first design**: Least-privilege access, input validation, no auth bypass
4. **Deterministic behavior**: Each task mode operates predictably
5. **Transparency**: All retrieved context labeled with source, type, and rhetorical role

---

## Architecture Layers

### 1. Document Ingestion Pipeline

**Purpose**: Process and index user documents for retrieval

**Components**:
- **Document Parser**: Extract text from PDFs, video transcripts, notes
- **Chunk Processor**: Segment documents into retrievable units (300-500 tokens)
- **Metadata Extractor**: Extract source name, content type, rhetorical role
- **Embedding Generator**: Generate vector embeddings using text-embedding-3-large
- **Vector Store**: Store embeddings in Pinecone/Weaviate with metadata

**Security**:
- File type validation (whitelist: PDF, TXT, MD, SRT, VTT)
- Size limits (max 50MB per file)
- Malware scanning before processing
- User-scoped isolation (documents never cross user boundaries)

**Flow**:
```
Upload → Validate → Parse → Chunk → Extract Metadata → Embed → Store
```

---

### 2. Retrieval-Augmented Generation (RAG) Engine

**Purpose**: Retrieve relevant context for user queries

**Components**:
- **Query Encoder**: Transform user query + editor content into embeddings
- **Semantic Search**: Retrieve top-k relevant chunks (k=5-10)
- **Reranker**: Re-rank results using cross-encoder for precision
- **Context Assembler**: Format retrieved chunks with source labels

**Retrieval Strategy**:
- Hybrid search: 70% semantic similarity + 30% keyword matching
- Filters: content_type, rhetorical_role, recency
- Diversity: Maximum 3 chunks per source document

**Output Format**:
```json
{
  "chunks": [
    {
      "content": "...",
      "source": "Cognitive_Science_Intro.pdf",
      "page": 12,
      "content_type": "research_paper",
      "rhetorical_role": "argument",
      "similarity_score": 0.89
    }
  ]
}
```

---

### 3. Prompt Layering System

**Purpose**: Structure LLM prompts with strict safety and behavioral constraints

**Layer Architecture** (concatenated in order):

#### Layer 1: System Rules (Immutable)
```
CRITICAL CONSTRAINTS:
- Zero hallucination tolerance
- All outputs must be traceable to retrieved context OR labeled as "Methodological Guidance"
- NEVER generate content outside provided corpus
- NEVER impersonate the user or use first-person as user
- NEVER claim to "think like" the user
- Explicitly flag missing information with: "[No relevant source found]"
```

#### Layer 2: Identity & Scope
```
ROLE: Cognitive assistant providing thinking-aligned guidance
SCOPE: Reasoning from user's uploaded documents only
NON-SCOPE: Generic advice, web knowledge, personal opinions
```

#### Layer 3: Task Mode (One per request)
```
MODE: {START|CONTINUE|REFRAME|STUCK_DIAGNOSIS|OUTLINE}

START:
  Output: How to begin approaching the topic
  Format: 1) Likely first move, 2) Supporting rationale from sources, 3) Alternative paths

CONTINUE:
  Output: Logical next steps in existing writing
  Format: 1) Likely next move, 2) Reasoning from user's prior patterns, 3) Cautions

REFRAME:
  Output: Alternative angles consistent with prior reasoning
  Format: 1) Alternative framing, 2) Supporting rationale, 3) Trade-offs

STUCK_DIAGNOSIS:
  Output: Explain why progress typically stalls at this point
  Format: 1) Likely blockage cause, 2) Patterns from user's past work, 3) Suggested path

OUTLINE:
  Output: Skeletal structure only (no prose)
  Format: Hierarchical outline with 1-2 word labels per section
```

#### Layer 4: Retrieved Context
```
RETRIEVED SOURCES (ranked by relevance):

[Source 1]
- Source: Cognitive_Science_Intro.pdf (page 12)
- Type: research_paper
- Role: argument
- Content: "..."

[Source 2]
- Source: Lecture_04.mp4 (timestamp 04:20)
- Type: video_transcript
- Role: example
- Content: "..."
```

#### Layer 5: User Input
```
USER EDITOR CONTENT:
"..."

USER QUERY:
Mode: {mode}
Additional context: {optional}
```

#### Layer 6: Output Format Enforcement
```
MANDATORY OUTPUT STRUCTURE:

## {Mode} Guidance

### 1. Likely Next Move
[Your recommendation]

### 2. Supporting Rationale
[Citations from sources above - use exact Source names]

### 3. Alternative Paths (Optional)
[If applicable]

### 4. Cautions or Limitations
[What's uncertain or missing from sources]

FREE-FORM PROSE PROHIBITED unless user explicitly requests it.
```

---

### 4. Style & Reasoning Adaptation

**Purpose**: Infer user's writing patterns without mimicry

**Analysis Pipeline**:
1. **Pattern Extraction** (offline, runs on document upload):
   - Sentence structure (average length, complexity)
   - Argumentation style (deductive, inductive, abductive)
   - Rhetorical devices (analogies, examples, questions)
   - Transition patterns
   - Vocabulary distribution

2. **Encoding**:
   - Store as descriptive metadata (NOT aspirational)
   - Example: "User frequently uses analogies to explain abstract concepts" (not "Think in analogies")

3. **Adaptation**:
   - Adjust suggestion structure to match user patterns
   - Adapt approach (top-down vs bottom-up), NOT opinions

**Anti-Patterns (Forbidden)**:
- "You typically argue that..." → "Based on prior work, arguments often follow X structure"
- Exaggerated confidence
- Stylistic mimicry (writing AS the user)

---

### 5. API Layer

**Endpoints**:

#### POST /api/documents/upload
- **Auth**: Bearer token (JWT)
- **Input**: multipart/form-data (file + metadata)
- **Validation**: file type, size, user quota
- **Output**: `{document_id, status: "processing"}`
- **Rate Limit**: 10 uploads/hour per user

#### GET /api/documents
- **Auth**: Bearer token
- **Output**: List of user's documents with processing status

#### POST /api/assist
- **Auth**: Bearer token
- **Input**:
```json
{
  "mode": "START|CONTINUE|REFRAME|STUCK_DIAGNOSIS|OUTLINE",
  "editor_content": "...",
  "additional_context": "..." (optional)
}
```
- **Validation**:
  - Mode must be one of 5 allowed values
  - Editor content max 10,000 chars
  - Sanitize all inputs
- **Output**:
```json
{
  "guidance": "...",
  "sources": [
    {
      "source": "filename.pdf",
      "page": 12,
      "type": "research_paper",
      "role": "argument",
      "score": 0.89
    }
  ],
  "mode": "START"
}
```
- **Rate Limit**: 30 requests/hour per user

#### DELETE /api/documents/{id}
- **Auth**: Bearer token + ownership verification
- **Authorization**: User can only delete their own documents

**Security**:
- All inputs sanitized (prevent injection attacks)
- CORS restricted to frontend domain
- CSRF tokens for state-changing operations
- SQL parameterized queries only
- No eval() or exec() on user input
- Least-privilege database access (read-only for assistant queries)

---

### 6. Evaluation Framework

**Dimensions**:

1. **Structural Similarity** (40%):
   - Does output match user's typical structure?
   - Measured via embedding similarity to user's past outlines

2. **Reasoning-Path Alignment** (30%):
   - Does the suggested approach match user's reasoning patterns?
   - NOT answer similarity (process over content)

3. **Failure-Mode Alignment** (15%):
   - Does system correctly identify uncertainty?
   - False negative rate for "[No relevant source found]"

4. **Continuation Plausibility** (10%):
   - Human eval: Would this be a logical next step?

5. **Preference Consistency** (5%):
   - Cross-session consistency in recommendations

**Test Suite**:
- 50 synthetic user scenarios
- Each with: document corpus + partial writing + expected mode behavior
- Automated tests for security (injection attempts, IDOR, rate limit bypass)
- Red-team testing for hallucination detection

---

## Technology Stack

### Backend
- **Framework**: FastAPI (Python) - async, type-safe, auto-validation
- **Vector DB**: Pinecone (managed) or Weaviate (self-hosted)
- **Embeddings**: Hugging Face all-MiniLM-L6-v2 (local)
- **LLM**: GPT-4 Turbo (with structured outputs)
- **Document Parsing**: PyMuPDF (PDF), python-docx, subtitle-parser
- **Database**: PostgreSQL (user data, document metadata)
- **Authentication**: OAuth 2.0 + JWT

### Frontend
- **Framework**: Vanilla JS (current) → Migrate to React/Vue for state management
- **HTTP Client**: Fetch API with retry logic
- **State Management**: Context API or Zustand

### Infrastructure
- **Hosting**: Cloud provider (AWS/GCP/Azure)
- **CDN**: CloudFlare (frontend assets)
- **Monitoring**: Sentry (errors), DataDog (metrics)
- **Secrets**: AWS Secrets Manager / HashiCorp Vault

---

## MVP Feature Scope

### Included
1. PDF upload and processing (max 10 documents per user)
2. Text extraction and chunking
3. Vector embedding and storage
4. All 5 task modes (START, CONTINUE, REFRAME, STUCK_DIAGNOSIS, OUTLINE)
5. Basic user authentication
6. Source citation display
7. Rate limiting and input validation

### Excluded (Post-MVP)
1. Video transcript processing (manual upload of .srt files instead)
2. Real-time collaboration
3. Advanced style adaptation (start with simple pattern matching)
4. Mobile app
5. OCR for scanned documents
6. Multi-language support

---

## Security Considerations

### Threat Model
1. **Unauthorized access**: Mitigated by JWT + user-scoped data isolation
2. **Injection attacks**: Mitigated by input sanitization + parameterized queries
3. **Prompt injection**: Mitigated by strict prompt layering + output validation
4. **Data exfiltration**: Mitigated by encryption at rest + TLS in transit
5. **Denial of service**: Mitigated by rate limiting + request size limits
6. **IDOR**: Mitigated by ownership verification on all document operations

### Privacy
- Documents encrypted at rest (AES-256)
- No third-party data sharing
- User can delete all data on account closure
- Audit logs for all document access

---

## Deployment Strategy

### Phase 1: Local Development
- Docker Compose with PostgreSQL + Weaviate
- Local file storage
- Mock authentication

### Phase 2: Staging
- Cloud deployment (single instance)
- Real vector DB (Pinecone free tier)
- OAuth integration
- Load testing

### Phase 3: Production
- Multi-region deployment
- Auto-scaling
- CDN integration
- Monitoring and alerting

---

## Open Questions & Trade-offs

1. **Embedding model**: Open-source local (free) vs hosted API (costly)?
   - **Decision**: Use local all-MiniLM-L6-v2 for zero-cost embeddings

2. **Chunk size**: 300 vs 500 tokens?
   - **Decision**: 400 tokens (balance between context and precision)

3. **Reranking**: Add cross-encoder (slower, better) or skip (faster, good enough)?
   - **Decision**: Skip for MVP, add post-launch if retrieval quality insufficient

4. **LLM provider**: Hosted premium vs Groq (fast, low cost)?
   - **Decision**: Groq (Llama 3 8B) for speed and cost control

---

## Success Metrics

1. **Retrieval Quality**: Top-5 hit rate > 85%
2. **User Satisfaction**: 4+ stars on suggestion quality
3. **Safety**: Zero hallucination incidents in user reports
4. **Performance**: p95 response time < 3s
5. **Uptime**: 99.5% availability

---

## Appendix: Example Prompt (START mode)

```
CRITICAL CONSTRAINTS:
- Zero hallucination tolerance
- All outputs traceable to retrieved context OR labeled "Methodological Guidance"
- NEVER generate outside provided corpus
- NEVER impersonate user
- Explicitly flag missing info: "[No relevant source found]"

ROLE: Cognitive assistant providing thinking-aligned guidance
SCOPE: Reasoning from user's uploaded documents only

MODE: START
Output: How to begin approaching the topic
Format: 1) Likely first move, 2) Supporting rationale from sources, 3) Alternative paths

RETRIEVED SOURCES (ranked by relevance):

[Source 1]
- Source: Cognitive_Science_Intro.pdf (page 12)
- Type: research_paper
- Role: argument
- Content: "External cognition refers to the use of tools and artifacts to augment human thinking. Vannevar Bush's Memex concept from 1945 proposed a device that could store and retrieve information based on associative trails, mimicking human thought processes."

[Source 2]
- Source: Lecture_04.mp4 (timestamp 04:20)
- Type: video_transcript
- Role: example
- Content: "When explaining complex systems, start by grounding the reader in a familiar context. For instance, comparing digital note-taking to the physical act of writing in a journal helps establish common ground before introducing new concepts."

USER EDITOR CONTENT:
[Empty - user hasn't started writing]

USER QUERY:
Mode: START
Additional context: "I want to write about how digital tools change the way we think"

MANDATORY OUTPUT STRUCTURE:

## START Guidance

### 1. Likely Next Move
[Your recommendation]

### 2. Supporting Rationale
[Citations from sources above - use exact Source names]

### 3. Alternative Paths (Optional)
[If applicable]

### 4. Cautions or Limitations
[What's uncertain or missing from sources]
```

**Expected Assistant Output**:
```markdown
## START Guidance

### 1. Likely Next Move
Begin by defining "external cognition" as the core concept, then ground it in historical context using Vannevar Bush's Memex as the foundational example.

### 2. Supporting Rationale
- **Cognitive_Science_Intro.pdf (page 12)**: Defines external cognition as "the use of tools and artifacts to augment human thinking" and introduces Bush's Memex (1945) as an early conceptual framework for associative information retrieval.
- **Lecture_04.mp4 (04:20)**: Recommends starting with familiar contexts before introducing new concepts, which supports opening with a historical grounding.

### 3. Alternative Paths
Start with a contemporary example (e.g., smartphone usage) then trace backward to historical roots. This inverts the chronology but may engage readers faster.

### 4. Cautions or Limitations
No sources explicitly address "how digital tools change thinking" from a neuroscience or behavioral perspective. The current corpus focuses on historical/conceptual frameworks, not empirical cognitive effects.
```
