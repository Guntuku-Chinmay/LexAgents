"""
Automated Test Suite for LexAgents Core Legal Accuracy Sprint.
Verifies:
1. Primary debugging case (Car / Cow / Pole collision)
2. Mandatory benchmark queries (1-30) across all 11 canonical domains
3. Explicit identifier strictness (Article 15 != 16; Article 16(4) isolation)
4. Negative domain isolation & exclusion signals
5. Adversarial / messy queries handling
6. Multilingual legal query mapping (Hindi and Telugu)
7. Safe insufficient-evidence behavior and elimination of false 98% confidence
"""

import pytest
from backend.app.retrieval.canonical_taxonomy import SUPPORTED_DOMAINS, get_domain
from backend.app.retrieval.query_analyzer import analyze_query
from backend.app.retrieval.relevance_gate import evaluate_candidate_relevance, filter_evidence_through_gate
from backend.app.retrieval.corpus_coverage import is_domain_indexed, get_coverage
from backend.app.retrieval.vector_bm25 import HybridRetriever
from backend.app.agents.reflection import orchestrator

corpus_retriever = HybridRetriever(storage_path="data/qdrant_db")

# ============================================================
# 1. PRIMARY DEBUGGING CASE TEST (CAR / COW / POLE)
# ============================================================

def test_primary_debugging_case_car_cow_pole():
    query = (
        "If I've a car I was un drunk. A cow came in front of me suddenly. "
        "For saving the cattle I dashed the electric pole. "
        "Help me to prove I've no mistakes"
    )
    analysis = analyze_query(query)

    # 1. Structured analysis checks
    assert analysis.query_type == "fact_pattern", f"Expected fact_pattern, got {analysis.query_type}"
    assert analysis.primary_domain == "Motor Vehicle Law", f"Expected Motor Vehicle Law, got {analysis.primary_domain}"
    assert "Civil Law" in analysis.secondary_domains or "Criminal Law" in analysis.secondary_domains
    
    # 2. Fact extraction checks
    facts_str = " ".join(analysis.facts).lower()
    assert "motor vehicle" in facts_str or "vehicle" in facts_str or "driving" in facts_str
    assert "animal" in facts_str or "cattle" in facts_str
    assert "electric" in facts_str or "pole" in facts_str
    assert "sobriety" in facts_str or "fault" in facts_str or "intoxication" in facts_str

    # 3. Legal issues extraction checks
    issues_str = " ".join(analysis.legal_issues).lower()
    assert "negligence" in issues_str or "inevitable accident" in issues_str or "liability" in issues_str

    # 4. Relevance gate check: Constitutional Article 165 MUST be rejected
    mock_art_165 = {
        "id": "const_art_165",
        "text": "Article 165. Advocate-General for the State. (1) The Governor of each State shall appoint...",
        "metadata": {
            "doc_type": "constitutional",
            "article": "165",
            "title": "Constitution of India Article 165"
        }
    }
    is_accepted, reason, _ = evaluate_candidate_relevance(mock_art_165, analysis)
    assert not is_accepted, "Relevance gate failed: Constitutional Article 165 was accepted for Motor Vehicle query!"
    assert "Motor Vehicle" in reason or "Constitutional" in reason

    # 5. End-to-end research loop execution
    response = orchestrator.run_research(query, use_web=False)

    # Forbidden behavior checks:
    # A. Article 165 must NOT be in final answer
    assert "Article 165" not in response.answer, f"Forbidden failure: Article 165 found in answer: {response.answer}"
    
    # B. Article 165 must NOT be in citations
    for c in response.citations:
        assert "165" not in c.source and "165" not in c.text, f"Forbidden failure: Article 165 found in citations: {c}"

    # C. Verification results must NOT claim "supported" with 98% confidence
    for v in response.verification_results:
        if "Article 165" in v.claim or "165" in str(v.issues):
            assert not v.supported, "Forbidden failure: Mismatched constitutional claim was marked supported!"
            assert v.confidence < 0.5, f"Forbidden failure: False confidence {v.confidence} on mismatched claim!"

    # D. Because Motor Vehicles Act is not indexed in corpus, safe insufficient evidence or gap note must be stated
    assert (
        "insufficient" in response.answer.lower() or 
        "motor vehicle" in response.answer.lower() or
        "not currently contain" in response.answer.lower()
    ), f"Expected safe response, got: {response.answer}"


# ============================================================
# 2. MANDATORY BENCHMARK QUERIES (1-30) ACROSS 11 DOMAINS
# ============================================================

