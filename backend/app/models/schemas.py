"""Pydantic schemas for request/response validation."""
from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal
from datetime import datetime
from enum import Enum


class TaskMode(str, Enum):
    """Allowed task modes for the assistant."""
    START = "START"
    CONTINUE = "CONTINUE"
    REFRAME = "REFRAME"
    STUCK_DIAGNOSIS = "STUCK_DIAGNOSIS"
    OUTLINE = "OUTLINE"


class RhetoricalRole(str, Enum):
    """Rhetorical role of content chunk."""
    ARGUMENT = "argument"
    EXAMPLE = "example"
    BACKGROUND = "background"
    CONCLUSION = "conclusion"
    DEFINITION = "definition"
    UNKNOWN = "unknown"


class ContentType(str, Enum):
    """Type of source document."""
    RESEARCH_PAPER = "research_paper"
    VIDEO_TRANSCRIPT = "video_transcript"
    LECTURE_NOTES = "lecture_notes"
    PERSONAL_NOTES = "personal_notes"
    BOOK_EXCERPT = "book_excerpt"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class DocumentStatus(str, Enum):
    """Processing status of uploaded document."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


# Request Schemas

class AssistRequest(BaseModel):
    """Request for assistant guidance."""
    mode: TaskMode = Field(..., description="Task mode for assistance")
    editor_content: str = Field(
        default="",
        max_length=10000,
        description="Current content in user's editor"
    )
    additional_context: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Optional additional context"
    )

    @field_validator('editor_content', 'additional_context')
    @classmethod
    def sanitize_input(cls, v: Optional[str]) -> Optional[str]:
        """Sanitize input to prevent injection attacks."""
        if v is None:
            return v
        # Remove potential script tags and SQL injection patterns
        dangerous_patterns = ['<script', 'javascript:', 'onerror=', '--', ';--', "';", '/*', '*/', 'DROP ', 'DELETE ']
        sanitized = v
        for pattern in dangerous_patterns:
            sanitized = sanitized.replace(pattern, '')
        return sanitized.strip()


class DocumentUploadResponse(BaseModel):
    """Response after document upload."""
    document_id: str = Field(..., description="Unique document identifier")
    filename: str = Field(..., description="Original filename")
    status: DocumentStatus = Field(..., description="Processing status")
    created_at: datetime = Field(..., description="Upload timestamp")


class DocumentListResponse(BaseModel):
    """Response for listing user documents."""
    id: str
    title: str
    content_type: ContentType
    status: DocumentStatus
    created_at: datetime
    updated_at: datetime
    chunk_count: Optional[int] = None


# Response Schemas

class SourceCitation(BaseModel):
    """Citation for a retrieved source."""
    source: str = Field(..., description="Source filename or identifier")
    page: Optional[int] = Field(None, description="Page number (for PDFs)")
    timestamp: Optional[str] = Field(None, description="Timestamp (for videos)")
    content_type: ContentType = Field(..., description="Type of source")
    rhetorical_role: RhetoricalRole = Field(..., description="Role of content")
    similarity_score: float = Field(..., ge=0.0, le=1.0, description="Relevance score")
    content_preview: str = Field(..., max_length=200, description="Preview of content")


class AssistResponse(BaseModel):
    """Response from assistant with guidance."""
    guidance: str = Field(..., description="Structured guidance output")
    sources: List[SourceCitation] = Field(
        default_factory=list,
        description="Retrieved source citations"
    )
    mode: TaskMode = Field(..., description="Task mode used")
    metadata: dict = Field(
        default_factory=dict,
        description="Additional metadata (retrieval stats, etc.)"
    )


# Internal Models

class ChunkMetadata(BaseModel):
    """Metadata for a document chunk."""
    document_id: str
    chunk_index: int
    page_number: Optional[int] = None
    timestamp: Optional[str] = None
    content_type: ContentType
    rhetorical_role: RhetoricalRole
    source_filename: str


class RetrievalResult(BaseModel):
    """Result from vector search."""
    chunk_id: str
    content: str
    metadata: ChunkMetadata
    similarity_score: float


class UserStyleProfile(BaseModel):
    """User's writing and reasoning style profile."""
    user_id: str
    avg_sentence_length: float
    complexity_score: float  # Flesch-Kincaid or similar
    reasoning_style: Literal["deductive", "inductive", "abductive", "mixed"]
    uses_analogies: bool
    uses_examples: bool
    uses_questions: bool
    transition_patterns: List[str]
    vocabulary_level: str  # academic, technical, general
    updated_at: datetime


class PromptComponents(BaseModel):
    """Components for constructing the final prompt."""
    system_rules: str
    identity_scope: str
    task_mode: str
    retrieved_context: str
    user_input: str
    output_format: str
    style_adaptation: Optional[str] = None
