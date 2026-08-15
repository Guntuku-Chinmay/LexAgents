import os
import pytest
import shutil
from fastapi.testclient import TestClient

# Force Mock LLM and separate paths for testing
os.environ["MOCK_LLM"] = "True"
os.environ["OPENAI_API_KEY"] = "mock-key-for-testing"
os.environ["SQLITE_DB_PATH"] = "backend/app/database/test_lexagents.db"
os.environ["QDRANT_STORAGE_PATH"] = "data/test_qdrant_db"

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.database.db_manager import db
from backend.app.retrieval.vector_bm25 import retriever

@pytest.fixture(scope="session", autouse=True)
def setup_test_directories():
    """Ensure test directories are created and clean."""
    os.makedirs("data/test_qdrant_db", exist_ok=True)
    os.makedirs("backend/app/database", exist_ok=True)
    yield
    # Clean up test files after test suite completes (ignore windows file lock issues)
    try:
        if os.path.exists("backend/app/database/test_lexagents.db"):
            os.remove("backend/app/database/test_lexagents.db")
    except Exception as e:
        pass
    try:
        if os.path.exists("data/test_qdrant_db"):
            shutil.rmtree("data/test_qdrant_db")
    except Exception as e:
        pass

@pytest.fixture(autouse=True)
def clean_database():
    """Ensure a clean database state for each test."""
    # Reset SQLite tables
    with db._get_connection() as conn:
        conn.execute("DELETE FROM logs")
        conn.execute("DELETE FROM sessions")
        conn.execute("DELETE FROM documents")
        conn.execute("DELETE FROM evaluations")
        conn.commit()
        
    # Clear collections in Qdrant
    retriever.delete_collection("cases")
    retriever.delete_collection("statutes")
    retriever.delete_collection("legal_documents")
    retriever.delete_collection("test_statutes")
    
    yield

@pytest.fixture
def client():
    """Get TestClient for FastAPI endpoints."""
    with TestClient(app) as c:
        yield c
