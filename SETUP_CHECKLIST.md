# Setup Checklist - Chunk Labeling System

Use this checklist to set up and verify the chunk labeling system integration.

## ✅ Pre-Integration Checklist

- [x] Existing RAG system is working
- [x] PostgreSQL database is running
- [x] Pinecone is configured
- [x] Backend API is functional
- [x] Code has been integrated

## 📋 Setup Steps

### Step 1: Database Migration

- [ ] Navigate to backend directory
  ```bash
  cd backend
  ```

- [ ] Run migration script
  ```bash
  python migrations/create_chunk_labels_table.py
  ```

- [ ] Verify success message:
  ```
  ✓ chunk_labels table is ready
  Migration completed successfully!
  ```

- [ ] Verify table exists in database
  ```sql
  SELECT * FROM chunk_labels LIMIT 1;
  ```

**Expected Result**: Table exists (even if empty)

---

### Step 2: Test Labeling Service

- [ ] Run test script
  ```bash
  python test_labeling.py
  ```

- [ ] Verify output shows:
  - ✓ ChunkLabelingService initialized
  - ✓ Test cases run successfully
  - ✓ Pattern matching works
  - ✓ Topic tags extracted
  - ✓ Confidence scores calculated

**Expected Result**: All tests pass without errors

---

### Step 3: Restart Backend

- [ ] Stop current backend process (if running)

- [ ] Start backend
  ```bash
  python -m app.main
  # or
  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
  ```

- [ ] Check startup logs for:
  ```
  Database tables initialized successfully
  Application startup complete
  ```

**Expected Result**: Backend starts without errors

---

### Step 4: Verify API Endpoints

- [ ] Open browser to `http://localhost:8000/docs`

- [ ] Scroll to "labeling" section

- [ ] Verify 6 endpoints exist:
  - [ ] POST /api/v1/labeling/auto-label
  - [ ] POST /api/v1/labeling/labels
  - [ ] GET /api/v1/labeling/labels/{chunk_id}
  - [ ] POST /api/v1/labeling/labels/batch
  - [ ] POST /api/v1/labeling/documents/{document_id}/unlabeled
  - [ ] DELETE /api/v1/labeling/labels/{chunk_id}

**Expected Result**: All 6 endpoints visible in Swagger UI

---

### Step 5: Test Auto-Labeling Endpoint

- [ ] In Swagger UI, expand `POST /api/v1/labeling/auto-label`

- [ ] Click "Try it out"

- [ ] Enter test data:
  ```json
  {
    "chunk_text": "Therefore, we can conclude that machine learning requires large datasets.",
    "source_type": "research_paper",
    "page_number": 1,
    "timestamp": null
  }
  ```

- [ ] Click "Execute"

- [ ] Verify response contains:
  - `rhetorical_role` (should be "conclusion" or "argument")
  - `topic_tags` (may contain ["Machine Learning"])
  - `token_count` (should be ~15)
  - `confidence_label` (high/medium/low)
  - `coverage_score` (0-100)

**Expected Result**: 200 OK with valid label data

---

### Step 6: Test Full Upload Flow

- [ ] Upload a test document via your upload endpoint

- [ ] Check database for labels:
  ```sql
  SELECT
    chunk_id,
    rhetorical_role,
    confidence_label,
    coverage_score,
    human_verified
  FROM chunk_labels
  ORDER BY created_at DESC
  LIMIT 10;
  ```

- [ ] Verify:
  - [ ] Labels were created
  - [ ] `is_auto_labeled = true`
  - [ ] `human_verified = false`
  - [ ] `rhetorical_role` is set
  - [ ] `confidence_label` is set

**Expected Result**: Labels exist in database with auto-labeled status

---

### Step 7: Verify Pinecone Metadata

- [ ] Check Pinecone vectors include new metadata

- [ ] Query a test vector and verify metadata contains:
  - [ ] `confidence_label`
  - [ ] `coverage_score`
  - [ ] `topic_tags` (if any)
  - [ ] `token_count`

**Expected Result**: Pinecone vectors have enriched metadata

---

### Step 8: Test Quality Filtering

- [ ] Update your retrieval code to use filters:
  ```python
  results = vector_store.search(
      query="test query",
      user_id=user_id,
      min_confidence="high",
      min_coverage_score=70
  )
  ```

- [ ] Verify filtered results only include high-confidence chunks

**Expected Result**: Filtering works correctly

---

## 🔍 Verification Checklist

### Database Verification

- [ ] `chunk_labels` table exists
- [ ] Table has correct schema (see LABELING_SYSTEM.md)
- [ ] Foreign keys work (CASCADE delete)
- [ ] Indexes exist on `chunk_id`, `user_id`, `document_id`

### API Verification

- [ ] All 6 endpoints respond correctly
- [ ] Authentication required (401 if no token)
- [ ] User isolation works (can't access other users' labels)
- [ ] Validation works (400 for invalid input)

### Labeling Service Verification

