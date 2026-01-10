"""SQLAlchemy database models."""
from sqlalchemy import Column, String, Integer, DateTime, Enum as SQLEnum, ForeignKey, Text, Float, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum


Base = declarative_base()


class DocumentStatusEnum(str, enum.Enum):
    """Document processing status."""
    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"


class ContentTypeEnum(str, enum.Enum):
    """Content type classification."""
    RESEARCH_PAPER = "research_paper"
    VIDEO_TRANSCRIPT = "video_transcript"
    LECTURE_NOTES = "lecture_notes"
    PERSONAL_NOTES = "personal_notes"
    BOOK_EXCERPT = "book_excerpt"
    ARTICLE = "article"
    UNKNOWN = "unknown"


class User(Base):
    """User account model."""
    __tablename__ = "users"

    id = Column(String(36), primary_key=True)
    email = Column(String(255), unique=True, nullable=False, index=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    documents = relationship("Document", back_populates="user", cascade="all, delete-orphan")
    style_profile = relationship("StyleProfile", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Document(Base):
    """User document model."""
    __tablename__ = "documents"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    content_type = Column(SQLEnum(ContentTypeEnum), nullable=False)
    status = Column(SQLEnum(DocumentStatusEnum), default=DocumentStatusEnum.UPLOADED, nullable=False)
    file_size_bytes = Column(Integer, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="documents")


class StyleProfile(Base):
    """User writing and reasoning style profile."""
    __tablename__ = "style_profiles"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True)
    avg_sentence_length = Column(Float, default=15.0, nullable=False)
    complexity_score = Column(Float, default=8.0, nullable=False)  # Flesch-Kincaid grade level
    reasoning_style = Column(String(50), default="mixed", nullable=False)  # deductive, inductive, abductive, mixed
    uses_analogies = Column(Boolean, default=False, nullable=False)
    uses_examples = Column(Boolean, default=True, nullable=False)
    uses_questions = Column(Boolean, default=False, nullable=False)
    vocabulary_level = Column(String(50), default="general", nullable=False)  # academic, technical, general
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="style_profile")


class AssistanceLog(Base):
    """Log of assistance requests for evaluation."""
    __tablename__ = "assistance_logs"

    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    mode = Column(String(50), nullable=False)
    editor_content = Column(Text, nullable=True)
    additional_context = Column(Text, nullable=True)
    guidance_output = Column(Text, nullable=False)
    source_count = Column(Integer, default=0, nullable=False)
    retrieval_time_ms = Column(Integer, nullable=True)
    generation_time_ms = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
