import os
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from backend.app.core.config import settings

class DBManager:
    def __init__(self, db_path: str = settings.SQLITE_DB_PATH):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Sessions Table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    query TEXT NOT NULL,
                    final_answer TEXT,
                    iterations INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Logs Table for trace history
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    step_name TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES sessions (session_id)
                )
            """)
            
            # Documents metadata table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS documents (
                    doc_id TEXT PRIMARY KEY,
                    filename TEXT NOT NULL,
                    doc_type TEXT NOT NULL,
                    metadata_json TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Evaluation results table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS evaluations (
                    eval_id TEXT PRIMARY KEY,
                    run_timestamp TIMESTAMP NOT NULL,
                    system_type TEXT NOT NULL,
                    metrics_json TEXT NOT NULL,
                    config_json TEXT NOT NULL
                )
            """)
            conn.commit()

    # Session CRUD
    def create_session(self, session_id: str, query: str):
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO sessions (session_id, query) VALUES (?, ?)",
                (session_id, query)
            )
            conn.commit()

    def update_session_answer(self, session_id: str, final_answer: str, iterations: int):
        with self._get_connection() as conn:
            conn.execute(
                "UPDATE sessions SET final_answer = ?, iterations = ? WHERE session_id = ?",
                (final_answer, iterations, session_id)
            )
            conn.commit()

    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if row:
                return dict(row)
            return None

    # Logging / Trace
    def add_log(self, session_id: str, step_name: str, event_type: str, payload: Any):
        payload_str = json.dumps(payload)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO logs (session_id, step_name, event_type, payload) VALUES (?, ?, ?, ?)",
                (session_id, step_name, event_type, payload_str)
            )
            conn.commit()

    def get_logs(self, session_id: str) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM logs WHERE session_id = ? ORDER BY log_id ASC",
                (session_id,)
            ).fetchall()
            logs = []
            for r in rows:
                d = dict(r)
                d["payload"] = json.loads(d["payload"])
                logs.append(d)
            return logs

    # Documents
    def add_document(self, doc_id: str, filename: str, doc_type: str, metadata: Dict[str, Any]):
        metadata_str = json.dumps(metadata)
        with self._get_connection() as conn:
            conn.execute(
                "INSERT OR REPLACE INTO documents (doc_id, filename, doc_type, metadata_json) VALUES (?, ?, ?, ?)",
                (doc_id, filename, doc_type, metadata_str)
            )
            conn.commit()

    def get_documents(self, doc_type: Optional[str] = None) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            if doc_type:
                rows = conn.execute(
                    "SELECT * FROM documents WHERE doc_type = ?", (doc_type,)
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM documents").fetchall()
            
            docs = []
            for r in rows:
                d = dict(r)
                d["metadata"] = json.loads(d["metadata_json"])
                del d["metadata_json"]
                docs.append(d)
            return docs

    # Evaluation
    def add_evaluation(self, eval_id: str, system_type: str, metrics: Dict[str, Any], config: Dict[str, Any]):
        now = datetime.utcnow().isoformat()
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO evaluations (eval_id, run_timestamp, system_type, metrics_json, config_json) VALUES (?, ?, ?, ?, ?)",
                (eval_id, now, system_type, json.dumps(metrics), json.dumps(config))
            )
            conn.commit()

    def get_evaluations(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM evaluations ORDER BY run_timestamp DESC").fetchall()
            evals = []
            for r in rows:
                d = dict(r)
                d["metrics"] = json.loads(d["metrics_json"])
                d["config"] = json.loads(d["config_json"])
                del d["metrics_json"]
                del d["config_json"]
                evals.append(d)
            return evals

db = DBManager()
