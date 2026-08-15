import json
import logging
from typing import List, Dict, Any
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import Evidence

logger = logging.getLogger(__name__)

class SynthesisAgent:
    def synthesize(self, query: str, evidence: List[Evidence]) -> Dict[str, Any]:
        """
        Synthesize retrieved evidence into a cohesive legal research answer.
        Identifies conflicts and aligns citations.
        """
        if not evidence:
            return {
                "answer": "No relevant legal evidence was found to answer this query. Consequently, no legal claims can be verified or presented.",
                "conflicts": []
            }

        # Format evidence list for the LLM prompt
        evidence_summary = []
        for idx, ev in enumerate(evidence):
            evidence_summary.append(
                f"Source [{idx + 1}]:\n"
                f"ID: {ev.id}\n"
                f"Source: {ev.source}\n"
                f"Type: {ev.doc_type}\n"
                f"Content: {ev.text}\n"
                f"---"
            )
        evidence_context = "\n".join(evidence_summary)

        system_prompt = f"""You are the Synthesis Agent for LexAgents. Your job is to draft a research-grade, objective legal research report answering the user's query based ONLY on the provided evidence.

Available Evidence:
{evidence_context}

Instructions:
1. Draft a clear, professional, and well-structured answer.
2. Every major legal assertion or claim you write MUST be backed by one or more sources from the evidence list. Cite sources inline using bracketed numbers like [1], [2], corresponding to the source indexes above (e.g., "Under California law, security deposits must be returned within 21 days [1].").
3. Distinguish clearly between statutory codes (legislative rules) and case law (judicial interpretations/precedents).
4. Identify any contradictions, conflicts, or tensions between the sources (for example, if a private lease agreement states a timeline of 30 days, but a state statute mandates 21 days).
5. If there is insufficient evidence to answer a part of the query, explicitly state that the evidence is lacking for that claim. Do not invent any case law, citations, or facts.
6. Clearly communicate uncertainty where the law is ambiguous or evidence is conflicting.

Your output MUST be a JSON object with this structure:
{{
  "answer": "Your detailed synthesized legal answer text with inline citations.",
  "conflicts": [
     "Describe conflict 1 (if any)",
     "Describe conflict 2 (if any)"
  ]
}}

Respond ONLY with valid JSON. Do not include markdown code block formatting in your raw response, but if you do, ensure it is valid JSON.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Synthesize an answer for: {query}"}
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
            return {
                "answer": data.get("answer", ""),
                "conflicts": data.get("conflicts", [])
            }
        except Exception as e:
            logger.error(f"Synthesis failed: {e}. Falling back to default text.")
            return {
                "answer": f"Error synthesizing retrieved evidence: {e}. Raw evidence was retrieved from: " + ", ".join([e.source for e in evidence]),
                "conflicts": []
            }

synthesis_agent = SynthesisAgent()
