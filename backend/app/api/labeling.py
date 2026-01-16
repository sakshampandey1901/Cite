"""
API endpoints for chunk labeling operations.

Provides endpoints for:
- Auto-labeling chunks
- Manual label override
- Batch labeling
- Retrieving unlabeled chunks
- Label management
"""

import logging
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.security import get_current_user
from app.models.database import get_db, User, Document, ChunkLabel
from app.models.schemas import (
    AutoLabelRequest,
    AutoLabelResponse,
    ChunkLabelRequest,
    ChunkLabelResponse,
    ChunkLabelBatchRequest,
    ChunkLabelBatchResponse,
    UnlabeledChunksRequest,
    UnlabeledChunksResponse,
    UnlabeledChunkInfo,
    RhetoricalRole,
    ConfidenceLabel,
)
from app.services.chunk_labeling import ChunkLabelingService

logger = logging.getLogger(__name__)
router = APIRouter()
labeling_service = ChunkLabelingService()


@router.post("/auto-label", response_model=AutoLabelResponse)
async def auto_label_chunk(
    request: AutoLabelRequest,
    current_user: User = Depends(get_current_user),
) -> AutoLabelResponse:
    """
    Automatically label a chunk with rhetorical role and metadata.

    This endpoint analyzes chunk text and assigns:
    - Rhetorical role (argument, example, background, etc.)
    - Topic tags (up to 3)
    - Token count
    - Confidence label
    - Coverage score

    Args:
        request: AutoLabelRequest with chunk text and metadata
        current_user: Authenticated user

    Returns:
        AutoLabelResponse with assigned labels
    """
    try:
        result = labeling_service.auto_label_chunk(
            chunk_text=request.chunk_text,
            source_type=request.source_type,
            page_number=request.page_number,
            timestamp=request.timestamp,
        )
        return result
    except Exception as e:
        logger.error(f"Auto-labeling failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Auto-labeling failed: {str(e)}",
        )


@router.post("/labels", response_model=ChunkLabelResponse)
async def save_chunk_label(
    request: ChunkLabelRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChunkLabelResponse:
    """
    Save or update a chunk label (manual or auto-labeled).

    This endpoint persists label assignments to the database.
    Can be used for both auto-labels and human corrections.

    Args:
        request: ChunkLabelRequest with label data
        current_user: Authenticated user
        db: Database session

    Returns:
        ChunkLabelResponse with saved label data
    """
    try:
        # Parse chunk_id to extract components
        # Expected format: {user_id}_{document_id}_{chunk_index}
        parts = request.chunk_id.split("_")
        if len(parts) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chunk_id format. Expected: user_id_document_id_chunk_index",
            )

        user_id = parts[0]
        document_id = parts[1]
        chunk_index = int(parts[2])

        # Verify user owns this chunk
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot label chunks from other users",
            )

        # Verify document exists and belongs to user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Get existing label to retrieve chunk text
        existing = labeling_service.get_label(db, request.chunk_id)
        if not existing:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Chunk not found. Labels can only be updated for existing chunks.",
            )

        # Save label
        label = labeling_service.save_label(
            db=db,
            chunk_id=request.chunk_id,
            user_id=user_id,
            document_id=document_id,
            chunk_index=chunk_index,
            chunk_text=existing.chunk_text,
            source_type=existing.source_type,
            rhetorical_role=request.rhetorical_role,
            topic_tags=request.topic_tags,
            token_count=existing.token_count,
            confidence_label=request.confidence_label,
            coverage_score=request.coverage_score,
            page_number=existing.page_number,
            timestamp=existing.timestamp,
            is_auto_labeled=not request.human_verified,
            human_verified=request.human_verified,
        )

        return labeling_service.to_response_schema(label)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to save label: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save label: {str(e)}",
        )


@router.get("/labels/{chunk_id}", response_model=ChunkLabelResponse)
async def get_chunk_label(
    chunk_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChunkLabelResponse:
    """
    Get label for a specific chunk.

    Args:
        chunk_id: Chunk identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        ChunkLabelResponse with label data
    """
    try:
        # Parse chunk_id to verify user ownership
        parts = chunk_id.split("_")
        if len(parts) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chunk_id format",
            )

        user_id = parts[0]
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access chunks from other users",
            )

        label = labeling_service.get_label(db, chunk_id)
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found",
            )

        return labeling_service.to_response_schema(label)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get label: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get label: {str(e)}",
        )


