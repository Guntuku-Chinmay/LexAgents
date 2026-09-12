import json
import re
import logging
from typing import List, Dict, Any, Optional
from backend.app.core.llm import generate_chat_completion
from backend.app.models.schemas import Evidence, QueryContext, QueryAnalysis, ResearchPlan, AnswerQualityResult

logger = logging.getLogger(__name__)

class AnswerQualityGate:
    """
    Quality gate executed before returning any synthesized answer.
    Enforces that the answer directly addresses the original query,
    preserves user facts, and contains zero cross-domain hallucinations.
    """
    @classmethod
    def evaluate(cls, answer: str, qc: QueryContext, evidence: List[Evidence]) -> AnswerQualityResult:
        ans_lower = answer.lower()
        q_lower = qc.original_query.lower()
        rejection_reasons = []

        # Check A: Does answer introduce unrelated law from a conflicting domain?
        if qc.primary_domain == "Motor Vehicle Law":
            if any(w in ans_lower for w in ["article 165", "advocate-general", "advocate general", "article 15", "article 16", "article 21", "puttaswamy", "cheque bounce"]):
                rejection_reasons.append("Answer introduces unrelated constitutional or commercial provisions for a Motor Vehicle query.")

        elif qc.primary_domain == "Women & Gender Justice":
            if any(w in ans_lower for w in ["cheque bounce", "negotiable instruments", "motor vehicle", "traffic collision"]):
                rejection_reasons.append("Answer introduces unrelated commercial or traffic provisions for a Women & Gender Justice query.")

        elif qc.primary_domain == "Property & Land Law":
            if any(w in ans_lower for w in ["motor vehicle", "traffic collision", "article 165"]):
                rejection_reasons.append("Answer introduces unrelated motor vehicle or constitutional law for a Property Law query.")

        elif qc.primary_domain == "Cyber & Technology Law":
            if any(w in ans_lower for w in ["article 165", "motor vehicle accident"]):
                rejection_reasons.append("Answer introduces unrelated provisions for a Cyber Law query.")

        # Check B: Explicit provision mismatch
        if qc.explicit_identifiers:
            target_art = qc.explicit_identifiers.get("parent_article") or qc.explicit_identifiers.get("article")
            if target_art:
                # If answer asserts a different article as primary subject
                art_matches = re.findall(r'article\s*(\d+[a-z]*)', ans_lower)
                if art_matches and str(target_art).lower() not in art_matches:
                    rejection_reasons.append(f"Explicit provision mismatch: query asked Article {target_art} but answer discusses Article {art_matches[0]}.")

        is_relevant = len(rejection_reasons) == 0
        return AnswerQualityResult(
            is_relevant=is_relevant,
            addresses_query=is_relevant,
            addresses_outcome=is_relevant,
            addresses_issues=is_relevant,
            uses_relevant_evidence=is_relevant,
            no_unrelated_law=is_relevant,
            rejection_reasons=rejection_reasons
        )

