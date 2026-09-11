import json
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import TaskDecomposition, CoordinatorOutput

from backend.app.retrieval.query_analyzer import analyze_query
from backend.app.retrieval.corpus_coverage import is_domain_indexed

logger = logging.getLogger(__name__)

class CoordinatorAgent:
    def decompose_query(self, query: str, active_documents: List[Dict[str, Any]], use_web: bool = True) -> CoordinatorOutput:
        """
        Analyze a query and decompose it into sub-tasks for specialized agents
        using structured query analysis and domain routing.
        """
        # Run structured query analysis first
        analysis = analyze_query(query)
        primary_domain = analysis.primary_domain

        docs_summary = []
        for doc in active_documents:
            docs_summary.append(f"- ID: {doc['doc_id']}, Name: {doc['filename']}, Type: {doc['doc_type']}")
        docs_context = "\n".join(docs_summary) if docs_summary else "No user-uploaded documents available."

        system_prompt = f"""You are the Coordinator Agent for LexAgents, an advanced legal RAG system.
Your job is to receive an Indian legal query and decompose it into specific, actionable search tasks for specialized agents.

Query Domain Analysis:
- Primary Domain: {primary_domain}
- Query Type: {analysis.query_type}
- Secondary Domains: {', '.join(analysis.secondary_domains) if analysis.secondary_domains else 'None'}
- Legal Issues: {', '.join(analysis.legal_issues) if analysis.legal_issues else 'General Inquiry'}

You have access to the following specialized agent types:
1. 'constitutional': Search and retrieve Articles from the Constitution of India, amendments, and fundamental rights. (ONLY use for Constitutional Law).
2. 'statute': Search and retrieve codified legislative Central Acts and State legislation (e.g. IPC, Negotiable Instruments Act, POSH Act, Motor Vehicles Act).
3. 'case_law': Search and retrieve Supreme Court (SC) and High Court (HC) judgments, opinions, precedents, and citations.
4. 'regulatory': Search and retrieve regulations, rules, circulars, and notifications from regulators like RBI, SEBI, and TRAI.
5. 'legal_document': Search and retrieve clauses or provisions from the user-uploaded contract or agreement files.
6. 'web_research': Retrieve general or recent web updates (use if the domain has no indexed corpus or recent updates are requested).

Current User-Uploaded Documents:
{docs_context}

Your output MUST be a JSON object conforming to the following structure:
{{
  "tasks": [
    {{
      "query": "Precise search query for the specific agent",
      "agent": "constitutional" | "statute" | "case_law" | "regulatory" | "legal_document" | "web_research",
      "reason": "Brief justification for this task"
    }}
  ]
}}

CRITICAL DOMAIN ROUTING CONSTRAINTS:
- For Constitutional Law queries (Article 15, Article 21, fundamental rights): dispatch 'constitutional' and/or 'case_law'.
- For Motor Vehicle Law queries: dispatch 'statute', 'case_law', or 'web_research'. NEVER dispatch 'constitutional'.
- For Women & Gender Justice (POSH, sexual harassment): dispatch 'statute' and 'case_law'.
- For Corporate & Commercial Law (Section 138, cheque bounce, contracts, SEBI): dispatch 'statute', 'case_law', or 'regulatory'.
- For Property & Land Law: dispatch 'legal_document' if uploaded files exist, else 'statute'/'case_law'.
- If active user-uploaded documents exist and are relevant, include 'legal_document'.

Respond ONLY with valid JSON. Do not include markdown code block formatting in your raw response.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Decompose this legal query: {query}"}
        ]

        try:
            response_text = generate_chat_completion(messages, json_mode=True)
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            tasks = []
            for t in data.get("tasks", []):
                agent = t["agent"]
                # Domain safety gate: do not allow 'constitutional' for Motor Vehicle Law
                if primary_domain == "Motor Vehicle Law" and agent == "constitutional":
                    agent = "statute"
                    
                if agent not in ["constitutional", "statute", "case_law", "regulatory", "legal_document", "web_research"]:
                    if "constitut" in agent and primary_domain == "Constitutional Law":
                        agent = "constitutional"
                    elif "regul" in agent or "circular" in agent:
                        agent = "regulatory"
                    else:
                        agent = "statute"
                tasks.append(
                    TaskDecomposition(
                        query=t["query"],
                        agent=agent,
                        reason=t["reason"]
                    )
                )
            if tasks:
                return CoordinatorOutput(tasks=tasks)
            raise ValueError("No tasks generated by LLM")
        except Exception as e:
            logger.warning(f"Coordinator LLM decomposition fallback triggered: {e}")
            # Domain-aware deterministic fallback
            fallback_tasks = []
            
            if primary_domain == "Constitutional Law":
                fallback_tasks.append(TaskDecomposition(query=query, agent="constitutional", reason="Search constitutional provisions"))
                if any(w in query.lower() for w in ["judgment", "court", "precedent", "puttaswamy", "maneka"]):
                    fallback_tasks.append(TaskDecomposition(query=query, agent="case_law", reason="Search constitutional precedents"))
            elif primary_domain == "Motor Vehicle Law":
                fallback_tasks.append(TaskDecomposition(query="Motor Vehicles Act road accident negligence liability compensation", agent="statute", reason="Search motor vehicle statutory provisions"))
                fallback_tasks.append(TaskDecomposition(query="road accident sudden animal unavoidable accident inevitable accident negligence", agent="case_law", reason="Search motor accident judicial precedents"))
                if use_web:
                    fallback_tasks.append(TaskDecomposition(query=query, agent="web_research", reason="Authoritative search for motor vehicle statutory provisions"))
            elif primary_domain == "Women & Gender Justice":
                fallback_tasks.append(TaskDecomposition(query=query, agent="statute", reason="Search POSH Act provisions"))
                fallback_tasks.append(TaskDecomposition(query=query, agent="case_law", reason="Search workplace harassment precedents"))
            elif primary_domain == "Corporate & Commercial Law":
                if any(w in query.lower() for w in ["sebi", "insider", "upsi"]):
                    fallback_tasks.append(TaskDecomposition(query=query, agent="regulatory", reason="Search SEBI regulations"))
                else:
                    fallback_tasks.append(TaskDecomposition(query=query, agent="statute", reason="Search commercial statutes"))
                    fallback_tasks.append(TaskDecomposition(query=query, agent="case_law", reason="Search commercial case law"))
            else:
                fallback_tasks.append(TaskDecomposition(query=query, agent="statute", reason="Search applicable statutory codes"))
                fallback_tasks.append(TaskDecomposition(query=query, agent="case_law", reason="Search judicial precedents"))

            if active_documents and (primary_domain in ["Property & Land Law", "Corporate & Commercial Law"] or "lease" in query.lower() or "agreement" in query.lower()):
                fallback_tasks.append(TaskDecomposition(query=query, agent="legal_document", reason="Search custom documents"))

            return CoordinatorOutput(tasks=fallback_tasks)

coordinator_agent = CoordinatorAgent()
