import logging
import httpx
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

logger = logging.getLogger(__name__)

class FirecrawlClient:
    """
    Firecrawl API Client for web scraping and crawling official legal sources.
    Includes budget controls, timeouts, domain filtering, and graceful degradation.
    """
    def __init__(
        self,
        api_key: Optional[str] = settings.FIRECRAWL_API_KEY,
        base_url: str = settings.FIRECRAWL_BASE_URL,
        enabled: bool = settings.FIRECRAWL_ENABLED,
        timeout: float = settings.FIRECRAWL_TIMEOUT,
        max_pages_per_run: int = settings.FIRECRAWL_MAX_PAGES_PER_RUN,
        max_pages_per_source: int = settings.FIRECRAWL_MAX_PAGES_PER_SOURCE
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.enabled = enabled and bool(api_key)
        self.timeout = timeout
        self.max_pages_per_run = max_pages_per_run
        self.max_pages_per_source = max_pages_per_source
        self._pages_crawled_this_run = 0

    def is_available(self) -> bool:
        """Check if Firecrawl is configured and enabled."""
        return self.enabled and bool(self.api_key)

    def scrape_url(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Scrape a single URL using Firecrawl /v1/scrape.
        Returns parsed markdown content and metadata, or None on failure.
        """
        if not self.is_available():
            logger.info("Firecrawl is disabled or API key missing. Skipping scrape.")
            return None

        if self._pages_crawled_this_run >= self.max_pages_per_run:
            logger.warning(f"Firecrawl budget reached ({self.max_pages_per_run} pages). Skipping {url}")
            return None

        endpoint = f"{self.base_url}/v1/scrape"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "url": url,
            "formats": ["markdown"],
            "onlyMainContent": True
        }

        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                
            if response.status_code == 200:
                self._pages_crawled_this_run += 1
                data = response.json()
                result_data = data.get("data", {})
                return {
                    "url": url,
                    "markdown": result_data.get("markdown", ""),
                    "title": result_data.get("metadata", {}).get("title", ""),
                    "description": result_data.get("metadata", {}).get("description", ""),
                    "status_code": response.status_code
                }
            elif response.status_code == 429:
                logger.warning(f"Firecrawl rate limit (429) encountered for {url}.")
                return None
            else:
                logger.warning(f"Firecrawl returned status {response.status_code} for {url}: {response.text[:100]}")
                return None
        except Exception as e:
            logger.error(f"Firecrawl scrape failed for {url}: {e}")
            return None

    def search(self, query: str, allowed_domains: Optional[List[str]] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """Convenience alias for search_and_scrape."""
        return self.search_and_scrape(query, allowed_domains, limit)

    def search_and_scrape(self, query: str, allowed_domains: Optional[List[str]] = None, limit: int = 3) -> List[Dict[str, Any]]:
        """
        Search and scrape pages matching a query, restricted to allowed official domains.
        Gracefully degrades if API is unavailable.
        """
        if not self.is_available():
            logger.info("Firecrawl is disabled or unconfigured. Cannot perform search_and_scrape.")
            return []

        endpoint = f"{self.base_url}/v1/search"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload: Dict[str, Any] = {
            "query": query,
            "limit": min(limit, self.max_pages_per_source),
            "scrapeOptions": {"formats": ["markdown"]}
        }
        
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(endpoint, json=payload, headers=headers)
                
            if response.status_code == 200:
                data = response.json()
                items = data.get("data", [])
                results = []
                for item in items:
                    url = item.get("url", "")
                    # Domain validation
                    if allowed_domains:
                        if not any(domain in url for domain in allowed_domains):
                            continue
                    results.append({
                        "url": url,
                        "markdown": item.get("markdown", ""),
                        "title": item.get("title", ""),
                        "description": item.get("description", "")
                    })
                    self._pages_crawled_this_run += 1
                    if self._pages_crawled_this_run >= self.max_pages_per_run:
                        break
                return results
            else:
                logger.warning(f"Firecrawl search returned status {response.status_code}: {response.text[:100]}")
                return []
        except Exception as e:
            logger.error(f"Firecrawl search failed: {e}")
            return []

firecrawl_client = FirecrawlClient()
