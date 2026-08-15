import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import TaskDecomposition, CoordinatorOutput

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    def decompose_query(self, query: str, active_documents: List[Dict[str, Any]], use_web: bool = True) -> CoordinatorOutput:
        """
        Analyze a query and decompose it into sub-tasks for specialized agents.
        """
        # Format active documents list for context
        docs_summary = []
        for doc in active_documents:
            docs_summary.append(f"- ID: {doc['doc_id']}, Name: {doc['filename']}, Type: {doc['doc_type']}")
        docs_context = "\n".join(docs_summary) if docs_summary else "No user-uploaded documents available."

        system_prompt = f"""You are the Coordinator Agent for LexAgents, an advanced legal RAG system.
Your job is to receive a legal query and decompose it into specific, actionable search tasks for specialized agents.

You have access to the following specialized agent types:
1. 'case_law': Search and retrieve relevant legal judgments, opinions, precedents, and court cases.
2. 'statute': Search and retrieve relevant statutes, acts, codes, regulations, rules, or legislative provisions.
3. 'legal_document': Search and retrieve clauses/provisions from the user-uploaded documents.
4. 'web_research': Retrieve general or recent web updates (use this ONLY if there's a need for recent news/developments not in standard codes, or if web search is specifically requested).

Current User-Uploaded Documents:
{docs_context}

Your output MUST be a JSON object conforming to the following structure:
{{
  "tasks": [
    {{
      "query": "Precise search query for the specific agent",
      "agent": "case_law" | "statute" | "legal_document" | "web_research",
      "reason": "Brief justification for this task"
    }}
  ]
}}

Decompose the user's query carefully.
- If the query mentions specific contracts, clauses, or files that the user uploaded, dispatch a task to 'legal_document'.
- If the query has elements related to codified law or regulations (e.g., California Civil Code, U.S. Code, bankruptcy rules), dispatch a task to 'statute'.
- If the query has elements related to court decisions, judicial interpretation, or common law precedents, dispatch a task to 'case_law'.
- Keep web search queries restricted unless the question asks about recent developments or events beyond established codes and case law.

Respond ONLY with valid JSON. Do not include markdown code block formatting in your raw response, but if you do, ensure it is valid JSON.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Decompose this legal query: {query}"}
        ]

        try:
            response_text = generate_chat_completion(messages, json_mode=True)
            # Remove possible markdown fences if returned
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            tasks = []
            for t in data.get("tasks", []):
                tasks.append(
                    TaskDecomposition(
                        query=t["query"],
                        agent=t["agent"],
                        reason=t["reason"]
                    )
                )
            return CoordinatorOutput(tasks=tasks)
        except Exception as e:
            logger.error(f"Failed to decompose query in Coordinator: {e}. Falling back to default tasks.")
            # Standard baseline fallback to ensure robustness
            fallback_tasks = [
                TaskDecomposition(query=query, agent="statute", reason="Search legislative codes"),
                TaskDecomposition(query=query, agent="case_law", reason="Search judicial precedents")
            ]
            if active_documents:
                fallback_tasks.append(TaskDecomposition(query=query, agent="legal_document", reason="Search custom documents"))
            return CoordinatorOutput(tasks=fallback_tasks)

coordinator_agent = CoordinatorAgent()
