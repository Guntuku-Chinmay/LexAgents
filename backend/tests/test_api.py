import io
from fastapi.testclient import TestClient
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever

def test_health_check(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"

def test_root_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"
    assert response.json()["service"] == "LexAgents API"

def test_cors_headers(client):
    headers = {
        "Origin": "https://lex-agents.vercel.app",
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type"
    }
    response = client.options("/api/research", headers=headers)
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "https://lex-agents.vercel.app"

    bad_headers = {
        "Origin": "https://unauthorized-domain.com",
        "Access-Control-Request-Method": "POST"
    }
    bad_response = client.options("/api/research", headers=bad_headers)
    assert bad_response.headers.get("access-control-allow-origin") is None

def test_conduct_research_api(client):
    import uuid
    uuid_s = str(uuid.uuid5(uuid.NAMESPACE_DNS, "s1"))
    
    # Seed mock data
    retriever.index_chunks("statutes", [
        {"id": uuid_s, "text": "Section 138 of Negotiable Instruments Act notice timeline is 30 days.", "metadata": {"doc_type": "central_act", "filename": "statute1.txt"}}
    ])
    
    payload = {
        "query": "Does the cheque notice clause in the lease agreement allowing 60 days comply with Indian law?",
        "use_web": False
    }
    response = client.post("/api/research", json=payload)
    assert response.status_code == 200
    
    data = response.json()
    assert "session_id" in data
    assert "answer" in data
    assert "citations" in data
    assert "verification_results" in data

def test_document_upload_api(client):
    file_content = b"Section 5. Cheque bounce notice period. Any unpaid rent cheque delay beyond 60 days entitles Rajesh Kumar to evict."
    file_data = {"file": ("lease_clause_eviction.txt", io.BytesIO(file_content), "text/plain")}
    
    response = client.post("/api/documents/upload", files=file_data)
    assert response.status_code == 200
    
    data = response.json()
    assert data["status"] == "success"
    assert data["filename"] == "lease_clause_eviction.txt"
    assert data["chunks_ingested"] == 1

def test_get_source_api(client):
    import uuid
    uuid_c = str(uuid.uuid5(uuid.NAMESPACE_DNS, "c_source_1"))
    
    # Seed point
    retriever.index_chunks("cases", [
        {"id": uuid_c, "text": "Granberry v Covas judgment holds timeline rule.", "metadata": {"doc_type": "case", "filename": "case1.txt"}}
    ])
    
    response = client.get(f"/api/sources/{uuid_c}")
    assert response.status_code == 200
    assert response.json()["id"] == uuid_c
    assert response.json()["doc_type"] == "case"

    # Test non-existent source
    response_not_found = client.get("/api/sources/missing_id")
    assert response_not_found.status_code == 404

def test_evaluation_endpoints(client):
    # Trigger evaluation run
    # Needs a mock benchmark file created at the expected test path, which we have at data/benchmark/legal_queries.json
    response_eval = client.post("/api/evaluate")
    assert response_eval.status_code == 200
    assert response_eval.json()["status"] == "success"
    assert len(response_eval.json()["results"]) > 0

    # Retrieve evaluation history list
    response_history = client.get("/api/evaluation/results")
    assert response_history.status_code == 200
    assert len(response_history.json()) > 0

def test_get_observability_api(client):
    import uuid
    session_id = str(uuid.uuid4())
    db.create_session(session_id, "Test Query")
    db.add_log(session_id, "Decomposition (Iteration 1)", "trace", {
        "tasks": [{"query": "subtask 1", "agent": "statute", "reason": "reason 1"}]
    })
    db.add_log(session_id, "Verification (Iteration 1)", "trace", {
        "verification_results": [
            {
                "claim": "Test claim text",
                "supported": True,
                "confidence": 0.95,
                "issues": [],
                "importance": "high",
                "verification_status": "supported",
                "evidence_links": [
                    {
                        "evidence_index": 1,
                        "evidence_id": "ev_id_1",
                        "relationship": "supports"
                    }
                ]
            }
        ]
    })
    
    response = client.get(f"/api/sessions/{session_id}/observability")
    assert response.status_code == 200
    data = response.json()
    assert "session" in data
    assert "observability" in data
    assert len(data["observability"]["tasks"]) > 0
    assert data["observability"]["tasks"][0]["agent_name"] == "statute"
    
    assert len(data["observability"]["verifications"]) > 0
    assert data["observability"]["verifications"][0]["verification_status"] == "supported"
    assert data["observability"]["verifications"][0]["importance"] == "high"
    assert len(data["observability"]["verifications"][0]["evidence_links"]) > 0
    assert data["observability"]["verifications"][0]["evidence_links"][0]["relationship"] == "supports"
