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
        Evidence(id="ev1", text="Civil Code § 1950.5 requires landlord return deposit in 21 days.", source="Statute Title 11", doc_type="statute", score=0.9),
        Evidence(id="ev2", text="Granberry case held failure to return in 21 days forfeits right to retain.", source="Granberry v Covas", doc_type="case", score=0.8)
    ]
    
    res = synthesis_agent.synthesize("What is the refund timeline?", evidence)
    assert "answer" in res
    assert "conflicts" in res

def test_verification_agent():
    evidence = [
        Evidence(id="ev1", text="Civil Code § 1950.5 requires landlord return deposit in 21 days.", source="Statute Title 11", doc_type="statute", score=0.9)
    ]
    
    # Text with citation
    answer = "A landlord must return the security deposit in 21 days [1]."
    results = verification_agent.verify(answer, evidence)
    
    assert len(results) > 0
    # First result should be the verified claim
    assert results[0].claim != ""
    assert results[0].supported is True
    assert results[0].citation_correct is True

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
        {"id": uuid_s, "text": "California Code § 1950.5 timeline is 21 days.", "metadata": {"doc_type": "statute", "filename": "statute1.txt"}}
    ])
    retriever.index_chunks("cases", [
        {"id": uuid_c, "text": "Granberry holds 21-day timeline forfeiture.", "metadata": {"doc_type": "case", "filename": "case1.txt"}}
    ])

    response = orchestrator.run_research("What is the security deposit return timeline in California?", max_iterations=2)
    
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
