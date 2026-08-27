import os
from backend.app.ingestion.parser import chunk_text, extract_metadata_from_filename
from backend.app.ingestion.indexer import ingest_file
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever

def test_chunk_text():
    sample_text = "This is a simple sentence. " * 50  # 250 words total approx
    chunks = chunk_text(sample_text, max_chunk_words=100, overlap_words=10)
    assert len(chunks) > 1
    assert all("text" in c and "id" in c for c in chunks)

def test_extract_metadata_from_filename():
    meta_case = extract_metadata_from_filename("dalmia_cement_v_galaxy_traders_2001.txt")
    assert meta_case["doc_type"] == "sc_judgment"
    assert "Supreme Court" in meta_case["court"]
    assert meta_case["judgment_date"] == "2001-01-01"
    assert "dalmia cement v. galaxy traders" in meta_case["case_name"].lower()

    meta_statute = extract_metadata_from_filename("negotiable_instruments_act_1881.txt")
    assert meta_statute["doc_type"] == "central_act"
    
    meta_custom = extract_metadata_from_filename("my_private_lease.txt")
    assert meta_custom["doc_type"] == "user_upload"

def test_ingest_file(tmp_path):
    # Create temp mock file
    test_file = tmp_path / "mock_statute_code_title_10.txt"
    test_file.write_text("Section 101. This represents some statutory law provision content text.\n\nSection 102. Another provision item.")
    
    chunks_count = ingest_file(str(test_file), metadata_override={"jurisdiction": "India"}, collection_name="test_statutes")
    assert chunks_count > 0
    
    # Verify metadata saved in SQLite
    documents = db.get_documents()
    assert len(documents) == 1
    assert documents[0]["filename"] == "mock_statute_code_title_10.txt"
    assert documents[0]["doc_type"] == "central_act"
    assert documents[0]["metadata"]["jurisdiction"] == "India"

    # Verify indexed in Qdrant collection
    scroll_res, _ = retriever.client.scroll(collection_name="test_statutes")
    assert len(scroll_res) == chunks_count
    assert scroll_res[0].payload["metadata"]["jurisdiction"] == "India"

def test_ingestion_idempotency_and_versioning(tmp_path):
    # 1. Ingest a file first time
    test_file = tmp_path / "negotiable_instruments_act_1881.txt"
    test_file.write_text("Original Section 138: Notice timeline is 15 days from receipt.")
    
    chunks_1 = ingest_file(str(test_file), collection_name="test_statutes")
    assert chunks_1 > 0
    
    docs_1 = db.get_documents()
    assert len(docs_1) == 1
    doc_1 = docs_1[0]
    assert doc_1["version"] == 1
    assert doc_1["status"] == "ACTIVE"
    assert doc_1["content_hash"] is not None
    
    # Verify vector has status ACTIVE in Qdrant
    scroll_1, _ = retriever.client.scroll(collection_name="test_statutes")
    assert all(p.payload["metadata"]["status"] == "ACTIVE" for p in scroll_1)
    
    # 2. Ingest the same file again (same contents, same name) -> Idempotent skip
    chunks_2 = ingest_file(str(test_file), collection_name="test_statutes")
    # Ingestion skipped, chunks returned matches
    assert chunks_2 == chunks_1
    
    docs_2 = db.get_documents()
    assert len(docs_2) == 1  # No duplicate document created
    
    # 3. Modify content and ingest (same filename, changed contents) -> Create version 2
    test_file.write_text("Amended Section 138: Notice timeline is updated to 30 days from receipt.")
    chunks_3 = ingest_file(str(test_file), collection_name="test_statutes")
    assert chunks_3 > 0
    
    docs_3 = db.get_documents()
    assert len(docs_3) == 2  # New logical version created
    
    # Find version 1 and version 2 documents
    v1_doc = next(d for d in docs_3 if d["version"] == 1)
    v2_doc = next(d for d in docs_3 if d["version"] == 2)
    
    assert v1_doc["status"] == "SUPERSEDED"
    assert v2_doc["status"] == "ACTIVE"
    assert v2_doc["parent_doc_id"] == v1_doc["doc_id"]
    
    # Verify status updates in Qdrant payload
    scroll_3, _ = retriever.client.scroll(collection_name="test_statutes")
    v1_points = [p for p in scroll_3 if p.payload["metadata"]["document_id"] == v1_doc["doc_id"]]
    v2_points = [p for p in scroll_3 if p.payload["metadata"]["document_id"] == v2_doc["doc_id"]]
    
    assert len(v1_points) > 0
    assert len(v2_points) > 0
    assert all(p.payload["metadata"]["status"] == "SUPERSEDED" for p in v1_points)
    assert all(p.payload["metadata"]["status"] == "ACTIVE" for p in v2_points)

    # 4. Search dynamic filtering
    # Active search (should exclude superseded)
    active_search = retriever.search_hybrid(collection_name="test_statutes", query="Section 138 timeline", limit=10)
    assert len(active_search) > 0
    # All retrieved active search results must be ACTIVE status
    assert all(r["metadata"].get("status") == "ACTIVE" for r in active_search)

    # Historical search (using query matching 'histor' or 'supersed' or 'previous')
    historical_search = retriever.search_hybrid(collection_name="test_statutes", query="historical timeline of Section 138", limit=10)
    assert len(historical_search) > 0
    # Can fetch superseded version
    has_superseded = any(r["metadata"].get("status") == "SUPERSEDED" for r in historical_search)
    assert has_superseded, "Historical search should be able to fetch superseded versions."
