# Chunk Labeling System Documentation

## Overview

The chunk labeling system enhances the RAG (Retrieval-Augmented Generation) pipeline by providing detailed metadata annotations for content chunks. This enables better retrieval quality, human verification, and continuous improvement through active learning.

## Features

### 1. **Auto-Labeling**
- Automatically assigns rhetorical roles to chunks (argument, example, background, etc.)
- Extracts topic tags from content (up to 3 per chunk)
- Calculates confidence scores for label assignments
- Computes coverage scores (how well labels represent the content)

### 2. **Quality Metadata**
- **Rhetorical Role**: argument, example, background, conclusion, methodology, insight, observation, definition, insufficient_data, unknown
- **Topic Tags**: Up to 3 high-level topics derived from text
- **Confidence Label**: high, medium, low
- **Coverage Score**: 0-100 percentage
- **Token Count**: Number of tokens in chunk

### 3. **Human Verification**
- Track which chunks are auto-labeled vs. human-verified
- Update labels with manual corrections
- Query for unlabeled/unverified chunks
- Support batch labeling operations

### 4. **Enhanced Retrieval**
- Filter by confidence level during search
- Filter by minimum coverage score
- Weight results by label quality
- Search by topic tags

## Architecture

```
Document Upload
    ↓
Parse & Chunk (document_processor)
    ↓
Auto-Label Chunks (chunk_labeling service)
    ├─ Detect rhetorical role
    ├─ Extract topic tags
    ├─ Calculate confidence
    └─ Compute coverage score
    ↓
Save to Database (chunk_labels table)
    ↓
Embed & Store (vector_store with metadata)
    ↓
Retrieval (with quality filters)
```

## Database Schema

### ChunkLabel Table

```sql
CREATE TABLE chunk_labels (
    id VARCHAR(36) PRIMARY KEY,
    chunk_id VARCHAR(255) UNIQUE NOT NULL,  -- Format: {user_id}_{document_id}_{chunk_index}
    user_id VARCHAR(36) NOT NULL,
    document_id VARCHAR(36) NOT NULL,
    chunk_index INTEGER NOT NULL,

    -- Content
    chunk_text TEXT NOT NULL,
    token_count INTEGER NOT NULL,

    -- Source location
    source_type VARCHAR(50) NOT NULL,
    page_number INTEGER,
    timestamp VARCHAR(50),

    -- Labels
    rhetorical_role VARCHAR(50) NOT NULL,
    topic_tags TEXT,  -- JSON array: ["tag1", "tag2", "tag3"]

    -- Quality
    confidence_label VARCHAR(20) NOT NULL,
    coverage_score INTEGER NOT NULL,  -- 0-100

    -- Tracking
    is_auto_labeled BOOLEAN NOT NULL DEFAULT TRUE,
    human_verified BOOLEAN NOT NULL DEFAULT FALSE,

    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
);
```

## API Endpoints

All endpoints are under `/api/v1/labeling` and require authentication.

### 1. Auto-Label a Chunk

**POST** `/api/v1/labeling/auto-label`

Automatically label chunk text without saving to database.

**Request:**
```json
{
  "chunk_text": "Therefore, we can conclude that...",
  "source_type": "research_paper",
  "page_number": 5,
  "timestamp": null
}
```

**Response:**
```json
{
  "rhetorical_role": "conclusion",
  "topic_tags": ["Machine Learning", "Neural Networks"],
  "token_count": 150,
  "confidence_label": "high",
  "coverage_score": 85
}
```

### 2. Save/Update Chunk Label

**POST** `/api/v1/labeling/labels`

Save or update a chunk label in the database.

**Request:**
```json
{
  "chunk_id": "user123_doc456_0",
  "rhetorical_role": "argument",
  "topic_tags": ["AI", "Ethics"],
  "confidence_label": "high",
  "coverage_score": 90,
  "human_verified": true
}
```

**Response:**
```json
{
  "chunk_id": "user123_doc456_0",
  "rhetorical_role": "argument",
  "topic_tags": ["AI", "Ethics"],
  "token_count": 150,
  "confidence_label": "high",
  "coverage_score": 90,
  "is_auto_labeled": false,
  "human_verified": true,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:30:00Z"
}
```

### 3. Get Chunk Label

**GET** `/api/v1/labeling/labels/{chunk_id}`

Retrieve label for a specific chunk.

**Response:**
```json
{
  "chunk_id": "user123_doc456_0",
  "rhetorical_role": "argument",
  "topic_tags": ["AI", "Ethics"],
  "token_count": 150,
  "confidence_label": "high",
  "coverage_score": 90,
  "is_auto_labeled": true,
  "human_verified": false,
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### 4. Batch Label Chunks

**POST** `/api/v1/labeling/labels/batch`

Update multiple chunk labels at once.

**Request:**
```json
{
  "document_id": "doc456",
  "labels": [
    {
      "chunk_id": "user123_doc456_0",
      "rhetorical_role": "argument",
      "topic_tags": ["AI"],
      "confidence_label": "high",
      "coverage_score": 90,
      "human_verified": true
    },
    {
      "chunk_id": "user123_doc456_1",
      "rhetorical_role": "example",
      "topic_tags": ["Machine Learning"],
      "confidence_label": "medium",
      "coverage_score": 75,
      "human_verified": true
    }
  ]
}
```

**Response:**
```json
{
  "document_id": "doc456",
  "labeled_count": 2,
  "failed_count": 0,
  "labels": [...]
}
```

### 5. Get Unlabeled Chunks

**POST** `/api/v1/labeling/documents/{document_id}/unlabeled`

Get chunks that need human verification.

**Request:**
```json
{
  "document_id": "doc456",
  "limit": 50,
  "offset": 0
}
```

**Response:**
```json
{
  "document_id": "doc456",
  "total_unlabeled": 120,
  "chunks": [
    {
      "chunk_id": "user123_doc456_0",
      "chunk_index": 0,
      "chunk_text": "Machine learning is...",
      "token_count": 150,
      "page_number": 1,
      "timestamp": null,
      "auto_labeled_role": "definition",
      "auto_confidence": "medium"
    }
  ]
}
```

### 6. Delete Chunk Label

**DELETE** `/api/v1/labeling/labels/{chunk_id}`

Delete a chunk label from the database.

**Response:**
```json
{
  "message": "Label deleted successfully"
}
```

## Usage in Document Processing

### Integrating with Document Upload

When processing documents, use the enhanced labeling:

```python
from app.services.document_processor import DocumentProcessor
from app.services.chunk_labeling import ChunkLabelingService
from app.models.database import get_db