BENCHMARK_CASES = [
    # A. Constitution
    ("What does Article 15 say about discrimination?", "Constitutional Law", "explicit_reference", "15"),
    ("What is Article 16(4)?", "Constitutional Law", "explicit_reference", "16"),
    ("What are the reasonable restrictions under Article 19(2)?", "Constitutional Law", "explicit_reference", "19"),
    ("What is the right to property under the Constitution?", "Constitutional Law", "conceptual_inquiry", None),
    ("What is the procedure for constitutional amendment?", "Constitutional Law", "conceptual_inquiry", None),

    # B. Criminal
    ("What is the law relating to theft?", "Criminal Law", "conceptual_inquiry", None),
    ("What is the difference between murder and culpable homicide?", "Criminal Law", "conceptual_inquiry", None),
    ("What is criminal conspiracy?", "Criminal Law", "conceptual_inquiry", None),

    # C. Criminal Procedure
    ("How does bail work?", "Criminal Procedure", "conceptual_inquiry", None),
    ("What happens after an FIR?", "Criminal Procedure", "conceptual_inquiry", None),
    ("What are the rules relating to arrest?", "Criminal Procedure", "conceptual_inquiry", None),

    # D. Motor Vehicle
    ("What happens if someone drives without a valid licence?", "Motor Vehicle Law", "conceptual_inquiry", None),
    ("What compensation may be available after a road accident?", "Motor Vehicle Law", "conceptual_inquiry", None),
    ("A driver swerved to avoid a cow and hit an electric pole. What legal issues may arise?", "Motor Vehicle Law", "fact_pattern", None),

    # E. Women & Gender
    ("What protection is available against workplace sexual harassment?", "Women & Gender Justice", "conceptual_inquiry", None),
    ("What can a woman do in a domestic violence situation?", "Women & Gender Justice", "conceptual_inquiry", None),
    ("What laws address dowry-related offences?", "Women & Gender Justice", "conceptual_inquiry", None),

    # F. Consumer
    ("What can a consumer do when a service is deficient?", "Consumer Law", "conceptual_inquiry", None),
    ("What is product liability?", "Consumer Law", "conceptual_inquiry", None),

    # G. Cyber
    ("What legal remedies may be available after an online financial scam?", "Cyber & Technology Law", "conceptual_inquiry", None),
    ("What laws deal with electronic records?", "Cyber & Technology Law", "conceptual_inquiry", None),

    # H. Property
    ("What happens when a landlord refuses to return a security deposit?", "Property & Land Law", "fact_pattern", None),
    ("What is a lease?", "Property & Land Law", "conceptual_inquiry", None),
    ("How is property transferred?", "Property & Land Law", "conceptual_inquiry", None),

    # I. Labour
    ("What rights may an employee have when terminated unlawfully?", "Labour & Employment Law", "conceptual_inquiry", None),
    ("What protection exists regarding workplace safety?", "Labour & Employment Law", "conceptual_inquiry", None),
    ("What laws concern wages?", "Labour & Employment Law", "conceptual_inquiry", None),

    # J. Corporate & Commercial
    ("What are the duties of company directors?", "Corporate & Commercial Law", "conceptual_inquiry", None),
    ("What happens when a contract is breached?", "Corporate & Commercial Law", "conceptual_inquiry", None),
    ("What is the legal process for company incorporation?", "Corporate & Commercial Law", "conceptual_inquiry", None)
]

@pytest.mark.parametrize("query,expected_domain,expected_type,expected_art", BENCHMARK_CASES)
def test_mandatory_benchmark_classification(query, expected_domain, expected_type, expected_art):
    analysis = analyze_query(query)
    assert analysis.primary_domain == expected_domain, f"Query '{query}' failed domain check: expected {expected_domain}, got {analysis.primary_domain}"
    assert analysis.query_type == expected_type, f"Query '{query}' failed type check: expected {expected_type}, got {analysis.query_type}"
    if expected_art:
        assert str(analysis.explicit_identifiers.get("parent_article") or analysis.explicit_identifiers.get("article")) == expected_art


# ============================================================
# 3. EXPLICIT IDENTIFIER STRICTNESS TESTS
# ============================================================

def test_explicit_article_15_isolation():
    query = "What does Article 15 of the Indian Constitution provide?"
    analysis = analyze_query(query)
    assert analysis.explicit_identifiers.get("parent_article") == "15"

    # Search corpus
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=5)
    assert len(res) > 0
    top = res[0]
    top_art = str(top.get("metadata", {}).get("parent_article") or top.get("metadata", {}).get("article") or "").strip()
    assert top_art == "15", f"Expected Article 15, got Article {top_art}"

    # Article 16 must not be top
    assert top_art != "16", "Article 16 erroneously returned for Article 15 query!"

def test_explicit_article_16_4_isolation():
    query = "What does Article 16(4) of the Constitution of India provide?"
    analysis = analyze_query(query)
    assert analysis.explicit_identifiers.get("parent_article") == "16"
    assert analysis.explicit_identifiers.get("clause") == "4"

    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=5)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    text = top.get("text", "")
    top_art = str(meta.get("parent_article") or meta.get("article") or "").strip()
    assert top_art == "16"
    assert "16(4)" in str(meta.get("articles", [])) or "16(4)" in text or "(4)" in text or meta.get("clause") == "4"


