import uuid
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.llm import generate_embeddings

logger = logging.getLogger(__name__)

class HybridRetriever:
    def __init__(self, storage_path: str = settings.QDRANT_STORAGE_PATH):
        # Local storage path-based client avoids running a docker container
        self.client = QdrantClient(path=storage_path)

    def init_collection(self, collection_name: str, vector_size: int = 1536):
        """Initialize collection in Qdrant if it doesn't exist."""
        collections = self.client.get_collections().collections
        exists = any(c.name == collection_name for c in collections)
        if not exists:
            logger.info(f"Creating Qdrant collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(size=vector_size, distance=Distance.COSINE)
            )

    def delete_collection(self, collection_name: str):
        """Delete Qdrant collection."""
        try:
            self.client.delete_collection(collection_name)
        except Exception as e:
            logger.warning(f"Failed to delete collection {collection_name}: {e}")

    def index_chunks(self, collection_name: str, chunks: List[Dict[str, Any]]):
        """
        Embed and index document chunks.
        Each chunk is a dict:
        {
           "id": str, # optional, generated if missing
           "text": str,
           "metadata": dict
        }
        """
        self.init_collection(collection_name)
        
        texts = [chunk["text"] for chunk in chunks]
        if not texts:
            return

        embeddings = generate_embeddings(texts)
        points = []
        for i, chunk in enumerate(chunks):
            chunk_id = chunk.get("id") or str(uuid.uuid4())
            metadata = chunk.get("metadata") or {}
            
            # Store the text inside payload for retrieval
            payload = {
                "text": chunk["text"],
                "metadata": metadata
            }
            
            points.append(
                PointStruct(
                    id=chunk_id,
                    vector=embeddings[i],
                    payload=payload
                )
            )

        self.client.upsert(
            collection_name=collection_name,
            points=points
        )
        logger.info(f"Successfully indexed {len(chunks)} chunks in collection '{collection_name}'")

    def _get_qdrant_filter(self, metadata_filter: Optional[Dict[str, Any]]) -> Optional[Filter]:
        """Convert a simple dict filter into Qdrant FieldConditions."""
        if not metadata_filter:
            return None
        
        conditions = []
        for key, val in metadata_filter.items():
            conditions.append(
                FieldCondition(
                    key=f"metadata.{key}",
                    match=MatchValue(value=val)
                )
            )
        
        if conditions:
            return Filter(must=conditions)
        return None

    def search_vector(
        self, 
        collection_name: str, 
        query: str, 
        limit: int = 5, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Dense Vector search in Qdrant."""
        self.init_collection(collection_name)
        
        query_vector = generate_embeddings([query])[0]
        q_filter = self._get_qdrant_filter(metadata_filter)
        
        query_response = self.client.query_points(
            collection_name=collection_name,
            query=query_vector,
            query_filter=q_filter,
            limit=limit
        )
        
        results = []
        for res in query_response.points:
            results.append({
                "id": str(res.id),
                "text": res.payload.get("text", ""),
                "metadata": res.payload.get("metadata", {}),
                "score": float(res.score)
            })
        return results

    def _get_all_chunks_filtered(self, collection_name: str, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Get all chunks from a collection matching metadata filters to build a local BM25 index."""
        self.init_collection(collection_name)
        q_filter = self._get_qdrant_filter(metadata_filter)
        
        # Scroll through all points in collection
        scroll_results, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=q_filter,
            limit=10000, # Large limit since sample collections are small
            with_payload=True,
            with_vectors=False
        )
        
        chunks = []
        for point in scroll_results:
            chunks.append({
                "id": str(point.id),
                "text": point.payload.get("text", ""),
                "metadata": point.payload.get("metadata", {})
            })
        return chunks

    def search_bm25(
        self, 
        collection_name: str, 
        query: str, 
        limit: int = 5, 
        metadata_filter: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Sparse BM25 search over filtered corpus chunks."""
        chunks = self._get_all_chunks_filtered(collection_name, metadata_filter)
        if not chunks:
            return []

        # Simple whitespace/punctuation-based tokenization
        def tokenize(text: str) -> List[str]:
            return text.lower().replace(".", " ").replace(",", " ").replace(";", " ").replace(":", " ").split()

        tokenized_corpus = [tokenize(c["text"]) for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        # Zip, sort, and slice
        scored_chunks = []
        for i, chunk in enumerate(chunks):
            # Normalize BM25 score to [0, 1] rough range for presentation
            raw_score = float(scores[i])
            scored_chunks.append({
                **chunk,
                "score": raw_score
            })
            
        scored_chunks.sort(key=lambda x: x["score"], reverse=True)
        return scored_chunks[:limit]

    def search_hybrid(
        self,
        collection_name: str,
        query: str,
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense Vector search and sparse BM25 search
        using Reciprocal Rank Fusion (RRF).
        """
        # Fetch more candidates from each search to improve RRF quality
        candidate_limit = limit * 2
        
        vector_res = self.search_vector(collection_name, query, limit=candidate_limit, metadata_filter=metadata_filter)
        bm25_res = self.search_bm25(collection_name, query, limit=candidate_limit, metadata_filter=metadata_filter)
        
        if not vector_res and not bm25_res:
            return []
        if not vector_res:
            return bm25_res[:limit]
        if not bm25_res:
            return vector_res[:limit]

        # Apply Reciprocal Rank Fusion
        rrf_scores = {}
        doc_map = {}

        for rank, doc in enumerate(vector_res):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank + rrf_k)

        for rank, doc in enumerate(bm25_res):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank + rrf_k)

        # Sort documents based on RRF scores
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        # Build final outputs
        hybrid_results = []
        for rank, doc_id in enumerate(sorted_ids[:limit]):
            doc = doc_map[doc_id]
            # Standardize score to show RRF metric
            doc["score"] = float(rrf_scores[doc_id])
            doc["retrieval_method"] = "hybrid"
            hybrid_results.append(doc)

        return hybrid_results

# Global retriever instance
retriever = HybridRetriever()
