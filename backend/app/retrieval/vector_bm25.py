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
    """Helper to extract exact legal identifiers from natural language queries (English, Hindi, Telugu) for query boosting."""
    identifiers = {}
    
    # Articles (e.g. Article 21, Art. 21, अनुच्छेद 21, ఆర్టికల్ 21)
    art_match = re.search(r'(?:Article|Art\.|अनुच्छेद|ఆర్టికల్|నిబంధన)\s*([A-Za-z0-9\(\)]+)', query, re.IGNORECASE)
    if art_match:
        identifiers["article"] = art_match.group(1)
        
    # Sections (e.g. Section 138, Section 420, धारा 138, సెక్షన్ 138)
    sec_match = re.search(r'(?:Section|Sec\.|§|धारा|సెక్షన్|విభాగం)\s*([A-Za-z0-9\(\)]+)', query, re.IGNORECASE)
    if sec_match:
        identifiers["section"] = sec_match.group(1)
        
    # Regulations (e.g. Regulation 3, Reg 4, विनियमन 3, రెగ్యులేషన్ 3)
    reg_match = re.search(r'(?:Regulation|Reg\.|विनियमन|రెగ్యులేషన్)\s*([A-Za-z0-9\(\)]+)', query, re.IGNORECASE)
    if reg_match:
        identifiers["regulation"] = reg_match.group(1)

    # Rules (e.g. Rule 4, नियम 4, రూల్ 4)
    rule_match = re.search(r'(?:Rule|नियम|రూల్)\s*([A-Za-z0-9\(\)]+)', query, re.IGNORECASE)
    if rule_match:
        identifiers["rule"] = rule_match.group(1)
        
    return identifiers


