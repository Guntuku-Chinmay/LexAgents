# Technical Architecture Documentation

This document describes the technical layout, data flow, and components of the LexAgents system.

---

## 1. Modular Hybrid Retrieval (`retrieval/vector_bm25.py`)

LexAgents combines dense semantic vector search with sparse keyword search using a custom Hybrid Retriever:
- **Vector Indexing (Dense)**: Utilizes a local path-based `qdrant-client` instance. Text chunks are passed to the embedding API and stored alongside payload metadata in Qdrant collections.
- **BM25 Indexing (Sparse)**: Dynamically constructs an in-memory `BM25Okapi` index using tokenized representations of chunks pre-filtered by metadata, ensuring high-speed local lexical matches.
- **Reciprocal Rank Fusion (RRF)**: Merges the ranked outputs of dense and sparse searches based on the formula:
  
  $$RRF\_Score(d) = \sum_{m \in M} \frac{1}{k + r_m(d)}$$
  
  Where $M$ is the set of retrieval methods (Vector and BM25), $r_m(d)$ is the rank of document $d$ in method $m$, and $k$ is a constant (default: 60). The top $N$ fused results are returned.

---

## 2. Collaborative Multi-Agent Network (`agents/`)

- **Coordinator Agent**: Implements query parsing and intent analysis. It outputs a structured list of tasks containing target sub-queries, specialized agent destinations, and rationale.
- **Case Law Agent**: Targets the `cases` collection in Qdrant. Returns structured evidence entries with judge opinions, citation details, dates, and court names.
- **Statute Agent**: Targets the `statutes` collection in Qdrant. Extracts precise section numbers (e.g. § 1950.5(g)(1)) to index legislative codes.
- **Legal Document Agent**: Interacts with the `legal_documents` collection which contains chunked segments of user-uploaded agreements, contracts, and notices.
- **Web Research Agent**: Configurable DuckDuckGo search crawler for fetching external updates.

---

## 3. Claim Extraction and Verification Engine (`agents/verification.py`)

Verification is implemented in a two-stage hybrid pipeline:
1. **Factual Claim Decomposition**: The Synthesis Agent outputs an answer embedding bracketed indices (e.g., `[1]`, `[2]`) mapping to the retrieved evidence. The Verification Agent decomposes the answer into key factual assertions and programmatically maps the cited indices to their unique database IDs.
2. **Semantic Verification**: For each claim, the agent cross-references the asserted text with the exact passage in the source document. The LLM acts as a semantic checker, classifying the claim state:
   - **Supported**: The claim is fully and accurately backed by the text of the source.
   - **Unsupported / Contradicted**: Discrepancies exist (e.g. lease contract states 30 days but California statute mandates 21 days). These are logged with structured issue details.

---

## 4. Orchestrator Graph Loop & Self-Reflection (`agents/reflection.py`)

The main orchestration runner implements a stateful loop with safeguards:
- **Safeguards**: Enforces `max_iterations = 3`, tracks execution latency timeouts, and maintains a registry of previous search queries to prevent infinite query recursion or duplicate API calls.
- **Reflection Check**: At the end of each iteration, the Reflection Agent reviews the verification matrix.
  - If all claims are **Supported**, the loop terminates, and the final grounded answer is returned.
  - If any claims are flagged as **Unsupported / Missing Details**, the Reflection Agent formulates follow-up queries specifically targeting the missing information and dispatches them for another retrieval pass.
- **Cost & Token tracking**: The trace monitors iteration metrics and outputs them to the user and SQLite logs.
