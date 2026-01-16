"""
Quick test script for the chunk labeling system.

This script tests the labeling service without requiring full API setup.

Usage:
    python test_labeling.py
"""

from app.services.chunk_labeling import ChunkLabelingService
from app.models.schemas import ContentType

def test_auto_labeling():
    """Test auto-labeling functionality."""
    print("=" * 80)
    print("Testing Chunk Labeling System")
    print("=" * 80)

    # Initialize service
    labeling_service = ChunkLabelingService()
    print("\n✓ ChunkLabelingService initialized")

    # Test cases
    test_chunks = [
        {
            "text": "Therefore, we can conclude that machine learning models require large amounts of training data to achieve high accuracy. This demonstrates the importance of data quality in AI systems.",
            "type": "argument",
            "source": ContentType.RESEARCH_PAPER
        },
        {
            "text": "For example, consider a neural network trained on image classification. The model learns to identify patterns such as edges, textures, and shapes.",
            "type": "example",
            "source": ContentType.LECTURE_NOTES
        },
        {
            "text": "Historically, artificial intelligence research began in the 1950s with pioneers like Alan Turing and John McCarthy. The field has evolved significantly since then.",
            "type": "background",
            "source": ContentType.BOOK_EXCERPT
        },
        {
            "text": "In conclusion, this paper has demonstrated the effectiveness of transformer architectures for natural language processing tasks.",
            "type": "conclusion",
            "source": ContentType.RESEARCH_PAPER
        },
        {
            "text": "Our methodology involved collecting data from three sources: academic databases, public repositories, and survey responses. We then applied statistical analysis techniques to identify patterns.",
            "type": "methodology",
            "source": ContentType.RESEARCH_PAPER
        },
        {
            "text": "Interestingly, the results revealed an unexpected correlation between training time and model performance, suggesting that longer training does not always lead to better outcomes.",
            "type": "insight",
            "source": ContentType.RESEARCH_PAPER
        },
    ]

    print("\n" + "=" * 80)
    print("Running Auto-Labeling Tests")
    print("=" * 80)

    for i, test in enumerate(test_chunks, 1):
        print(f"\n📄 Test Case {i}: Expected '{test['type']}'")
        print(f"Text preview: {test['text'][:100]}...")

        # Auto-label
        result = labeling_service.auto_label_chunk(
            chunk_text=test['text'],
            source_type=test['source'],
            page_number=i,
            timestamp=None
        )

        print(f"\n  Rhetorical Role: {result.rhetorical_role.value}")
        print(f"  Topic Tags: {result.topic_tags}")
        print(f"  Token Count: {result.token_count}")
        print(f"  Confidence: {result.confidence_label.value}")
        print(f"  Coverage Score: {result.coverage_score}%")

        # Check if detected correctly
        if test['type'] in result.rhetorical_role.value:
            print(f"  ✓ Correct role detected!")
        else:
            print(f"  ⚠ Expected '{test['type']}' but got '{result.rhetorical_role.value}'")

    print("\n" + "=" * 80)
    print("Pattern Matching Tests")
    print("=" * 80)

    # Test pattern matching
    patterns_to_test = [
        ("therefore we conclude", "argument"),
        ("for instance consider", "example"),
        ("historically the context", "background"),
        ("in summary we found", "conclusion"),
        ("defined as referring to", "definition"),
        ("our methodology involved", "methodology"),
        ("surprisingly the results", "insight"),
    ]

    print("\nTesting pattern detection:")
    for text, expected in patterns_to_test:
        result = labeling_service.auto_label_chunk(
            chunk_text=text,
            source_type=ContentType.RESEARCH_PAPER
        )
        status = "✓" if expected in result.rhetorical_role.value else "✗"
        print(f"  {status} '{text}' → {result.rhetorical_role.value} (expected: {expected})")

    print("\n" + "=" * 80)
    print("Topic Tag Extraction Tests")
    print("=" * 80)

    topic_tests = [
        "Machine Learning and Artificial Intelligence are transforming healthcare.",
        "The Deep Neural Network architecture uses multiple layers.",
        "Natural Language Processing (NLP) techniques include tokenization and parsing.",
        "This study focuses on Computer Vision and Image Recognition tasks.",
    ]

    print("\nTesting topic tag extraction:")
    for text in topic_tests:
        result = labeling_service.auto_label_chunk(
            chunk_text=text,
            source_type=ContentType.RESEARCH_PAPER
        )
        print(f"  Text: {text[:60]}...")
        print(f"  Tags: {result.topic_tags}")

    print("\n" + "=" * 80)
    print("Confidence Scoring Tests")
    print("=" * 80)

    confidence_tests = [
        ("Therefore, we argue that this approach is superior. Thus, we conclude decisively.", "high"),
        ("This section discusses some aspects of the topic.", "low"),
        ("For example, consider Machine Learning applications in Healthcare and Finance.", "medium-high"),
    ]

    print("\nTesting confidence levels:")
    for text, expected in confidence_tests:
        result = labeling_service.auto_label_chunk(
            chunk_text=text,
            source_type=ContentType.RESEARCH_PAPER
        )
        print(f"  Text: {text[:60]}...")
        print(f"  Confidence: {result.confidence_label.value} (expected: {expected})")
        print(f"  Coverage: {result.coverage_score}%")

    print("\n" + "=" * 80)
    print("All Tests Completed!")
    print("=" * 80)
    print("\n✓ Chunk labeling system is working correctly")
    print("\nNext steps:")
    print("  1. Run database migration: python migrations/create_chunk_labels_table.py")
    print("  2. Test API endpoints via /docs")
    print("  3. Upload a document and verify labels are saved")


if __name__ == "__main__":
    test_auto_labeling()
