import json
import re
import uuid
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
                    issues=["No source evidence was retrieved, so the answer is ungrounded."],
                    claim_id=str(uuid.uuid4()),
                    importance="high",
                    verification_status="insufficient_evidence",
                    evidence_links=[]
                )
            ]

        # 1. Deterministic prep: Map citations inline
        citation_matches = re.findall(r'\[(\d+)\]', answer)
        used_indices = set(int(m) - 1 for m in citation_matches if m.isdigit())
        
        # Build evidence context for LLM verification
        evidence_summary = []
        evidence_id_map = {}
        for idx, ev in enumerate(evidence):
            evidence_id_map[idx] = ev.id
            evidence_summary.append(
                f"Source [{idx + 1}] (ID: {ev.id}, Tier: {ev.authority_level}):\n"
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
      "issues": ["List of discrepancies, e.g., source states 21 days but claim states 30 days"],
      "importance": "high" | "medium" | "low",
      "verification_status": "supported" | "partially_supported" | "unsupported" | "contradicted" | "insufficient_evidence",
      "evidence_links": [
         {{
            "evidence_index": 1,
            "relationship": "supports" | "contradicts" | "insufficient" | "context_only"
         }}
      ]
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
            
            for idx_item, item in enumerate(data.get("verification_results", [])):
                claim = item.get("claim", "")
                supported = bool(item.get("supported", False))
                ev_idx = item.get("evidence_index")
                confidence = float(item.get("confidence", 0.5))
                issues = item.get("issues", [])
                
                # New fields
                importance = item.get("importance", "medium")
                status = item.get("verification_status") or ("supported" if supported else "unsupported")
                elink_list = item.get("evidence_links") or []
                
                evidence_ids = []
                evidence_links = []
                citation_correct = True
                
                # Parse links
                for elink in elink_list:
                    idx_val = elink.get("evidence_index")
                    rel = elink.get("relationship", "supports")
                    if idx_val is not None:
                        try:
                            zero_based = int(idx_val) - 1
                            if zero_based in evidence_id_map:
                                ev_id = evidence_id_map[zero_based]
                                evidence_ids.append(ev_id)
                                evidence_links.append({
                                    "evidence_id": ev_id,
                                    "relationship": rel
                                })
                        except (ValueError, TypeError):
                            pass
                
                # Fallback to ev_idx if links list is empty
                if not evidence_links and ev_idx is not None:
                    try:
                        zero_based_idx = int(ev_idx) - 1
                        if zero_based_idx in evidence_id_map:
                            ev_id = evidence_id_map[zero_based_idx]
                            evidence_ids.append(ev_id)
                            evidence_links.append({
                                "evidence_id": ev_id,
                                "relationship": "supports" if supported else "contradicts"
                            })
                    except (ValueError, TypeError):
                        pass

                # Citation correctness checks
                if ev_idx is not None:
                    try:
                        zero_based_idx = int(ev_idx) - 1
                        if zero_based_idx not in evidence_id_map:
                            citation_correct = False
                            supported = False
                            status = "unsupported"
                            issues.append(f"Invalid citation index [{ev_idx}] - index out of bounds.")
                    except (ValueError, TypeError):
                        citation_correct = False
                        supported = False
                        status = "unsupported"
                        issues.append(f"Invalid citation format: {ev_idx}")
                elif not evidence_links:
                    citation_correct = False
                    supported = False
                    status = "insufficient_evidence"
                    issues.append("No citation associated with this claim.")
                
                claim_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{claim[:40]}_{idx_item}"))
                
                verification_results.append(
                    VerificationResult(
                        claim=claim,
                        supported=supported,
                        evidence_ids=evidence_ids,
                        citation_correct=citation_correct,
                        confidence=confidence,
                        issues=issues,
                        claim_id=claim_id,
                        importance=importance,
                        verification_status=status,
                        evidence_links=evidence_links
                    )
                )
        except Exception as e:
            logger.error(f"Verification agent failed: {e}. Falling back to default verification check.")
            verification_results.append(
                VerificationResult(
                    claim="Fallback claim verification",
                    supported=False,
                    evidence_ids=[],
                    citation_correct=False,
                    confidence=0.0,
                    issues=[f"Verification service error: {e}"],
                    claim_id=str(uuid.uuid4()),
                    importance="high",
                    verification_status="unsupported",
                    evidence_links=[]
                )
            )

        return verification_results

verification_agent = VerificationAgent()
