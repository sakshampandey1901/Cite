"""Document processing service for ingestion pipeline."""
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import tiktoken
from sqlalchemy.orm import Session
from app.models.schemas import ContentType, RhetoricalRole
from app.services.chunk_labeling import ChunkLabelingService


class DocumentChunk:
    """Represents a processed document chunk."""

    def __init__(
        self,
        content: str,
        chunk_index: int,
        page_number: int = None,
        timestamp: str = None,
        metadata: dict = None
    ):
        self.content = content
        self.chunk_index = chunk_index
        self.page_number = page_number
        self.timestamp = timestamp
        self.metadata = metadata or {}


class DocumentProcessor:
    """Processes documents into chunks for embedding."""

    CHUNK_SIZE = 400  # tokens
    CHUNK_OVERLAP = 50  # tokens

    def __init__(self):
        self.encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        self.labeling_service = ChunkLabelingService()

    def process_pdf(self, file_path: Path) -> Tuple[List[DocumentChunk], ContentType]:
        """
        Extract text from PDF and chunk it.

        Args:
            file_path: Path to PDF file

        Returns:
            Tuple of (chunks, inferred_content_type)
        """
        chunks = []
        full_text = []

        try:
            doc = fitz.open(file_path)

            for page_num, page in enumerate(doc, start=1):
                text = page.get_text()
                if text.strip():
                    full_text.append(text)
                    # Create page-based chunks
                    page_chunks = self._chunk_text(text, page_number=page_num)
                    chunks.extend(page_chunks)

            doc.close()

            # Infer content type from document structure
            content_type = self._infer_content_type("\n".join(full_text[:5]))  # First 5 pages

            # Assign rhetorical roles
            chunks = self._assign_rhetorical_roles(chunks, full_text)

            return chunks, content_type

        except Exception as e:
            raise ValueError(f"Failed to process PDF: {str(e)}")

    def process_text(self, file_path: Path) -> Tuple[List[DocumentChunk], ContentType]:
        """
        Process plain text file.

        Args:
            file_path: Path to text file

        Returns:
            Tuple of (chunks, inferred_content_type)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                text = f.read()

            chunks = self._chunk_text(text)
            content_type = self._infer_content_type(text[:2000])  # First 2000 chars
            chunks = self._assign_rhetorical_roles(chunks, [text])

            return chunks, content_type

        except Exception as e:
            raise ValueError(f"Failed to process text file: {str(e)}")

    def process_subtitle(self, file_path: Path) -> Tuple[List[DocumentChunk], ContentType]:
        """
        Process subtitle file (SRT/VTT).

        Args:
            file_path: Path to subtitle file

        Returns:
            Tuple of (chunks, content_type)
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract text from subtitle format
            # Simple regex for SRT format
            text_blocks = re.findall(r'\d+:\d+:\d+,\d+ --> \d+:\d+:\d+,\d+\n(.+?)(?=\n\n|\Z)',
                                    content, re.DOTALL)

            full_text = " ".join(text_blocks)
            chunks = self._chunk_text(full_text)

            # Assign timestamps (simplified - would need more sophisticated parsing)
            chunks = self._assign_rhetorical_roles(chunks, [full_text])

            return chunks, ContentType.VIDEO_TRANSCRIPT

        except Exception as e:
            raise ValueError(f"Failed to process subtitle file: {str(e)}")

    def _chunk_text(
        self,
        text: str,
        page_number: int = None
    ) -> List[DocumentChunk]:
        """
        Chunk text into overlapping segments.

        Args:
            text: Text to chunk
            page_number: Page number for PDF chunks

        Returns:
            List of DocumentChunks
        """
        # Tokenize
        tokens = self.encoding.encode(text)
        chunks = []

        chunk_index = 0
        start = 0

        while start < len(tokens):
            end = min(start + self.CHUNK_SIZE, len(tokens))
            chunk_tokens = tokens[start:end]
            chunk_text = self.encoding.decode(chunk_tokens)

            chunks.append(DocumentChunk(
                content=chunk_text.strip(),
                chunk_index=chunk_index,
                page_number=page_number
            ))

            chunk_index += 1
            start += self.CHUNK_SIZE - self.CHUNK_OVERLAP

        return chunks

    def _infer_content_type(self, sample_text: str) -> ContentType:
        """
        Infer content type from text sample.

        Args:
            sample_text: Sample of document text

        Returns:
            Inferred ContentType
        """
        sample_lower = sample_text.lower()

        # Heuristics for content type detection
        if any(indicator in sample_lower for indicator in ['abstract', 'introduction', 'methodology', 'references']):
            return ContentType.RESEARCH_PAPER
        elif any(indicator in sample_lower for indicator in ['transcript', 'speaker', '[inaudible]']):
            return ContentType.VIDEO_TRANSCRIPT
        elif any(indicator in sample_lower for indicator in ['lecture', 'professor', 'today we will']):
            return ContentType.LECTURE_NOTES
        elif any(indicator in sample_lower for indicator in ['chapter', 'isbn', 'copyright']):
            return ContentType.BOOK_EXCERPT
        else:
            return ContentType.UNKNOWN

    def _assign_rhetorical_roles(
        self,
        chunks: List[DocumentChunk],
        full_text_pages: List[str]
    ) -> List[DocumentChunk]:
        """
        Assign rhetorical roles to chunks based on content.

        Args:
            chunks: List of chunks to annotate
            full_text_pages: Full text split by pages

        Returns:
            Chunks with rhetorical roles assigned
        """
        for chunk in chunks:
            chunk.metadata['rhetorical_role'] = self._infer_rhetorical_role(chunk.content)

        return chunks

    def _infer_rhetorical_role(self, text: str) -> RhetoricalRole:
        """
        Infer rhetorical role from chunk text.

        Args:
            text: Chunk text

        Returns:
            Inferred RhetoricalRole
        """
        text_lower = text.lower()

        # Heuristics for rhetorical role
        if any(indicator in text_lower for indicator in ['therefore', 'thus', 'consequently', 'we argue']):
            return RhetoricalRole.ARGUMENT
        elif any(indicator in text_lower for indicator in ['for example', 'for instance', 'such as', 'consider']):
            return RhetoricalRole.EXAMPLE
        elif any(indicator in text_lower for indicator in ['in conclusion', 'to summarize', 'in summary']):
            return RhetoricalRole.CONCLUSION
        elif any(indicator in text_lower for indicator in ['define', 'refers to', 'is defined as']):
            return RhetoricalRole.DEFINITION
        elif any(indicator in text_lower for indicator in ['background', 'historically', 'context', 'previously']):
            return RhetoricalRole.BACKGROUND
        else:
            return RhetoricalRole.UNKNOWN

    def process_and_label_chunks(
        self,
        chunks: List[DocumentChunk],
        content_type: ContentType,
        user_id: str,
        document_id: str,
        db: Optional[Session] = None,
    ) -> List[DocumentChunk]:
        """
        Process chunks with enhanced labeling service and optionally save to DB.

        This method:
        1. Auto-labels each chunk using the ChunkLabelingService
        2. Enriches chunk metadata with confidence scores and topic tags
        3. Optionally saves labels to database for tracking and verification

        Args:
            chunks: List of DocumentChunks to process
            content_type: Type of source document
            user_id: User ID
            document_id: Document ID
            db: Optional database session for saving labels

        Returns:
            List of chunks with enriched metadata
        """
        for chunk in chunks:
            # Auto-label the chunk
            label_result = self.labeling_service.auto_label_chunk(
                chunk_text=chunk.content,
                source_type=content_type,
                page_number=chunk.page_number,
                timestamp=chunk.timestamp,
            )

            # Enrich chunk metadata with labeling results
            chunk.metadata['rhetorical_role'] = label_result.rhetorical_role
            chunk.metadata['topic_tags'] = label_result.topic_tags
            chunk.metadata['confidence_label'] = label_result.confidence_label
            chunk.metadata['coverage_score'] = label_result.coverage_score
            chunk.metadata['token_count'] = label_result.token_count

            # Optionally save to database for tracking and human verification
            if db is not None:
                try:
                    chunk_id = f"{user_id}_{document_id}_{chunk.chunk_index}"
                    self.labeling_service.save_label(
                        db=db,
                        chunk_id=chunk_id,
                        user_id=user_id,
                        document_id=document_id,
                        chunk_index=chunk.chunk_index,
                        chunk_text=chunk.content,
                        source_type=content_type,
                        rhetorical_role=label_result.rhetorical_role,
                        topic_tags=label_result.topic_tags,
                        token_count=label_result.token_count,
                        confidence_label=label_result.confidence_label,
                        coverage_score=label_result.coverage_score,
                        page_number=chunk.page_number,
                        timestamp=chunk.timestamp,
                        is_auto_labeled=True,
                        human_verified=False,
                    )
                except Exception as e:
                    # Log error but don't fail the entire processing
                    import logging
                    logger = logging.getLogger(__name__)
                    logger.warning(f"Failed to save label for chunk {chunk.chunk_index}: {e}")

        return chunks
