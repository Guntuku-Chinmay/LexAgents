import pytest
from backend.app.models.schemas import Evidence, VerificationResult, TaskDecomposition
from backend.app.agents.coordinator import coordinator_agent
from backend.app.agents.constitutional import constitutional_research_agent
from backend.app.agents.regulatory import regulatory_agent
from backend.app.agents.synthesis import synthesis_agent
from backend.app.agents.verification import verification_agent
from backend.app.agents.reflection import reflection_agent, orchestrator
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever

def test_coordinator_agent():
    # Decompose mock query
    output = coordinator_agent.decompose_query("Test tenant query", active_documents=[])
    assert len(output.tasks) > 0
    assert any(t.agent in ["case_law", "statute"] for t in output.tasks)

def test_coordinator_indian_routing():
    # Test constitutional routing
    out_const = coordinator_agent.decompose_query("Does Article 21 protect digital privacy?", active_documents=[])
    assert any(t.agent == "constitutional" for t in out_const.tasks)

    # Test regulatory routing
    out_reg = coordinator_agent.decompose_query("SEBI PIT rules regarding insider trading.", active_documents=[])
    assert any(t.agent == "regulatory" for t in out_reg.tasks)

def test_constitutional_agent():
    import uuid
    uuid_c = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c_india_1"))
    retriever.index_chunks("statutes", [
        {
            "id": uuid_c,
            "text": "Article 21 guarantees protection of life and liberty.",
            "metadata": {"doc_type": "constitutional", "article": "21", "filename": "const.txt"}
        }
    ])
    ev_list = constitutional_research_agent.search("Article 21 privacy")
    assert len(ev_list) > 0
    assert ev_list[0].doc_type == "constitutional"
    assert "Article 21" in ev_list[0].source

def test_regulatory_agent():
    import uuid
    uuid_r = str(uuid.uuid5(uuid.NAMESPACE_DNS, "sebi_reg_1"))
    retriever.index_chunks("statutes", [
        {
            "id": uuid_r,
            "text": "Regulation 3 SEBI PIT prohibited communication.",
            "metadata": {"doc_type": "regulation", "regulation": "3", "filename": "sebi.txt"}
        }
    ])
    ev_list = regulatory_agent.search("Regulation 3 UPSI")
    assert len(ev_list) > 0
    assert ev_list[0].doc_type == "regulation"
    assert "Regulation 3" in ev_list[0].source

def test_synthesis_agent():
    evidence = [
        Evidence(id="ev1", text="Section 138 of Negotiable Instruments Act requires cheque notice in 30 days.", source="NI Act Section 138", doc_type="central_act", score=0.9),
        Evidence(id="ev2", text="Dalmia Cement case held notice period under Section 138 is mandatory.", source="Dalmia Cement v Galaxy", doc_type="sc_judgment", score=0.8)
    ]
    
    res = synthesis_agent.synthesize("What is the refund timeline?", evidence)
    assert "answer" in res
    assert "conflicts" in res

def test_verification_agent():
    evidence = [
        Evidence(id="ev1", text="Section 138 of Negotiable Instruments Act requires cheque notice in 30 days.", source="NI Act Section 138", doc_type="central_act", score=0.9)
    ]
    
    # Text with citation
    answer = "A cheque notice must be issued within 30 days under Section 138 [1]."
    results = verification_agent.verify(answer, evidence)
    
    assert len(results) > 0
    # First result should be the verified claim
    assert results[0].claim != ""
    assert results[0].supported is True
    assert results[0].citation_correct is True

