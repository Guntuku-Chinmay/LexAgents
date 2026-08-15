import json
import re
import logging
from typing import List, Dict, Any
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import Evidence, VerificationResult

logger = logging.getLogger(__name__)

class VerificationAgent:
    def verify(self, answer: str, evidence: List[Evidence]) -> List[VerificationResult]:
        """
        Verify claims made in the synthesized answer against the retrieved evidence.
        Combines deterministic regex/index checks and semantic LLM evaluation.
        """
        if not evidence:
            return [
                VerificationResult(
                    claim="Answer generated without evidence",
                    supported=False,
                    evidence_ids=[],
                    citation_correct=False,
                    confidence=1.0,
                    issues=["No source evidence was retrieved, so the answer is ungrounded."]
                )
            ]

        # 1. Deterministic prep: Map citations inline
        # Find all citation marks like [1], [2], etc.
        citation_matches = re.findall(r'\[(\d+)\]', answer)
        used_indices = set(int(m) - 1 for m in citation_matches if m.isdigit())
        
        # Build evidence context for LLM verification
        evidence_summary = []
        evidence_id_map = {}
        for idx, ev in enumerate(evidence):
            evidence_id_map[idx] = ev.id
            evidence_summary.append(
                f"Source [{idx + 1}] (ID: {ev.id}):\n"
                f"Source Name: {ev.source}\n"
                f"Text: {ev.text}\n"
                f"---"
            )
        evidence_context = "\n".join(evidence_summary)

        system_prompt = f"""You are the Verification Agent for LexAgents. Your job is to verify all key legal claims and assertions made in a generated answer against the source documents.

Here is the source evidence that was available during synthesis:
{evidence_context}

Here is the synthesized answer:
\"\"\"{answer}\"\"\"

Your tasks:
1. Extract the main factual legal claims/assertions made in the answer.
2. For each claim, identify which sources (e.g. Source [1], Source [2]) are cited or should support it.
3. Compare the claim text against the source text. Determine:
   - Is the claim actually supported by the source text? (i.e. does the source contain the facts stated?)
   - Is the citation correct? (i.e. is the footnote mapped to the correct source, or is it hallucinated?)
   - Are there issues, contradictions, or is the source outdated?
4. Output your analysis in a structured JSON format.

Your output MUST be a JSON object with this structure:
{{
  "verification_results": [
    {{
      "claim": "The exact legal claim extracted from the answer",
      "supported": true | false,
      "evidence_index": 1, // The 1-based index of the cited source (e.g. 1 for Source [1]), or null if uncited
      "confidence": 0.95, // Float between 0.0 and 1.0
      "issues": ["List of discrepancies, e.g., source states 21 days but claim states 30 days"]
    }}
  ]
}}

Respond ONLY with valid JSON. Do not include markdown code block formatting in your raw response.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": "Extract and verify the claims."}
        ]

        verification_results = []
        try:
            response_text = generate_chat_completion(messages, json_mode=True)
            clean_text = response_text.strip()
            if clean_text.startswith("```json"):
                clean_text = clean_text[7:]
            if clean_text.endswith("```"):
                clean_text = clean_text[:-3]
            clean_text = clean_text.strip()
            
            data = json.loads(clean_text)
            
            for item in data.get("verification_results", []):
                claim = item.get("claim", "")
                supported = bool(item.get("supported", False))
                ev_idx = item.get("evidence_index")
                confidence = float(item.get("confidence", 0.5))
                issues = item.get("issues", [])
                
                # Deterministic check: Verify the evidence index maps to a real source
                citation_correct = True
                evidence_ids = []
                
                if ev_idx is not None:
                    zero_based_idx = int(ev_idx) - 1
                    if zero_based_idx in evidence_id_map:
                        evidence_ids.append(evidence_id_map[zero_based_idx])
                    else:
                        citation_correct = False
                        supported = False
                        issues.append(f"Invalid citation index [{ev_idx}] - index out of bounds.")
                else:
                    citation_correct = False
                    supported = False
                    issues.append("No citation associated with this claim.")
                
                verification_results.append(
                    VerificationResult(
                        claim=claim,
                        supported=supported,
                        evidence_ids=evidence_ids,
                        citation_correct=citation_correct,
                        confidence=confidence,
                        issues=issues
                    )
                )
        except Exception as e:
            logger.error(f"Verification agent failed: {e}. Falling back to default verification check.")
            # Fallback for error state
            verification_results.append(
                VerificationResult(
                    claim="Fallback claim verification",
                    supported=False,
                    evidence_ids=[],
                    citation_correct=False,
                    confidence=0.0,
                    issues=[f"Verification service error: {e}"]
                )
            )

        return verification_results

verification_agent = VerificationAgent()