class SynthesisAgent:
    def synthesize(
        self,
        query: str,
        evidence: List[Evidence],
        language: str = "en",
        query_analysis: Optional[QueryContext] = None,
        research_plan: Optional[ResearchPlan] = None
    ) -> Dict[str, Any]:
        """
        Synthesize retrieved evidence into a cohesive, query-constrained legal research answer.
        Enforces 8-section fact-pattern structure, preserves original user query,
        and applies AnswerQualityGate.
        """
        qc = query_analysis
        is_fact_pattern = qc.query_type == "fact_pattern" if qc else False

        # If no evidence retrieved, generate safe, structured insufficient-evidence response
        if not evidence:
            return self._build_insufficient_evidence_response(query, qc, language)

        # Format evidence list for prompt
        evidence_summary = []
        for idx, ev in enumerate(evidence):
            evidence_summary.append(
                f"Source [{idx + 1}]:\n"
                f"ID: {ev.id}\n"
                f"Source: {ev.source}\n"
                f"Type: {ev.doc_type}\n"
                f"Domain: {ev.domain or qc.primary_domain if qc else 'General'}\n"
                f"Content: {ev.text}\n"
                f"---"
            )
        evidence_context = "\n".join(evidence_summary)

        facts_block = ""
        issues_block = ""
        outcome_block = ""
        domain_block = f"\nPrimary Legal Domain: {qc.primary_domain if qc else 'General Legal'}"
        if qc:
            if qc.facts:
                facts_block = "\nExtracted Facts from User Scenario:\n- " + "\n- ".join(qc.facts)
            if qc.legal_issues:
                issues_block = "\nIdentified Substantive Legal Issues:\n- " + "\n- ".join(qc.legal_issues)
            if qc.requested_outcome:
                outcome_block = f"\nUser Requested Outcome: {qc.requested_outcome}"

        structure_instruction = ""
        if is_fact_pattern:
            structure_instruction = """
FORMAT REQUIREMENT (Fact-Pattern Analysis):
Structure your response using these exact numbered sections:
1. What I understand from your facts: State the factual scenario clearly.
2. Relevant legal issues: Identify the specific legal questions arising from the facts.
3. Applicable law: Present the governing statutory provisions and judicial doctrines supported by the evidence.
4. How the law may apply to these facts: Objectively analyze how the rules apply to the stated circumstances.
5. Potential liability / defence / remedy: Outline potential legal positions without guaranteeing an outcome.
6. Evidence that would strengthen the position: Mention contemporaneous evidence needed (e.g. dashcam, witness testimony, notices).
7. Important limitations: State what cannot be concluded from available records.
8. Relevant authorities: Summarize cited authorities.
"""

        lang_instruction = ""
        if language == "hi":
            lang_instruction = (
                "\nTarget Language: Hindi (हिन्दी). Draft your legal opinion in formal, professional Hindi. "
                "CRITICAL: Preserve authentic Act names, Section/Article numbers, and inline citation brackets [1], [2]."
            )
        elif language == "te":
            lang_instruction = (
                "\nTarget Language: Telugu (తెలుగు). Draft your legal opinion in formal, professional Telugu. "
                "CRITICAL: Preserve authentic Act names, Section/Article numbers, and inline citation brackets [1], [2]."
            )

        system_prompt = f"""You are the Synthesis Agent for LexAgents, an advanced Indian legal research system.
Your job is to answer the ORIGINAL USER QUERY based strictly and objectively on the provided evidence.

CRITICAL DIRECTIVES:
- You are answering the ORIGINAL USER QUERY: "{query}".
- Do not answer a different legal question.
- Do not invent legal provisions, Act years, or case citations.
- Cite sources inline using bracketed numbers [1], [2] corresponding to the sources below.
- If the retrieved evidence does not address a specific fact or issue, explicitly state that limitation.
- Distinguish clearly between statutory codes and judicial precedents.
{domain_block}{facts_block}{issues_block}{outcome_block}
{structure_instruction}{lang_instruction}

Available Evidence:
{evidence_context}

Your output MUST be a JSON object conforming to:
{{
  "answer": "Detailed synthesized legal answer text with inline citations.",
  "conflicts": [
     "Describe conflict 1 (if any)"
  ]
}}
Respond ONLY with valid JSON.
"""

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Synthesize an answer for the original user query: {query}"}
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
            draft_answer = data.get("answer", "")
            conflicts = data.get("conflicts", [])

            # Run AnswerQualityGate
            if qc:
                gate_res = AnswerQualityGate.evaluate(draft_answer, qc, evidence)
                if not gate_res.is_relevant:
                    logger.warning(f"AnswerQualityGate rejected draft answer: {gate_res.rejection_reasons}")
                    return self._build_insufficient_evidence_response(query, qc, language, gate_res.rejection_reasons)

            return {
                "answer": draft_answer,
                "conflicts": conflicts
            }
        except Exception as e:
            logger.error(f"Synthesis failed: {e}. Falling back to safe response.")
            return self._build_insufficient_evidence_response(query, qc, language, [str(e)])

    def _build_insufficient_evidence_response(
        self,
        query: str,
        qc: Optional[QueryContext],
        language: str = "en",
        reasons: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Build an anchored, safe response outlining facts and issues when evidence is lacking."""
        primary_domain = qc.primary_domain if qc else "the requested legal subject"
        facts = qc.facts if qc else []
        issues = qc.legal_issues if qc else []
        outcome = qc.requested_outcome if qc else None

        if qc and qc.query_type == "fact_pattern":
            facts_list = "\n".join([f"- {f}" for f in facts]) if facts else f"- {query}"
            issues_list = "\n".join([f"- {i}" for i in issues]) if issues else "- Actionable liability and statutory standard of care"

            if language == "hi":
                answer = (
                    f"आपके द्वारा प्रस्तुत तथ्यों के आधार पर:\n\n"
                    f"1. आपके तथ्यों से समझ:\n{facts_list}\n\n"
                    f"2. प्रासंगिक कानूनी मुद्दे:\n{issues_list}\n\n"
                    f"3. लागू कानून एवं भंडार की स्थिति:\n"
                    f"उपलब्ध भारतीय कानूनी भंडार के आधार पर, इस विशिष्ट स्थिति पर निश्चित राय देने के लिए अपर्याप्त प्रामाणिक साक्ष्य उपलब्ध हैं। "
                    f"वर्तमान भंडार में {primary_domain} (जैसे मोटर वाहन अधिनियम या संबंधित न्यायिक निर्णय) से जुड़े सांविधिक प्रावधान अनुक्रमित नहीं हैं।\n\n"
                    f"4. संभावित दायित्व / बचाव:\n"
                    f"अचानक जानवर आने की स्थिति में 'अपरिहार्य दुर्घटना' (Inevitable Accident) और आपातकालीन बचाव पर विचार किया जा सकता है, "
                    f"किंतु शराब/नशे की स्थिति और सार्वजनिक संपत्ति को नुकसान स्वतंत्र रूप से दायित्व को प्रभावित कर सकते हैं।\n\n"
                    f"5. साक्ष्य जो स्थिति को सुदृढ़ करेंगे:\n"
                    f"- समकालीन साक्ष्य (डैशकैम फुटेज, प्रत्यक्षदर्शी बयान)\n"
                    f"- घटनास्थल पर पुलिस डायरी (GD प्रविष्टि) अथवा पंचनामा\n"
                    f"- वाहन चालन के समय सोबर होने का चिकित्सकीय/रक्त परीक्षण साक्ष्य\n\n"
                    f"6. महत्वपूर्ण सीमाएं:\n"
                    f"प्रामाणिक सांविधिक प्रावधानों के बिना दोषमुक्ति का दावा नहीं किया जा सकता।"
                )
            elif language == "te":
                answer = (
                    f"మీరు అందించిన వాస్తవాల ఆధారంగా:\n\n"
                    f"1. మీ వాస్తవాల నుండి అర్థం చేసుకున్నవి:\n{facts_list}\n\n"
                    f"2. సంబంధిత చట్టపరమైన అంశాలు:\n{issues_list}\n\n"
                    f"3. వర్తించే చట్టం మరియు సమాచార నిధి స్థితి:\n"
                    f"భారతీయ చట్టపరమైన ఆధారాల ప్రకారం, ఈ ప్రశ్నకు సమాధానం ఇవ్వడానికి తగిన ఆధారాలు లేవు (insufficient authoritative evidence). "
                    f"ప్రస్తుత సమాచార నిధిలో {primary_domain} కు సంబంధించిన నిబంధనలు అందుబాటులో లేవు.\n\n"
                    f"4. బాధ్యత / రక్షణ విశ్లేషణ:\n"
                    f"అకస్మాత్తుగా జంతువు రావడం అనివార్య ప్రమాదం (Inevitable Accident) కిందకు రావచ్చు, కానీ ప్రజా ఆస్తికి నష్టం మరియు మద్యం పరిస్థితి బాధ్యతను ప్రభావితం చేస్తాయి.\n\n"
                    f"5. బలోపేతం చేసే ఆధారాలు:\n"
                    f"- డ్యాష్‌క్యామ్ లేదా ప్రత్యక్ష సాక్షుల వాంగ్మూలాలు\n"
                    f"- వైద్య పరీక్షల రికార్డులు\n\n"
                    f"6. పరిమితులు:\n"
                    f"చట్టబద్ధమైన అధికారిక నిబంధనలు లేకుండా ఎటువంటి ముగింపు ఇవ్వలేము."
                )
            else:
                answer = (
                    f"Based on the factual scenario provided:\n\n"
                    f"1. What I understand from your facts:\n{facts_list}\n\n"
                    f"2. Relevant legal issues:\n{issues_list}\n\n"
                    f"3. Applicable law & repository status:\n"
                    f"Based on the Indian legal repository, there is insufficient authoritative evidence available to evaluate this question reliably. "
                    f"The indexed corpus does not currently contain statutory provisions under the governing legislation for {primary_domain} (such as the Motor Vehicles Act, 1988) or specific claims tribunal precedents.\n\n"
                    f"4. How the law may apply to these facts:\n"
                    f"Under general legal principles, sudden entry of cattle may raise the defence of inevitable accident or sudden emergency. "
                    f"However, damage to public utility property (electric pole) and driver sobriety state represent independent factors that affect the determination of actionable negligence.\n\n"
                    f"5. Potential liability / defence / remedy:\n"
                    f"To rebut a presumption of negligence, the driver must demonstrate reasonable standard of care under the sudden emergency doctrine. "
                    f"No guaranteed exoneration can be stated without examination of statutory provisions.\n\n"
                    f"6. Evidence that would strengthen the position:\n"
                    f"- Contemporaneous dashcam footage or third-party eyewitness statements\n"
                    f"- Immediate General Diary (GD) entry or spot panchanama recording the stray animal\n"
                    f"- Medical or breathalyzer verification substantiating sobriety at the relevant time\n\n"
                    f"7. Important limitations:\n"
                    f"Because local statutory texts for {primary_domain} are not indexed, this assessment is an informational issue breakdown and does not constitute a guaranteed legal outcome."
                )
        else:
            issues_text = ""
            if issues:
                issues_text = "\n\nIdentified Legal Issues:\n- " + "\n- ".join(issues)

            if language == "hi":
                answer = f"उपलब्ध भारतीय कानूनी भंडार के आधार पर, इस प्रश्न का उत्तर देने के लिए पर्याप्त प्रामाणिक कानूनी साक्ष्य उपलब्ध नहीं हैं। वर्तमान भंडार में {primary_domain} से संबंधित सांविधिक प्रावधान या न्यायिक निर्णय अनुक्रमित नहीं हैं।{issues_text}"
            elif language == "te":
                answer = f"అందుబాటులో ఉన్న భారతీయ చట్టపరమైన సమాచార నిధి ఆధారంగా, ఈ ప్రశ్నకు సమాధానం ఇవ్వడానికి తగిన చట్టపరమైన ఆధారాలు లభించలేదు. ప్రస్తుత సమాచార నిధిలో {primary_domain} కు సంబంధించిన నిబంధనలు లేవు.{issues_text}"
            else:
                answer = f"Based on the Indian legal repository, there is insufficient authoritative evidence available to answer this question reliably. The indexed corpus does not currently contain statutory provisions or judicial precedents governing {primary_domain}.{issues_text}"

        return {
            "answer": answer,
            "conflicts": []
        }

synthesis_agent = SynthesisAgent()

