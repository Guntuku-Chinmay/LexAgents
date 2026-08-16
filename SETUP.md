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

## 4. Environment Variables Reference (`.env`)

- `OPENAI_API_KEY`: API Key. If set to `mock-key-for-testing`, triggers local offline simulator.
- `LLM_MODEL`: Model name (default: `gpt-4o-mini`).
- `EMBEDDING_MODEL`: Embedding model (default: `text-embedding-3-small`).
- `DATABASE_URL`: PostgreSQL connection URL (e.g. `postgresql://postgres:postgrespassword@localhost:5432/lexagents`).
- `QDRANT_STORAGE_PATH`: Local directory path for Qdrant storage.
- `WEB_SEARCH_ENABLED`: Set `True`/`False` to toggle web search agent capabilities.
