# Chunk Labeling System Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER UPLOADS DOCUMENT                         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     DOCUMENT PROCESSOR                               │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 1. Parse Document (PDF/TXT/SRT)                           │     │
│  │ 2. Extract Text                                           │     │
│  │ 3. Chunk into 400-token segments with 50-token overlap   │     │
│  │ 4. Detect content type (research_paper, video, etc.)     │     │
│  └───────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│               CHUNK LABELING SERVICE (NEW)                           │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ For each chunk:                                           │     │
│  │                                                           │     │
│  │  1. Detect Rhetorical Role                               │     │
│  │     └─ Pattern matching (regex)                          │     │
│  │     └─ 10 roles: argument, example, background, etc.     │     │
│  │                                                           │     │
│  │  2. Extract Topic Tags                                   │     │
│  │     └─ Find capitalized phrases                          │     │
│  │     └─ Find acronyms                                     │     │
│  │     └─ Max 3 tags per chunk                              │     │
│  │                                                           │     │
│  │  3. Calculate Confidence                                 │     │
│  │     └─ Role confidence (50%)                             │     │
│  │     └─ Tag count (30%)                                   │     │
│  │     └─ Coverage score (20%)                              │     │
│  │     └─ Result: high/medium/low                           │     │
│  │                                                           │     │
│  │  4. Calculate Coverage Score                             │     │
│  │     └─ Content representation (0-100%)                   │     │
│  │     └─ Based on: tags, length, structure                │     │
│  │                                                           │     │
│  │  5. Count Tokens                                         │     │
│  │     └─ Using tiktoken                                    │     │
│  └───────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   DATABASE PERSISTENCE (NEW)                         │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ Save to chunk_labels table:                               │     │
│  │                                                           │     │
│  │  • chunk_id (unique)                                      │     │
│  │  • chunk_text                                             │     │
│  │  • rhetorical_role                                        │     │
│  │  • topic_tags (JSON)                                      │     │
│  │  • confidence_label                                       │     │
│  │  • coverage_score                                         │     │
│  │  • token_count                                            │     │
│  │  • is_auto_labeled = true                                 │     │
│  │  • human_verified = false                                 │     │
│  │  • timestamps                                             │     │
│  └───────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    VECTOR STORE (ENHANCED)                           │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ Generate embeddings (sentence-transformers)               │     │
│  │                                                           │     │
│  │ Store in Pinecone with metadata:                          │     │
│  │  • content                                                │     │
│  │  • rhetorical_role                                        │     │
│  │  • topic_tags              ← NEW                          │     │
│  │  • confidence_label        ← NEW                          │     │
│  │  • coverage_score          ← NEW                          │     │
│  │  • token_count             ← NEW                          │     │
│  │  • page_number, timestamp                                 │     │
│  └───────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     READY FOR RETRIEVAL                              │
└─────────────────────────────────────────────────────────────────────┘
```

## Retrieval Flow (Enhanced)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER QUERY                                   │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  VECTOR SEARCH (ENHANCED)                            │
│  ┌───────────────────────────────────────────────────────────┐     │
│  │ 1. Generate query embedding                               │     │
│  │                                                           │     │
│  │ 2. Build filters:                                         │     │
│  │    • user_id (always)                                     │     │
│  │    • content_type (optional)                              │     │
│  │    • rhetorical_role (optional)                           │     │
│  │    • min_confidence (optional)  ← NEW                     │     │
│  │    • min_coverage_score (optional) ← NEW                  │     │
│  │                                                           │     │
│  │ 3. Search Pinecone with filters                           │     │
│  │                                                           │     │
│  │ 4. Return top-k results with quality metadata             │     │
│  └───────────────────────────────────────────────────────────┘     │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    PROMPT BUILDER                                    │
│  Uses retrieved chunks with quality metadata to build prompt         │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    LLM GENERATION                                    │
│  Generates response with high-quality, well-labeled sources          │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   RESPONSE TO USER                                   │
└─────────────────────────────────────────────────────────────────────┘
```

## Human Verification Workflow

