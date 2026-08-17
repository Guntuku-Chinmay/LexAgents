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
    meta_case = extract_metadata_from_filename("brown_v_board_of_education_supreme_court_1954.txt")
    assert meta_case["doc_type"] == "sc_judgment"
    assert "Supreme Court" in meta_case["court"]
    assert meta_case["judgment_date"] == "1954-01-01"
    assert "brown v. board of education" in meta_case["case_name"].lower()

    meta_statute = extract_metadata_from_filename("california_civil_code_section_1950_5.txt")
    assert meta_statute["doc_type"] == "central_act"
    
    meta_custom = extract_metadata_from_filename("my_private_lease.txt")
    assert meta_custom["doc_type"] == "user_upload"

def test_ingest_file(tmp_path):
    # Create temp mock file
    test_file = tmp_path / "mock_statute_code_title_10.txt"
    test_file.write_text("Section 101. This represents some statutory law provision content text.\n\nSection 102. Another provision item.")
    
    chunks_count = ingest_file(str(test_file), metadata_override={"jurisdiction": "California"}, collection_name="test_statutes")
    assert chunks_count > 0
    
    # Verify metadata saved in SQLite
    documents = db.get_documents()
    assert len(documents) == 1
    assert documents[0]["filename"] == "mock_statute_code_title_10.txt"
    assert documents[0]["doc_type"] == "central_act"
    assert documents[0]["metadata"]["jurisdiction"] == "California"

    # Verify indexed in Qdrant collection
    scroll_res, _ = retriever.client.scroll(collection_name="test_statutes")
    assert len(scroll_res) == chunks_count
    assert scroll_res[0].payload["metadata"]["jurisdiction"] == "California"
