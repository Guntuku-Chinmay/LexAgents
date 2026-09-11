import pytest
from unittest.mock import patch, MagicMock
from backend.app.ingestion.firecrawl import FirecrawlClient
from backend.app.ingestion.adapters import (
    IndiaCodeAdapter,
    SupremeCourtAdapter,
    SEBIAdapter,
    RBIAdapter,
    get_adapter_for_url
)
from backend.app.agents.web_research import web_research_agent

def test_official_source_adapters_domain_validation():
    # India Code
    assert IndiaCodeAdapter.is_allowed_url("https://www.indiacode.nic.in/handle/123456789/1362") is True
    assert IndiaCodeAdapter.is_allowed_url("https://randomsite.com/act") is False

    # Supreme Court
    assert SupremeCourtAdapter.is_allowed_url("https://main.sci.gov.in/judgment/2024") is True
    assert SupremeCourtAdapter.is_allowed_url("https://judgments.ecourts.gov.in/pdf/123") is True
    assert SupremeCourtAdapter.is_allowed_url("https://wikipedia.org/puttaswamy") is False

    # SEBI
    assert SEBIAdapter.is_allowed_url("https://www.sebi.gov.in/legal/regulations/jan-2015/pit.html") is True
    assert SEBIAdapter.is_allowed_url("https://fake-sebi.com") is False

    # RBI
    assert RBIAdapter.is_allowed_url("https://www.rbi.org.in/scripts/BS_CircularIndexDisplay.aspx") is True
    assert RBIAdapter.is_allowed_url("https://rbi.fake.org") is False

def test_get_adapter_for_url():
    adapter1 = get_adapter_for_url("https://www.indiacode.nic.in/show-data?actid=123")
    assert isinstance(adapter1, IndiaCodeAdapter)

    adapter2 = get_adapter_for_url("https://main.sci.gov.in/case-status")
    assert isinstance(adapter2, SupremeCourtAdapter)

    adapter3 = get_adapter_for_url("https://www.sebi.gov.in/regulations")
    assert isinstance(adapter3, SEBIAdapter)

    adapter4 = get_adapter_for_url("https://www.rbi.org.in/notifications")
    assert isinstance(adapter4, RBIAdapter)

    adapter_none = get_adapter_for_url("https://unknown-domain.com")
    assert adapter_none is None

def test_adapter_metadata_extraction():
    text = "Section 138. Dishonour of cheque for insufficiency of funds in the account."
    url = "https://www.indiacode.nic.in/handle/123456789/1362"
    meta = IndiaCodeAdapter.extract_metadata(text, url, title="Negotiable Instruments Act, 1881")
    assert meta["source_name"] == "India Code (Legislative Department)"
    assert meta["doc_type"] == "statute"
    assert meta["authority_tier"] == "TIER 1"
    assert meta["section"] == "138"
    assert meta["url"] == url

def test_firecrawl_client_graceful_degradation():
    # Client initialized without API key or disabled
    client = FirecrawlClient(api_key="", enabled=False)
    assert client.is_available() is False
    assert client.scrape_url("https://main.sci.gov.in/judgment") is None
    assert client.search("Article 21 Supreme Court") == []

def test_firecrawl_client_budget_limit():
    client = FirecrawlClient(api_key="test-key", enabled=True, max_pages_per_run=1)
    client._pages_crawled_this_run = 1
    # Should stop scraping because max pages reached
    assert client.scrape_url("https://main.sci.gov.in/judgment") is None

def test_web_research_agent_offline_graceful_fallback():
    # When use_web is False or offline
    results = web_research_agent.search("SEBI insider trading regulations 2015", enabled=False)
    assert results == []
