# LexAgents: Multi-Agent Collaborative RAG for Legal Research

LexAgents is a research-grade prototype of a **Multi-Agent Collaborative Retrieval-Augmented Generation (RAG)** system designed specifically for legal research. It structures and orchestrates specialized retrieval agents, conducts programmatically grounded citation verification, and implements iterative self-reflection to resolve unsupported claims.

## 1. Research Hypothesis
*A multi-agent collaborative RAG architecture with specialized retrieval agents, factual verification, and iterative self-reflection improves citation correctness, groundedness, and overall reliability of legal research compared to conventional single-pipeline vector RAG.*

---

## 2. Core Architecture

The system decomposes complex legal queries into targeted search tasks, dispatches them to domain-specific retrieval agents, synthesizes a structured report, verifies every generated claim against raw sources, and reflects on whether additional retrieval loop iterations are required.

```
       User Query
           │
           ▼
  Coordinator Agent (Task Decomposition)
           │
    ┌──────┼──────┬──────────────────────┐
    │      │      │                      │
    ▼      ▼      ▼                      ▼
Case Law Statute Legal Document Web Research
Agent    Agent   Agent          Agent
    │      │      │                      │
    └──────┼──────┴──────────────────────┘
           ▼
   Evidence Aggregator (Deduplication)
           │
           ▼
    Synthesis Agent (Citation Grounding)
           │
           ▼
   Verification Agent (Factual Claim Check)
           │
           ▼
   Reflection Loop Control ────[Insufficient Evidence?]────► (Refined Search Loop)
           │
           ▼ (Yes, or Max Iteration Limit)
      Final Answer
```

---

## 3. Technology Stack
- **Language**: Python (v3.10+)
- **API Framework**: FastAPI, Uvicorn
- **Vector Database**: Qdrant (using local path storage, no Docker required for simpler setup)
- **BM25 Search**: Rank-BM25 on tokenized passages
- **Orchestration**: Direct Graph Loop Runner (custom Python Orchestrator)
- **Database**: SQLite3 (for session history, trace event logging, and evaluation runs)
- **Frontend**: Vanilla CSS & JavaScript served directly from FastAPI

---

## 4. Project Directory Structure
```
LexAgents/
├── backend/
│   ├── app/
│   │   ├── api/          # FastAPI routes
│   │   ├── agents/       # Agent modules (Coordinator, Case Law, Statute, Web, etc.)
│   │   ├── core/         # Configuration, Settings, LLM wrappers
│   │   ├── database/     # SQLite database manager
│   │   ├── evaluation/   # Evaluation run executor and metric calculators
│   │   ├── ingestion/    # Document parsers, chunkers, indexers
│   │   ├── models/       # Pydantic schema representations
│   │   ├── retrieval/    # Hybrid Vector + BM25 RRF retriever
│   │   └── main.py       # FastAPI application entrypoint
│   └── tests/            # Pytest test suite (100% mock-compatible)
├── frontend/             # Single-page web portal (HTML, CSS, JS)
├── data/
│   ├── corpus/           # Local cases and statutes raw text database
│   └── benchmark/        # Reproducibility legal queries evaluation dataset
├── scripts/              # Bootstrap and evaluation execution triggers
├── configs/              # Configurations
├── experiments/          # Evaluation report outputs, tables, and comparison charts
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variables template
└── .gitignore
```

---

## 5. Quick Start Setup

### Prerequisites
- Python 3.10 or higher
- `pip` or `uv` package manager

### Installation
1. Clone the repository and navigate into it:
   ```bash
   git clone https://github.com/Guntuku-Chinmay/LexAgents.git
   cd LexAgents
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # On Windows:
   .venv\Scripts\activate
   # On Unix/macOS:
   source .venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy the `.env.example` to `.env` and set your API keys:
   ```bash
   cp .env.example .env
   ```

---

## 6. Running the System

### 1. Ingest/Bootstrap the Sample Corpus
Populates the Qdrant vector database and SQLite metadata stores with sample California tenant deposit statutes and related landmark case law:
```bash
python scripts/bootstrap_corpus.py
```

### 2. Run the Web Application
Launch the FastAPI backend server:
```bash
python -m uvicorn backend.app.main:app --reload --port 8000
```
Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.

### 3. Run Reproducible Evaluations
Run the pipeline evaluation against the benchmark dataset and generate plots:
```bash
python scripts/run_eval.py
```
This writes the following metrics and visual comparisons under the `experiments/results/` directory:
- `summary_table.csv`
- `report.md`
- `comparison_chart.png`

### 4. Run Automated Tests
```bash
python -m pytest backend/tests/
```

---

## 7. Configuration Variables
Modify these inside your `.env` file:
- `OPENAI_API_KEY`: API Key for LLM and embedding access. Defaults to `mock-key-for-testing` which triggers mock-mode locally for testing/dry runs.
- `LLM_MODEL`: LLM Model (default: `gpt-4o-mini`).
- `EMBEDDING_MODEL`: Embedding model (default: `text-embedding-3-small`).
- `WEB_SEARCH_ENABLED`: Set to `True`/`False` to toggle duckduckgo web crawling.