@router.post("/labels/batch", response_model=ChunkLabelBatchResponse)
async def batch_label_chunks(
    request: ChunkLabelBatchRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> ChunkLabelBatchResponse:
    """
    Save multiple chunk labels in a batch.

    Args:
        request: ChunkLabelBatchRequest with document_id and labels
        current_user: Authenticated user
        db: Database session

    Returns:
        ChunkLabelBatchResponse with batch results
    """
    try:
        # Verify document belongs to user
        document = db.query(Document).filter(
            Document.id == request.document_id,
            Document.user_id == current_user.id,
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        labeled_count = 0
        failed_count = 0
        responses = []

        for label_req in request.labels:
            try:
                # Parse chunk_id
                parts = label_req.chunk_id.split("_")
                if len(parts) < 3:
                    failed_count += 1
                    continue

                user_id = parts[0]
                document_id = parts[1]
                chunk_index = int(parts[2])

                # Verify ownership
                if user_id != current_user.id or document_id != request.document_id:
                    failed_count += 1
                    continue

                # Get existing label
                existing = labeling_service.get_label(db, label_req.chunk_id)
                if not existing:
                    failed_count += 1
                    continue

                # Save label
                label = labeling_service.save_label(
                    db=db,
                    chunk_id=label_req.chunk_id,
                    user_id=user_id,
                    document_id=document_id,
                    chunk_index=chunk_index,
                    chunk_text=existing.chunk_text,
                    source_type=existing.source_type,
                    rhetorical_role=label_req.rhetorical_role,
                    topic_tags=label_req.topic_tags,
                    token_count=existing.token_count,
                    confidence_label=label_req.confidence_label,
                    coverage_score=label_req.coverage_score,
                    page_number=existing.page_number,
                    timestamp=existing.timestamp,
                    is_auto_labeled=not label_req.human_verified,
                    human_verified=label_req.human_verified,
                )

                responses.append(labeling_service.to_response_schema(label))
                labeled_count += 1

            except Exception as e:
                logger.error(f"Failed to label chunk {label_req.chunk_id}: {e}")
                failed_count += 1

        return ChunkLabelBatchResponse(
            document_id=request.document_id,
            labeled_count=labeled_count,
            failed_count=failed_count,
            labels=responses,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Batch labeling failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Batch labeling failed: {str(e)}",
        )


@router.post("/documents/{document_id}/unlabeled", response_model=UnlabeledChunksResponse)
async def get_unlabeled_chunks(
    document_id: str,
    request: UnlabeledChunksRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UnlabeledChunksResponse:
    """
    Get unlabeled (or not human-verified) chunks for a document.

    Args:
        document_id: Document ID
        request: UnlabeledChunksRequest with pagination params
        current_user: Authenticated user
        db: Database session

    Returns:
        UnlabeledChunksResponse with unlabeled chunks
    """
    try:
        # Verify document belongs to user
        document = db.query(Document).filter(
            Document.id == document_id,
            Document.user_id == current_user.id,
        ).first()

        if not document:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Document not found",
            )

        # Get unlabeled chunks
        chunks, total = labeling_service.get_unlabeled_chunks(
            db=db,
            document_id=document_id,
            limit=request.limit,
            offset=request.offset,
        )

        # Convert to response format
        chunk_infos = []
        for chunk in chunks:
            chunk_info = UnlabeledChunkInfo(
                chunk_id=chunk.chunk_id,
                chunk_index=chunk.chunk_index,
                chunk_text=chunk.chunk_text,
                token_count=chunk.token_count,
                page_number=chunk.page_number,
                timestamp=chunk.timestamp,
                auto_labeled_role=RhetoricalRole[chunk.rhetorical_role.name] if chunk.is_auto_labeled else None,
                auto_confidence=ConfidenceLabel[chunk.confidence_label.name] if chunk.is_auto_labeled else None,
            )
            chunk_infos.append(chunk_info)

        return UnlabeledChunksResponse(
            document_id=document_id,
            total_unlabeled=total,
            chunks=chunk_infos,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get unlabeled chunks: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get unlabeled chunks: {str(e)}",
        )


@router.delete("/labels/{chunk_id}")
async def delete_chunk_label(
    chunk_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Delete a chunk label.

    Args:
        chunk_id: Chunk identifier
        current_user: Authenticated user
        db: Database session

    Returns:
        Success message
    """
    try:
        # Parse chunk_id to verify user ownership
        parts = chunk_id.split("_")
        if len(parts) < 3:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid chunk_id format",
            )

        user_id = parts[0]
        if user_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete chunks from other users",
            )

        label = db.query(ChunkLabel).filter(ChunkLabel.chunk_id == chunk_id).first()
        if not label:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Label not found",
            )

        db.delete(label)
        db.commit()

        return {"message": "Label deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete label: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete label: {str(e)}",
        )
