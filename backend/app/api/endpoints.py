import os
import shutil
import logging
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException
from pydantic import BaseModel

from backend.app.models.schemas import QueryRequest, ResearchResponse, Evidence, EvaluationRunResult
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever
from backend.app.agents.reflection import orchestrator
from backend.app.ingestion.indexer import ingest_file
from backend.app.evaluation.evaluator import Evaluator

router = APIRouter(prefix="/api")
logger = logging.getLogger(__name__)

class IngestRequest(BaseModel):
    filepath: str
    doc_type: Optional[str] = None
    collection_name: Optional[str] = None

@router.get("/health")
def health_check():
    """Basic service health check."""
    return {"status": "healthy", "service": "LexAgents API"}

@router.post("/research", response_model=ResearchResponse)
def conduct_research(request: QueryRequest):
    """
    Run the multi-agent collaborative RAG loop for a legal query.
    Returns final answer, verified citations, and detailed step-by-step trace.
    """
    try:
        response = orchestrator.run_research(
            query=request.query,
            session_id=request.session_id,
            use_web=request.use_web,
            max_iterations=3
        )
        return response
    except Exception as e:
        logger.error(f"Error conducting research: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/documents/upload")
def upload_document(file: UploadFile = File(...)):
    """
    Ingest a user-provided legal document (TXT, MD, or JSON) into the vector store.
    """
    allowed_exts = [".txt", ".md", ".json"]
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in allowed_exts:
        raise HTTPException(
            status_code=400, 
            detail=f"Invalid file format. Only {', '.join(allowed_exts)} are supported."
        )
        
    upload_dir = "data/corpus/user_uploads"
    os.makedirs(upload_dir, exist_ok=True)
    
    # Sanitize filename
    safe_filename = "".join([c for c in file.filename if c.isalpha() or c.isdigit() or c in "._- "]).strip()
    dest_path = os.path.join(upload_dir, safe_filename)
    
    try:
        # Save file to disk
        with open(dest_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Ingest file into legal_documents vector database
        chunks_count = ingest_file(
            filepath=dest_path,
            metadata_override={"doc_type": "user_upload"},
            collection_name="legal_documents"
        )
        
        return {
            "filename": safe_filename,
            "chunks_ingested": chunks_count,
            "status": "success",
            "message": f"Successfully indexed {chunks_count} clauses into document collection."
        }
    except Exception as e:
        logger.error(f"Failed to upload document: {e}")
        # Clean up failed file
        if os.path.exists(dest_path):
            os.remove(dest_path)
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/ingest")
def force_ingest(request: IngestRequest):
    """
    Force ingestion of a local file path.
    """
    if not os.path.exists(request.filepath):
        raise HTTPException(status_code=404, detail="Target file path not found.")
    try:
        meta_override = {}
        if request.doc_type:
            meta_override["doc_type"] = request.doc_type
            
        chunks = ingest_file(
            filepath=request.filepath,
            metadata_override=meta_override,
            collection_name=request.collection_name
        )
        return {"status": "success", "chunks_indexed": chunks}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/sources/{id}", response_model=Evidence)
def get_source(id: str):
    """
    Retrieve details and text content for a specific indexed chunk ID.
    """
    # Find document type from SQLite to know which collection to query in Qdrant
    # (Since chunk id is in Qdrant, check each collection or check our records)
    collections = ["cases", "statutes", "legal_documents"]
    for col in collections:
        try:
            points = retriever.client.retrieve(collection_name=col, ids=[id])
            if points:
                p = points[0]
                return Evidence(
                    id=str(p.id),
                    text=p.payload.get("text", ""),
                    source=p.payload.get("metadata", {}).get("filename", "Source"),
                    doc_type=p.payload.get("metadata", {}).get("doc_type", "unknown"),
                    score=1.0,
                    metadata=p.payload.get("metadata", {})
                )
        except Exception:
            continue
            
    raise HTTPException(status_code=404, detail=f"Source with chunk ID '{id}' not found.")

@router.get("/research/{session_id}")
def get_research_session(session_id: str):
    """
    Fetch the final answer and step-by-step trace logs of a research session.
    """
    session = db.get_session(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session ID not found.")
        
    logs = db.get_logs(session_id)
    return {
        "session": session,
        "trace": logs
    }

@router.post("/evaluate")
def run_evaluation():
    """
    Trigger the evaluation pipeline against the legal benchmark.
    """
    try:
        evaluator = Evaluator()
        results = evaluator.evaluate_all(use_web=False)
        return {
            "status": "success",
            "message": f"Successfully completed evaluation on {len(results)} queries.",
            "results": results
        }
    except Exception as e:
        logger.error(f"Evaluation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/evaluation/results", response_model=List[EvaluationRunResult])
def get_evaluation_runs():
    """
    List all past evaluation runs stored in SQLite.
    """
    try:
        evals = db.get_evaluations()
        results = []
        for ev in evals:
            results.append(
                EvaluationRunResult(
                    eval_id=ev["eval_id"],
                    run_timestamp=ev["run_timestamp"],
                    system_type=ev["system_type"],
                    metrics=ev["metrics"],
                    config=ev["config"]
                )
            )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
