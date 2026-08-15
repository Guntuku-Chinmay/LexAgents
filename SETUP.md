# Local Setup Guide

This guide provides step-by-step instructions to configure, initialize, and run LexAgents on Windows.

---

## 1. Environment Setup

Ensure you have **Python 3.10+** installed on your system.

1. **Clone the repository**:
   ```powershell
   git clone https://github.com/Guntuku-Chinmay/LexAgents.git
   cd LexAgents
   ```

2. **Create Python virtual environment**:
   Using `uv` (recommended for speed) or python:
   ```powershell
   # Using uv:
   uv venv
   # Or using standard python:
   python -m venv .venv
   ```

3. **Activate the virtual environment**:
   ```powershell
   .venv\Scripts\activate
   ```

4. **Install Python packages**:
   ```powershell
   # Using uv:
   uv pip install -r requirements.txt
   # Or using pip:
   pip install -r requirements.txt
   ```

---

## 2. Configuration Settings (`.env`)

Copy the env template:
```powershell
cp .env.example .env
```

Open `.env` in a text editor and adjust the settings:
- **`OPENAI_API_KEY`**: Set your OpenAI API key. If left blank or set to `mock-key-for-testing`, the system runs in an offline Simulator mode.
- **`OPENAI_API_BASE`**: Base URL for OpenAI-compatible LLM endpoints.
- **`LLM_MODEL`**: Chat model (e.g., `gpt-4o-mini`, `gpt-4o`).
- **`EMBEDDING_MODEL`**: Embedding model (e.g., `text-embedding-3-small`).
- **`WEB_SEARCH_ENABLED`**: Set to `True` or `False` to toggle internet search access.

---

## 3. Seed/Bootstrap Corpus

Before running queries, initialize the vector index and SQLite database with the sample tenant-landlord statutes and court cases:
```powershell
python scripts/bootstrap_corpus.py
```
This script:
1. Deletes any old test collections in Qdrant.
2. Ingests Cases (`data/corpus/cases/`) into Qdrant `cases`.
3. Ingests Statutes (`data/corpus/statutes/`) into Qdrant `statutes`.
4. Ingests the Lease Agreement (`data/corpus/sample_lease_agreement.txt`) into Qdrant `legal_documents`.

---

## 4. Run Server & Web UI

Start the backend application:
```powershell
python -m uvicorn backend.app.main:app --reload --port 8000
```
- Open [http://127.0.0.1:8000/](http://127.0.0.1:8000/) in your web browser.
- Access API interactive docs at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs).

---

## 5. Troubleshooting Windows Issues

- **`PermissionError: [WinError 32]`**:
  This happens during test teardown if SQLite file handles remain locked. It is harmless as the `clean_database` fixture clears the tables before every test. We have wrapped the teardown deletions in try-except blocks to prevent this from failing tests.
- **Qdrant local collection API**:
  If you see `'QdrantClient' object has no attribute 'search'`, make sure you have `qdrant-client>=1.6.0` installed. In recent versions of `qdrant-client` under local/in-memory mode, we use `client.query_points()` instead of `.search()`, which has been fully handled in this codebase.
