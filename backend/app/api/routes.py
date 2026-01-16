"""API routes for the cognitive assistant."""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from fastapi.responses import JSONResponse
from typing import List
import uuid
from pathlib import Path
import time
import shutil

from app.models.schemas import (
    AssistRequest, AssistResponse, DocumentUploadResponse,
    DocumentListResponse, TaskMode, SourceCitation
)
from app.models.database import get_db, Document
from app.core.security import get_current_user_id, sanitize_filename, validate_file_type
from app.core.config import settings
from app.core.rate_limiter import rate_limiter
from app.services.document_processor import DocumentProcessor
from app.services.vector_store import VectorStore
from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService
from sqlalchemy.orm import Session


router = APIRouter()

# Initialize services
document_processor = DocumentProcessor()
vector_store = VectorStore()
prompt_builder = PromptBuilder()
llm_service = LLMService()


@router.post("/documents/upload", response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Upload and process a document.

    Security:
    - Requires authentication
    - Rate limited (configurable per user)
    - Validates file type and size
    - Sanitizes filename
    - User-scoped storage
    """
    # Check rate limit
    rate_limiter.check_rate_limit(user_id, "upload", settings.RATE_LIMIT_UPLOAD)

    # Validate file type
    if not validate_file_type(file.filename, settings.allowed_extensions_list):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(settings.allowed_extensions_list)}"
        )

    # Check file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.file.tell()
    file.file.seek(0)  # Reset

    if file_size > settings.max_file_size_bytes:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE_MB}MB"
        )

    # Sanitize filename
    safe_filename = sanitize_filename(file.filename)
    document_id = str(uuid.uuid4())

    # Save file temporarily
    upload_dir = Path(settings.UPLOAD_DIR) / user_id
    upload_dir.mkdir(parents=True, exist_ok=True)

    file_path = upload_dir / f"{document_id}_{safe_filename}"

    try:
        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Process document based on type
        file_ext = file_path.suffix.lower().lstrip('.')

        if file_ext == 'pdf':
            chunks, content_type = document_processor.process_pdf(file_path)
        elif file_ext in ['txt', 'md']:
            chunks, content_type = document_processor.process_text(file_path)
        elif file_ext in ['srt', 'vtt']:
            chunks, content_type = document_processor.process_subtitle(file_path)
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Unsupported file type"
            )

        # Prepare chunks for vector store
        chunk_dicts = []
        for chunk in chunks:
            # Get rhetorical role and convert enum to string value
            rhetorical_role = chunk.metadata.get('rhetorical_role', 'unknown')
            if hasattr(rhetorical_role, 'value'):
                rhetorical_role = rhetorical_role.value

            chunk_dicts.append({
                'content': chunk.content,
                'chunk_index': chunk.chunk_index,
                'page_number': chunk.page_number,
                'timestamp': chunk.timestamp,
                'source_filename': safe_filename,
                'content_type': content_type.value,
                'rhetorical_role': rhetorical_role
            })

        # Insert into vector store
        vector_store.upsert_chunks(chunk_dicts, user_id, document_id)

        # Save document metadata to database
        db_document = Document(
            id=document_id,
            user_id=user_id,
            filename=safe_filename,
            original_filename=file.filename,
            content_type=content_type,
            status="ready",
            file_size_bytes=file_size,
            chunk_count=len(chunks)
        )
        db.add(db_document)
        db.commit()
        db.refresh(db_document)

        # Clean up temporary file
        file_path.unlink()

        return DocumentUploadResponse(
            document_id=document_id,
            filename=safe_filename,
            status="ready",
            created_at=time.time()
        )

    except Exception as e:
        # Clean up on error
        db.rollback()
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Document processing failed: {str(e)}"
        )


@router.post("/assist", response_model=AssistResponse)
async def get_assistance(
    request: AssistRequest,
    user_id: str = Depends(get_current_user_id)
):
    """
    Get cognitive assistance based on mode and context.

    Security:
    - Requires authentication
    - Input validation via Pydantic
    - Rate limited (configurable per user)
    - User-scoped retrieval
    """
    # Check rate limit
    rate_limiter.check_rate_limit(user_id, "assist", settings.RATE_LIMIT_ASSIST)

    start_time = time.time()

    try:
        # Build search query from editor content and mode
        if request.editor_content.strip():
            query = f"{request.mode.value}: {request.editor_content[:500]}"
        else:
            query = f"{request.mode.value} guidance"

        if request.additional_context:
            query += f" {request.additional_context}"

        # Retrieve relevant chunks
        retrieval_start = time.time()
        retrieved_chunks = vector_store.search(
            query=query,
            user_id=user_id,
            top_k=8
        )
        retrieval_time = int((time.time() - retrieval_start) * 1000)

        # Apply diversity filter (max 3 chunks per source)
        filtered_chunks = []
        source_counts = {}
        for chunk in retrieved_chunks:
            source = chunk.metadata.source_filename
            if source_counts.get(source, 0) < 3:
                filtered_chunks.append(chunk)
                source_counts[source] = source_counts.get(source, 0) + 1

        # Build prompt
        prompt = prompt_builder.build_prompt(
            mode=request.mode,
            editor_content=request.editor_content,
            retrieved_sources=filtered_chunks[:5],  # Top 5 after filtering
            additional_context=request.additional_context
        )

        # Generate guidance
        generation_start = time.time()
        guidance = llm_service.generate_guidance(prompt)
        generation_time = int((time.time() - generation_start) * 1000)

        # Validate output
        is_valid, error_msg = llm_service.validate_generation(guidance, request.mode)
        if not is_valid:
            # Log validation failure and return fallback
            guidance = llm_service.fallback_response(request.mode, error_msg)

        # Format source citations
        citations = []
        for chunk in filtered_chunks[:5]:
            citations.append(SourceCitation(
                source=chunk.metadata.source_filename,
                page=chunk.metadata.page_number,
                timestamp=chunk.metadata.timestamp,
                content_type=chunk.metadata.content_type,
                rhetorical_role=chunk.metadata.rhetorical_role,
                similarity_score=chunk.similarity_score,
                content_preview=chunk.content[:200]
            ))

        total_time = int((time.time() - start_time) * 1000)

        return AssistResponse(
            guidance=guidance,
            sources=citations,
            mode=request.mode,
            metadata={
                'retrieval_time_ms': retrieval_time,
                'generation_time_ms': generation_time,
                'total_time_ms': total_time,
                'source_count': len(citations)
            }
        )

    except Exception as e:
        # Return safe fallback on error
        return AssistResponse(
            guidance=llm_service.fallback_response(request.mode, str(e)),
            sources=[],
            mode=request.mode,
            metadata={'error': str(e)}
        )


@router.get("/documents", response_model=List[DocumentListResponse])
async def list_documents(
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    List user's documents.

    Security:
    - Requires authentication
    - User-scoped query
    """
    try:
        # Query user's documents from database
        documents = db.query(Document).filter(
            Document.user_id == user_id
        ).order_by(
            Document.created_at.desc()
        ).all()

        # Convert to response model
        return [
            DocumentListResponse(
                id=doc.id,
                title=doc.original_filename,
                content_type=doc.content_type.value,
                status=doc.status.value,
                created_at=doc.created_at,
                updated_at=doc.updated_at,
                chunk_count=doc.chunk_count
            )
            for doc in documents
        ]

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve documents: {str(e)}"
        )


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: str,
    user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db)
):
    """
    Delete a document.

    Security:
    - Requires authentication
    - Ownership verification (user can only delete their own documents)
    """
    try:
        # Verify ownership and get document from database
        db_document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == user_id
        ).first()

        if not db_document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found or you don't have permission to delete it"
            )

        # Delete from vector store
        vector_store.delete_document(user_id, document_id)

        # Delete from database (cascade will handle related records)
        db.delete(db_document)
        db.commit()

        return JSONResponse(
            status_code=status.HTTP_200_OK,
            content={"message": "Document deleted successfully"}
        )

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete document: {str(e)}"
        )


@router.get("/health")
async def health_check():
    """Health check endpoint (no authentication required)."""
    return {"status": "healthy", "service": "cognitive-assistant"}