```
┌─────────────────────────────────────────────────────────────────────┐
│                    GET UNLABELED CHUNKS                              │
│  POST /api/v1/labeling/documents/{doc_id}/unlabeled                 │
│                                                                      │
│  Returns: chunks where human_verified = false                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    DISPLAY TO USER                                   │
│  Show chunk with:                                                    │
│  • Auto-assigned role                                                │
│  • Auto-extracted topic tags                                         │
│  • Confidence level                                                  │
│  • Coverage score                                                    │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                   USER REVIEWS & CORRECTS                            │
│  • Accept auto-label (mark as verified)                              │
│  • Correct rhetorical role                                           │
│  • Edit topic tags                                                   │
│  • Adjust confidence/coverage                                        │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    UPDATE LABEL                                      │
│  POST /api/v1/labeling/labels                                        │
│                                                                      │
│  Update database:                                                    │
│  • rhetorical_role (if corrected)                                    │
│  • topic_tags (if edited)                                            │
│  • human_verified = true                                             │
│  • updated_at = now()                                                │
└────────────────────────────┬────────────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                  IMPROVED LABEL IN DATABASE                          │
│  Can be used for:                                                    │
│  • Better retrieval filtering                                        │
│  • Training ML classifiers                                           │
│  • Analytics and metrics                                             │
└─────────────────────────────────────────────────────────────────────┘
```

## API Endpoints Architecture

```
/api/v1/labeling/
│
├── POST   /auto-label
│   └─ Input: chunk_text, source_type
│   └─ Output: Auto-generated labels (not saved)
│   └─ Use case: Test labeling before saving
│
├── POST   /labels
│   └─ Input: chunk_id, rhetorical_role, topic_tags, confidence, etc.
│   └─ Output: Saved label
│   └─ Use case: Save or update label
│
├── GET    /labels/{chunk_id}
│   └─ Output: Label for specific chunk
│   └─ Use case: Retrieve existing label
│
├── POST   /labels/batch
│   └─ Input: document_id, list of labels
│   └─ Output: Batch results
│   └─ Use case: Update multiple labels at once
│
├── POST   /documents/{document_id}/unlabeled
│   └─ Input: limit, offset
│   └─ Output: Unverified chunks
│   └─ Use case: Get chunks needing human review
│
└── DELETE /labels/{chunk_id}
    └─ Output: Success message
    └─ Use case: Remove label
```

## Data Flow

```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│              │     │              │     │              │
│  PostgreSQL  │────▶│   Backend    │────▶│   Pinecone   │
│              │     │              │     │              │
│ chunk_labels │     │   FastAPI    │     │  Vectors +   │
│   table      │     │              │     │  Metadata    │
│              │     │              │     │              │
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       │                    │                    │
       ▼                    ▼                    ▼
┌──────────────────────────────────────────────────────┐
│                  LABELING SERVICE                     │
│                                                       │
│  • Auto-label chunks                                 │
│  • Save to PostgreSQL (audit trail)                  │
│  • Enrich Pinecone metadata (for filtering)          │
│  • Retrieve for verification                         │
│                                                       │
└───────────────────────────────────────────────────────┘
```

## Quality Filtering Flow

```
User Query: "Explain machine learning ethics"
    +
    Filter: min_confidence = "high"
    +
    Filter: min_coverage_score = 70
    │
    ▼
┌─────────────────────────────────────┐
│  Pinecone Query with Filters        │
│                                     │
│  WHERE user_id = "user123"          │
│    AND confidence_label = "high"    │
│    AND coverage_score >= 70         │
│                                     │
└──────────────┬──────────────────────┘
               │
               ▼
Only returns high-quality, well-covered chunks
               │
               ▼
Better RAG responses
```

## Technology Stack

```
┌─────────────────────────────────────────────────────────┐
│                    LABELING SYSTEM                       │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Language:           Python 3.11                         │
│  Framework:          FastAPI                             │
│  ORM:                SQLAlchemy                          │
│  Database:           PostgreSQL                          │
│  Vector DB:          Pinecone                            │
│  Embeddings:         sentence-transformers              │
│  Tokenization:       tiktoken                            │
│  Validation:         Pydantic                            │
│                                                          │
│  Pattern Matching:   Regular expressions                │
│  Topic Extraction:   Heuristic (capitalized phrases)    │
│  Confidence Calc:    Composite scoring                  │
│  Coverage Calc:      Multi-factor heuristic             │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

## Performance Characteristics

```
Operation                    Time         Impact
─────────────────────────────────────────────────────
Pattern matching             1-5ms        Negligible
Topic extraction            2-10ms        Negligible
Confidence calculation      <1ms         Negligible
Coverage calculation        <1ms         Negligible
Database save               5-10ms       Minimal
Pinecone metadata update    included     None

Total per chunk:            ~15-35ms     <2% overhead
```

## Storage Requirements

```
Component              Per Chunk    1000 Chunks
──────────────────────────────────────────────
PostgreSQL record      ~500 bytes   ~0.5 MB
Pinecone metadata      ~50 bytes    ~50 KB
──────────────────────────────────────────────
Total                  ~550 bytes   ~0.55 MB
```

---

**Legend:**
- `┌─┐` = Component/Service
- `│ │` = Boundaries
- `▼ ` = Data flow direction
- `←` = New/enhanced feature
- `└─` = Sub-component
