import os
import json
import uuid
import datetime
import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.core.config import settings
from backend.app.database.models import (
    Base, User, Session as DBSession, Log as DBLog, Query as DBQuery,
    AgentTask as DBAgentTask, AgentRun as DBAgentRun, Document as DBDocument,
    Source as DBSource, Claim as DBClaim, VerificationResultModel,
    ClaimSourceLink, ReflectionCycle, Evaluation as DBEvaluation,
    EvaluationResultModel
)

logger = logging.getLogger(__name__)

class DBManager:
    def __init__(self):
        # Configure database URL. If none provided, default to local SQLite path
        db_url = settings.DATABASE_URL
        if not db_url:
            db_url = f"sqlite:///{settings.SQLITE_DB_PATH}"
            
        connect_args = {}
        if db_url.startswith("sqlite"):
            connect_args = {"check_same_thread": False}
            
        logger.info(f"Connecting DBManager to: {db_url}")
        self.engine = create_engine(db_url, connect_args=connect_args)
        Base.metadata.create_all(self.engine)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def _get_db(self):
        db = self.SessionLocal()
        try:
            return db
        except Exception as e:
            db.close()
            raise e

    # Session CRUD
    def create_session(self, session_id: str, query: str):
        db = self._get_db()
        try:
            db_session = DBSession(
                session_id=session_id,
                query=query
            )
            db.add(db_session)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error in create_session: {e}")
            raise e
        finally:
            db.close()

    def update_session_answer(self, session_id: str, final_answer: str, iterations: int):
        db = self._get_db()
        try:
            session_obj = db.query(DBSession).filter_by(session_id=session_id).first()
            if session_obj:
                session_obj.final_answer = final_answer
                session_obj.iterations = iterations
                db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error in update_session_answer: {e}")
            raise e
        finally:
            db.close()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        db = self._get_db()
        try:
            s = db.query(DBSession).filter_by(session_id=session_id).first()
            if s:
                return {
                    "session_id": s.session_id,
                    "query": s.query,
                    "final_answer": s.final_answer,
                    "iterations": s.iterations,
                    "created_at": s.created_at.isoformat() if s.created_at else None
                }
            return None
        finally:
            db.close()

    # Logging / Trace
    def add_log(self, session_id: str, step_name: str, event_type: str, payload: Any):
        payload_str = json.dumps(payload)
        db = self._get_db()
        try:
            db_log = DBLog(
                session_id=session_id,
                step_name=step_name,
                event_type=event_type,
                payload=payload_str
            )
            db.add(db_log)
            
            # Enrich PostgreSQL observability tables by parsing standard trace step events
            self._parse_and_persist_observability(session_id, step_name, payload, db)
            
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error in add_log: {e}")
            raise e
        finally:
            db.close()

    def get_logs(self, session_id: str) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            logs = db.query(DBLog).filter_by(session_id=session_id).order_by(DBLog.log_id.asc()).all()
            result = []
            for l in logs:
                result.append({
                    "log_id": l.log_id,
                    "session_id": l.session_id,
                    "step_name": l.step_name,
                    "event_type": l.event_type,
                    "payload": json.loads(l.payload) if l.payload else {},
                    "created_at": l.created_at.isoformat() if l.created_at else None
                })
            return result
        finally:
            db.close()

    # Documents
    def add_document(self, doc_id: str, filename: str, doc_type: str, metadata: Dict[str, Any]):
        metadata_str = json.dumps(metadata)
        db = self._get_db()
        try:
            db_doc = DBDocument(
                doc_id=doc_id,
                filename=filename,
                doc_type=doc_type,
                metadata_json=metadata_str
            )
            db.merge(db_doc)
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error in add_document: {e}")
            raise e
        finally:
            db.close()

    def get_documents(self, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            if doc_type:
                docs = db.query(DBDocument).filter_by(doc_type=doc_type).all()
            else:
                docs = db.query(DBDocument).all()
            
            result = []
            for d in docs:
                result.append({
                    "doc_id": d.doc_id,
                    "filename": d.filename,
                    "doc_type": d.doc_type,
                    "metadata": json.loads(d.metadata_json) if d.metadata_json else {}
                })
            return result
        finally:
            db.close()

    # Evaluation
    def add_evaluation(self, eval_id: str, system_type: str, metrics: Dict[str, Any], config: Dict[str, Any]):
        db = self._get_db()
        try:
            db_eval = DBEvaluation(
                eval_id=eval_id,
                run_timestamp=datetime.datetime.utcnow(),
                system_type=system_type,
                metrics_json=json.dumps(metrics),
                config_json=json.dumps(config)
            )
            db.add(db_eval)
            
            # Enrich evaluation_results relational table
            # If metrics contains system runs (Baseline_A, Baseline_B, etc.)
            for sys_name in ["Baseline_A", "Baseline_B", "System_C", "System_D"]:
                if sys_name in metrics:
                    sys_metrics = metrics[sys_name]
                    result_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{eval_id}_{sys_name}"))
                    db.add(EvaluationResultModel(
                        result_id=result_id,
                        eval_id=eval_id,
                        query_id="macro_average",
                        system_type=sys_name,
                        latency=sys_metrics.get("avg_latency", 0.0),
                        iterations=int(sys_metrics.get("avg_iterations", 1.0)),
                        metrics_json=json.dumps(sys_metrics)
                    ))
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error in add_evaluation: {e}")
            raise e
        finally:
            db.close()

    def get_evaluations(self) -> List[Dict[str, Any]]:
        db = self._get_db()
        try:
            evals = db.query(DBEvaluation).order_by(DBEvaluation.run_timestamp.desc()).all()
            result = []
            for e in evals:
                result.append({
                    "eval_id": e.eval_id,
                    "run_timestamp": e.run_timestamp.isoformat() if e.run_timestamp else None,
                    "system_type": e.system_type,
                    "metrics": json.loads(e.metrics_json) if e.metrics_json else {},
                    "config": json.loads(e.config_json) if e.config_json else {}
                })
            return result
        finally:
            db.close()

    # --- Observability Persister ---
    def _parse_and_persist_observability(self, session_id: str, step_name: str, payload: Any, db):
        """
        Intercepts logging triggers from agent loops to write state to relational Postgres schemas.
        """
        try:
            # 1. Coordinator Decomposition Task mappings
            if "Decomposition" in step_name and isinstance(payload, dict):
                # Ensure query is mapped in queries table
                query_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_query"))
                existing_query = db.query(DBQuery).filter_by(query_id=query_id).first()
                if not existing_query:
                    session_obj = db.query(DBSession).filter_by(session_id=session_id).first()
                    db.add(DBQuery(
                        query_id=query_id,
                        session_id=session_id,
                        query_text=session_obj.query if session_obj else "Unknown Query"
                    ))
                
                # Log tasks mapped
                for idx, task in enumerate(payload.get("tasks", [])):
                    task_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_task_{step_name}_{idx}"))
                    db.merge(DBAgentTask(
                        task_id=task_id,
                        session_id=session_id,
                        query_text=task.get("query", ""),
                        agent_name=task.get("agent", ""),
                        reason=task.get("reason", "")
                    ))

            # 2. Agent run and retrievals logs
            elif "Retrieval" in step_name and isinstance(payload, dict):
                retrieval_iter = 1
                if "Iteration" in step_name:
                    try:
                        retrieval_iter = int(step_name.split("Iteration ")[1].split(")")[0])
                    except Exception:
                        pass
                
                # Record agent run details
                run_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_run_{step_name}"))
                db.merge(DBAgentRun(
                    run_id=run_id,
                    session_id=session_id,
                    agent_name="coordinator_search",
                    status="completed",
                    started_at=datetime.datetime.utcnow(),
                    completed_at=datetime.datetime.utcnow(),
                    duration=0.0,
                    retrieval_iteration=retrieval_iter,
                    source_count=payload.get("retrieved_count", 0)
                ))

                # Feed individual sources chunks
                for item in payload.get("evidence_list", []):
                    source_id = item.get("id")
                    if source_id:
                        doc_id = item.get("metadata", {}).get("document_id") or "global_source"
                        db.merge(DBSource(
                            source_id=source_id,
                            doc_id=doc_id,
                            text=item.get("text", ""),
                            metadata_json=json.dumps(item.get("metadata", {}))
                        ))

            elif "Verification" in step_name and isinstance(payload, dict):
                for idx, item in enumerate(payload.get("verification_results", [])):
                    claim_text = item.get("claim", "")
                    supported = bool(item.get("supported", False))
                    confidence = float(item.get("confidence", 0.5))
                    issues = item.get("issues", [])
                    evidence_ids = item.get("evidence_ids", [])
                    
                    status = item.get("verification_status") or ("supported" if supported else "unsupported")
                    importance = item.get("importance") or "medium"
                    evidence_links = item.get("evidence_links") or []
                    
                    claim_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_claim_{idx}_{step_name[:15]}"))
                    db.merge(DBClaim(
                        claim_id=claim_id,
                        session_id=session_id,
                        claim_text=claim_text
                    ))
                    
                    verification_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_ver_{idx}_{step_name[:15]}"))
                    db.merge(VerificationResultModel(
                        verification_id=verification_id,
                        session_id=session_id,
                        claim_text=claim_text,
                        supported=supported,
                        confidence=confidence,
                        issues_json=json.dumps(issues),
                        verification_status=status,
                        importance=importance
                    ))
                    
                    if evidence_links:
                        for elink in evidence_links:
                            ev_id = elink.get("evidence_id")
                            rel = elink.get("relationship") or ("supports" if supported else "contradicts")
                            if ev_id:
                                link_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{verification_id}_{ev_id}"))
                                db.merge(ClaimSourceLink(
                                    link_id=link_id,
                                    verification_id=verification_id,
                                    source_id=ev_id,
                                    relationship=rel
                                ))
                    else:
                        for ev_id in evidence_ids:
                            link_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{verification_id}_{ev_id}"))
                            db.merge(ClaimSourceLink(
                                link_id=link_id,
                                verification_id=verification_id,
                                source_id=ev_id,
                                relationship="supports" if supported else "contradicts"
                            ))

            # 4. Reflection loops logs
            elif "Reflection" in step_name and isinstance(payload, dict):
                iteration = 1
                if "Iteration" in step_name:
                    try:
                        iteration = int(step_name.split("Iteration ")[1].split(")")[0])
                    except Exception:
                        pass
                cycle_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{session_id}_cycle_{iteration}"))
                db.merge(ReflectionCycle(
                    cycle_id=cycle_id,
                    session_id=session_id,
                    iteration=iteration,
                    reasoning=payload.get("reasoning", ""),
                    sufficient=bool(payload.get("sufficient", True))
                ))
        except Exception as persist_error:
            # Observability persister is non-blocking to protect execution thread
            logger.warning(f"Failed to record relational observability logs: {persist_error}")

    def clear_all_tables(self):
        db = self._get_db()
        try:
            for table in reversed(Base.metadata.sorted_tables):
                db.execute(table.delete())
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error clearing tables: {e}")
        finally:
            db.close()

    def _get_connection(self):
        class ConnWrapper:
            def __init__(self, connection):
                self.connection = connection
                self.trans = None
            def execute(self, statement, *args, **kwargs):
                from sqlalchemy import text
                if isinstance(statement, str):
                    statement = text(statement)
                return self.connection.execute(statement, *args, **kwargs)
            def commit(self):
                if self.trans:
                    self.trans.commit()
            def __enter__(self):
                self.trans = self.connection.begin()
                return self
            def __exit__(self, exc_type, exc_val, exc_tb):
                if exc_type:
                    if self.trans:
                        self.trans.rollback()
                else:
                    if self.trans:
                        try:
                            self.trans.commit()
                        except Exception:
                            pass
                self.connection.close()
        return ConnWrapper(self.engine.connect())
        
    def get_observability_data(self, session_id: str) -> Dict[str, Any]:
        db = self._get_db()
        try:
            tasks = db.query(DBAgentTask).filter_by(session_id=session_id).all()
            runs = db.query(DBAgentRun).filter_by(session_id=session_id).all()
            queries = db.query(DBQuery).filter_by(session_id=session_id).all()
            claims = db.query(DBClaim).filter_by(session_id=session_id).all()
            verifications = db.query(VerificationResultModel).filter_by(session_id=session_id).all()
            reflections = db.query(ReflectionCycle).filter_by(session_id=session_id).all()
            
            return {
                "tasks": [
                    {
                        "task_id": t.task_id,
                        "agent_name": t.agent_name,
                        "query_text": t.query_text,
                        "reason": t.reason,
                        "created_at": t.created_at.isoformat() if t.created_at else None
                    }
                    for t in tasks
                ],
                "runs": [
                    {
                        "run_id": r.run_id,
                        "agent_name": r.agent_name,
                        "status": r.status,
                        "started_at": r.started_at.isoformat() if r.started_at else None,
                        "completed_at": r.completed_at.isoformat() if r.completed_at else None,
                        "duration": r.duration,
                        "retrieval_iteration": r.retrieval_iteration,
                        "source_count": r.source_count,
                        "error": r.error
                    }
                    for r in runs
                ],
                "queries": [
                    {
                        "query_id": q.query_id,
                        "query_text": q.query_text,
                        "created_at": q.created_at.isoformat() if q.created_at else None
                    }
                    for q in queries
                ],
                "claims": [
                    {
                        "claim_id": c.claim_id,
                        "claim_text": c.claim_text,
                        "created_at": c.created_at.isoformat() if c.created_at else None
                    }
                    for c in claims
                ],
                "verifications": [
                    {
                        "verification_id": v.verification_id,
                        "claim_text": v.claim_text,
                        "supported": v.supported,
                        "confidence": v.confidence,
                        "issues": json.loads(v.issues_json) if v.issues_json else [],
                        "verification_status": v.verification_status,
                        "importance": v.importance,
                        "evidence_links": [
                            {
                                "evidence_id": link.source_id,
                                "relationship": link.relationship
                            }
                            for link in db.query(ClaimSourceLink).filter_by(verification_id=v.verification_id).all()
                        ],
                        "created_at": v.created_at.isoformat() if v.created_at else None
                    }
                    for v in verifications
                ],
                "reflections": [
                    {
                        "cycle_id": rf.cycle_id,
                        "iteration": rf.iteration,
                        "reasoning": rf.reasoning,
                        "sufficient": rf.sufficient,
                        "created_at": rf.created_at.isoformat() if rf.created_at else None
                    }
                    for rf in reflections
                ]
            }
        finally:
            db.close()

db = DBManager()
