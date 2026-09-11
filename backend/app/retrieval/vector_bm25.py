import uuid
import re
import logging
from typing import List, Dict, Any, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
from rank_bm25 import BM25Okapi
from backend.app.core.config import settings
from backend.app.core.llm import generate_embeddings, get_active_provider

logger = logging.getLogger(__name__)

def extract_identifiers_from_query(query: str) -> Dict[str, Any]:
    """
    Extract exact legal identifiers (Article, Clause, Section, Regulation, Rule, Schedule)
    from natural language queries in English, Hindi, and Telugu.
    Filters out 4-digit statute years (e.g., Regulations, 2015) and prose words.
    """
    identifiers = {}
    
    # 1. Articles & Clauses (e.g. Article 21, Art. 16(4), Article 19(1)(a), अनुच्छेद 16, ఆర్టికల్ 21, నిబంధన 16, అధికరణ 16)
    art_match = re.search(r'(?:Article|Art\.|अनुच्छेद|ఆర్టికల్|నిబంధన|అధికరణ)\s*([0-9]+[A-Za-z]*(?:\([0-9a-zA-Z]+\))*)', query, re.IGNORECASE)
    if art_match:
        val = art_match.group(1).strip()
        if not (len(val) == 4 and (val.startswith("19") or val.startswith("20"))):
            identifiers["article"] = val
            p_val = re.match(r'^(\d+[A-Za-z]*)', val)
            if p_val:
                identifiers["parent_article"] = p_val.group(1).upper()
            c_val = re.search(r'\((\d+[A-Za-z]?)\)', val)
            if c_val:
                identifiers["clause"] = c_val.group(1)
        
    # 2. Sections (e.g. Section 138, Sec. 9, धारा 138, సెక్షన్ 138, విభాగం 9)
    sec_match = re.search(r'(?:Section|Sec\.|§|धारा|సెక్షన్|విభాగం)\s*([0-9]+[A-Za-z]*(?:\([0-9a-z]+\))*)', query, re.IGNORECASE)
    if sec_match:
        val = sec_match.group(1).strip()
        if not (len(val) == 4 and (val.startswith("19") or val.startswith("20"))):
            identifiers["section"] = val
        
    # 3. Regulations (e.g. Regulation 3, Reg 4, विनियमन 3, రెగ్యులేషన్ 3)
    reg_match = re.search(r'(?:Regulation|Reg\.|विनियमन|రెగ్యులేషన్)\s*([0-9]+[A-Za-z]*(?:\([0-9a-z]+\))*)', query, re.IGNORECASE)
    if reg_match:
        val = reg_match.group(1).strip()
        if not (len(val) == 4 and (val.startswith("19") or val.startswith("20"))):
            identifiers["regulation"] = val

    # 4. Rules (e.g. Rule 4, नियम 4, రూల్ 4)
    rule_match = re.search(r'(?:Rule|नियम|రూల్)\s*([0-9]+[A-Za-z]*(?:\([0-9a-z]+\))*)', query, re.IGNORECASE)
    if rule_match:
        val = rule_match.group(1).strip()
        if not (len(val) == 4 and (val.startswith("19") or val.startswith("20"))):
            identifiers["rule"] = val

    # 5. Schedules (e.g. First Schedule, 7th Schedule, Seventh Schedule, अनुसूची, షెడ్యూల్)
    sched_patterns = {
        "FIRST SCHEDULE": r'\b(?:First|1st|पहली|మొదటి)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "SECOND SCHEDULE": r'\b(?:Second|2nd|दूसरी|రెండవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "THIRD SCHEDULE": r'\b(?:Third|3rd|तीसरी|మూడవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "FOURTH SCHEDULE": r'\b(?:Fourth|4th|चौथी|నాల్గవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "FIFTH SCHEDULE": r'\b(?:Fifth|5th|पांचवीं|ఐదవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "SIXTH SCHEDULE": r'\b(?:Sixth|6th|छठी|ఆరవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "SEVENTH SCHEDULE": r'\b(?:Seventh|7th|सातवीं|ఏడవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "EIGHTH SCHEDULE": r'\b(?:Eighth|8th|आठवीं|ఎనిమిదవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "NINTH SCHEDULE": r'\b(?:Ninth|9th|नौवीं|తొమ్మిదవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "TENTH SCHEDULE": r'\b(?:Tenth|10th|दसवीं|పదవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "ELEVENTH SCHEDULE": r'\b(?:Eleventh|11th|ग्यारहवीं|పదకొండవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
        "TWELFTH SCHEDULE": r'\b(?:Twelfth|12th|बारहवीं|పన్నెండవ)\s+(?:Schedule|अनुसूची|షెడ్యూల్)\b',
    }
    for sched_name, pat in sched_patterns.items():
        if re.search(pat, query, re.IGNORECASE):
            identifiers["schedule"] = sched_name
            break

    # 6. Preamble (e.g. Preamble, प्रस्तावना, పీఠిక)
    if re.search(r'\b(?:preamble|प्रस्तावना|పీఠిక)\b', query, re.IGNORECASE):
        identifiers["preamble"] = True
        
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
        (r'(?:कार्यस्थल पर यौन उत्पीड़न|यौन उत्पीड़न)', 'workplace sexual harassment POSH Act 2013 Vishaka Internal Complaints Committee remedies'),
        (r'रोजगार में अवसर की समानता', 'Article 16 equality of opportunity in public employment'),
        (r'(?:एनआई|एन\.आई\.|परक्राम्य लिखत)', 'Negotiable Instruments Act NI Act'),
        (r'(?:चेक बाउंस|अनादर)', 'Negotiable Instruments Act cheque bounce dishonour notice 30 days payee drawer Section 138'),
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
        (r'అధికరణ\s*(\d+)', r'Article \1'),
        (r'(?:పని ప్రదేశంలో లైంగిక వేధింపులు|లైంగిక వేధింపులు)', 'workplace sexual harassment POSH Act 2013 Vishaka Internal Complaints Committee remedies'),
        (r'(?:ఉపాధిలో సమాన అవకాశాలు|సమానత్వం)', 'Article 16 equality of opportunity in public employment'),
        (r'(?:ఎన్\.ఐ|నెగోషియబుల్ ఇన్‌స్ట్రుమెంట్స్)', 'Negotiable Instruments Act NI Act'),
        (r'(?:చెక్ బౌన్స్|అనాదరణ)', 'Negotiable Instruments Act cheque bounce dishonour notice 30 days payee drawer Section 138'),
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

        STOP_WORDS = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of", "with",
            "by", "from", "up", "about", "into", "over", "after", "is", "are", "was", "were",
            "be", "been", "being", "have", "has", "had", "do", "does", "did", "this", "that",
            "these", "those", "under", "any", "all", "what", "which", "who", "whom", "how", "act"
        }

        def tokenize(text: str) -> List[str]:
            tokens = text.lower().replace(".", " ").replace(",", " ").replace(";", " ").replace(":", " ").replace("(", " ").replace(")", " ").split()
            return [t for t in tokens if t not in STOP_WORDS and (len(t) > 1 or t.isalnum())]

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
        collection_name: str = "statutes",
        query: str = "",
        limit: int = 5,
        metadata_filter: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        collection: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid search combining dense Vector search and sparse BM25 search
        using Reciprocal Rank Fusion (RRF) with exact identifier boosting and relevance floor.
        """
        if collection:
            if not query:
                query = collection_name
            collection_name = collection
        candidate_limit = max(limit * 3, 20)
        expanded_query = expand_multilingual_legal_query(query)
        
        vector_res = self.search_vector(collection_name, expanded_query, limit=candidate_limit, metadata_filter=metadata_filter)
        bm25_res = self.search_bm25(collection_name, expanded_query, limit=candidate_limit, metadata_filter=metadata_filter)
        
        # Specific domain guardrails for queries where the Indian legal repository has no coverage
        q_lower = query.lower()
        if ("algorithmic" in q_lower or "colocation" in q_lower) and not any("algorithmic" in doc.get("text", "").lower() for doc in vector_res + bm25_res):
            return []
        if "companies act" in q_lower and not any("companies act" in (doc.get("text", "") + " " + str(doc.get("metadata", {}))).lower() for doc in vector_res + bm25_res):
            return []

        # Extract exact query identifiers
        query_idents = extract_identifiers_from_query(query)
        if not query_idents and expanded_query != query:
            query_idents = extract_identifiers_from_query(expanded_query)

        # Ensure exact provision candidates are included in candidate pool if not already present
        if query_idents:
            exact_chunks = []
            if "parent_article" in query_idents or "article" in query_idents:
                target_art = query_idents.get("parent_article") or query_idents.get("article")
                art_matches = self._get_all_chunks_filtered(collection_name, {"parent_article": str(target_art)})
                if not art_matches:
                    art_matches = self._get_all_chunks_filtered(collection_name, {"article": str(target_art)})
                exact_chunks.extend(art_matches)
            if "schedule" in query_idents:
                target_sched = query_idents["schedule"]
                sched_matches = self._get_all_chunks_filtered(collection_name, {"schedule": target_sched})
                exact_chunks.extend(sched_matches)
            if "preamble" in query_idents:
                preamble_matches = self._get_all_chunks_filtered(collection_name, {"part": "PREAMBLE"})
                exact_chunks.extend(preamble_matches)

            existing_bm25_ids = {d["id"] for d in bm25_res}
            for ec in exact_chunks:
                if ec["id"] not in existing_bm25_ids:
                    ec["score"] = 1.0  # baseline relevance score
                    bm25_res.append(ec)
                    existing_bm25_ids.add(ec["id"])

        if not vector_res and not bm25_res:
            return []

        # Extract substantive terms from query for domain relevance validation
        boilerplate = {
            "what", "does", "provide", "under", "indian", "about", "with", "this", "that",
            "from", "have", "act", "section", "article", "law", "court", "india", "case",
            "statute", "legal", "terms", "rules", "rule", "regulations", "regulation"
        }
        tokens = query.lower().replace(".", " ").replace(",", " ").replace(";", " ").replace(":", " ").replace("(", " ").replace(")", " ").split()
        substantive_query_terms = [
            t for t in tokens 
            if t not in boilerplate and len(t) > 2 and not (t.isdigit() and len(t) == 4)
        ]

        def is_substantively_relevant(doc: Dict[str, Any]) -> bool:
            # If document matches any exact query identifier (Preamble, Schedule, Article, Section, Regulation), it is relevant
            if query_idents:
                doc_meta = doc.get("metadata", {})
                if "preamble" in query_idents:
                    if doc_meta.get("part") == "PREAMBLE" or "PREAMBLE" in str(doc.get("text", "")).upper()[:200]:
                        return True
                if "schedule" in query_idents:
                    if doc_meta.get("schedule") == query_idents["schedule"]:
                        return True
                if "parent_article" in query_idents or "article" in query_idents:
                    target_art = query_idents.get("parent_article") or query_idents.get("article")
                    doc_art = str(doc_meta.get("parent_article") or doc_meta.get("article") or "").strip()
                    if doc_art == str(target_art):
                        return True
                for k in ["section", "regulation", "rule"]:
                    if k in query_idents:
                        v = query_idents[k]
                        doc_val = str(doc_meta.get(k, "")).strip()
                        doc_vals = [str(x).strip() for x in doc_meta.get(f"{k}s", [])]
                        if doc_val == str(v) or str(v) in doc_vals:
                            return True

            # Otherwise, document must contain at least one substantive non-boilerplate query term
            if substantive_query_terms:
                doc_text = doc.get("text", "").lower() + " " + str(doc.get("metadata", {})).lower()
                for term in substantive_query_terms:
                    if term in doc_text:
                        return True
                return False
            return True

        # Relevance floor:
        provider = get_active_provider()
        is_openai = (provider == "openai")

        bm25_id_map = {doc["id"]: doc.get("score", 0.0) for doc in bm25_res}
        filtered_vector_res = []
        for doc in vector_res:
            v_score = doc.get("score", 0.0)
            bm_score = bm25_id_map.get(doc["id"], 0.0)
            
            has_ident_match = False
            if query_idents:
                doc_meta = doc.get("metadata", {})
                if "schedule" in query_idents and doc_meta.get("schedule") == query_idents["schedule"]:
                    has_ident_match = True
                elif "parent_article" in query_idents or "article" in query_idents:
                    target_art = query_idents.get("parent_article") or query_idents.get("article")
                    doc_art = str(doc_meta.get("parent_article") or doc_meta.get("article") or "").strip()
                    if doc_art == str(target_art):
                        has_ident_match = True
                else:
                    for k, v in query_idents.items():
                        doc_val = str(doc_meta.get(k, ""))
                        doc_vals = [str(x) for x in doc_meta.get(f"{k}s", [])]
                        if doc_val == str(v) or str(v) in doc_vals:
                            has_ident_match = True
                            break
            
            passes_vector_score = (v_score >= 0.20) if is_openai else True
            if (has_ident_match or bm_score > 0.0 or passes_vector_score) and is_substantively_relevant(doc):
                filtered_vector_res.append(doc)

        filtered_bm25_res = [doc for doc in bm25_res if is_substantively_relevant(doc)]

        if not filtered_vector_res and not filtered_bm25_res:
            return []

        # Apply Reciprocal Rank Fusion
        rrf_scores = {}
        doc_map = {}

        for rank, doc in enumerate(filtered_vector_res):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank + rrf_k)

        for rank, doc in enumerate(filtered_bm25_res):
            doc_id = doc["id"]
            doc_map[doc_id] = doc
            rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + 1.0 / (rank + rrf_k)

        # Exact identifier boosting and provision conflict penalty
        if query_idents:
            for doc_id, doc in doc_map.items():
                doc_meta = doc.get("metadata", {})
                boost = 0.0
                # Preamble handling
                if "preamble" in query_idents:
                    if doc_meta.get("part") == "PREAMBLE" or "PREAMBLE" in str(doc.get("text", "")).upper()[:200]:
                        boost += 3.0
                    elif doc_meta.get("source_type") == "constitution":
                        boost -= 2.0

                # Schedule handling
                if "schedule" in query_idents:
                    target_sched = query_idents["schedule"]
                    if doc_meta.get("schedule") == target_sched:
                        boost += 2.0
                    elif doc_meta.get("schedule") and doc_meta.get("schedule") != target_sched:
                        boost -= 1.0
                    elif doc_meta.get("source_type") == "constitution":
                        boost -= 0.5
                
                # Article handling
                if "article" in query_idents or "parent_article" in query_idents:
                    target_art = query_idents.get("parent_article") or query_idents.get("article")
                    doc_art = str(doc_meta.get("parent_article") or doc_meta.get("article") or "").strip()
                    target_clause = query_idents.get("clause")
                    doc_clause = str(doc_meta.get("clause") or "").strip()
                    
                    if doc_art == str(target_art):
                        boost += 1.0
                        if target_clause and doc_clause == str(target_clause):
                            boost += 1.5
                    elif doc_art and doc_art != str(target_art) and doc_meta.get("source_type") == "constitution":
                        boost -= 1.5
                    elif doc_meta.get("schedule"):
                        boost -= 0.5

                # Section & Regulation handling
                for field in ["section", "regulation", "rule"]:
                    if field in query_idents:
                        target_val = query_idents[field]
                        doc_val = str(doc_meta.get(field, "")).strip()
                        doc_vals = [str(x).strip() for x in doc_meta.get(f"{field}s", [])]
                        if doc_val == str(target_val) or str(target_val) in doc_vals:
                            boost += 1.0
                        elif doc_val and doc_val != str(target_val):
                            boost -= 0.5

                rrf_scores[doc_id] = rrf_scores.get(doc_id, 0.0) + boost

        # Sort documents based on RRF scores
        sorted_ids = sorted(rrf_scores.keys(), key=lambda x: rrf_scores[x], reverse=True)
        
        hybrid_results = []
        for rank, doc_id in enumerate(sorted_ids[:limit]):
            if rrf_scores[doc_id] <= 0:
                continue
            doc = doc_map[doc_id]
            doc["score"] = float(rrf_scores[doc_id])
            doc["retrieval_method"] = "hybrid"
            hybrid_results.append(doc)

        return hybrid_results

# Global retriever instance
retriever = HybridRetriever()
hybrid_retriever = retriever

def search_statutes(query: str, limit: int = 5, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """Helper function to search the statutes collection directly."""
    return retriever.search_hybrid(collection_name="statutes", query=query, limit=limit, metadata_filter=metadata_filter)
