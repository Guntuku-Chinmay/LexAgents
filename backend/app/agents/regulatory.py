import logging
from typing import List, Dict, Any, Optional
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class RegulatoryAgent:
    def search(self, query: str, limit: int = 4, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Evidence]:
        """
        Search regulations, rules, notifications, circulars, and orders from regulatory bodies.
        """
        logger.info(f"RegulatoryAgent searching: '{query}'")
        try:
            # We will scroll through different regulatory metadata types
            evidence_list = []
            for doc_type in ["regulation", "government_circular", "government_notification", "rules"]:
                combined_filter = {"doc_type": doc_type}
                if metadata_filter:
                    combined_filter.update(metadata_filter)
                    
                results = retriever.search_hybrid(
                    collection_name="statutes",
                    query=query,
                    limit=limit,
                    metadata_filter=combined_filter
                )
                
                for r in results:
                    meta = r.get("metadata", {})
                    source_name = meta.get("title") or meta.get("filename") or "Regulatory Material"
                    reg_num = meta.get("regulation") or meta.get("rule") or meta.get("section")
                    if reg_num:
                        if meta.get("doc_type") == "regulation":
                            source_name = f"{source_name} Regulation {reg_num}"
                        elif meta.get("doc_type") == "rules":
                            source_name = f"{source_name} Rule {reg_num}"
                        else:
                            source_name = f"{source_name} Clause/Reg {reg_num}"
                    
                    evidence_list.append(
                        Evidence(
                            id=r["id"],
                            text=r["text"],
                            source=source_name,
                            doc_type=meta.get("doc_type", doc_type),
                            score=r["score"],
                            metadata=meta
                        )
                    )
                if len(evidence_list) >= limit:
                    break
                    
            return evidence_list[:limit]
        except Exception as e:
            logger.error(f"RegulatoryAgent search failed: {e}")
            return []

regulatory_agent = RegulatoryAgent()