def test_verification_multi_valued_classification():
    from backend.app.core.llm import set_mock_response, clear_mock_responses
    
    evidence = [
        Evidence(id="ev_ni", text="Section 138 Negotiable Instruments Act timeline is 30 days.", source="NI Act Section 138", doc_type="central_act", score=0.9),
        Evidence(id="ev_const", text="Article 21 guarantees protection of life.", source="Constitution Article 21", doc_type="constitutional", score=0.8)
    ]
    
    set_mock_response(
        "verify",
        {
            "verification_results": [
                {
                    "claim": "Cheque bounce notice can be sent after 60 days.",
                    "supported": False,
                    "evidence_index": 1,
                    "confidence": 0.99,
                    "issues": ["Notice must be sent within 30 days, not 60"],
                    "importance": "high",
                    "verification_status": "contradicted",
                    "evidence_links": [
                        {
                            "evidence_index": 1,
                            "relationship": "contradicts"
                        }
                    ]
                },
                {
                    "claim": "Article 21 guarantees right to privacy in absolute terms.",
                    "supported": False,
                    "evidence_index": 2,
                    "confidence": 0.8,
                    "issues": ["Right to privacy is fundamental but subject to reasonable restrictions"],
                    "importance": "medium",
                    "verification_status": "partially_supported",
                    "evidence_links": [
                        {
                            "evidence_index": 2,
                            "relationship": "context_only"
                        }
                    ]
                }
            ]
        }
    )
    
    try:
        ans = "Cheque bounce notice can be sent after 60 days [1]. Article 21 guarantees right to privacy in absolute terms [2]."
        results = verification_agent.verify(ans, evidence)
        assert len(results) == 2
        
        assert results[0].verification_status == "contradicted"
        assert results[0].supported is False
        assert results[0].evidence_links[0]["relationship"] == "contradicts"
        
        assert results[1].verification_status == "partially_supported"
        assert results[1].evidence_links[0]["relationship"] == "context_only"
    finally:
        clear_mock_responses()

def test_reflection_agent():
    from backend.app.core.llm import set_mock_response, clear_mock_responses
    
    # If all claims verified: should return sufficient=True
    ver_ok = [
        VerificationResult(claim="Claim A", supported=True, evidence_ids=["e1"], citation_correct=True, confidence=0.95)
    ]
    sufficient, tasks, reasoning = reflection_agent.reflect("query", "answer", ver_ok, [])
    assert sufficient is True
    assert len(tasks) == 0

    # If some claims unsupported: should return sufficient=False and generate follow-up tasks
    # Register mock response for reflect loop containing B
    set_mock_response(
        "reflect",
        {
            "sufficient": False,
            "reasoning": "Claim B is unsupported.",
            "follow_up_tasks": [
                {"query": "search query", "agent": "case_law", "reason": "need evidence"}
            ]
        }
    )
    
    try:
        ver_bad = [
            VerificationResult(claim="Claim B", supported=False, evidence_ids=[], citation_correct=False, confidence=0.1, issues=["No cited source"])
        ]
        sufficient, tasks, reasoning = reflection_agent.reflect("query", "answer", ver_bad, ["past search query"])
        assert sufficient is False
        assert len(tasks) > 0
        assert isinstance(tasks[0], TaskDecomposition)
    finally:
        clear_mock_responses()

def test_orchestrator_end_to_end_loop():
    import uuid
    uuid_s = str(uuid.uuid5(uuid.NAMESPACE_DNS, "s1"))
    uuid_c = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c1"))
    
    # Seed mock data
    retriever.index_chunks("statutes", [
        {"id": uuid_s, "text": "Section 138 of Negotiable Instruments Act notice timeline is 30 days.", "metadata": {"doc_type": "central_act", "filename": "statute1.txt"}}
    ])
    retriever.index_chunks("cases", [
        {"id": uuid_c, "text": "Dalmia Cement holds 30-day notice is mandatory.", "metadata": {"doc_type": "sc_judgment", "filename": "case1.txt"}}
    ])

    response = orchestrator.run_research("What is the cheque bounce notice timeline in India?", max_iterations=2)
    
    assert response.session_id is not None
    assert response.answer != ""
    assert len(response.citations) > 0
    assert len(response.verification_results) > 0
    assert response.iterations >= 1
    assert len(response.trace) > 0

    # Verify session logs were written to SQLite
    session_record = db.get_session(response.session_id)
    assert session_record is not None
    assert session_record["iterations"] == response.iterations

    trace_logs = db.get_logs(response.session_id)
    assert len(trace_logs) > 0
    assert any(log["step_name"].startswith("Iteration 1 Start") for log in trace_logs)


