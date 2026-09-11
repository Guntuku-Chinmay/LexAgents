import logging
import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from backend.app.core.config import settings
from backend.app.models.schemas import Evidence
from backend.app.ingestion.firecrawl import firecrawl_client
from backend.app.ingestion.adapters import get_adapter_for_url

logger = logging.getLogger(__name__)

class WebResearchAgent:
    def search(self, query: str, limit: int = 3, enabled: bool = True) -> List[Evidence]:
        """
        Perform a controlled search on official Indian legal portals via Firecrawl
        or fallback to DuckDuckGo for recent legal updates.
        Returns external evidence with source URLs, authority tiers, and timestamps.
        """
        # Respect configurations
        if not enabled or not settings.WEB_SEARCH_ENABLED:
            logger.info("Web research is disabled. Skipping web search.")
            return []

        logger.info(f"WebResearchAgent searching: '{query}'")
        evidence_list = []

        # 1. Attempt Firecrawl search across official Indian legal domains if enabled
        if settings.FIRECRAWL_ENABLED and firecrawl_client.is_available():
            try:
                allowed_official_domains = [
                    "indiacode.nic.in",
                    "main.sci.gov.in",
                    "sci.gov.in",
                    "judgments.ecourts.gov.in",
                    "sebi.gov.in",
                    "rbi.org.in"
                ]
                firecrawl_results = firecrawl_client.search_and_scrape(
                    query=f"{query} site:gov.in OR site:nic.in",
                    allowed_domains=allowed_official_domains,
                    limit=limit
                )
                if firecrawl_results:
                    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
                    for r in firecrawl_results:
                        url = r.get("url", "")
                        markdown_text = r.get("markdown", "")
                        title = r.get("title", "Official Legal Source")
                        
                        adapter = get_adapter_for_url(url)
                        authority = adapter.authority_tier if adapter else "TIER 2"
                        doc_type = adapter.doc_type if adapter else "statute"
                        source_name = adapter.source_name if adapter else f"Official Portal: {title}"

                        meta = {
                            "url": url,
                            "title": title,
                            "retrieved_at": timestamp,
                            "source_name": source_name,
                            "authority_tier": authority,
                            "doc_type": doc_type
                        }

                        evidence_list.append(
                            Evidence(
                                id=str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
                                text=markdown_text[:1500] if markdown_text else title,
                                source=f"{source_name} ({url})",
                                doc_type=doc_type,
                                score=0.85,
                                metadata=meta,
                                source_id=str(uuid.uuid5(uuid.NAMESPACE_URL, url)),
                                authority_level=authority,
                                retrieval_method="firecrawl_official_source",
                                url=url
                            )
                        )
                    if evidence_list:
                        logger.info(f"Retrieved {len(evidence_list)} official source items via Firecrawl.")
                        return evidence_list[:limit]
            except Exception as e:
                logger.warning(f"Firecrawl official search encountered error: {e}. Falling back to DDGS.")

        # 2. Controlled fallback to DuckDuckGo search
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