# Initialize services
processor = DocumentProcessor()
labeling_service = ChunkLabelingService()

# Process document
chunks, content_type = processor.process_pdf(file_path)

# Auto-label and save to database
db = next(get_db())
labeled_chunks = processor.process_and_label_chunks(
    chunks=chunks,
    content_type=content_type,
    user_id=user_id,
    document_id=document_id,
    db=db  # Pass DB session to save labels
)

# Prepare for vector store with enriched metadata
vector_chunks = []
for chunk in labeled_chunks:
    vector_chunks.append({
        'content': chunk.content,
        'chunk_index': chunk.chunk_index,
        'source_filename': filename,
        'content_type': content_type.value,
        'rhetorical_role': chunk.metadata['rhetorical_role'].value,
        'page_number': chunk.page_number,
        'timestamp': chunk.timestamp,
        'confidence_label': chunk.metadata['confidence_label'].value,
        'coverage_score': chunk.metadata['coverage_score'],
        'topic_tags': chunk.metadata['topic_tags'],
        'token_count': chunk.metadata['token_count'],
    })

# Store in vector database
vector_store.upsert_chunks(vector_chunks, user_id, document_id)
```

## Usage in Retrieval

### Filter by Quality

```python
from app.services.vector_store import VectorStore

vector_store = VectorStore()

# Search with quality filters
results = vector_store.search(
    query="machine learning ethics",
    user_id=user_id,
    top_k=10,
    min_confidence="high",  # Only high-confidence labels
    min_coverage_score=70,  # Only chunks with 70%+ coverage
)
```

## Label Quality Metrics

### Confidence Score Calculation

The confidence score is a composite of:
- **Role Confidence (50%)**: Based on pattern matching strength
- **Topic Tag Count (30%)**: Number of extracted tags (max 3)
- **Coverage Score (20%)**: How well content is represented

### Coverage Score Factors

- **Baseline**: 50%
- **Topic Tags**: +10% per tag (max 3)
- **Text Length**:
  - Short (<50 words): +20%
  - Long (>200 words): -10%
- **Structural Elements**: +5% for lists, +5% for headings
- **Range**: Clamped to 0-100

## Best Practices

### 1. Auto-Labeling First
Always run auto-labeling on upload to get baseline labels and identify low-confidence chunks for human review.

### 2. Prioritize Human Verification
Focus human verification on:
- Low confidence labels (`confidence_label = "low"`)
- Frequently retrieved chunks
- High-impact documents

### 3. Use Topic Tags for Search
Topic tags enable semantic filtering beyond rhetorical roles.

### 4. Monitor Coverage
Low coverage scores indicate chunks that may need better labeling or are inherently difficult to categorize.

### 5. Batch Operations
Use batch endpoints for efficient labeling workflows.

## Migration Guide

### Creating the Database Table

Run this migration to add the `chunk_labels` table:

```python
from app.models.database import Base, engine

# This will create all tables including chunk_labels
Base.metadata.create_all(bind=engine)
```

### Backfilling Existing Chunks

For existing documents in Pinecone, you can backfill labels:

```python
from app.services.chunk_labeling import ChunkLabelingService
from app.services.vector_store import VectorStore

labeling_service = ChunkLabelingService()
vector_store = VectorStore()

# Fetch existing chunks from Pinecone
# For each chunk:
#   1. Auto-label the content
#   2. Save to chunk_labels table
#   3. Update Pinecone metadata with confidence/coverage
```

## Future Enhancements

### Planned Features

1. **ML-Based Labeling**: Train classifiers on human-verified data
2. **Active Learning**: Identify high-value chunks for human review
3. **Label Analytics**: Dashboard for quality metrics
4. **Fine-Tuned Embeddings**: Use labeled data to improve embeddings
5. **Multi-Label Support**: Allow multiple rhetorical roles per chunk
6. **Hierarchical Tags**: Support nested topic taxonomies

## Troubleshooting

### Labels Not Saving
- Verify database connection
- Check user owns the document
- Ensure chunk_id format: `{user_id}_{document_id}_{chunk_index}`

### Low Confidence Scores
- Normal for short chunks (<10 words)
- Review pattern matching in `chunk_labeling.py`
- Consider manual verification

### Missing Topic Tags
- Normal for generic or transitional text
- Heuristic relies on capitalized phrases and acronyms
- Consider NER models for better extraction

## Support

For issues or questions:
- Check application logs for detailed error messages
- Review API endpoint documentation
- Consult the main README for general setup

---

**Version**: 1.0.0
**Last Updated**: 2024-01-15
