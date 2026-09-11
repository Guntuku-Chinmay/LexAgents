import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from backend.app.api.endpoints import router as api_router
from backend.app.core.config import settings

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("lexagents_backend")

app = FastAPI(
    title="LexAgents: Multi-Agent Collaborative Legal RAG System",
    description="An AI-assisted legal research platform with specialized retrieval, evidence verification, and iterative self-reflection.",
    version="1.0.0"
)

# CORS configuration
origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",") if origin.strip()]
logger.info(f"Configured CORS Allowed Origins: {origins}")

is_wildcard = "*" in origins
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=not is_wildcard,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def root_info():
    """Root service information."""
    return {
        "service": "LexAgents API",
        "status": "healthy",
        "version": "1.0.0",
        "description": "Multi-Agent Collaborative RAG for Indian Legal Research",
        "endpoints": {
            "health": "/health",
            "api_health": "/api/health",
            "docs": "/docs",
            "research": "/api/research"
        }
    }

@app.get("/health")
def health_check():
    """Service health check."""
    return {"status": "healthy", "service": "LexAgents API"}

# Register API Router
app.include_router(api_router)

# Mount Frontend static files if built index exists
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
if os.path.exists(os.path.join(frontend_dir, "out", "index.html")):
    app.mount("/", StaticFiles(directory=os.path.join(frontend_dir, "out"), html=True), name="frontend")

@app.on_event("startup")
def startup_event():
    logger.info("Initializing LexAgents Backend System...")
    logger.info(f"Using SQLite DB path: {settings.SQLITE_DB_PATH}")
    logger.info(f"Using Qdrant DB path: {settings.QDRANT_STORAGE_PATH}")

    # Auto-bootstrap corpus if database is unseeded and not in unit test mock mode
    if os.environ.get("MOCK_LLM", "False").lower() not in ("true", "1", "yes"):
        try:
            from backend.app.database.db_manager import db
            docs = db.get_documents()
            if not docs:
                logger.info("No documents found in database. Auto-bootstrapping Indian legal corpus...")
                from scripts.bootstrap_corpus import bootstrap
                bootstrap()
        except Exception as e:
            logger.warning(f"Auto-bootstrap check skipped or encountered error: {e}")
