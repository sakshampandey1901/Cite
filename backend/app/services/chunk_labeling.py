"""
Chunk labeling service for RAG annotation and quality metadata.

This service provides:
1. Auto-labeling of chunks with rhetorical roles and topic tags
2. Confidence scoring for label assignments
3. Coverage score calculation
4. Topic extraction from chunk text
5. Integration with database for label persistence
"""

import re
import json
import logging
import tiktoken
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from uuid import uuid4

from app.models.database import ChunkLabel, RhetoricalRoleEnum, ConfidenceLabelEnum, ContentTypeEnum
from app.models.schemas import (
    RhetoricalRole,
    ConfidenceLabel,
    ContentType,
    AutoLabelRequest,
    AutoLabelResponse,
    ChunkLabelResponse,
)

logger = logging.getLogger(__name__)


class ChunkLabelingService:
    """Service for labeling content chunks with metadata."""

    def __init__(self):
        """Initialize the labeling service."""
        self.tokenizer = tiktoken.get_encoding("cl100k_base")

        # Patterns for rhetorical role detection
        self.role_patterns = {
            RhetoricalRole.ARGUMENT: [
                r'\b(therefore|thus|consequently|hence|it follows that)\b',
                r'\b(because|since|given that|as a result)\b',
                r'\b(argues?|claims?|asserts?|contends?|posits?)\b',
                r'\b(proves?|demonstrates?|shows? that)\b',
            ],
            RhetoricalRole.EXAMPLE: [
                r'\b(for example|for instance|such as|e\.g\.|eg)\b',
                r'\b(to illustrate|consider the case|imagine)\b',
                r'\b(specifically|in particular)\b',
            ],
            RhetoricalRole.BACKGROUND: [
                r'\b(historically|context|background|previously)\b',
                r'\b(traditionally|in the past|over time)\b',
                r'\b(introduction|overview|setting)\b',
            ],
            RhetoricalRole.CONCLUSION: [
                r'\b(in conclusion|to summarize|in summary|overall)\b',
                r'\b(finally|ultimately|in the end)\b',
                r'\b(to conclude|therefore we|thus we can)\b',
            ],
            RhetoricalRole.METHODOLOGY: [
                r'\b(method|methodology|approach|procedure|technique)\b',
                r'\b(we (used|employed|applied|conducted|performed))\b',
                r'\b(experimental setup|study design|protocol)\b',
                r'\b(data collection|analysis|measurement)\b',
            ],
            RhetoricalRole.INSIGHT: [
                r'\b(interestingly|notably|surprisingly|remarkably)\b',
                r'\b(reveals?|suggests?|indicates?|implies?)\b',
                r'\b(key finding|important|significant|crucial)\b',
            ],
            RhetoricalRole.OBSERVATION: [
                r'\b(observed?|noticed?|found|detected|identified)\b',
                r'\b(we see|it appears|seems to be)\b',
                r'\b(evidence suggests?|data shows?)\b',
            ],
            RhetoricalRole.DEFINITION: [
                r'\b(defined as|refers to|means|is called)\b',
                r'\b(terminology|term|concept|definition)\b',
                r'\b(in other words|that is|i\.e\.|ie)\b',
            ],
        }

    def auto_label_chunk(
        self,
        chunk_text: str,
        source_type: ContentType,
        page_number: Optional[int] = None,
        timestamp: Optional[str] = None,
    ) -> AutoLabelResponse:
        """
        Automatically label a chunk with metadata.

        Args:
            chunk_text: The text content to label
            source_type: Type of source document
            page_number: Optional page number
            timestamp: Optional timestamp

        Returns:
            AutoLabelResponse with assigned labels and metadata
        """
        # Calculate token count
        token_count = len(self.tokenizer.encode(chunk_text))

        # Detect rhetorical role
        rhetorical_role, role_confidence = self._detect_rhetorical_role(chunk_text)

        # Extract topic tags
        topic_tags = self._extract_topic_tags(chunk_text)

        # Calculate coverage score (what % of content is represented)
        coverage_score = self._calculate_coverage_score(chunk_text, topic_tags)

        # Determine overall confidence
        confidence_label = self._determine_confidence(
            chunk_text, role_confidence, len(topic_tags or []), coverage_score
        )

        return AutoLabelResponse(
            rhetorical_role=rhetorical_role,
            topic_tags=topic_tags,
            token_count=token_count,
            confidence_label=confidence_label,
            coverage_score=coverage_score,
        )

    def _detect_rhetorical_role(self, text: str) -> Tuple[RhetoricalRole, float]:
        """
        Detect the rhetorical role of a chunk.

        Returns:
            Tuple of (role, confidence_score)
        """
        text_lower = text.lower()
        role_scores = {}

        # Check each role's patterns
        for role, patterns in self.role_patterns.items():
            score = 0
            for pattern in patterns:
                matches = len(re.findall(pattern, text_lower, re.IGNORECASE))
                score += matches

            if score > 0:
                # Normalize score by text length (matches per 100 words)
                word_count = len(text_lower.split())
                normalized_score = (score / max(word_count, 1)) * 100
                role_scores[role] = normalized_score

        if not role_scores:
            return RhetoricalRole.UNKNOWN, 0.0

        # Get role with highest score
        best_role = max(role_scores, key=role_scores.get)
        best_score = role_scores[best_role]

        # Convert score to confidence (0-1)
        confidence = min(best_score / 5.0, 1.0)  # 5 matches per 100 words = 100% confidence

        # If confidence is very low, mark as insufficient data
        if confidence < 0.1 and len(text.split()) < 20:
            return RhetoricalRole.INSUFFICIENT_DATA, 0.0

        return best_role, confidence

    def _extract_topic_tags(self, text: str, max_tags: int = 3) -> Optional[List[str]]:
        """
        Extract topic tags from chunk text.

        Uses simple heuristics:
        1. Look for capitalized phrases (potential named entities)
        2. Extract frequently occurring noun phrases
        3. Limit to top 3 most relevant

        Args:
            text: Chunk text
            max_tags: Maximum number of tags to return

        Returns:
            List of topic tags or None if no tags found
        """
        # Simple extraction: find capitalized multi-word phrases
        # This is a heuristic approach - could be enhanced with NER or LLM

        # Pattern for capitalized phrases (e.g., "Machine Learning", "Neural Networks")
        capitalized_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
        matches = re.findall(capitalized_pattern, text)

        # Count frequency
        tag_counts = {}
        for match in matches:
            # Skip very long phrases
            if len(match.split()) > 4:
                continue
            tag_counts[match] = tag_counts.get(match, 0) + 1

        # Also look for technical terms (acronyms)
        acronym_pattern = r'\b([A-Z]{2,})\b'
        acronyms = re.findall(acronym_pattern, text)
        for acronym in acronyms:
            # Skip very short acronyms
            if len(acronym) < 2:
                continue
            tag_counts[acronym] = tag_counts.get(acronym, 0) + 1

        if not tag_counts:
            return None

        # Sort by frequency and take top N
        sorted_tags = sorted(tag_counts.items(), key=lambda x: x[1], reverse=True)
        top_tags = [tag for tag, _ in sorted_tags[:max_tags]]

        return top_tags if top_tags else None

    def _calculate_coverage_score(self, text: str, topic_tags: Optional[List[str]]) -> int:
        """
        Calculate what percentage of the chunk content is represented by labels.

        This is a heuristic score based on:
        - Presence of topic tags
        - Text length (longer text is harder to fully cover)
        - Structural indicators (headings, bullets, etc.)

        Returns:
            Score from 0-100
        """
        score = 50  # Start at 50% baseline

        # Adjust for topic tags
        if topic_tags:
            score += len(topic_tags) * 10  # +10 per tag

        # Adjust for text length
        word_count = len(text.split())
        if word_count < 50:
            score += 20  # Short chunks are easier to cover
        elif word_count > 200:
            score -= 10  # Long chunks harder to fully represent

        # Check for structural elements (lists, headings)
        if re.search(r'^\s*[-*•]\s', text, re.MULTILINE):
            score += 5  # List items
        if re.search(r'^#+\s', text, re.MULTILINE):
            score += 5  # Markdown headings

        # Clamp to 0-100
        return max(0, min(100, score))

    def _determine_confidence(
        self,
        text: str,
        role_confidence: float,
        tag_count: int,
        coverage_score: int,
    ) -> ConfidenceLabel:
        """
        Determine overall confidence level for the label assignment.

        Args:
            text: Chunk text
            role_confidence: Confidence in rhetorical role (0-1)
            tag_count: Number of topic tags found
            coverage_score: Coverage score (0-100)

        Returns:
            ConfidenceLabel (HIGH, MEDIUM, or LOW)
        """
        # Calculate composite score
        composite = (
            role_confidence * 0.5 +  # 50% weight on role confidence
            (tag_count / 3.0) * 0.3 +  # 30% weight on tags (max 3)
            (coverage_score / 100.0) * 0.2  # 20% weight on coverage
        )

        # Also consider text length
        word_count = len(text.split())
        if word_count < 10:
            return ConfidenceLabel.LOW  # Too short to be confident

        # Map composite score to label
        if composite >= 0.7:
            return ConfidenceLabel.HIGH
        elif composite >= 0.4:
            return ConfidenceLabel.MEDIUM
        else:
            return ConfidenceLabel.LOW

    def save_label(
        self,
        db: Session,
        chunk_id: str,
        user_id: str,
        document_id: str,
        chunk_index: int,
        chunk_text: str,
        source_type: ContentType,
        rhetorical_role: RhetoricalRole,
        topic_tags: Optional[List[str]],
        token_count: int,
        confidence_label: ConfidenceLabel,
        coverage_score: int,
        page_number: Optional[int] = None,
        timestamp: Optional[str] = None,
        is_auto_labeled: bool = True,
        human_verified: bool = False,
    ) -> ChunkLabel:
        """
        Save chunk label to database.

        Args:
            db: Database session
            chunk_id: Unique chunk identifier
            user_id: User ID
            document_id: Document ID
            chunk_index: Index of chunk in document
            chunk_text: Text content
            source_type: Type of source
            rhetorical_role: Assigned role
            topic_tags: Topic tags
            token_count: Number of tokens
            confidence_label: Confidence level
            coverage_score: Coverage score
            page_number: Optional page number
            timestamp: Optional timestamp
            is_auto_labeled: Whether auto-labeled
            human_verified: Whether human verified

        Returns:
            ChunkLabel database object
        """
        # Check if label already exists
        existing = db.query(ChunkLabel).filter(ChunkLabel.chunk_id == chunk_id).first()

        # Convert enums
        db_source_type = ContentTypeEnum[source_type.name]
        db_role = RhetoricalRoleEnum[rhetorical_role.name]
        db_confidence = ConfidenceLabelEnum[confidence_label.name]

        # Serialize topic tags to JSON
        topic_tags_json = json.dumps(topic_tags) if topic_tags else None

        if existing:
            # Update existing label
            existing.rhetorical_role = db_role
            existing.topic_tags = topic_tags_json
            existing.confidence_label = db_confidence
            existing.coverage_score = coverage_score
            existing.human_verified = human_verified
            db.commit()
            db.refresh(existing)
            return existing
        else:
            # Create new label
            label = ChunkLabel(
                id=str(uuid4()),
                chunk_id=chunk_id,
                user_id=user_id,
                document_id=document_id,
                chunk_index=chunk_index,
                chunk_text=chunk_text,
                token_count=token_count,
                source_type=db_source_type,
                page_number=page_number,
                timestamp=timestamp,
                rhetorical_role=db_role,
                topic_tags=topic_tags_json,
                confidence_label=db_confidence,
                coverage_score=coverage_score,
                is_auto_labeled=is_auto_labeled,
                human_verified=human_verified,
            )
            db.add(label)
            db.commit()
            db.refresh(label)
            return label

    def get_label(self, db: Session, chunk_id: str) -> Optional[ChunkLabel]:
        """
        Get label for a chunk.

        Args:
            db: Database session
            chunk_id: Chunk identifier

        Returns:
            ChunkLabel or None if not found
        """
        return db.query(ChunkLabel).filter(ChunkLabel.chunk_id == chunk_id).first()

    def get_unlabeled_chunks(
        self, db: Session, document_id: str, limit: int = 50, offset: int = 0
    ) -> Tuple[List[ChunkLabel], int]:
        """
        Get chunks that haven't been human-verified.

        Args:
            db: Database session
            document_id: Document ID
            limit: Max chunks to return
            offset: Offset for pagination

        Returns:
            Tuple of (list of chunks, total count)
        """
        # Get all chunks for document that are not human-verified
        query = db.query(ChunkLabel).filter(
            ChunkLabel.document_id == document_id,
            ChunkLabel.human_verified == False,
        )

        total = query.count()
        chunks = query.order_by(ChunkLabel.chunk_index).limit(limit).offset(offset).all()

        return chunks, total

    def to_response_schema(self, label: ChunkLabel) -> ChunkLabelResponse:
        """
        Convert database model to response schema.

        Args:
            label: ChunkLabel database object

        Returns:
            ChunkLabelResponse schema
        """
        # Parse topic tags from JSON
        topic_tags = None
        if label.topic_tags:
            try:
                topic_tags = json.loads(label.topic_tags)
            except json.JSONDecodeError:
                logger.warning(f"Failed to parse topic_tags for chunk {label.chunk_id}")

        return ChunkLabelResponse(
            chunk_id=label.chunk_id,
            rhetorical_role=RhetoricalRole[label.rhetorical_role.name],
            topic_tags=topic_tags,
            token_count=label.token_count,
            confidence_label=ConfidenceLabel[label.confidence_label.name],
            coverage_score=label.coverage_score,
            is_auto_labeled=label.is_auto_labeled,
            human_verified=label.human_verified,
            created_at=label.created_at,
            updated_at=label.updated_at,
        )
