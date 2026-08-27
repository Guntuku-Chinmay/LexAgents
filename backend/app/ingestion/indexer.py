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
    if doc_type in ["case", "sc_judgment", "hc_judgment"]:
        return "cases"
    elif doc_type in ["statute", "constitutional", "constitutional_amendment", "central_act", "state_act", "rules", "regulation", "government_notification", "government_order", "government_circular"]:
        return "statutes"
    else:
        return "legal_documents"

def ingest_file(filepath: str, metadata_override: Optional[Dict[str, Any]] = None, collection_name: Optional[str] = None) -> int:
    """
    Ingest a single file: parse it, verify SHA-256 hash duplication, and handle versioning.
    Returns the number of indexed chunks.
    """
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"File not found: {filepath}")

    # 1. Compute SHA-256 content hash
    import hashlib
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        buf = f.read()
        hasher.update(buf)
    content_hash = hasher.hexdigest()

    logger.info(f"Ingesting file: {filepath} (SHA-256: {content_hash})")

    # 2. Parse and chunk file
    chunks = parse_and_chunk_file(filepath, metadata_override)
    if not chunks:
        logger.warning(f"No chunks extracted from file: {filepath}")
        return 0

    # Get metadata from the first chunk
    doc_metadata = chunks[0]["metadata"]
    doc_type = doc_metadata.get("doc_type", "user_upload")
    filename = os.path.basename(filepath)

    # 3. Duplicate Detection Check
    existing_by_hash = db.get_document_by_hash(content_hash)
    if existing_by_hash:
        logger.info(f"Duplicate content detected for {filename} (SHA-256: {content_hash}). Skipping indexing.")
        return len(chunks)

    # 4. Versioning and Lifecycle Status
    existing_by_filename = db.get_document_by_filename(filename)
    
    version = 1
    parent_doc_id = None
    
    if existing_by_filename:
        prev_doc_id = existing_by_filename["doc_id"]
        prev_version = existing_by_filename["version"]
        parent_doc_id = existing_by_filename["parent_doc_id"] or prev_doc_id
        version = prev_version + 1
        
        # Supercede previous active version in database and Qdrant
        db.update_document_status(prev_doc_id, "SUPERSEDED")
        retriever.update_document_status_payload(prev_doc_id, "SUPERSEDED")
        logger.info(f"Superseding previous version {prev_version} (ID: {prev_doc_id}) of {filename} with version {version}")

    # Generate stable unique document ID for this version
    doc_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{filename}_v{version}"))

    # Add payload metadata to chunks
    for chunk in chunks:
        chunk["metadata"]["document_id"] = doc_id
        chunk["metadata"]["parent_doc_id"] = parent_doc_id
        chunk["metadata"]["version"] = version
        chunk["metadata"]["status"] = "ACTIVE"
        chunk["metadata"]["content_hash"] = content_hash
        chunk["metadata"]["authority"] = doc_metadata.get("authority_level", "TIER 4")

    # 5. Determine target collection
    if not collection_name:
        collection_name = get_collection_for_doc_type(doc_type)

    # 6. Save document meta in DB
    db.add_document(
        doc_id=doc_id,
        filename=filename,
        doc_type=doc_type,
        metadata=doc_metadata,
        content_hash=content_hash,
        version=version,
        status="ACTIVE",
        parent_doc_id=parent_doc_id
    )

    # 7. Index chunks in Qdrant hybrid index
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
