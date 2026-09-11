import logging
import re
from typing import Dict, Any, List, Optional
from backend.app.ingestion.parser import _extract_inline_identifiers

logger = logging.getLogger(__name__)

class OfficialSourceAdapter:
    """Base class for official Indian legal source adapters."""
    source_name: str = "Official Indian Legal Source"
    allowed_domains: List[str] = []
    authority_tier: str = "TIER 1"
    doc_type: str = "statute"

    @classmethod
    def is_allowed_url(cls, url: str) -> bool:
        return any(domain in url.lower() for domain in cls.allowed_domains)

    @classmethod
    def extract_metadata(cls, text: str, url: str, title: Optional[str] = None) -> Dict[str, Any]:
        """Extract structured legal metadata from scraped official document text."""
        meta = {
            "source_name": cls.source_name,
            "authority_tier": cls.authority_tier,
            "doc_type": cls.doc_type,
            "url": url,
            "title": title or cls.source_name,
            "status": "ACTIVE",
            "jurisdiction": "India",
        }
        _extract_inline_identifiers(text, meta)
        return meta


class IndiaCodeAdapter(OfficialSourceAdapter):
    """Adapter for India Code (indiacode.nic.in) - official repository of Central and State Acts."""
    source_name = "India Code (Legislative Department)"
    allowed_domains = ["indiacode.nic.in"]
    authority_tier = "TIER 1"
    doc_type = "statute"


class SupremeCourtAdapter(OfficialSourceAdapter):
    """Adapter for Supreme Court of India Judgments (main.sci.gov.in / judgments.ecourts.gov.in)."""
    source_name = "Supreme Court of India"
    allowed_domains = ["main.sci.gov.in", "sci.gov.in", "judgments.ecourts.gov.in"]
    authority_tier = "TIER 1"
    doc_type = "case"


class SEBIAdapter(OfficialSourceAdapter):
    """Adapter for SEBI Regulations and Circulars (sebi.gov.in)."""
    source_name = "Securities and Exchange Board of India (SEBI)"
    allowed_domains = ["sebi.gov.in"]
    authority_tier = "TIER 2"
    doc_type = "regulatory"


class RBIAdapter(OfficialSourceAdapter):
    """Adapter for RBI Notifications and Master Directions (rbi.org.in)."""
    source_name = "Reserve Bank of India (RBI)"
    allowed_domains = ["rbi.org.in"]
    authority_tier = "TIER 2"
    doc_type = "regulatory"


ADAPTER_REGISTRY = {
    "indiacode": IndiaCodeAdapter,
    "supreme_court": SupremeCourtAdapter,
    "sebi": SEBIAdapter,
    "rbi": RBIAdapter
}

def get_adapter_for_url(url: str) -> Optional[OfficialSourceAdapter]:
    """Find appropriate official source adapter based on URL."""
    for adapter_cls in ADAPTER_REGISTRY.values():
        if adapter_cls.is_allowed_url(url):
            return adapter_cls()
    return None
