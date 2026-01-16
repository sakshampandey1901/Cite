#!/usr/bin/env python3
"""Download required embedding models for production deployment."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from sentence_transformers import SentenceTransformer
from app.core.config import settings

def download_embedding_model():
    """Download and cache the embedding model."""
    print("=" * 60)
    print("Embedding Model Download")
    print("=" * 60)

    model_name = settings.EMBEDDING_MODEL
    print(f"\n1. Downloading model: {model_name}")
    print("   This may take a few minutes on first run...")

    try:
        # Download and cache model
        model = SentenceTransformer(model_name)

        print(f"✅ Model downloaded successfully")

        # Test model
        print("\n2. Testing model...")
        test_text = "This is a test sentence."
        embedding = model.encode(test_text)

        print(f"✅ Model working correctly")
        print(f"   - Embedding dimension: {len(embedding)}")
        print(f"   - Expected dimension: 384")

        if len(embedding) != 384:
            print("⚠️  Warning: Unexpected embedding dimension")
            return False

        print("\n" + "=" * 60)
        print("✅ Model download complete!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error downloading model: {e}")
        print("\nTroubleshooting:")
        print("1. Check internet connectivity")
        print("2. Verify model name in .env is correct")
        print("3. Ensure sufficient disk space (~100MB)")
        print("4. Check HuggingFace Hub status")
        return False

if __name__ == "__main__":
    success = download_embedding_model()
    sys.exit(0 if success else 1)
