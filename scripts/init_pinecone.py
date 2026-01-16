#!/usr/bin/env python3
"""Initialize Pinecone index for production deployment."""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from pinecone import Pinecone, ServerlessSpec
from app.core.config import settings

def init_pinecone_index():
    """Create Pinecone index if it doesn't exist."""
    print("=" * 60)
    print("Pinecone Index Initialization")
    print("=" * 60)

    # Initialize Pinecone client
    print(f"\n1. Connecting to Pinecone (Environment: {settings.PINECONE_ENVIRONMENT})...")
    pc = Pinecone(api_key=settings.PINECONE_API_KEY)

    # Check if index exists
    index_name = settings.PINECONE_INDEX_NAME
    existing_indexes = pc.list_indexes()

    if any(idx.name == index_name for idx in existing_indexes):
        print(f"✅ Index '{index_name}' already exists")

        # Get index stats
        index = pc.Index(index_name)
        stats = index.describe_index_stats()
        print(f"\nIndex Statistics:")
        print(f"  - Total vectors: {stats.total_vector_count}")
        print(f"  - Dimension: {stats.dimension}")
        print(f"  - Namespaces: {len(stats.namespaces)}")

        return True

    # Create index
    print(f"\n2. Creating index '{index_name}'...")
    print(f"   - Dimension: 384 (sentence-transformers/all-MiniLM-L6-v2)")
    print(f"   - Metric: cosine")
    print(f"   - Cloud: {settings.PINECONE_CLOUD}")
    print(f"   - Region: {settings.PINECONE_ENVIRONMENT}")

    try:
        pc.create_index(
            name=index_name,
            dimension=384,  # all-MiniLM-L6-v2 embedding dimension
            metric="cosine",
            spec=ServerlessSpec(
                cloud=settings.PINECONE_CLOUD,
                region=settings.PINECONE_ENVIRONMENT
            )
        )

        print(f"✅ Index '{index_name}' created successfully")
        print("\nWaiting for index to be ready...")

        # Wait for index to be ready
        index = pc.Index(index_name)
        print("✅ Index is ready")

        print("\n" + "=" * 60)
        print("✅ Pinecone initialization complete!")
        print("=" * 60)

        return True

    except Exception as e:
        print(f"\n❌ Error creating index: {e}")
        print("\nTroubleshooting:")
        print("1. Verify PINECONE_API_KEY is correct")
        print("2. Check PINECONE_ENVIRONMENT matches your project")
        print("3. Ensure you have permissions to create indexes")
        print("4. Verify you haven't exceeded free tier limits")
        return False

if __name__ == "__main__":
    success = init_pinecone_index()
    sys.exit(0 if success else 1)
