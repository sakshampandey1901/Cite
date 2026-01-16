"""LLM service for generating assistance using Groq."""
from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.models.schemas import TaskMode


class LLMService:
    """Manages LLM interactions for assistance generation."""

    def __init__(self):
        """Initialize Groq client."""
        self.client = Groq(api_key=settings.GROQ_API_KEY)
        self.model = settings.GROQ_MODEL

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def generate_guidance(
        self,
        prompt: str,
        max_tokens: int = 1000,
        temperature: float = 0.3
    ) -> str:
        """
        Generate guidance using Groq.

        Args:
            prompt: Complete prompt with all layers
            max_tokens: Maximum tokens in response
            temperature: Sampling temperature (lower = more deterministic)

        Returns:
            Generated guidance text
        """
        try:
            # Split prompt into system and user parts for better API compatibility
            parts = prompt.split("\n---\n", 1)
            if len(parts) >= 2:
                system_content = parts[0]
                user_content = "\n---\n".join(parts[1:])

                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": user_content}
                ]
            else:
                # Fallback: use entire prompt as user message
                messages = [{"role": "user", "content": prompt}]

            message = self.client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=messages
            )

            # Extract text from response
            guidance = message.choices[0].message.content

            return guidance

        except Exception as e:
            # Log error and re-raise
            raise RuntimeError(f"LLM generation failed: {str(e)}")

    def validate_generation(self, output: str, mode: TaskMode) -> tuple[bool, str]:
        """
        Validate generated output for safety and structure.

        Args:
            output: Generated output
            mode: Task mode

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required sections
        required_sections = [
            f"## {mode.value} Guidance",
            "### 1. Likely Next Move",
            "### 2. Supporting Rationale",
            "### 4. Cautions or Limitations"
        ]

        for section in required_sections:
            if section not in output:
                return False, f"Missing required section: {section}"

        # Check for forbidden first-person patterns
        forbidden_patterns = {
            "I think": "First-person opinion detected",
            "I believe": "First-person opinion detected",
            "I would": "First-person suggestion detected",
            "In my opinion": "Personal opinion detected",
            "My approach": "First-person perspective detected",
            "I recommend": "First-person recommendation detected"
        }

        output_lower = output.lower()
        for pattern, error_msg in forbidden_patterns.items():
            if pattern.lower() in output_lower:
                return False, error_msg

        # Check for hallucination indicators (should flag uncertainty)
        # If no sources mentioned but making specific claims
        if "**Source" not in output and "[No relevant source" not in output:
            # Check if making specific factual claims
            claim_indicators = ["research shows", "studies indicate", "evidence suggests"]
            for indicator in claim_indicators:
                if indicator.lower() in output_lower:
                    return False, "Factual claims without source citations detected"

        # Check length (prevent overly verbose responses)
        word_count = len(output.split())
        if word_count > 300:
            return False, f"Response too long ({word_count} words, max 300)"

        return True, ""

    def fallback_response(self, mode: TaskMode, error_context: str = "") -> str:
        """
        Generate safe fallback response when generation fails.

        Args:
            mode: Task mode
            error_context: Error context for logging

        Returns:
            Safe fallback guidance
        """
        return f"""## {mode.value} Guidance

### 1. Likely Next Move
Unable to generate specific guidance at this time.

### 2. Supporting Rationale
[No relevant source found - insufficient context in document corpus]

### 3. Alternative Paths
Consider uploading additional documents related to your topic for more targeted guidance.

### 4. Cautions or Limitations
The system encountered an issue generating guidance. This may indicate:
- Insufficient relevant documents in your corpus
- Need for more specific context in your query
- Technical limitation requiring retry

Error context: {error_context if error_context else "Unknown error"}"""
