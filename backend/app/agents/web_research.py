import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from backend.app.core.config import settings
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class WebResearchAgent:
    def search(self, query: str, limit: int = 3, enabled: bool = True) -> List[Evidence]:
        """
        Perform a controlled search on DuckDuckGo for recent legal updates.
        Returns external evidence with source URLs and timestamp.
        """
        # Respect configurations
        if not enabled or not settings.WEB_SEARCH_ENABLED:
            logger.info("Web research is disabled. Skipping web search.")
            return []

        logger.info(f"WebResearchAgent searching: '{query}'")
        evidence_list = []
        try:
            with DDGS() as ddgs:
                results = list(ddgs.text(query, max_results=limit))
                
            timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
            for r in results:
                title = r.get("title", "Web Resource")
                href = r.get("href", "")
                body = r.get("body", "")
                
                # Metadata to track web source context
                meta = {
                    "url": href,
                    "title": title,
                    "retrieved_at": timestamp,
                    "doc_type": "web"
                }
                
                evidence_list.append(
                    Evidence(
                        id=str(uuid.uuid5(uuid.NAMESPACE_URL, href)),
                        text=body,
                        source=f"Web: {title} ({href})",
                        doc_type="external_source",
                        score=0.7,
                        metadata=meta,
                        source_id=str(uuid.uuid5(uuid.NAMESPACE_URL, href)),
                        authority_level="TIER 4",
                        retrieval_method="web_search",
                        url=href
                    )
                )
        except Exception as e:
            logger.error(f"WebResearchAgent search failed (possibly offline or rate limited): {e}")
            # Non-blocking, return empty list gracefully
            return []

        return evidence_list

web_research_agent = WebResearchAgent()
