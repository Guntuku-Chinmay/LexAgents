# Setup & Installation Guide

This document describes how to configure, initialize, and deploy LexAgents in your local environment or using Docker.

---

## 1. Prerequisites
- **Python 3.10+**
- **Node.js 18+** & `npm`
- **Docker** & **Docker Compose** (Optional, recommended for PostgreSQL/Qdrant services)

---

## 2. Option A: Quickstart via Docker Compose (Recommended)

You can run the entire system with zero manual service setup using Docker Compose:

1. Clone the repository:
   ```bash
   git clone https://github.com/Guntuku-Chinmay/LexAgents.git
   cd LexAgents
   ```
2. Build and launch all services:
   ```bash
   docker-compose up --build
   ```
This starts:
- **Next.js Web Client**: [http://localhost:3000](http://localhost:3000)
- **FastAPI backend API**: [http://localhost:8000](http://localhost:8000)
- **PostgreSQL Database**: Port `5432`
- **Qdrant Vector DB**: Port `6333`

---

## 3. Option B: Local Manual Setup

If you prefer to run services manually on your local system:

### 1. Backend REST API
1. Navigate to the root directory and create virtual environment:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # On Windows
   # or
   source .venv/bin/activate # On macOS/Linux
   ```
2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Copy environment template to `.env`:
   ```bash
   cp .env.example .env
   ```
4. Adjust config variables in `.env`:
   - `OPENAI_API_KEY`: Set your OpenAI key. Defaults to `mock-key-for-testing` to run in mock mode.
   - `DATABASE_URL`: Set PostgreSQL URL. If left empty, SQLAlchemy automatically falls back to local SQLite files under `backend/app/database/lexagents.db`.
5. Bootstrap/seed Qdrant indexes and SQLite/PostgreSQL tables:
   ```bash
   python scripts/bootstrap_corpus.py
   ```
6. Start backend FastAPI server:
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

### 2. Next.js Frontend Client
1. Navigate to the client directory:
   ```bash
   cd frontend
   ```
2. Install Node modules:
   ```bash
   npm install
   ```
3. Start local development server:
   ```bash
   npm run dev
   ```
4. Open [http://localhost:3000](http://localhost:3000) in your browser.

---

## 4. Environment Variables Reference

### Backend Settings (`.env` or Server Environment)

- `OPENAI_API_KEY`: API Key. If set to `mock-key-for-testing`, triggers local offline simulator.
- `OPENAI_API_BASE`: OpenAI compatible API base URL. Defaults to `https://api.openai.com/v1`.
- `LLM_MODEL`: Model name (default: `gpt-4o-mini`).
- `EMBEDDING_MODEL`: Embedding model (default: `text-embedding-3-small`).
- `DATABASE_URL`: PostgreSQL connection URL (e.g., `postgresql://user:pass@host:port/dbname`). If left empty, falls back to local SQLite under `SQLITE_DB_PATH`.
- `QDRANT_URL`: Optional remote Qdrant database URL (e.g., `https://qdrant-instance.cloud.qdrant.io:6333`).
- `QDRANT_API_KEY`: Optional remote Qdrant API key.
- `QDRANT_STORAGE_PATH`: Local directory path for Qdrant storage if running locally (default: `data/qdrant_db`).
- `CORS_ORIGINS`: Comma-separated list of allowed CORS origins (default: `http://localhost:3000,http://127.0.0.1:3000,https://lex-agents.vercel.app`).
- `WEB_SEARCH_ENABLED`: Set `True`/`False` to toggle web search capabilities.
- `PORT`: Server port (default: `8000`).
- `HOST`: Server host (default: `127.0.0.1`).

### Frontend Settings (`.env.local` or Vercel Environment)

- `NEXT_PUBLIC_API_URL`: The public url of your FastAPI backend service (e.g., `https://lex-agents-backend.up.railway.app` or similar). If left empty, falls back to `http://localhost:8000` in development mode, but raises a descriptive runtime error in production client sessions.

---

## 5. Production Deployment Guide

### 1. Backend Deployment (FastAPI)
The FastAPI backend can be deployed using the existing `backend/Dockerfile` to platform-as-a-service providers like **Render**, **Railway**, **Fly.io**, or **AWS ECS/Fargate**.

#### Step-by-Step with Railway/Render:
1. Connect your Github repository to the platform.
2. Select `backend/Dockerfile` as the build context / build path.
3. Configure the required environment variables:
   - `OPENAI_API_KEY`: Your production OpenAI API key.
   - `DATABASE_URL`: Connection string to your hosted PostgreSQL database.
   - `QDRANT_URL` and `QDRANT_API_KEY`: Connection details for your hosted Qdrant vector database.
   - `CORS_ORIGINS`: Set to your production frontend URL: `https://lex-agents.vercel.app` (or your custom Vercel domain).
4. Set the start command or let the Dockerfile default CMD handle it (`python -m uvicorn backend.app.main:app --host 0.0.0.0 --port 8000`).

### 2. Frontend Deployment (Vercel)
The Next.js client is already configured for deployment under the `frontend/` subdirectory on Vercel.

1. In your **Vercel Dashboard**, go to **Settings > General** and ensure the **Root Directory** is set to `frontend`.
2. Go to **Settings > Environment Variables** and add `NEXT_PUBLIC_API_URL` pointing to your deployed FastAPI backend URL (e.g. `https://lex-agents-backend.up.railway.app`).
3. Trigger a redeploy of your Vercel project to bundle the updated API url.

### 3. Verifying Connectivity
Once both are deployed, check the following:
- Verify the backend is up by visiting `https://<your-backend-domain>/health` in a browser. It should return `{"status": "healthy", "service": "LexAgents API"}`.
- Open your Vercel deployment (`https://lex-agents.vercel.app`), enter a test query, and observe that research, verification, and reflection results populate correctly without producing "Failed to fetch" errors.
