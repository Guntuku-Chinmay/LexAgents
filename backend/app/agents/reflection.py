import json
import logging
import time
import uuid
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
from backend.app.core.config import settings
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import (
    Evidence, VerificationResult, ResearchTraceStep, ResearchResponse, TaskDecomposition
)
from backend.app.database.db_manager import db
from backend.app.agents.coordinator import coordinator_agent
from backend.app.agents.constitutional import constitutional_research_agent
from backend.app.agents.regulatory import regulatory_agent
from backend.app.agents.case_law import case_law_agent
from backend.app.agents.statute import statute_agent
from backend.app.agents.legal_document import legal_document_agent
from backend.app.agents.web_research import web_research_agent
from backend.app.agents.synthesis import synthesis_agent
from backend.app.agents.verification import verification_agent

logger = logging.getLogger(__name__)

class ReflectionAgent:
    def reflect(
        self,
        query: str,
        answer: str,
        verification_results: List[VerificationResult],
        history_queries: List[str]
    ) -> Tuple[bool, List[TaskDecomposition], str]:
        """
        Analyze verification results to decide if more evidence is needed.
        If yes, generate follow-up tasks.
        """
        # Find unsupported or problematic claims
        unsupported_claims = [v for v in verification_results if not v.supported]
        
        if not unsupported_claims:
            return True, [], "All claims successfully verified and supported."

        # If we have unsupported claims, ask the LLM if we can resolve them with more search,
        # and if so, what precise search queries to run.
        claims_summary = []
        for idx, uc in enumerate(unsupported_claims):
            claims_summary.append(
                f"Claim [{idx+1}]: {uc.claim}\n"
                f"Issues: {', '.join(uc.issues)}"
            )
        claims_context = "\n\n".join(claims_summary)
        history_context = ", ".join(history_queries)

        system_prompt = f"""You are the Self-Reflection Agent for LexAgents. Your job is to check if a draft legal answer has unsupported claims or citation issues, and determine if additional retrieval is required.

Here are the problematic/unsupported claims:
{claims_context}

Past search queries run in this session:
[{history_context}]

Instructions:
1. Determine if additional retrieval can help verify or support these claims.
2. If yes, generate up to 2 precise follow-up search tasks. Select the most relevant specialized agent ('case_law', 'statute', 'legal_document', 'web_research').
3. Do not repeat any past search queries.
4. If the claims are inherently unresolvable because the evidence simply doesn't exist, set 'sufficient' to true and do not create follow-up tasks.

Your output MUST be a JSON object with this structure:
{{
  "sufficient": false, // Set to true if no more search can help, or false if we need to search more
  "reasoning": "Brief explanation of what is missing and how the new queries address it",
  "follow_up_tasks": [
     {{
       "query": "Precise search query",
       "agent": "case_law" | "statute" | "legal_document" | "web_research",
       "reason": "Why this search is needed"
     }}
  ]
}}

Respond ONLY with valid JSON. Do not include markdown code block formatting in your raw response.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Reflect on the draft answer for: {query}"}
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
            sufficient = bool(data.get("sufficient", True))
            reasoning = data.get("reasoning", "")
            
            follow_ups = []
            if not sufficient:
                for t in data.get("follow_up_tasks", []):
                    # Guard against repeating historical queries
                    q = t["query"].strip()
                    if q.lower() not in [hq.lower() for hq in history_queries]:
                        follow_ups.append(
                            TaskDecomposition(
                                query=q,
                                agent=t["agent"],
                                reason=t["reason"]
                            )
                        )
            
            # If no new valid queries were generated, terminate loop
            if not follow_ups:
                sufficient = True
                reasoning = "No new queries could be generated. Terminating loop."
                
            return sufficient, follow_ups, reasoning
        except Exception as e:
            logger.error(f"Reflection failed: {e}. Defaulting to sufficient=True.")
            return True, [], f"Reflection error: {e}"

reflection_agent = ReflectionAgent()

class Orchestrator:
    def __init__(self):
        self.coordinator = coordinator_agent
        self.constitutional = constitutional_research_agent
        self.regulatory = regulatory_agent
        self.case_law = case_law_agent
        self.statute = statute_agent
        self.legal_doc = legal_document_agent
        self.web = web_research_agent
        self.synthesis = synthesis_agent
        self.verification = verification_agent
        self.reflection = reflection_agent

    def run_research(self, query: str, session_id: Optional[str] = None, use_web: bool = True, max_iterations: int = 3) -> ResearchResponse:
        """
        Execute the complete multi-agent collaborative RAG loop.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.info(f"Starting research session {session_id} for query: '{query}'")
        
        # Initialize DB record
        db.create_session(session_id, query)

        # Track state across loop
        history_queries: List[str] = []
        collected_evidence: Dict[str, Evidence] = {}  # Deduplicate chunks by ID
        trace: List[ResearchTraceStep] = []

        def add_trace_step(step_name: str, payload: Any):
            timestamp = datetime.utcnow().isoformat()
            db.add_log(session_id, step_name, "trace", payload)
            trace.append(ResearchTraceStep(step_name=step_name, timestamp=timestamp, payload=payload))

        # Get uploaded custom documents to pass to Coordinator
        uploaded_docs = db.get_documents(doc_type="user_upload")

        # Start of iteration loop
        iteration = 0
        tasks_to_run: List[TaskDecomposition] = []

        while iteration < max_iterations:
            iteration += 1
            logger.info(f"Session {session_id}: Starting iteration {iteration}")
            add_trace_step(f"Iteration {iteration} Start", {"iteration": iteration})

            # Step 1: Decomposition
            if iteration == 1:
                # Coordinator decomposes initial query
                coordinator_output = self.coordinator.decompose_query(query, uploaded_docs, use_web)
                tasks_to_run = coordinator_output.tasks
            # Else tasks_to_run is populated by the previous Reflection step

            add_trace_step(f"Decomposition (Iteration {iteration})", {
                "tasks": [t.model_dump() for t in tasks_to_run]
            })

            # Step 2: Dispatch and retrieve evidence
            new_evidence_count = 0
            iteration_evidence: List[Evidence] = []
            
            for task in tasks_to_run:
                history_queries.append(task.query)
                logger.info(f"Dispatching task to '{task.agent}': '{task.query}'")
                
                results: List[Evidence] = []
                if task.agent == "constitutional":
                    results = self.constitutional.search(task.query)
                elif task.agent == "regulatory":
                    results = self.regulatory.search(task.query)
                elif task.agent == "case_law":
                    results = self.case_law.search(task.query)
                elif task.agent == "statute":
                    results = self.statute.search(task.query)
                elif task.agent == "legal_document":
                    results = self.legal_doc.search(task.query)
                elif task.agent == "web_research":
                    results = self.web.search(task.query, enabled=use_web)
                
                for ev in results:
                    iteration_evidence.append(ev)
                    if ev.id not in collected_evidence:
                        collected_evidence[ev.id] = ev
                        new_evidence_count += 1
                    else:
                        # Deduplicate: preserve highest score and log all retrieval methods
                        existing = collected_evidence[ev.id]
                        methods = set((existing.retrieval_method or "").split(","))
                        methods.add(ev.retrieval_method or "hybrid")
                        merged_method = ",".join(sorted(list(methods)))
                        
                        if ev.score > existing.score:
                            ev.retrieval_method = merged_method
                            collected_evidence[ev.id] = ev
                        else:
                            existing.retrieval_method = merged_method

            add_trace_step(f"Retrieval (Iteration {iteration})", {
                "retrieved_count": len(iteration_evidence),
                "new_unique_evidence": new_evidence_count,
                "evidence_list": [ev.model_dump() for ev in iteration_evidence]
            })

            # Step 3: Synthesis
            # Always synthesize with all aggregated unique evidence collected so far
            current_evidence_pool = list(collected_evidence.values())
            synthesis_res = self.synthesis.synthesize(query, current_evidence_pool)
            draft_answer = synthesis_res["answer"]
            conflicts = synthesis_res["conflicts"]

            add_trace_step(f"Synthesis (Iteration {iteration})", {
                "draft_answer": draft_answer,
                "conflicts": conflicts
            })

            # Step 4: Verification
            ver_results = self.verification.verify(draft_answer, current_evidence_pool)
            
            add_trace_step(f"Verification (Iteration {iteration})", {
                "verification_results": [v.model_dump() for v in ver_results]
            })

            # Step 5: Reflection & Loop decision
            sufficient, follow_up_tasks, reasoning = self.reflection.reflect(
                query, draft_answer, ver_results, history_queries
            )

            add_trace_step(f"Reflection (Iteration {iteration})", {
                "sufficient": sufficient,
                "reasoning": reasoning,
                "follow_up_tasks": [t.model_dump() for t in follow_up_tasks]
            })

            if sufficient or not follow_up_tasks:
                logger.info(f"Session {session_id} achieved sufficient evidence or loop termination triggered.")
                break
                
            tasks_to_run = follow_up_tasks

        # Finalize answer in SQLite session DB
        db.update_session_answer(session_id, draft_answer, iteration)
        
        # Format final citations list
        # Map only the evidence chunks that are actually cited in the final verification results
        cited_ids = set()
        for v in ver_results:
            if v.supported:
                cited_ids.update(v.evidence_ids)
                
        final_citations = [collected_evidence[cid] for cid in cited_ids if cid in collected_evidence]
        # Fallback to all retrieved if cited mapping is empty
        if not final_citations:
            final_citations = list(collected_evidence.values())

        # Compile and return ResearchResponse
        response = ResearchResponse(
            session_id=session_id,
            answer=draft_answer,
            citations=final_citations,
            verification_results=ver_results,
            iterations=iteration,
            trace=trace
        )
        return response

orchestrator = Orchestrator()
