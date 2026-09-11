import os
import logging
import time
from qdrant_client.models import Filter, FieldCondition, MatchValue, PointIdsList
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.ingestion.indexer import ingest_file

logger = logging.getLogger("constitution_bootstrap")
logging.basicConfig(level=logging.INFO)

def bootstrap_constitution():
    start_time = time.time()
    logger.info("=== Starting Complete Constitution of India Corpus Bootstrap ===")
    
    # 1. Audit pre-existing records
    docs = db.get_documents()
    existing_const_docs = [
        d for d in docs 
        if "constitution" in (d.get("filename") or "").lower() or "constitution" in (d.get("title") or "").lower()
    ]
    logger.info(f"Found {len(existing_const_docs)} pre-existing Constitution document(s) in SQLite:")
    for d in existing_const_docs:
        logger.info(f"  - Doc ID: {d.get('doc_id')}, File: {d.get('filename')}, Status: {d.get('status')}, Version: {d.get('version')}")

    # Inspect pre-existing chunks in Qdrant
    retriever.init_collection("statutes")
    q_filter = Filter(must=[FieldCondition(key="metadata.filename", match=MatchValue(value="constitution_of_india.txt"))])
    old_points, _ = retriever.client.scroll(
        collection_name="statutes",
        scroll_filter=q_filter,
        limit=10000,
        with_payload=True,
        with_vectors=False
    )
    old_chunk_count = len(old_points)
    logger.info(f"Found {old_chunk_count} pre-existing Constitution chunk(s) in Qdrant 'statutes' collection.")
    
    # 2. Safe cleanup of old/stale records from Qdrant:
    # Preserve any non-constitution statutes (e.g. POSH, SEBI)
    from qdrant_client.http.models import PointStruct
    all_points, _ = retriever.client.scroll(
        collection_name="statutes",
        limit=10000,
        with_payload=True,
        with_vectors=True
    )
    non_const_points = [
        p for p in all_points 
        if p.payload.get("metadata", {}).get("filename") != "constitution_of_india.txt"
    ]
    logger.info(f"Preserving {len(non_const_points)} non-constitution points in statutes collection.")
    retriever.delete_collection("statutes")
    retriever.init_collection("statutes")
    if non_const_points:
        restore_points = [
            PointStruct(id=p.id, vector=p.vector, payload=p.payload)
            for p in non_const_points
        ]
        retriever.client.upsert(collection_name="statutes", points=restore_points)
        logger.info(f"Restored {len(restore_points)} non-constitution points.")

    # 3. Ingest complete authoritative Constitution
    const_file = os.path.abspath(r"data\corpus\statutes\constitution_of_india.txt")
    if not os.path.exists(const_file):
        raise FileNotFoundError(f"Canonical Constitution file not found at: {const_file}")
        
    logger.info(f"Ingesting canonical Constitution from {const_file}...")
    chunks_indexed = ingest_file(const_file, force_reindex=True)
    logger.info(f"Successfully indexed {chunks_indexed} chunks.")

    # 4. Post-ingestion audit
    final_points, _ = retriever.client.scroll(
        collection_name="statutes",
        scroll_filter=q_filter,
        limit=10000,
        with_payload=True,
        with_vectors=False
    )
    final_chunk_count = len(final_points)
    
    final_docs = db.get_documents()
    active_const_docs = [
        d for d in final_docs 
        if "constitution" in (d.get("filename") or "").lower() and d.get("status") == "ACTIVE"
    ]
    
    elapsed = time.time() - start_time
    logger.info("=== Bootstrap Complete ===")
    logger.info(f"Pre-existing chunks purged: {old_chunk_count}")
    logger.info(f"New chunks indexed in Qdrant: {final_chunk_count}")
    logger.info(f"Active Constitution document in DB: {active_const_docs[0].get('doc_id') if active_const_docs else 'None'}")
    logger.info(f"Bootstrap elapsed time: {elapsed:.2f} seconds")
    
    return {
        "pre_existing_docs": len(existing_const_docs),
        "purged_chunks": old_chunk_count,
        "final_chunks": final_chunk_count,
        "elapsed_seconds": elapsed,
        "active_doc_id": active_const_docs[0].get("doc_id") if active_const_docs else None
    }

if __name__ == "__main__":
    bootstrap_constitution()
