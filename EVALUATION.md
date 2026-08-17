# Evaluation Engine & Reproducibility Guide

LexAgents includes a built-in evaluation framework designed to run automated benchmarks comparing multiple RAG pipelines against standardized legal queries.

---

## 1. Benchmark Dataset Format (`data/benchmark/legal_queries.json`)

The evaluation runs against a dataset of structured queries. Each test item is formatted as a JSON object:

```json
{
  "id": "q_unique_id",
  "question": "The complex legal question to answer",
  "jurisdiction": "India",
  "expected_sources": [
    "negotiable_instruments_act_1881.txt",
    "dalmia_cement_v_galaxy_traders_2001.txt"
  ],
  "reference_answer": "The ground-truth answer detailing expected statutory and case linkages.",
  "relevant_documents": ["negotiable_instruments_act_1881.txt", "dalmia_cement_v_galaxy_traders_2001.txt"],
  "metadata": {
    "topic": "cheque bounce notice compliance",
    "complexity": "medium"
  }
}
```

---

## 2. Calculated Metrics

- **Retrieval Precision**: Ratio of retrieved documents that match the ground-truth `expected_sources`.
- **Retrieval Recall**: Ratio of ground-truth `expected_sources` that are successfully retrieved by the search agents.
- **Citation Precision**: The proportion of generated assertions/claims in the report that are successfully verified as "Supported" by their cited passages.
- **Citation Recall**: The proportion of ground-truth `expected_sources` that are actually cited in the final verified claims.
- **Unsupported Claim Rate**: The proportion of claims that fail verification (either unsupported by context or contradictory).

---

## 3. Running the Benchmark

### 1. Via Command Line
To run the evaluation pipeline, ensure your virtual environment is active and run:
```bash
python scripts/run_eval.py
```
*Note: If no `OPENAI_API_KEY` is present in your environment, the script automatically defaults to running in mock mode. This generates deterministic simulator responses, allowing you to run verification dry runs without incurring API costs.*

### 2. Via Web Interface
1. Start the server:
   ```bash
   python -m uvicorn backend.app.main:app --reload
   ```
2. Navigate to [http://127.0.0.1:8000/](http://127.0.0.1:8000/).
3. Open the **Evaluation Engine** tab.
4. Click **Run System Evaluation Benchmark**. The metrics table and performance comparison chart will be rendered directly on the screen.

---

## 4. Evaluation Outputs (`experiments/results/`)

Every evaluation run saves data under `experiments/results/`:
- `evaluation_<timestamp>.json`: The raw claim outputs, answers, latencies, and metrics for each query and pipeline type.
- `summary_table.csv`: A macro-average performance table comparing all four pipelines.
- `report.md`: A detailed markdown evaluation report explaining key findings.
- `comparison_chart.png`: A bar plot comparing recall, precision, and unsupported claim rates across the pipelines.