def expand_multilingual_legal_query(query: str) -> str:
    """
    Expand Hindi and Telugu legal queries with canonical English statutory/legal equivalents
    so that sparse BM25 and dense vector search ground accurately against the English Indian legal corpus.
    Preserves original query and appends matched canonical terms.
    """
    has_indic = any('\u0900' <= c <= '\u097F' or '\u0C00' <= c <= '\u0C7F' for c in query)
    if not has_indic:
        return query

    expansions: List[str] = []

    # Hindi legal mappings
    hi_rules = [
        (r'धारा\s*(\d+)', r'Section \1'),
        (r'अनुच्छेद\s*(\d+)', r'Article \1'),
        (r'(?:एनआई|एन\.आई\.|परक्राम्य लिखत)', 'Negotiable Instruments Act NI Act'),
        (r'(?:चेक बाउंस|अनादर)', 'Negotiable Instruments Act cheque bounce dishonour notice 30 days payee drawer'),
        (r'(?:भारतीय दंड संहिता|आईपीसी)', 'Indian Penal Code IPC'),
        (r'(?:सर्वोच्च न्यायालय|उच्चतम न्यायालय)', 'Supreme Court'),
        (r'(?:निजता|गोपनीयता)', 'privacy surveillance fundamental right Article 21'),
        (r'मौलिक अधिकार', 'fundamental rights Constitution of India'),
        (r'जमानत', 'bail criminal procedure'),
        (r'(?:किराया|पट्टा|पट्टेदार)', 'lease agreement notice eviction landlord tenant clause'),
        (r'सेबी', 'SEBI insider trading UPSI'),
        (r'आरबीआई', 'RBI circular digital lending regulations'),
    ]

    # Telugu legal mappings
    te_rules = [
        (r'సెక్షన్\s*(\d+)', r'Section \1'),
        (r'విభాగం\s*(\d+)', r'Section \1'),
        (r'ఆర్టికల్\s*(\d+)', r'Article \1'),
        (r'నిబంధన\s*(\d+)', r'Article \1'),
        (r'(?:ఎన్\.ఐ|నెగోషియబుల్ ఇన్‌స్ట్రుమెంట్స్)', 'Negotiable Instruments Act NI Act'),
        (r'(?:చెక్ బౌన్స్|అనాదరణ)', 'Negotiable Instruments Act cheque bounce dishonour notice 30 days payee drawer'),
        (r'(?:ఐపీసీ|భారతీయ శిక్షా స్మృతి)', 'Indian Penal Code IPC'),
        (r'సుప్రీం కోర్టు', 'Supreme Court'),
        (r'(?:గోప్యత|గోప్యతా హక్కు)', 'privacy surveillance fundamental right Article 21'),
        (r'ప్రాథమిక హక్కులు', 'fundamental rights Constitution of India'),
        (r'బెయిల్', 'bail criminal procedure'),
        (r'(?:అద్దె|లీజు)', 'lease agreement notice eviction landlord tenant clause'),
        (r'సెబీ', 'SEBI insider trading UPSI'),
        (r'ఆర్బీఐ', 'RBI circular digital lending regulations'),
    ]

    for pattern, replacement in hi_rules + te_rules:
        if re.search(pattern, query, re.IGNORECASE):
            if r'\1' in replacement:
                expanded = re.sub(pattern, replacement, query)
                expansions.append(expanded)
            else:
                expansions.append(replacement)

    if expansions:
        return f"{query} {' '.join(expansions)}"
    return query

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
    def _get_qdrant_filter(self, metadata_filter: Optional[Dict[str, Any]], query: Optional[str] = None) -> Optional[Filter]:
        """Convert a simple dict filter into Qdrant FieldConditions, adding active status filter by default."""
        conditions = []
        if metadata_filter:
            for key, val in metadata_filter.items():
                if val is not None:
                    conditions.append(
                        FieldCondition(
                            key=f"metadata.{key}",
                            match=MatchValue(value=val)
                        )
                    )
        
        # Apply active status filter if not a historical query and status is not explicitly filtered
        has_status_filter = any(c.key == "metadata.status" for c in conditions) if conditions else False
        is_historical = False
        if query:
            is_historical = bool(re.search(
                r'(history|historical|supersede|superseded|repeal|repealed|older|previous|prior to|amended|former)', 
                query, 
                re.IGNORECASE
            ))
            
        if not is_historical and not has_status_filter:
            exclude_statuses = ["SUPERSEDED", "AMENDED", "REPEALED", "ARCHIVED"]
            must_not_conditions = []
            for estatus in exclude_statuses:
                must_not_conditions.append(
                    FieldCondition(
                        key="metadata.status",
                        match=MatchValue(value=estatus)
                    )
                )
            if conditions:
                return Filter(must=conditions, must_not=must_not_conditions)
            else:
                return Filter(must_not=must_not_conditions)

        if conditions:
            return Filter(must=conditions)
        return None

    def update_document_status_payload(self, document_id: str, status: str):
        """Update payload status for all points belonging to a document_id in Qdrant."""
        try:
            collections = [c.name for c in self.client.get_collections().collections]
        except Exception:
            collections = ["cases", "statutes", "legal_documents"]
            
        for col in collections:
            try:
                q_filter = Filter(must=[FieldCondition(key="metadata.document_id", match=MatchValue(value=document_id))])
                scroll_res, _ = self.client.scroll(
                    collection_name=col,
                    scroll_filter=q_filter,
                    limit=10000,
                    with_payload=True,
                    with_vectors=False
                )
                if scroll_res:
                    for p in scroll_res:
                        payload = p.payload
                        if "metadata" in payload:
                            payload["metadata"]["status"] = status
                            self.client.set_payload(
                                collection_name=col,
                                payload=payload,
                                points=[p.id]
                            )
            except Exception as e:
                logger.warning(f"Failed to update status payload in collection {col}: {e}")

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
        q_filter = self._get_qdrant_filter(metadata_filter, query)
        
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

    def _get_all_chunks_filtered(
        self, 
        collection_name: str, 
        metadata_filter: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get all chunks from a collection matching metadata filters to build a local BM25 index."""
        self.init_collection(collection_name)
        q_filter = self._get_qdrant_filter(metadata_filter, query)
        
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
        expanded_query = expand_multilingual_legal_query(query)
        
        vector_res = self.search_vector(collection_name, expanded_query, limit=candidate_limit, metadata_filter=metadata_filter)
        bm25_res = self.search_bm25(collection_name, expanded_query, limit=candidate_limit, metadata_filter=metadata_filter)
        
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

        # Exact identifier boosting (checks both original Indic query and expanded statutory terms)
        query_idents = extract_identifiers_from_query(query)
        if not query_idents and expanded_query != query:
            query_idents = extract_identifiers_from_query(expanded_query)
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
