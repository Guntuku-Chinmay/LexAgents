# LexAgents: Multi-Agent Collaborative RAG for Legal Research

LexAgents is a research-grade prototype of a **Multi-Agent Collaborative Retrieval-Augmented Generation (RAG)** system designed specifically for legal research. It structures and orchestrates specialized retrieval agents, conducts programmatically grounded citation verification, and implements iterative self-reflection to resolve unsupported claims.

This version features a modernized full-stack architecture with a **Next.js React Client** and a **PostgreSQL relational storage** engine.

## 1. Research Hypothesis
*A multi-agent collaborative RAG architecture with specialized retrieval agents, factual verification, and iterative self-reflection improves citation correctness, groundedness, and overall reliability of legal research compared to conventional single-pipeline vector RAG.*

---

## 2. System Architecture

```text
                         ┌──────────────────────────┐
                         │       Next.js App        │
                         │ React + TypeScript       │
                         │ Tailwind CSS             │
                         └────────────┬─────────────┘
                                      │
                              REST / Streaming API
                                      │
                         ┌────────────▼─────────────┐
                         │      FastAPI Backend      │
                         │       Python / AI         │
                         └────────────┬─────────────┘
                                      │
          ┌───────────────────────────┼───────────────────────────┐
          │                           │                           │
          ▼                           ▼                           ▼
    PostgreSQL                    Qdrant                    Redis Optional
    Application State             Vector Search             Cache / Jobs
    Agent Traces                  Legal Chunks              (Omitted / Local)
    Research Sessions
    Evaluation Results
          │                           │
          └───────────────────────────┼───────────────────────────┘
                                      │
                         ┌────────────▼─────────────┐
                         │      LexAgents Engine     │
                         │                          │
                         │ Coordinator              │
                         │ Case Law Agent           │
                         │ Statute Agent            │
                         │ Legal Document Agent     │
                         │ Web Research Agent       │
                         │ Synthesis                │
                         │ Verification             │
                         │ Reflection               │
                         └──────────────────────────┘
```

---

## 3. Technology Stack
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, Tailwind CSS v4, Lucide Icons.
- **Backend API**: FastAPI, Uvicorn, Python 3.10+
- **Relational Storage**: PostgreSQL (using SQLAlchemy with automatic local SQLite file fallback)
- **Vector Database**: Qdrant (using local path storage or local cluster)
- **Sparse BM25 Indexing**: Rank-BM25 on tokenized passages
- **Orchestrator**: Custom python Directed Graph state loop

---

## 4. Directory Layout
```
LexAgents/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI REST endpoints
│   │   ├── agents/       # Multi-agent engines (coordinator, case, statute, web, verification, reflection)
│   │   ├── core/         # Settings configuration & LLM simulator
│   │   ├── database/     # SQLAlchemy models & relational DBManager
│   │   ├── evaluation/   # Benchmark metric compilations & plotter
│   │   ├── models/       # Pydantic schema validation
│   │   ├── retrieval/    # Hybrid Vector+BM25 retriever
│   │   └── main.py       # FastAPI server entrypoint
│   ├── tests/            # Test suite (100% mock compliant)
│   └── Dockerfile        # Backend image configuration
├── frontend/
│   ├── app/              # Next.js layout, page, and CSS
│   ├── components/       # UI panels (Research workspace, timelines, claim verifiers, evaluation dashboard)
│   ├── lib/              # API wrappers and TypeScript interfaces
│   ├── package.json      # Frontend package details
│   ├── tsconfig.json     # TypeScript settings
│   └── Dockerfile        # Next.js image configuration
├── data/
│   ├── corpus/           # Seed court cases and statutes
│   └── benchmark/        # Golden standard legal evaluation scenarios
├── experiments/          # Metric reports, CSVs, and comparison charts
├── docker-compose.yml    # Full stack local orchestration configuration
├── requirements.txt      # Backend Python dependencies
└── .env.example          # Environment variables template
```

---

## 5. Quick Start Local Setup

### 1. Backend Setup
1. Activate virtual environment and install requirements:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # On Windows
   pip install -r requirements.txt
   ```
2. Copy and set environment variables:
   ```bash
   cp .env.example .env
   ```
3. Initialize the database and seed case/statutory indexes:
   ```bash
   python scripts/bootstrap_corpus.py
   ```
4. Start API server:
   ```bash
   python -m uvicorn backend.app.main:app --reload --port 8000
   ```

### 2. Frontend Setup
1. Navigate to the client folder and install Node packages:
   ```bash
   cd frontend
   npm install
   ```
2. Launch Next.js dev server:
   ```bash
   npm run dev
   ```
3. Open [http://localhost:3000](http://localhost:3000) in your web browser.

---

## 6. Docker Compose Setup (Recommended)
You can run the entire system (Next.js, FastAPI, Postgres, Qdrant) in one command:
```bash
docker-compose up --build
```
- Access Frontend Client: [http://localhost:3000](http://localhost:3000)
- Access Backend API: [http://localhost:8000](http://localhost:8000)
- Access Qdrant Admin Panel: [http://localhost:6333/dashboard](http://localhost:6333/dashboard)

---

## 7. Running Reproducible Evaluations
To run evaluation comparisons and compile metrics across pipelines:
```bash
# In the root folder:
.venv\Scripts\python scripts/run_eval.py
```
This triggers evaluations on golden-standard queries and regenerates the performance report and charts under the `experiments/results/` directory.

---

## 8. Running Automated Tests
```bash
.venv\Scripts\python -m pytest backend/tests/
```
