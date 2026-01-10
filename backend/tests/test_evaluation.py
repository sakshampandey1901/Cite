"""Evaluation tests for RAG quality and assistant behavior."""
import pytest
from app.services.prompt_builder import PromptBuilder
from app.services.llm_service import LLMService
from app.models.schemas import TaskMode, RetrievalResult, ChunkMetadata, ContentType, RhetoricalRole


class TestStructuralSimilarity:
    """Test structural similarity to user's past work."""

    def test_outline_mode_produces_skeletal_structure(self):
        """Test that OUTLINE mode produces skeletal structure only."""
        prompt_builder = PromptBuilder()

        # Mock retrieved sources
        sources = [
            RetrievalResult(
                chunk_id="test_1",
                content="Research shows three main approaches: deductive, inductive, and abductive reasoning.",
                metadata=ChunkMetadata(
                    document_id="doc1",
                    chunk_index=0,
                    page_number=1,
                    content_type=ContentType.RESEARCH_PAPER,
                    rhetorical_role=RhetoricalRole.ARGUMENT,
                    source_filename="test.pdf"
                ),
                similarity_score=0.9
            )
        ]

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.OUTLINE,
            editor_content="",
            retrieved_sources=sources
        )

        # Check that OUTLINE constraints are in prompt
        assert "skeletal structure" in prompt.lower()
        assert "no prose" in prompt.lower()

    def test_start_mode_requires_source_citation(self):
        """Test that START mode requires source citations."""
        prompt_builder = PromptBuilder()

        sources = [
            RetrievalResult(
                chunk_id="test_1",
                content="Cognitive load theory suggests...",
                metadata=ChunkMetadata(
                    document_id="doc1",
                    chunk_index=0,
                    page_number=5,
                    content_type=ContentType.RESEARCH_PAPER,
                    rhetorical_role=RhetoricalRole.BACKGROUND,
                    source_filename="cognitive_theory.pdf"
                ),
                similarity_score=0.85
            )
        ]

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.START,
            editor_content="",
            retrieved_sources=sources
        )

        # Check that citation requirements are in prompt
        assert "supporting rationale" in prompt.lower()
        assert "cite specific sources" in prompt.lower()


class TestReasoningPathAlignment:
    """Test that suggestions align with user's reasoning patterns."""

    def test_no_first_person_in_output(self):
        """Test that output validation rejects first-person perspective."""
        llm_service = LLMService()

        # Simulate output with first-person
        bad_output = """## START Guidance

### 1. Likely Next Move
I think you should start with an introduction.

### 2. Supporting Rationale
Based on my analysis...

### 4. Cautions or Limitations
None."""

        is_valid, error = llm_service.validate_generation(bad_output, TaskMode.START)
        assert not is_valid
        assert "first-person" in error.lower()

    def test_output_requires_all_sections(self):
        """Test that output validation requires all mandatory sections."""
        llm_service = LLMService()

        # Incomplete output
        incomplete_output = """## START Guidance

### 1. Likely Next Move
Begin with defining core concepts."""

        is_valid, error = llm_service.validate_generation(incomplete_output, TaskMode.START)
        assert not is_valid
        assert "missing" in error.lower()


class TestFailureModeAlignment:
    """Test uncertainty handling and missing information flagging."""

    def test_empty_sources_acknowledged(self):
        """Test that empty sources are properly acknowledged."""
        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.CONTINUE,
            editor_content="Test content",
            retrieved_sources=[]
        )

        # Check that missing sources are flagged
        assert "no relevant sources" in prompt.lower()

    def test_hallucination_detection(self):
        """Test that factual claims without citations are rejected."""
        llm_service = LLMService()

        # Output with unsupported factual claims
        hallucinated_output = """## START Guidance

### 1. Likely Next Move
Research shows that 85% of cognitive scientists agree on this approach.

### 2. Supporting Rationale
Studies indicate this is the best method.

### 4. Cautions or Limitations
None."""

        is_valid, error = llm_service.validate_generation(hallucinated_output, TaskMode.START)
        assert not is_valid


class TestContinuationPlausibility:
    """Test that suggestions are plausible continuations."""

    def test_continue_mode_uses_editor_content(self):
        """Test that CONTINUE mode incorporates editor content."""
        prompt_builder = PromptBuilder()

        editor_content = "The main argument is that cognitive tools extend human capability."

        sources = [
            RetrievalResult(
                chunk_id="test_1",
                content="Extended cognition theory posits that tools become part of cognitive system.",
                metadata=ChunkMetadata(
                    document_id="doc1",
                    chunk_index=0,
                    content_type=ContentType.RESEARCH_PAPER,
                    rhetorical_role=RhetoricalRole.ARGUMENT,
                    source_filename="extended_mind.pdf"
                ),
                similarity_score=0.92
            )
        ]

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.CONTINUE,
            editor_content=editor_content,
            retrieved_sources=sources
        )

        # Check that editor content is in prompt
        assert editor_content in prompt


class TestPreferenceConsistency:
    """Test cross-session consistency."""

    def test_same_input_produces_consistent_structure(self):
        """Test that same inputs produce structurally consistent outputs."""
        # This would require multiple runs and comparison
        # Placeholder for implementation
        pass


class TestPromptLayering:
    """Test prompt construction and layering."""

    def test_system_rules_always_first(self):
        """Test that system rules are always first in prompt."""
        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.START,
            editor_content="test",
            retrieved_sources=[]
        )

        # System rules should be at the top
        assert prompt.startswith("CRITICAL CONSTRAINTS")

    def test_all_layers_present(self):
        """Test that all required prompt layers are present."""
        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.REFRAME,
            editor_content="test",
            retrieved_sources=[]
        )

        required_sections = [
            "CRITICAL CONSTRAINTS",
            "ROLE:",
            "MODE: REFRAME",
            "RETRIEVED SOURCES",
            "MANDATORY OUTPUT STRUCTURE"
        ]

        for section in required_sections:
            assert section in prompt


class TestSecurityConstraints:
    """Test that security constraints are enforced in prompts."""

    def test_zero_hallucination_constraint(self):
        """Test that zero hallucination constraint is in prompt."""
        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.START,
            editor_content="",
            retrieved_sources=[]
        )

        assert "zero hallucination" in prompt.lower()

    def test_no_impersonation_constraint(self):
        """Test that no impersonation constraint is in prompt."""
        prompt_builder = PromptBuilder()

        prompt = prompt_builder.build_prompt(
            mode=TaskMode.START,
            editor_content="",
            retrieved_sources=[]
        )

        assert "never impersonate" in prompt.lower()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
