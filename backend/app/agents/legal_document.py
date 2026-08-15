import logging
from typing import List, Dict, Any, Optional
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class LegalDocumentAgent:
    def search(self, query: str, limit: int = 4, metadata_filter: Optional[Dict[str, Any]] = None) -> List[Evidence]:
        """
        Search user-uploaded legal documents (contracts, policies, agreements) and return evidence.
        """
        logger.info(f"LegalDocumentAgent searching: '{query}'")
        try:
            results = retriever.search_hybrid(
                collection_name="legal_documents",
                query=query,
                limit=limit,
                metadata_filter=metadata_filter
            )
            
            evidence_list = []
            for r in results:
                meta = r.get("metadata", {})
                source_name = meta.get("filename") or "Uploaded Legal Document"
                section = meta.get("section")
                if section:
                    source_name = f"{source_name} Section {section}"
                
                evidence_list.append(
                    Evidence(
                        id=r["id"],
                        text=r["text"],
                        source=source_name,
                        doc_type="user_upload",
                        score=r["score"],
                        metadata=meta
                    )
                )
            return evidence_list
        except Exception as e:
            logger.error(f"LegalDocumentAgent search failed: {e}")
            return []

legal_document_agent = LegalDocumentAgent()
