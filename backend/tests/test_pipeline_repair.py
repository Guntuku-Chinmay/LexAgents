import pytest
import uuid
from backend.app.models.schemas import Evidence, VerificationResult
from backend.app.retrieval.query_analyzer import analyze_query
from backend.app.retrieval.relevance_gate import evaluate_candidate_relevance
from backend.app.agents.reflection import orchestrator
from backend.app.agents.coordinator import coordinator_agent
from backend.app.agents.verification import verification_agent, get_confidence_label
from backend.app.agents.synthesis import AnswerQualityGate

# ============================================================
# 1. PRIMARY CAR / COW / ELECTRIC POLE REGRESSION TEST
# ============================================================

def test_primary_car_cow_pole_pipeline():
    """
    CRITICAL BENCHMARK:
    User Scenario:
    "If I've a car I was un drunk. A cow came in front of me suddenly.
    For saving the cattle I dashed the electric pole. Help me to prove I've no mistakes"

    MUST NOT:
    - Cite Article 165 or Advocate-General
    - Ground to unrelated Constitutional law
    - Display 98% false confidence or "Grounded & Verified"

    MUST:
    - Classify as Motor Vehicle Law / Tort
    - Identify inevitable accident / emergency / negligence
    - Acknowledge repository limitations regarding Motor Vehicles Act
    - Produce calibrated confidence label 'Insufficient evidence'
    """
    query = (
        "If I've a car I was un drunk. A cow came in front of me suddenly. "
        "For saving the cattle I dashed the electric pole. Help me to prove I've no mistakes"
    )
    analysis = analyze_query(query)

    # A. Classification
    assert analysis.primary_domain == "Motor Vehicle Law"
    assert analysis.query_type == "fact_pattern"

    # B. Fact & Issue extraction
    assert len(analysis.facts) >= 3
    assert any("vehicle" in f.lower() or "car" in f.lower() for f in analysis.facts)
    assert any("animal" in f.lower() or "cattle" in f.lower() or "cow" in f.lower() for f in analysis.facts)
    assert any("pole" in f.lower() for f in analysis.facts)

    assert len(analysis.legal_issues) >= 1
    assert any("negligence" in iss.lower() or "inevitable" in iss.lower() or "liability" in iss.lower() for iss in analysis.legal_issues)

    # C. Relevance gate rejects Article 165
    mock_165 = {
        "id": "const_art_165",
        "text": "Article 165. Advocate-General for the State. Governor shall appoint Advocate-General...",
        "metadata": {"doc_type": "constitutional", "article": "165", "title": "Constitution Article 165"}
    }
    is_accepted, reason, _ = evaluate_candidate_relevance(mock_165, analysis)
    assert not is_accepted
    assert "Motor Vehicle" in reason or "Constitutional" in reason

    # D. Full pipeline response
    res = orchestrator.run_research(query, use_web=False)

    # Verification: Article 165 is completely absent
    assert "Article 165" not in res.answer
    assert "Advocate-General" not in res.answer
    for c in res.citations:
        assert "165" not in c.source and "165" not in c.text

    # Verification status & confidence label
    assert res.overall_status in ["insufficient_evidence", "unsupported"]
    assert res.confidence_label == "Insufficient evidence"

    for v in res.verification_results:
        if not v.supported:
            assert v.confidence < 0.5


# ============================================================
# 2. CATEGORY A: EXACT PROVISION RETRIEVAL & ISOLATION
# ============================================================

@pytest.mark.parametrize("query,expected_domain,expected_art", [
    ("What does Article 15 of the Indian Constitution provide?", "Constitutional Law", "15"),
    ("What does Article 16 of the Constitution of India provide?", "Constitutional Law", "16"),
    ("What is Article 16(4) of the Indian Constitution?", "Constitutional Law", "16"),
    ("What does Article 19(1)(a) protect?", "Constitutional Law", "19"),
    ("What does Article 21 of the Constitution guarantee?", "Constitutional Law", "21"),
    ("What remedies are provided under Article 32 of the Constitution?", "Constitutional Law", "32"),
    ("What is Article 300A concerning property rights?", "Constitutional Law", "300A"),
    ("What is the amendment procedure under Article 368?", "Constitutional Law", "368"),
])
def test_category_a_exact_provisions(query, expected_domain, expected_art):
    analysis = analyze_query(query)
    assert analysis.primary_domain == expected_domain
    assert str(analysis.explicit_identifiers.get("parent_article") or analysis.explicit_identifiers.get("article")) == expected_art