- [ ] Pattern matching detects rhetorical roles
- [ ] Topic tags extracted from text
- [ ] Confidence scores calculated
- [ ] Coverage scores calculated
- [ ] Labels saved to database

### Integration Verification

- [ ] Document processor integrates labeling
- [ ] Vector store includes metadata
- [ ] Retrieval filtering works
- [ ] No errors in logs

---

## 🐛 Troubleshooting

### Migration Fails

**Symptom**: Error running migration script

**Checks**:
- [ ] PostgreSQL is running
- [ ] Database credentials in `.env` are correct
- [ ] User has CREATE TABLE permissions
- [ ] No syntax errors in output

**Fix**:
```bash
# Test connection manually
psql -h localhost -U your_user -d your_database

# Check .env file
cat .env | grep DATABASE
```

---

### Test Script Fails

**Symptom**: `test_labeling.py` errors

**Checks**:
- [ ] `tiktoken` installed: `pip install tiktoken`
- [ ] All dependencies installed
- [ ] Python 3.11+ being used

**Fix**:
```bash
pip install -r requirements.txt
```

---

### Labels Not Saving

**Symptom**: No records in `chunk_labels` table after upload

**Checks**:
- [ ] `process_and_label_chunks()` is being called
- [ ] Database session (`db`) is passed as parameter
- [ ] No errors in application logs
- [ ] Transaction is committed

**Fix**:
```python
# In upload handler, ensure:
labeled_chunks = processor.process_and_label_chunks(
    chunks=chunks,
    content_type=content_type,
    user_id=current_user.id,
    document_id=document_id,
    db=db  # ← MUST PASS DB SESSION
)
```

---

### API Returns 404

**Symptom**: Labeling endpoints not found

**Checks**:
- [ ] Backend restarted after integration
- [ ] `labeling_router` imported in `main.py`
- [ ] Router included: `app.include_router(labeling_router, ...)`
- [ ] No import errors in logs

**Fix**:
```bash
# Restart backend
pkill -f "uvicorn"
uvicorn app.main:app --reload
```

---

### Low Confidence Scores

**Symptom**: Most chunks have `confidence_label = "low"`

**Checks**:
- [ ] This is normal for short chunks (<20 words)
- [ ] This is normal for generic/transitional text
- [ ] Pattern matching rules may need tuning

**Fix**: This is expected behavior. Focus on:
1. Monitoring overall distribution
2. Manual verification of low-confidence chunks
3. Adjusting patterns in `chunk_labeling.py` if needed

---

## 📊 Success Metrics

After setup, you should see:

### Database Metrics
- ✅ `chunk_labels` table exists
- ✅ Labels created for each uploaded chunk
- ✅ Auto-labeled: ~100% of chunks
- ✅ Human-verified: 0% (initially)

### Label Quality Distribution (typical)
- High confidence: ~20-30%
- Medium confidence: ~50-60%
- Low confidence: ~10-20%

### API Performance
- Auto-label endpoint: <100ms response
- Save label endpoint: <200ms response
- Batch operations: <500ms for 10 labels

### System Performance
- Upload with labeling: <5% slower than before
- Retrieval with filters: Same speed or faster
- Database size: +~500 bytes per chunk

---

## 📝 Post-Setup Tasks

### Immediate (Day 1)
- [ ] Upload 1-2 test documents
- [ ] Verify labels in database
- [ ] Test API endpoints manually
- [ ] Review logs for errors

### Short Term (Week 1)
- [ ] Monitor label quality distribution
- [ ] Adjust pattern matching if needed
- [ ] Document any custom configurations
- [ ] Plan UI for human verification

### Long Term (Month 1)
- [ ] Analyze label accuracy
- [ ] Build verification workflow
- [ ] Train ML classifier on verified labels
- [ ] Implement active learning

---

## ✅ Final Verification

Run this SQL to verify everything is working:

```sql
-- Check table exists
SELECT COUNT(*) FROM chunk_labels;

-- Check recent labels
SELECT
    chunk_id,
    rhetorical_role,
    confidence_label,
    coverage_score,
    is_auto_labeled,
    human_verified,
    created_at
FROM chunk_labels
ORDER BY created_at DESC
LIMIT 5;

-- Check label distribution
SELECT
    rhetorical_role,
    COUNT(*) as count
FROM chunk_labels
GROUP BY rhetorical_role
ORDER BY count DESC;

-- Check confidence distribution
SELECT
    confidence_label,
    COUNT(*) as count
FROM chunk_labels
GROUP BY confidence_label;
```

**Expected Results**:
- Table exists and has records
- Recent labels show valid data
- Distribution looks reasonable
- No errors

---

## 🎉 You're Done!

If all checkboxes are checked, your chunk labeling system is:

✅ Installed
✅ Configured
✅ Tested
✅ Working
✅ Production-ready

Next: Start using it in production and monitoring quality metrics!

---

**Need Help?**
- Review: `LABELING_SYSTEM.md` for detailed docs
- Check: `INTEGRATION_COMPLETE.md` for examples
- Debug: Application logs for errors
