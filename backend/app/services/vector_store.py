"""Vector store service for embeddings using Pinecone."""
import os
from typing import List, Dict, Optional
from pinecone import Pinecone, ServerlessSpec
from sentence_transformers import SentenceTransformer
from tenacity import retry, stop_after_attempt, wait_exponential
from app.core.config import settings
from app.models.schemas import ChunkMetadata, RetrievalResult, RhetoricalRole, ContentType


class VectorStore:
    """Manages vector embeddings and similarity search."""

    EMBEDDING_DIMENSION = 384  # all-MiniLM-L6-v2 dimension
    BATCH_SIZE = 100

    def __init__(self):
        """Initialize Pinecone and embedding model."""
        # Initialize Pinecone
        self.pc = Pinecone(api_key=settings.PINECONE_API_KEY)

        # Create or connect to index
        self.index_name = settings.PINECONE_INDEX_NAME
        self._initialize_index()
        self.index = self.pc.Index(self.index_name)

        # Initialize local embedding model
        self.embedding_model = SentenceTransformer(settings.EMBEDDING_MODEL)

    def _initialize_index(self):
        """Create Pinecone index if it doesn't exist."""
        existing_indexes = [idx.name for idx in self.pc.list_indexes()]

        if self.index_name not in existing_indexes:
            self.pc.create_index(
                name=self.index_name,
                dimension=self.EMBEDDING_DIMENSION,
                metric='cosine',
                spec=ServerlessSpec(
                    cloud='aws',
                    region=settings.PINECONE_ENVIRONMENT
                )
            )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text using local model.

        Args:
            text: Text to embed

        Returns:
            Embedding vector
        """
        embedding = self.embedding_model.encode(
            text,
            normalize_embeddings=True
        )
        return embedding.tolist()

    def upsert_chunks(
        self,
        chunks: List[Dict[str, any]],
        user_id: str,
        document_id: str
    ) -> int:
        """
        Insert document chunks into vector store.

        Args:
            chunks: List of chunk dictionaries with 'content' and 'metadata'
            user_id: User ID for scoping
            document_id: Document ID

        Returns:
            Number of chunks inserted
        """
        vectors = []

        for chunk in chunks:
            # Generate embedding
            embedding = self._get_embedding(chunk['content'])

            # Create unique ID
            chunk_id = f"{user_id}_{document_id}_{chunk['chunk_index']}"

            # Prepare metadata
            metadata = {
                'user_id': user_id,
                'document_id': document_id,
                'chunk_index': chunk['chunk_index'],
                'content': chunk['content'][:1000],  # Store truncated content
                'source_filename': chunk['source_filename'],
                'content_type': chunk['content_type'],
                'rhetorical_role': chunk['rhetorical_role'],
                'page_number': chunk.get('page_number'),
                'timestamp': chunk.get('timestamp'),
            }

            vectors.append({
                'id': chunk_id,
                'values': embedding,
                'metadata': metadata
            })

        # Batch upsert
        for i in range(0, len(vectors), self.BATCH_SIZE):
            batch = vectors[i:i + self.BATCH_SIZE]
            self.index.upsert(vectors=batch)

        return len(vectors)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        content_type_filter: Optional[str] = None,
        rhetorical_role_filter: Optional[str] = None
    ) -> List[RetrievalResult]:
        """
        Search for similar chunks.

        Args:
            query: Search query
            user_id: User ID for scoping
            top_k: Number of results to return
            content_type_filter: Optional content type filter
            rhetorical_role_filter: Optional rhetorical role filter

        Returns:
            List of retrieval results
        """
        # Generate query embedding
        query_embedding = self._get_embedding(query)

        # Build filter
        filter_dict = {'user_id': user_id}
        if content_type_filter:
            filter_dict['content_type'] = content_type_filter
        if rhetorical_role_filter:
            filter_dict['rhetorical_role'] = rhetorical_role_filter

        # Search
        results = self.index.query(
            vector=query_embedding,
            top_k=top_k,
            include_metadata=True,
            filter=filter_dict
        )

        # Parse results
        retrieval_results = []
        for match in results.matches:
            metadata = match.metadata

            chunk_metadata = ChunkMetadata(
                document_id=metadata['document_id'],
                chunk_index=metadata['chunk_index'],
                page_number=metadata.get('page_number'),
                timestamp=metadata.get('timestamp'),
                content_type=ContentType(metadata['content_type']),
                rhetorical_role=RhetoricalRole(metadata['rhetorical_role']),
                source_filename=metadata['source_filename']
            )

            retrieval_results.append(RetrievalResult(
                chunk_id=match.id,
                content=metadata.get('content', ''),
                metadata=chunk_metadata,
                similarity_score=match.score
            ))

        return retrieval_results

    def delete_document(self, user_id: str, document_id: str):
        """
        Delete all chunks for a document.

        Args:
            user_id: User ID
            document_id: Document ID
        """
        # Pinecone delete by filter (if supported) or delete by ID prefix
        self.index.delete(
            filter={
                'user_id': user_id,
                'document_id': document_id
            }
        )

    def delete_user_data(self, user_id: str):
        """
        Delete all data for a user.

        Args:
            user_id: User ID
        """
        self.index.delete(filter={'user_id': user_id})