# ============================================================
# 4. NEGATIVE DOMAIN ISOLATION TESTS
# ============================================================

def test_negative_isolation_motor_vehicle_rejects_constitution():
    mv_query = "Car collision with electric pole on road after avoiding animal"
    analysis = analyze_query(mv_query)
    assert analysis.primary_domain == "Motor Vehicle Law"
    
    # Candidate from constitution
    const_doc = {
        "id": "c1",
        "text": "Article 165 Advocate-General for the State...",
        "metadata": {"doc_type": "constitutional", "article": "165"}
    }
    accepted, reason, _ = evaluate_candidate_relevance(const_doc, analysis)
    assert not accepted, "Negative isolation failure: Constitutional doc accepted for Motor Vehicle query"

def test_negative_isolation_workplace_harassment_rejects_motor_vehicle():
    query = "protection against workplace sexual harassment under POSH act"
    analysis = analyze_query(query)
    assert analysis.primary_domain == "Women & Gender Justice"

    mv_doc = {
        "id": "mv1",
        "text": "Motor Vehicles Act Section 166 Application for compensation in motor accident...",
        "metadata": {"doc_type": "central_act", "act_name": "Motor Vehicles Act, 1988"}
    }
    accepted, reason, _ = evaluate_candidate_relevance(mv_doc, analysis)
    assert not accepted, "Negative isolation failure: Motor vehicle doc accepted for POSH query"

def test_negative_isolation_cyber_fraud_rejects_unrelated_constitution():
    query = "someone stole money through my online UPI banking account"
    analysis = analyze_query(query)
    assert analysis.primary_domain == "Cyber & Technology Law"

    unrelated_const = {
        "id": "c2",
        "text": "Article 368 Power of Parliament to amend the Constitution and procedure therefor...",
        "metadata": {"doc_type": "constitutional", "article": "368"}
    }
    accepted, reason, _ = evaluate_candidate_relevance(unrelated_const, analysis)
    assert not accepted, "Negative isolation failure: Constitutional amendment accepted for UPI fraud query"


# ============================================================
# 5. ADVERSARIAL / MESSY QUERIES TESTS
# ============================================================

MESSY_CASES = [
    ("my boss keeps touching me and making comments what law can protect me", "Women & Gender Justice"),
    ("i got arrested yesterday how do i get bail", "Criminal Procedure"),
    ("my landlord took my deposit and not giving back", "Property & Land Law"),
    ("someone hacked my phone and took money from account", "Cyber & Technology Law"),
    ("i was driving drunk but a cow suddenly came and i hit a pole can i prove i wasn't at fault", "Motor Vehicle Law"),
    ("company fired me suddenly without notice what can i do", "Labour & Employment Law"),
    ("my online purchase is defective and seller refuses refund", "Consumer Law")
]

@pytest.mark.parametrize("messy_q,expected_dom", MESSY_CASES)
def test_adversarial_messy_queries(messy_q, expected_dom):
    analysis = analyze_query(messy_q)
    assert analysis.primary_domain == expected_dom, f"Messy query failed: expected {expected_dom}, got {analysis.primary_domain}"


# ============================================================
# 6. MULTILINGUAL QUERIES TESTS
# ============================================================

MULTILINGUAL_CASES = [
    ("भारतीय संविधान का अनुच्छेद 15 क्या कहता है?", "Constitutional Law", "15", "hi"),
    ("భారత రాజ్యాంగంలోని ఆర్టికల్ 16 దేనిని తెలుపుతుంది?", "Constitutional Law", "16", "te"),
    ("कार्यस्थल पर यौन उत्पीड़न की शिकायत कैसे दर्ज करें?", "Women & Gender Justice", None, "hi"),
    ("చెక్ బౌన్స్ అయినప్పుడు ఏ చట్టం వర్తిస్తుంది?", "Corporate & Commercial Law", None, "te")
]

@pytest.mark.parametrize("m_query,expected_dom,expected_art,expected_lang", MULTILINGUAL_CASES)
def test_multilingual_query_mapping(m_query, expected_dom, expected_art, expected_lang):
    analysis = analyze_query(m_query)
    assert analysis.language == expected_lang
    assert analysis.primary_domain == expected_dom
    if expected_art:
        assert str(analysis.explicit_identifiers.get("parent_article") or analysis.explicit_identifiers.get("article")) == expected_art


# ============================================================
# 7. CALIBRATED CONFIDENCE & ZERO FALSE VERIFICATION
# ============================================================

def test_calibrated_confidence_on_insufficient_evidence():
    query = "What happens if someone drives without a valid licence in a motor vehicle?"
    analysis = analyze_query(query)
    assert analysis.primary_domain == "Motor Vehicle Law"

    # Run research with local corpus
    response = orchestrator.run_research(query, use_web=False)

    # Must not have any verified claims at 0.98 or 0.99
    for v in response.verification_results:
        if not v.supported:
            assert v.confidence < 0.5
        else:
            assert v.confidence <= 0.95
