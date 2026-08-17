import logging
from typing import List, Dict, Any, Optional
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class StatuteAgent:
    def search(self, query: str, limit: int = 4, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Evidence]:
        """
        Search acts, statutes, sections, and rules, and return structured evidence.
        """
        logger.info(f"StatuteAgent searching: '{query}'")
        try:
            results = retriever.search_hybrid(
                collection_name="statutes",
                query=query,
                limit=limit,
                metadata_filter=metadata_filter
            )
            
            evidence_list = []
            for r in results:
                meta = r.get("metadata", {})
                source_name = meta.get("title") or meta.get("filename") or "Statute Document"
                section = meta.get("section")
                if section:
                    source_name = f"{source_name} § {section}"
                
                evidence_list.append(
                    Evidence(
                        id=r["id"],
                        text=r["text"],
                        source=source_name,
                        doc_type=meta.get("doc_type", "central_act"),
                        score=r["score"],
                        metadata=meta,
                        source_id=meta.get("document_id"),
                        authority_level=meta.get("authority_level", "TIER 2"),
                        retrieval_method=r.get("retrieval_method", "hybrid"),
                        url=meta.get("source_url")
                    )
                )
            return evidence_list
        except Exception as e:
            logger.error(f"StatuteAgent search failed: {e}")
            return []

statute_agent = StatuteAgent()