def test_orchestrator_reflection_recovery_loop():
    from backend.app.core.llm import set_mock_response, clear_mock_responses
    import uuid
    
    # 1. Seed two items
    uuid_ni = str(uuid.uuid5(uuid.NAMESPACE_DNS, "ni_138_test"))
    uuid_lease = str(uuid.uuid5(uuid.NAMESPACE_DNS, "lease_test"))
    
    # Custom documents index
    retriever.index_chunks("statutes", [
        {
            "id": uuid_ni, 
            "text": "Under Section 138 of Negotiable Instruments Act, 1881 notice must be given within 30 days.", 
            "metadata": {"doc_type": "central_act", "section": "138", "filename": "negotiable_instruments_act_1881.txt"}
        }
    ])
    retriever.index_chunks("legal_documents", [
        {
            "id": uuid_lease, 
            "text": "Section 1. Rent shall be paid by cheque. In case of return, payee has 60 days to give notice.", 
            "metadata": {"doc_type": "user_upload", "filename": "sample_lease_agreement.txt"}
        }
    ])

    # Let's register mock responses dynamically to simulate the two-cycle loop
    # Iteration 2 overrides (highest priority)
    set_mock_response(
        "synthesis: Act, 1881",
        {
            "answer": "No, the 60-day clause is invalid because Section 138 of the Negotiable Instruments Act mandates notice within 30 days [2].",
            "conflicts": ["Contract clause contradicts Section 138 NI Act"]
        }
    )
    
    set_mock_response(
        "verification: clause is invalid",
        {
            "verification_results": [
                {
                    "claim": "The 60-day notice clause is invalid under Section 138.",
                    "supported": True,
                    "evidence_index": 2,
                    "confidence": 0.98,
                    "issues": [],
                    "importance": "high",
                    "verification_status": "supported",
                    "evidence_links": [
                        {"evidence_index": 2, "relationship": "supports"}
                    ]
                }
            ]
        }
    )
    
    set_mock_response(
        "reflection: completed using Section 138",
        {
            "sufficient": True,
            "reasoning": "Legality verification completed using Section 138 NI Act.",
            "follow_up_tasks": []
        }
    )

    # General Agent fallbacks (Iteration 1)
    set_mock_response(
        "coordinator: Does the cheque notice",
        {
            "tasks": [
                {"query": "cheque notice in lease", "agent": "legal_document", "reason": "inspect lease agreement"}
            ]
        }
    )
    
    set_mock_response(
        "synthesis: payee has 60 days",
        {
            "answer": "Yes, under the agreement the landlord has 60 days to issue notice [1].",
            "conflicts": []
        }
    )
    
    set_mock_response(
        "verification: landlord has 60 days",
        {
            "verification_results": [
                {
                    "claim": "Landlord has 60 days to issue notice.",
                    "supported": False,
                    "evidence_index": 1,
                    "confidence": 0.9,
                    "issues": ["No statutory basis verified yet."],
                    "importance": "high",
                    "verification_status": "insufficient_evidence",
                    "evidence_links": [
                        {"evidence_index": 1, "relationship": "insufficient"}
                    ]
                }
            ]
        }
    )
    
    set_mock_response(
        "reflection: no statutory basis",
        {
            "sufficient": False,
            "reasoning": "Need to verify if 60 days complies with Section 138 of NI Act.",
            "follow_up_tasks": [
                {"query": "completed using Section 138", "agent": "statute", "reason": "verify statutory compliance"}
            ]
        }
    )

    try:
        response = orchestrator.run_research(
            "Does the cheque notice clause in the lease comply with Indian law?", 
            max_iterations=2
        )
        
        assert response.iterations == 2
        assert "Negotiable Instruments Act" in response.answer
        assert len(response.verification_results) > 0
        assert response.verification_results[0].verification_status == "supported"
    finally:
        clear_mock_responses()
