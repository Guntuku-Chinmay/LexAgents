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

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    """Service health check."""
    return {"status": "healthy", "service": "LexAgents API"}

# Register API Router
app.include_router(api_router)

# Mount Frontend static files
# Root mount must come after specific routers to avoid overriding them
frontend_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "frontend"))
os.makedirs(frontend_dir, exist_ok=True)

app.mount("/", StaticFiles(directory=frontend_dir, html=True), name="frontend")

@app.on_event("startup")
def startup_event():
    logger.info("Initializing LexAgents Backend System...")
    logger.info(f"Using SQLite DB path: {settings.SQLITE_DB_PATH}")
    logger.info(f"Using Qdrant DB path: {settings.QDRANT_STORAGE_PATH}")
