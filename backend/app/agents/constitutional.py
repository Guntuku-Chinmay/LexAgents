import logging
from typing import List, Dict, Any, Optional
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class ConstitutionalResearchAgent:
    def search(self, query: str, limit: int = 4, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Evidence]:
        """
        Search the constitutional provisions of the corpus (Constitution of India, Amendments).
        """
        logger.info(f"ConstitutionalResearchAgent searching: '{query}'")
        try:
            # Enforce constitutional metadata filters
            combined_filter = {"doc_type": "constitutional"}
            if metadata_filter:
                combined_filter.update(metadata_filter)
                
            results = retriever.search_hybrid(
                collection_name="statutes",
                query=query,
                limit=limit,
                metadata_filter=combined_filter
            )
            
            # If no direct constitutional results, check constitutional amendments
            if not results:
                combined_filter = {"doc_type": "constitutional_amendment"}
                if metadata_filter:
                    combined_filter.update(metadata_filter)
                results = retriever.search_hybrid(
                    collection_name="statutes",
                    query=query,
                    limit=limit,
                    metadata_filter=combined_filter
                )

            evidence_list = []
            for r in results:
                meta = r.get("metadata", {})
                source_name = meta.get("title") or meta.get("filename") or "Constitution of India"
                article = meta.get("article")
                if article:
                    source_name = f"{source_name} Article {article}"
                
                evidence_list.append(
                    Evidence(
                        id=r["id"],
                        text=r["text"],
                        source=source_name,
                        doc_type=meta.get("doc_type", "constitutional"),
                        score=r["score"],
                        metadata=meta
                    )
                )
            return evidence_list
        except Exception as e:
            logger.error(f"ConstitutionalResearchAgent search failed: {e}")
            return []

constitutional_research_agent = ConstitutionalResearchAgent()
