import os
import uuid
import logging
from typing import List, Dict, Any, Optional
from backend.app.ingestion.parser import parse_and_chunk_file
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever

logger = logging.getLogger(__name__)

def get_collection_for_doc_type(doc_type: str) -> str:
    """Map document type to Qdrant collection name."""
    if doc_type == "case":
        return "cases"
    elif doc_type == "statute":
        return "statutes"
    else:
        return "legal_documents"

def ingest_file(filepath: str, metadata_override: Optional[Dict[str, Any]] = None, collection_name: Optional[str] = None) -> int:
    """
    Ingest a single file: parse it, store metadata in SQLite, and index in Qdrant.
    Returns the number of indexed chunks.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    logger.info(f"Ingesting file: {filepath}")
    
    # 1. Parse and chunk file
    chunks = parse_and_chunk_file(filepath, metadata_override)
    if not chunks:
        logger.warning(f"No chunks extracted from file: {filepath}")
        return 0

    # Get metadata from the first chunk
    doc_metadata = chunks[0]["metadata"]
    doc_type = doc_metadata.get("doc_type", "user_upload")
    filename = os.path.basename(filepath)
    
    # Generate stable unique document ID
    doc_id = doc_metadata.get("document_id") or str(uuid.uuid5(uuid.NAMESPACE_DNS, filename))
    
    # Add doc_id to all chunks metadata
    for chunk in chunks:
        chunk["metadata"]["document_id"] = doc_id

    # 2. Determine target collection
    if not collection_name:
        collection_name = get_collection_for_doc_type(doc_type)

    # 3. Save document meta in SQLite
    db.add_document(
        doc_id=doc_id,
        filename=filename,
        doc_type=doc_type,
        metadata=doc_metadata
    )

    # 4. Index chunks in Qdrant hybrid index
    retriever.index_chunks(collection_name, chunks)
    
    logger.info(f"Finished ingesting {filename}. {len(chunks)} chunks written to Qdrant collection '{collection_name}'")
    return len(chunks)

def ingest_directory(directory_path: str, doc_type_override: Optional[str] = None) -> int:
    """Ingest all compatible files in a directory."""
    if not os.path.isdir(directory_path):
        logger.warning(f"Directory not found: {directory_path}")
        return 0
        
    count = 0
    for root, _, files in os.walk(directory_path):
        for f in files:
            if f.endswith((".txt", ".md", ".json")):
                filepath = os.path.join(root, f)
                meta_override = {}
                if doc_type_override:
                    meta_override["doc_type"] = doc_type_override
                try:
                    count += ingest_file(filepath, metadata_override=meta_override)
                except Exception as e:
                    logger.error(f"Failed to ingest {filepath}: {e}")
    return count
