"""Document processing service for ingestion pipeline."""
import fitz  # PyMuPDF
import re
from typing import List, Dict, Tuple
from pathlib import Path
import tiktoken
from app.models.schemas import ContentType, RhetoricalRole


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
