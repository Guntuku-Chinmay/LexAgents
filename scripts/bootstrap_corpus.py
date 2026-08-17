import os
import sys
import logging

# Add project root to python path to avoid import errors
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.app.ingestion.indexer import ingest_file, ingest_directory
from backend.app.retrieval.vector_bm25 import retriever

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("bootstrap_corpus")

def bootstrap():
    logger.info("Initializing LexAgents Corpus...")
    
    # 1. Clean existing collections to ensure reproducible state
    retriever.delete_collection("cases")
    retriever.delete_collection("statutes")
    retriever.delete_collection("legal_documents")
    
    # 2. Ingest Cases
    cases_dir = "data/corpus/cases"
    if os.path.exists(cases_dir):
        logger.info(f"Ingesting cases from {cases_dir}...")
        count = ingest_directory(cases_dir, doc_type_override=None)
        logger.info(f"Ingested {count} case chunks.")
    else:
        logger.error(f"Cases directory not found: {cases_dir}")

    # 3. Ingest Statutes
    statutes_dir = "data/corpus/statutes"
    if os.path.exists(statutes_dir):
        logger.info(f"Ingesting statutes from {statutes_dir}...")
        count = ingest_directory(statutes_dir, doc_type_override=None)
        logger.info(f"Ingested {count} statute chunks.")
    else:
        logger.error(f"Statutes directory not found: {statutes_dir}")

    # 4. Ingest Sample Lease Agreement as a user uploaded document
    lease_path = "data/corpus/sample_lease_agreement.txt"
    if os.path.exists(lease_path):
        logger.info(f"Ingesting sample lease agreement from {lease_path}...")
        count = ingest_file(lease_path, metadata_override={"doc_type": "user_upload"}, collection_name="legal_documents")
        logger.info(f"Ingested {count} lease agreement chunks.")
    else:
        logger.error(f"Lease path not found: {lease_path}")

    logger.info("LexAgents Corpus Bootstrapped successfully!")

if __name__ == "__main__":
    bootstrap()
