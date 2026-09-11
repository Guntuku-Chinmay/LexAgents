"""
Unit and integration tests for Constitution of India authoritative corpus.
Covers:
- Preamble retrieval
- Articles 1, 14, 15, 16, 19, 21, 32, 44, 51A, 226, 300A, 368
- Clause queries: 16(4), 19(1)(a), 19(2), 21
- Schedules: First, Seventh (Lists I, II, III), Eighth, Tenth, Twelfth
- Negative queries: 15!=16, 16!=15, 21!=16, 32!=21
- Dynamic synthesis without hardcoded article branches
- Verification Agent mismatch detection
- Multilingual queries (EN, HI, TE) for Article 16
"""

import pytest
import inspect
from backend.app.retrieval.vector_bm25 import HybridRetriever
from backend.app.core.llm import EvidenceGroundedReasoner

# Use the production bootstrapped Qdrant storage for constitution corpus tests
corpus_retriever = HybridRetriever(storage_path="data/qdrant_db")

def test_constitution_preamble_retrieval():
    results = corpus_retriever.search_hybrid(collection_name="statutes", query="What is the Preamble of the Constitution of India?", limit=3)
    assert len(results) > 0
    top = results[0]
    meta = top.get("metadata", {})
    text = top.get("text", "")
    is_preamble = (
        meta.get("part") == "PREAMBLE" or 
        "PREAMBLE" in text.upper()[:200] or 
        "WE, THE PEOPLE OF INDIA" in text
    )
    assert is_preamble, f"Top result was not Preamble: {top}"

@pytest.mark.parametrize("article_num", ["1", "14", "15", "16", "19", "21", "32", "44", "51A", "226", "300A", "368"])
def test_constitution_key_articles_retrieval(article_num):
    query = f"What does Article {article_num} of the Constitution of India provide?"
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=3)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    top_art = str(meta.get("parent_article") or meta.get("article") or "").strip().upper()
    assert top_art == article_num.upper(), f"Expected Article {article_num}, got {top_art}"

@pytest.mark.parametrize("query,expected_clause,expected_art", [
    ("What does Article 16(4) of the Constitution of India state regarding reservations?", "16(4)", "16"),
    ("What does Article 19(1)(a) guarantee under the Constitution of India?", "19(1)(a)", "19"),
    ("What reasonable restrictions are permitted under Article 19(2) of the Constitution?", "19(2)", "19"),
    ("What does Article 21 protect under the Constitution of India?", "21", "21")
])
def test_constitution_clause_isolation(query, expected_clause, expected_art):
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=3)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    text = top.get("text", "")
    top_art = str(meta.get("parent_article") or meta.get("article") or "").strip()
    articles_list = meta.get("articles", [])
    assert top_art == expected_art, f"Expected article {expected_art}, got {top_art}"
    if "(" in expected_clause:
        has_clause = (
            expected_clause in articles_list or 
            expected_clause in text or 
            f"({expected_clause.split('(')[1]}" in text or
            meta.get("clause") == expected_clause.split("(")[1].rstrip(")")
        )
        assert has_clause, f"Expected clause {expected_clause} in result"

@pytest.mark.parametrize("query,sched_name", [
    ("What does the First Schedule of the Constitution of India cover?", "FIRST SCHEDULE"),
    ("What are the lists under the Seventh Schedule of the Constitution?", "SEVENTH SCHEDULE"),
    ("What languages are listed in the Eighth Schedule of the Constitution?", "EIGHTH SCHEDULE"),
    ("What is the Tenth Schedule regarding anti-defection?", "TENTH SCHEDULE"),
    ("What powers of Municipalities are in the Twelfth Schedule?", "TWELFTH SCHEDULE")
])
def test_constitution_schedules_retrieval(query, sched_name):
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=3)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    top_sched = str(meta.get("schedule") or "").strip().upper()
    text = top.get("text", "").upper()
    assert sched_name in top_sched or sched_name in text, f"Expected {sched_name}, got {top_sched}"

@pytest.mark.parametrize("query,forbidden_art", [
    ("What does Article 15 of the Indian Constitution provide?", "16"),
    ("What does Article 16 of the Constitution of India state?", "15"),
    ("What is protected under Article 21 of the Constitution?", "16"),
    ("Explain Article 32 constitutional remedies", "21")
])
def test_constitution_negative_isolation(query, forbidden_art):
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=5)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    top_art = str(meta.get("parent_article") or meta.get("article") or "").strip()
    assert top_art != forbidden_art, f"Isolation failure: query for another article returned forbidden {forbidden_art}"

def test_dynamic_synthesis_no_hardcoding():
    src_code = inspect.getsource(EvidenceGroundedReasoner.synthesize_answer)
    for forbidden in ["if article == 15", "if article == 16", "elif article == 16", "elif article == 14", "if 'article 16' in query.lower(): return"]:
        assert forbidden not in src_code, f"Found hardcoded branch '{forbidden}' in synthesize_answer!"

    prompt_1 = "Source [1]:\nContent: Article 15: The State shall not discriminate against any citizen on grounds only of religion, race, caste, sex, place of birth or any of them."
    res_1 = EvidenceGroundedReasoner.synthesize_answer("What does Article 15 provide?", prompt_1)
    ans_1 = res_1.get("answer", "")
    assert "religion, race, caste, sex" in ans_1

    prompt_mutated = "Source [1]:\nContent: Article 15: Modified synthetic text specifically mentioning underwater space colonies and lunar jurisdictions."
    res_mutated = EvidenceGroundedReasoner.synthesize_answer("What does Article 15 provide?", prompt_mutated)
    ans_mutated = res_mutated.get("answer", "")
    assert "underwater space colonies" in ans_mutated

def test_verification_agent_mismatch_detection():
    # Matching
    prompt_match = "Query: What does Article 16 of the Constitution of India provide?\nSource [1]:\nContent: Article 16 provides for equality of opportunity for all citizens in matters relating to employment or appointment to any office under the State."
    v_res_match = EvidenceGroundedReasoner.verify_answer(prompt_match)
    results = v_res_match.get("verification_results", [])
    assert len(results) > 0
    assert results[0].get("supported") is True
    assert results[0].get("verification_status") == "supported"

    # Mismatch
    prompt_mismatch = "Query: What does Article 15 of the Constitution of India provide?\nSource [1]:\nContent: Article 16 provides equality in public employment."
    v_res_mismatch = EvidenceGroundedReasoner.verify_answer(prompt_mismatch)
    results_m = v_res_mismatch.get("verification_results", [])
    assert len(results_m) > 0
    assert results_m[0].get("supported") is False
    assert results_m[0].get("verification_status") == "unsupported"
    assert "mismatch" in results_m[0].get("claim", "").lower()

@pytest.mark.parametrize("lang,query", [
    ("English", "What does Article 16 of the Constitution of India provide?"),
    ("Hindi", "भारतीय संविधान का अनुच्छेद 16 क्या प्रावधान करता है?"),
    ("Telugu", "భారత రాజ్యాంగంలోని అధికరణ 16 ఏమి అందిస్తుంది?")
])
def test_multilingual_article16_retrieval(lang, query):
    res = corpus_retriever.search_hybrid(collection_name="statutes", query=query, limit=3)
    assert len(res) > 0
    top = res[0]
    meta = top.get("metadata", {})
    top_art = str(meta.get("parent_article") or meta.get("article") or "").strip()
    assert top_art == "16", f"Failed for {lang}: expected Article 16, got {top_art}"
