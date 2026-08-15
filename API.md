# API Reference Documentation

LexAgents exposes a clean REST API built with FastAPI. The interactive Swagger documentation is available at `/docs` when running the server.

---

## 1. Research Orchestration

### `POST /api/research`
Executes the collaborative multi-agent RAG workflow.

- **Request Body (`QueryRequest`)**:
  ```json
  {
    "query": "If a landlord fails to return the security deposit in 21 days but claims the lease contract permits 30 days, is it enforceable?",
    "session_id": "optional-uuid-here",
    "use_web": true
  }
  ```
- **Response Body (`ResearchResponse`)**:
  ```json
  {
    "session_id": "6abfd820-cf58-4e19-a0c2-86ac89197eba",
    "answer": "The synthesized answer text with inline citations like [1]...",
    "citations": [
      {
        "id": "uuid-here",
        "text": "Statute or case passage text",
        "source": "California Civil Code Section 1950.5",
        "doc_type": "statute",
        "score": 0.95,
        "metadata": {}
      }
    ],
    "verification_results": [
      {
        "claim": "Extract assertion text",
        "supported": true,
        "evidence_ids": ["uuid-here"],
        "citation_correct": true,
        "confidence": 0.95,
        "issues": []
      }
    ],
    "iterations": 1,
    "trace": [
      {
        "step_name": "Iteration 1 Start",
        "timestamp": "2026-08-15T15:00:00.000000",
        "payload": {}
      }
    ]
  }
  ```

---

## 2. Ingestion & Document Upload

### `POST /api/documents/upload`
Uploads a custom legal document (TXT, MD, or JSON) into the vector store.
- **Request**: Multipart Form Data
  - `file`: Binary file upload
- **Response**:
  ```json
  {
    "filename": "my_lease.txt",
    "chunks_ingested": 4,
    "status": "success",
    "message": "Successfully indexed 4 clauses into document collection."
  }
  ```

### `POST /api/ingest`
Force indexes a local file path.
- **Request Body**:
  ```json
  {
    "filepath": "E:/Projects/LexAgents/data/corpus/cases/granberry_v_covas_1999.txt",
    "doc_type": "case",
    "collection_name": "cases"
  }
  ```
- **Response**:
  ```json
  {
    "status": "success",
    "chunks_indexed": 3
  }
  ```

---

## 3. Retrieve Evidence

### `GET /api/sources/{id}`
Retrieve details and text content for a specific indexed chunk ID.
- **Path Parameter**: `id` (UUID of the indexed point)
- **Response**:
  ```json
  {
    "id": "uuid-here",
    "text": "Raw chunk passage text",
    "source": "california_civil_code_section_1950_5.txt",
    "doc_type": "statute",
    "score": 1.0,
    "metadata": {}
  }
  ```

### `GET /api/research/{session_id}`
Retrieve the trace logs and results of an existing research session from SQLite.
- **Path Parameter**: `session_id` (UUID string)
- **Response**:
  ```json
  {
    "session": {
      "session_id": "...",
      "query": "...",
      "final_answer": "...",
      "iterations": 1,
      "created_at": "..."
    },
    "trace": [
      {
        "log_id": 1,
        "session_id": "...",
        "step_name": "...",
        "event_type": "trace",
        "payload": {},
        "created_at": "..."
      }
    ]
  }
  ```

---

## 4. Benchmark & Health Check

### `POST /api/evaluate`
Triggers the reproducibility evaluation pipeline against the legal benchmark.
- **Response**:
  ```json
  {
    "status": "success",
    "message": "Successfully completed evaluation on 3 queries.",
    "results": [ ... ]
  }
  ```

### `GET /api/evaluation/results`
Returns list of all past evaluation run summaries stored in the SQLite store.
- **Response**:
  ```json
  [
    {
      "eval_id": "eval_20260815_203300",
      "run_timestamp": "2026-08-15T15:03:00Z",
      "system_type": "comparison",
      "metrics": {
        "Baseline_A": { ... },
        "System_D": { ... }
      },
      "config": {
        "benchmark_size": 3
      }
    }
  ]
  ```

### `GET /api/health`
Returns system liveness check.
- **Response**:
  ```json
  {
    "status": "healthy",
    "service": "LexAgents API"
  }
  ```
