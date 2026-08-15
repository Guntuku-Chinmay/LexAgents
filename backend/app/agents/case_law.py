import logging
from typing import List, Dict, Any, Optional
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class CaseLawAgent:
    def search(self, query: str, limit: int = 4, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Evidence]:
        """
        Search the case-law corpus and return structured evidence list.
        """
        logger.info(f"CaseLawAgent searching: '{query}'")
        try:
            results = retriever.search_hybrid(
                collection_name="cases",
                query=query,
                limit=limit,
                metadata_filter=metadata_filter
            )
            
            evidence_list = []
            for r in results:
                meta = r.get("metadata", {})
                source_name = meta.get("case_name") or meta.get("filename") or "Unknown Case"
                if "court" in meta and "date" in meta:
                    source_name = f"{source_name} ({meta['court']}, {meta['date'].split('-')[0]})"
                
                evidence_list.append(
                    Evidence(
                        id=r["id"],
                        text=r["text"],
                        source=source_name,
                        doc_type="case",
                        score=r["score"],
                        metadata=meta
                    )
                )
            return evidence_list
        except Exception as e:
            logger.error(f"CaseLawAgent search failed: {e}")
            return []

case_law_agent = CaseLawAgent()
