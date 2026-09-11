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

## 5. Production Deployment Guide (Render Backend + Vercel Frontend)

### 1. Backend Deployment on Render

The FastAPI backend is fully pre-configured for deployment on **Render** using either Render Blueprints (`render.yaml`) or a manual Web Service.

#### Option A: One-Click Deploy via Render Blueprint (Recommended)
1. Log into your [Render Dashboard](https://dashboard.render.com/).
2. Click **New +** and select **Blueprint**.
3. Connect your GitHub repository `https://github.com/Guntuku-Chinmay/LexAgents.git`.
4. Render automatically detects [`render.yaml`](render.yaml) and populates the build command, start command, and environment variables.
5. Click **Apply**. The backend builds, automatically bootstraps the Indian legal corpus, and starts on port `10000` with public HTTPS!

#### Option B: Manual Web Service Creation on Render
1. Click **New +** > **Web Service**.
2. Select repository: `Guntuku-Chinmay/LexAgents`.
3. Configure the following settings:
   - **Name**: `lexagents-backend`
   - **Region**: `Singapore` (or nearest region)
   - **Branch**: `main`
   - **Runtime**: `Python`
   - **Build Command**: `pip install -r requirements.txt && python scripts/bootstrap_corpus.py`
   - **Start Command**: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: `Free`
4. Add the following **Environment Variables**:
   | Variable | Value | Required / Notes |
   | :--- | :--- | :--- |
   | `LLM_PROVIDER` | `free_fallback` | Required for zero-cost operation |
   | `OPENAI_API_KEY` | `mock-key-for-testing` | Optional (set real key only if using `LLM_PROVIDER=openai`) |
   | `SQLITE_DB_PATH` | `backend/app/database/lexagents.db` | Local SQLite database path |
   | `QDRANT_STORAGE_PATH` | `data/qdrant_db` | Local Qdrant embedded vector storage |
   | `CORS_ORIGINS` | `https://*.vercel.app,http://localhost:3000` | Allowed origins (Vercel subdomains allowed automatically) |
   | `WEB_SEARCH_ENABLED` | `true` | Enables DuckDuckGo legal research agent |
   | `PYTHON_VERSION` | `3.11.9` | Python runtime version on Render |

---

### 2. Frontend Deployment on Vercel

The Next.js frontend is located in the `frontend/` directory and deploys cleanly to **Vercel**.

#### Step-by-Step Vercel Setup:
1. Log into [Vercel Dashboard](https://vercel.com/dashboard).
2. Click **Add New...** > **Project** and import `Guntuku-Chinmay/LexAgents`.
3. In **Configure Project**:
   - **Framework Preset**: `Next.js`
   - **Root Directory**: Click *Edit* and select `frontend` (CRITICAL)
   - **Build Command**: `npm run build` (or leave default Next.js build)
   - **Output Directory**: `.next`
4. Expand **Environment Variables** and add:
   | Variable | Value | Purpose |
   | :--- | :--- | :--- |
   | `NEXT_PUBLIC_API_URL` | `https://<your-render-backend-name>.onrender.com` | Points Next.js client to the deployed Render FastAPI backend |
5. Click **Deploy**. Vercel will build and assign a production URL (e.g. `https://lex-agents.vercel.app` or `https://lexagents-*.vercel.app`).

---

### 3. Verifying Production Connectivity

Once both Render and Vercel deployments are live:
1. **Verify Backend Health**:
   - Open `https://<your-backend>.onrender.com/health` $\rightarrow$ should return `{"status":"healthy","service":"LexAgents API"}`.
   - Open `https://<your-backend>.onrender.com/` $\rightarrow$ should return service status and API docs link.
2. **Verify Interactive Frontend**:
   - Open the Vercel URL in Google Chrome or Microsoft Edge.
   - Test an English query: *"Does the right to privacy under Article 21 extend to digital data protection?"*
   - Test a Hindi query: *"परक्राम्य लिखत अधिनियम की धारा 138 के तहत चेक बाउंस नोटिस की समयसीमा क्या है?"*
   - Test a Telugu query: *"చెక్ బౌన్స్ కేసులో సెక్షన్ 138 నిబంధనలు ఏమిటి?"*
   - Test Speech-to-Text (STT) by clicking the microphone button and speaking.
   - Test Text-to-Speech (TTS) by clicking the "Listen" button in the Synthesized Legal Opinion header.

---

## 6. Hackathon Portable Setup Instructions

For quick portable execution during the hackathon, follow these instructions:

### Prerequisites
*   **Docker Desktop**: Download and run [Docker Desktop](https://www.docker.com/products/docker-desktop). Make sure the Docker daemon is active.
*   **OpenAI API Key**: Obtain a key from [platform.openai.com](https://platform.openai.com/). If none is provided, the system will use local mocks for testing.

### Running with One-Click Scripts (Windows)
1.  Double-click `start-hackathon.bat` or run `.\start-hackathon.ps1` in PowerShell.
2.  If prompted, enter your `OPENAI_API_KEY` (the script automatically writes it to `.env` and handles setting up default settings).
3.  The script will clear old volumes and spin up the complete Docker Compose stack.

### Running Manually (Any OS)
1.  Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
2.  Set your `OPENAI_API_KEY` in `.env`.
3.  Start the stack:
    ```bash
    docker compose down -v
    docker compose up --build
    ```

### Port Map Reference
*   **Frontend UI**: [http://localhost:3000](http://localhost:3000)
*   **Backend API**: [http://localhost:8000](http://localhost:8000)
*   **Qdrant Panel**: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

### Operational Procedures
*   **How to stop**: Press `Ctrl+C` in the compose window, or run `docker compose down`.
*   **How to reset**: Run `docker compose down -v` to clear database volumes, then restart to re-seed all tables.
*   **Internet Access Requirement**: Internet is required to fetch OpenAI embeddings/chat models, and for web search queries.
*   **Offline/Mock Fallback**: If `OPENAI_API_KEY` is not set or set to `mock-key-for-testing`, the backend will simulate embedding generation and agent planning cycles offline using deterministic mocks, which allows offline demonstration.

