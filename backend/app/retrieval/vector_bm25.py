import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.llm import generate_embeddings

logger = logging.getLogger(__name__)

def extract_identifiers_from_query(query: str) -> Dict[str, Any]:
    """Helper to extract exact legal identifiers from a natural language query for query boosting."""
    identifiers = {}
    
    # Articles (e.g. Article 21, Art. 21)
    art_match = re.search(r'\b(?:Article|Art\.)\s*([A-Za-z0-9\(\)]+)\b', query, re.IGNORECASE)
    if art_match:
        identifiers["article"] = art_match.group(1)
        
    # Sections (e.g. Section 138, Section 420)
    sec_match = re.search(r'\b(?:Section|Sec\.|§)\s*([A-Za-z0-9\(\)]+)\b', query, re.IGNORECASE)
    if sec_match:
        identifiers["section"] = sec_match.group(1)
        
    # Regulations (e.g. Regulation 3, Reg 4)
    reg_match = re.search(r'\b(?:Regulation|Reg\.|Reg)\s*([A-Za-z0-9\(\)]+)\b', query, re.IGNORECASE)
    if reg_match:
        identifiers["regulation"] = reg_match.group(1)

    # Rules (e.g. Rule 4)
    rule_match = re.search(r'\b(?:Rule)\s*([A-Za-z0-9\(\)]+)\b', query, re.IGNORECASE)
    if rule_match:
        identifiers["rule"] = rule_match.group(1)
        
    return identifiers

class HybridRetriever:
    def __init__(self, storage_path: str = settings.QDRANT_STORAGE_PATH):
        if settings.QDRANT_URL:
            logger.info(f"Connecting to remote Qdrant at: {settings.QDRANT_URL}")
            self.client = QdrantClient(
                url=settings.QDRANT_URL,
                api_key=settings.QDRANT_API_KEY
            )
        else:
            logger.info(f"Connecting to local Qdrant storage at: {storage_path}")
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
           "id": str,
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
            if val is not None:
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
        
        scroll_results, _ = self.client.scroll(
            collection_name=collection_name,
            scroll_filter=q_filter,
            limit=10000,
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

        def tokenize(text: str) -> List[str]:
            return text.lower().replace(".", " ").replace(",", " ").replace(";", " ").replace(":", " ").split()

        tokenized_corpus = [tokenize(c["text"]) for c in chunks]
        bm25 = BM25Okapi(tokenized_corpus)
        
        tokenized_query = tokenize(query)
        scores = bm25.get_scores(tokenized_query)
        
        scored_chunks = []
        for i, chunk in enumerate(chunks):
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
        using Reciprocal Rank Fusion (RRF) with exact identifier boosting.
        """
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

        # Exact identifier boosting
        query_idents = extract_identifiers_from_query(query)
        if query_idents:
            for doc_id, doc in doc_map.items():
                doc_meta = doc.get("metadata", {})
                boost = 0.0
                for field, val in query_idents.items():
                    if doc_meta.get(field) == val:
                        # Match found! Boost the score
                        boost += 0.5
                if boost > 0.0:
                    rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + boost

        # Sort documents based on RRF scores
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        hybrid_results = []
        for rank, doc_id in enumerate(sorted_ids[:limit]):
            doc = doc_map[doc_id]
            doc["score"] = float(rrf_scores[doc_id])
            doc["retrieval_method"] = "hybrid"
            hybrid_results.append(doc)

        return hybrid_results

# Global retriever instance
retriever = HybridRetriever()