# ============================================================
# 3. CATEGORY B: FACT-PATTERN LEGAL DOMAIN ANCHORING
# ============================================================

@pytest.mark.parametrize("query,expected_domain", [
    ("My manager touches me inappropriately and threatens to terminate my employment. What legal protection do I have?", "Women & Gender Justice"),
    ("I paid a deposit of 50000 to my landlord. My lease ended 2 months ago and he refuses to return the money.", "Property & Land Law"),
    ("A cow jumped in front of my car suddenly and I swerved into a lamppost to avoid killing it. Can I be held liable for damages?", "Motor Vehicle Law"),
    ("Someone called posing as a bank manager and stole 2 lakhs from my account through an OTP scam. How can I recover my money?", "Cyber & Technology Law"),
    ("The company fired me without any written notice or severance pay after 4 years of service. What are my rights?", "Labour & Employment Law"),
    ("I bought an expensive laptop that stopped working in 2 weeks and the seller refuses to replace or refund it.", "Consumer Law"),
    ("A director transferred 10 crore from company accounts to his private firm without board approval. What actions can shareholders take?", "Corporate & Commercial Law"),
    ("Police entered my house at midnight and arrested my brother without showing any arrest memo or warrant. How can we get bail?", "Criminal Procedure"),
])
def test_category_b_fact_patterns(query, expected_domain):
    analysis = analyze_query(query)
    assert analysis.primary_domain == expected_domain
    assert analysis.query_type == "fact_pattern"
    assert len(analysis.facts) >= 1
    assert len(analysis.legal_issues) >= 1


# ============================================================
# 4. CROSS-DOMAIN NEGATIVE ISOLATION & CONTAMINATION BARRIER
# ============================================================

def test_cross_domain_negative_barriers():
    # 1. Motor Vehicle query must reject Constitutional provisions
    mv_analysis = analyze_query("Car crashed into barrier after tyre burst. Whose fault is it?")
    const_doc = {
        "id": "c1",
        "text": "Article 14. Equality before law.",
        "metadata": {"doc_type": "constitutional", "article": "14", "title": "Constitution"}
    }
    accepted, reason, _ = evaluate_candidate_relevance(const_doc, mv_analysis)
    assert not accepted
    assert "Motor Vehicle" in reason or "Constitutional" in reason

    # 2. POSH query must reject Motor Vehicle Act
    posh_analysis = analyze_query("Workplace harassment complaint procedure under POSH Act")
    mv_doc = {
        "id": "mv1",
        "text": "Section 166. Application for compensation under Motor Vehicles Act.",
        "metadata": {"doc_type": "central_act", "section": "166", "title": "Motor Vehicles Act, 1988"}
    }
    accepted, reason, _ = evaluate_candidate_relevance(mv_doc, posh_analysis)
    assert not accepted

    # 3. Cyber fraud query must reject Article 165
    cyber_analysis = analyze_query("Online phishing scam drained my bank balance")
    accepted, reason, _ = evaluate_candidate_relevance(const_doc, cyber_analysis)
    assert not accepted


# ============================================================
# 5. ANSWER QUALITY GATE
# ============================================================

def test_answer_quality_gate():
    qc = analyze_query("Car crashed into divider to save animal on highway. Help me prove innocence.")
    
    # Contaminated answer containing Article 165
    bad_answer = "Under Article 165 of the Constitution of India, the Advocate-General advises the State government."
    gate_res = AnswerQualityGate.evaluate(bad_answer, qc, [])
    assert not gate_res.is_relevant
    assert any("unrelated" in r.lower() for r in gate_res.rejection_reasons)


# ============================================================
# 6. CALIBRATED CONFIDENCE LABELS
# ============================================================

def test_calibrated_confidence_labels():
    assert get_confidence_label(0.95, True, "supported") == "Strong evidence"
    assert get_confidence_label(0.70, True, "supported") == "Moderate evidence"
    assert get_confidence_label(0.40, True, "supported") == "Limited evidence"
    assert get_confidence_label(0.15, True, "supported") == "Insufficient evidence"
    assert get_confidence_label(0.95, False, "unsupported") == "Insufficient evidence"
    assert get_confidence_label(0.95, True, "insufficient_evidence") == "Insufficient evidence"
