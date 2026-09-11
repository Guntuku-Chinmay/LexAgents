import uuid
import pytest
from backend.app.retrieval.vector_bm25 import extract_identifiers_from_query, expand_multilingual_legal_query, retriever
from backend.app.agents.synthesis import synthesis_agent
from backend.app.models.schemas import Evidence

def test_extract_identifiers_multilingual():
    # English
    en_res = extract_identifiers_from_query("Under Section 138 and Article 21, what applies?")
    assert en_res.get("section") == "138"
    assert en_res.get("article") == "21"

    # Hindi
    hi_res = extract_identifiers_from_query("धारा 138 एनआई एक्ट और अनुच्छेद 21 के तहत क्या प्रावधान हैं?")
    assert hi_res.get("section") == "138"
    assert hi_res.get("article") == "21"

    # Telugu
    te_res = extract_identifiers_from_query("సెక్షన్ 138 ఎన్.ఐ చట్టం మరియు ఆర్టికల్ 21 ప్రకారం నిబంధనలు ఏమిటి?")
    assert te_res.get("section") == "138"
    assert te_res.get("article") == "21"


def test_expand_multilingual_legal_query():
    # Hindi expansion
    hi_expanded = expand_multilingual_legal_query("धारा 138 एनआई एक्ट के तहत चेक बाउंस")
    assert "Section 138" in hi_expanded
    assert "Negotiable Instruments Act" in hi_expanded
    assert "cheque bounce" in hi_expanded

    # Telugu expansion
    te_expanded = expand_multilingual_legal_query("చెక్ బౌన్స్ కేసులో సెక్షన్ 138 నిబంధనలు")
    assert "Section 138" in te_expanded
    assert "Negotiable Instruments Act" in te_expanded
    assert "cheque bounce" in te_expanded

    # English query unchanged
    en_query = "What are the requirements of Section 138 notice?"
    assert expand_multilingual_legal_query(en_query) == en_query


def test_multilingual_grounded_retrieval():
    chunk_id = str(uuid.uuid4())
    retriever.index_chunks("statutes_i18n", [
        {
            "id": chunk_id,
            "text": "Section 138 of the Negotiable Instruments Act, 1881 requires notice within 30 days of dishonour.",
            "metadata": {"section": "138", "title": "Negotiable Instruments Act, 1881", "doc_type": "central_act"}
        }
    ])

    # Search with Hindi query
    hi_results = retriever.search_hybrid("statutes_i18n", "धारा 138 चेक बाउंस")
    assert len(hi_results) > 0
    assert any(r["metadata"].get("section") == "138" for r in hi_results)

    # Search with Telugu query
    te_results = retriever.search_hybrid("statutes_i18n", "చెక్ బౌన్స్ సెక్షన్ 138")
    assert len(te_results) > 0
    assert any(r["metadata"].get("section") == "138" for r in te_results)


def test_multilingual_synthesis_preserves_citations():
    mock_evidence = [
        Evidence(
            id="ev1",
            text="Under Section 138 of the Negotiable Instruments Act, 1881, notice must be issued within 30 days.",
            source="Negotiable Instruments Act, 1881, Section 138",
            doc_type="central_act",
            score=0.95
        ),
        Evidence(
            id="ev2",
            text="The Supreme Court in Dalmia Cement v. Galaxy Traders (2001) upheld that 30-day notice is mandatory.",
            source="Supreme Court Judgment: Dalmia Cement v. Galaxy Traders (2001)",
            doc_type="sc_judgment",
            score=0.90
        )
    ]

    # Hindi Synthesis
    hi_res = synthesis_agent.synthesize("धारा 138 चेक बाउंस", mock_evidence, language="hi")
    hi_text = hi_res["answer"]
    assert "Section 138" in hi_text or "138" in hi_text
    assert "[1]" in hi_text
    assert "Negotiable Instruments Act" in hi_text or "Dalmia Cement" in hi_text

    # Telugu Synthesis
    te_res = synthesis_agent.synthesize("చెక్ బౌన్స్ సెక్షన్ 138", mock_evidence, language="te")
    te_text = te_res["answer"]
    assert "Section 138" in te_text or "138" in te_text
    assert "[1]" in te_text
    assert "Negotiable Instruments Act" in te_text or "Dalmia Cement" in te_text


def test_api_multilingual_research(client):
    uuid_statute = str(uuid.uuid5(uuid.NAMESPACE_DNS, "statute_i18n"))
    retriever.index_chunks("statutes", [
        {
            "id": uuid_statute,
            "text": "Section 138 of the Negotiable Instruments Act, 1881 mandates 30 days statutory notice.",
            "metadata": {"title": "Negotiable Instruments Act, 1881", "doc_type": "central_act", "filename": "statute_i18n.txt"}
        }
    ])

    # Hindi API call
    hi_payload = {
        "query": "धारा 138 एनआई एक्ट के तहत चेक बाउंस",
        "language": "hi",
        "use_web": False
    }
    hi_res = client.post("/api/research", json=hi_payload)
    assert hi_res.status_code == 200
    hi_data = hi_res.json()
    assert hi_data["language"] == "hi"
    assert len(hi_data["answer"]) > 0
    assert "[1]" in hi_data["answer"]

    # Telugu API call
    te_payload = {
        "query": "చెక్ బౌన్స్ కేసులో సెక్షన్ 138",
        "language": "te",
        "use_web": False
    }
    te_res = client.post("/api/research", json=te_payload)
    assert te_res.status_code == 200
    te_data = te_res.json()
    assert te_data["language"] == "te"
    assert len(te_data["answer"]) > 0
    assert "[1]" in te_data["answer"]
