import os
import sys
import logging

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# If no OPENAI_API_KEY is found in the environment, default to mock mode
if not os.environ.get("OPENAI_API_KEY") or os.environ.get("OPENAI_API_KEY") == "mock-key-for-testing":
    os.environ["MOCK_LLM"] = "True"
    print("WARNING: No OPENAI_API_KEY found. Running evaluation in MOCK LLM mode.")

from backend.app.evaluation.evaluator import Evaluator
from scripts.bootstrap_corpus import bootstrap

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("run_eval")

def main():
    logger.info("Initializing corpus indexing for evaluation...")
    bootstrap()
    
    logger.info("Starting LexAgents system evaluation against benchmark...")
    evaluator = Evaluator()
    results = evaluator.evaluate_all(use_web=False)
    
    logger.info(f"Evaluation complete! Ran {len(results)} benchmark queries.")
    logger.info("Results saved in experiments/results/ directory:")
    logger.info("  - JSON detailed run: experiments/results/evaluation_<timestamp>.json")
    logger.info("  - CSV macro average summary: experiments/results/summary_table.csv")
    logger.info("  - Markdown report: experiments/results/report.md")
    logger.info("  - Comparison plot: experiments/results/comparison_chart.png")

if __name__ == "__main__":
    main()
