# Developer Contribution Guidelines

Thank you for contributing to LexAgents! Please follow these guidelines when adding new features, search agents, or extending the evaluation benchmark.

---

## 1. Development Process

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Guntuku-Chinmay/LexAgents.git
   cd LexAgents
   ```
2. **Set up virtual environment**:
   Make sure you activate the `.venv` and install all packages listed in `requirements.txt`.
3. **Run tests before coding**:
   Ensure the current test suite passes on your machine:
   ```bash
   python -m pytest backend/tests/
   ```
4. **Make changes on logical topics**:
   Use descriptive commits and clear code comments.
5. **Rerun tests and verify**:
   Ensure all tests pass and that the evaluation pipeline runs smoothly.

---

## 2. Implementing New Specialized Agents

If you want to add a new search agent type (e.g. for Administrative/Agency rulings, or specialized Contract clauses):
1. **Define agent class**: Create a file in `backend/app/agents/my_agent.py` mirroring the search logic of `statute_agent` or `case_law_agent`.
2. **Update Coordinator**: Update `backend/app/agents/coordinator.py` to include the new agent description in the system prompt. Add it as a routing option.
3. **Register in Orchestrator**: Update the import and execution dispatcher inside `backend/app/agents/reflection.py` to route tasks to the new agent when selected by the coordinator.
4. **Write unit tests**: Add tests verifying routing and retrieval inside `backend/tests/test_agents.py`.

---

## 3. Extending the Benchmark Dataset

To add more scenarios to the evaluation benchmark:
1. Open `data/benchmark/legal_queries.json`.
2. Append a new item following the schema:
   - `id`: unique ID (e.g. `q_04`).
   - `question`: precise legal query.
   - `jurisdiction`: relevant target area.
   - `expected_sources`: list of raw corpus filenames that must be retrieved (e.g. `["landmark_case_123.txt"]`).
   - `reference_answer`: ground truth answer block.
   - `relevant_documents`: list of files that are contextually relevant.
3. Add the supporting case/statute raw files under `data/corpus/cases/` or `data/corpus/statutes/`.
4. Re-run bootstrapping and verify the evaluation runner runs without error:
   ```bash
   python scripts/bootstrap_corpus.py
   python scripts/run_eval.py
   ```

---

## 4. Coding Conventions

- **Formatting**: Keep code lines clean, readable, and well-structured.
- **Type Annotations**: Use Pydantic schemas and standard typing annotations (`List`, `Dict`, `Optional`, `Tuple`) for all public agent methods and endpoints.
- **Mock-Compatibility**: Ensure all newly added agent prompts or completions have fallback mock outputs inside `backend/app/core/llm.py` so the test suite can be run completely offline.
