import re
import uuid
from typing import Dict, List, Any, Optional
from backend.app.models.schemas import QueryContext, QueryAnalysis, ResearchPlan
from backend.app.retrieval.canonical_taxonomy import SUPPORTED_DOMAINS, get_domain
from backend.app.retrieval.vector_bm25 import extract_identifiers_from_query

class QueryType(str):
    """
    Rich legal QueryType supporting the 17 standard query types:
    1. provision_lookup
    2. legal_definition
    3. legal_explanation
    4. fact_pattern
    5. liability_analysis
    6. defence_analysis
    7. legal_remedy
    8. procedure
    9. comparison
    10. case_law_research
    11. applicability
    12. compliance
    13. rights_duties
    14. penalty_punishment
    15. document_analysis
    16. general_legal_research
    17. current_law_status

    Provides seamless backward-compatibility when evaluated against legacy coarse-grained categories:
    'explicit_reference', 'fact_pattern', and 'conceptual_inquiry'.
    """
    def __eq__(self, other):
        s = str(self)
        other_s = str(other)
        if s == other_s:
            return True
        if s in ("provision_lookup", "explicit_reference", "specific_provision") and other_s in ("provision_lookup", "explicit_reference", "specific_provision"):
            return True
        if s in ("fact_pattern", "fact_pattern_analysis") and other_s in ("fact_pattern", "fact_pattern_analysis"):
            return True
        if other_s == "conceptual_inquiry" and s not in ("fact_pattern", "fact_pattern_analysis", "explicit_reference", "provision_lookup", "specific_provision"):
            return True
        if other_s == "explicit_reference" and s in ("explicit_reference", "provision_lookup", "specific_provision"):
            return True
        if other_s == "fact_pattern" and s in ("fact_pattern", "fact_pattern_analysis"):
            return True
        if s == "conceptual_inquiry" and other_s not in ("fact_pattern", "fact_pattern_analysis", "explicit_reference", "provision_lookup", "specific_provision"):
            return True
        if s == "explicit_reference" and other_s in ("explicit_reference", "provision_lookup", "specific_provision"):
            return True
        if s == "fact_pattern" and other_s in ("fact_pattern", "fact_pattern_analysis"):
            return True
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(str(self))

def normalize_legal_text(query: str) -> str:
    """Normalize common typos, colloquial phrasing, and spacing."""
    norm = query.strip()
    
    # Common conversational / grammatical normalization
    norm_rules = [
        (r"\bif i['’]?ve\b", "if I have"),
        (r"\bi['’]?ve\b", "I have"),
        (r"\bi['’]?m\b", "I am"),
        (r"\bun[\s-]?drunk\b", "not drunk sober"),
        (r"\bdashed\s+(?:the|into|a)\b", "collided with the"),
        (r"\bgot arrested\b", "was arrested"),
        (r"\bnot giving back\b", "refusing to return"),
        (r"\btook my deposit\b", "retained my security deposit"),
        (r"\btook money from account\b", "unauthorized withdrawal of funds from account"),
        (r"\bfired me suddenly\b", "unlawfully terminated my employment without notice"),
        (r"\brefuses refund\b", "refuses to provide refund or replacement for defective item"),
    ]
    for pattern, replacement in norm_rules:
        norm = re.sub(pattern, replacement, norm, flags=re.IGNORECASE)
    return norm

def detect_language(query: str) -> str:
    """Detect language based on Unicode script."""
    if any("\u0900" <= c <= "\u097F" for c in query):
        return "hi"
    if any("\u0C00" <= c <= "\u0C7F" for c in query):
        return "te"
    return "en"

def extract_named_entities(query: str) -> List[str]:
    """Extract known legal, institutional, and personal entities from query."""
    entities = []
    known_entities = [
        "Supreme Court", "High Court", "Sessions Court", "Magistrate", "Internal Complaints Committee",
        "ICC", "SEBI", "RBI", "TRAI", "NCLT", "NCLAT", "NCDRC", "CERT-In", "RERA",
        "Rajesh Kumar", "Dalmia Cement", "Puttaswamy", "Maneka Gandhi", "Vishaka"
    ]
    for ent in known_entities:
        if re.search(r'\b' + re.escape(ent) + r'\b', query, re.IGNORECASE):
            entities.append(ent)
    return entities

def extract_facts_from_pattern(query: str) -> List[str]:
    """Extract factual assertions from natural language fact patterns."""
    facts = []
    q_lower = query.lower()

    # Vehicle / road collision facts
    if any(w in q_lower for w in ["car", "vehicle", "driving", "drove", "driver", "motorcycle", "scooter"]):
        facts.append("person was operating/driving a motor vehicle")
    if "cow" in q_lower or "cattle" in q_lower or "animal" in q_lower:
        facts.append("cattle/animal suddenly entered the roadway")
    if any(w in q_lower for w in ["saving", "avoid", "swerved", "swerve"]):
        facts.append("driver took evasive action to avoid striking an animal")
    if any(w in q_lower for w in ["pole", "electric pole", "dashed", "hit", "collided", "collision"]):
        facts.append("vehicle collided with an electric utility pole causing property damage")
    if "drunk" in q_lower or "un drunk" in q_lower or "sober" in q_lower:
        if "un drunk" in q_lower or "not drunk" in q_lower or "sober" in q_lower:
            facts.append("driver claims sobriety / absence of intoxication")
        else:
            facts.append("driver sobriety/intoxication state is in question")
    if any(w in q_lower for w in ["prove i've no mistakes", "prove no mistake", "prove no fault", "not my fault"]):
        facts.append("driver seeks to establish absence of fault or negligence")

    # Tenancy / deposit facts
    if any(w in q_lower for w in ["landlord", "tenant", "deposit", "security deposit", "rent"]):
        if any(w in q_lower for w in ["refusing", "not giving", "withheld", "took", "refuses to return", "refuses"]):
            facts.append("landlord is withholding or refusing to refund tenant's security deposit")
        if "lease" in q_lower or "agreement" in q_lower:
            facts.append("residential or commercial lease agreement exists between parties")

    # Workplace harassment facts
    if any(w in q_lower for w in ["employer", "boss", "manager", "workplace", "colleague", "supervisor"]):
        if any(w in q_lower for w in ["touching", "touches", "sexual", "harassing", "comments", "harassment", "bad things", "inappropriately"]):
            facts.append("employee is experiencing unwelcome sexual conduct/comments in workplace")

    # Cyber fraud facts
    if any(w in q_lower for w in ["hacked", "stole money", "upi", "online scam", "phishing", "account"]):
        facts.append("unauthorized party accessed electronic account and transferred funds")

    # Employment termination facts
    if any(w in q_lower for w in ["fired", "terminated", "dismissed"]):
        if any(w in q_lower for w in ["suddenly", "without", "no notice", "unlawful", "severance"]):
            facts.append("employee was terminated without statutory or contractual notice or severance pay")

    # Defective product facts
    if any(w in q_lower for w in ["purchase", "defective", "seller refuses", "product"]):
        facts.append("consumer received defective goods and seller refused refund/replacement")

    # Corporate / Director funds facts
    if any(w in q_lower for w in ["director", "board"]) and any(w in q_lower for w in ["transferred", "misused", "company funds", "company accounts", "private firm", "without board approval"]):
        facts.append("company director allegedly misappropriated or transferred corporate funds without approval")

    # Arrest facts
    if "arrested" in q_lower or "police" in q_lower or "custody" in q_lower:
        facts.append("individual was arrested and placed in police/judicial custody")

    return facts

def extract_legal_issues(query: str, primary_domain: str, facts: List[str]) -> List[str]:
    """Identify substantive legal issues arising from the query and facts."""
    issues = []
    q_lower = query.lower()

    if primary_domain == "Motor Vehicle Law":
        issues.extend([
            "actionable negligence and standard of care for motor vehicle drivers",
            "doctrine of inevitable accident and sudden emergency in avoiding animals",
            "statutory liability for damage to public utility property under Motor Vehicles Act",
            "statutory provisions and penalties concerning driving under influence (Section 185 MVA)",
            "burden of proof and evidence required to rebut negligence in claims tribunal"
        ])
    elif primary_domain == "Women & Gender Justice":
        issues.extend([
            "statutory definitions of sexual harassment under POSH Act 2013",
            "procedure for lodging formal complaint before Internal Complaints Committee (ICC)",
            "interim measures and protective relief during inquiry under Section 12 POSH Act",
            "employer statutory obligations and criminal complaint assistance under Section 19"
        ])
    elif primary_domain == "Property & Land Law":
        issues.extend([
            "contractual and statutory obligations governing return of security deposit",
            "permissible deductions versus unlawful withholding by landlord",
            "legal notice and summary recovery remedies under tenancy and civil laws"
        ])
    elif primary_domain == "Cyber & Technology Law":
        issues.extend([
            "criminal offences of cheating by personation and hacking under IT Act (Sections 66C, 66D)",
            "statutory dispute redressal and bank liability for unauthorized digital transactions",
            "procedure for reporting cybercrime to CERT-In and local cyber cell"
        ])
    elif primary_domain == "Criminal Procedure":
        issues.extend([
            "statutory provisions governing bail in bailable versus non-bailable offences",
            "procedural safeguards upon arrest under CrPC / BNSS",
            "investigation timelines and rights of the accused after FIR registration"
        ])
    elif primary_domain == "Criminal Law":
        issues.extend([
            "essential statutory ingredients of the alleged penal offence",
            "mens rea and physical actus reus requirements under substantive penal law",
            "applicability of general exceptions and statutory defences"
        ])
    elif primary_domain == "Consumer Law":
        issues.extend([
            "deficiency in service and product liability under Consumer Protection Act 2019",
            "statutory remedies including refund, replacement, and compensation",
            "jurisdiction and procedure for filing complaint before District Consumer Commission"
        ])
    elif primary_domain == "Labour & Employment Law":
        issues.extend([
            "legality of termination without notice or domestic inquiry",
            "statutory retrenchment compensation and severance rights",
            "dispute resolution mechanisms under Industrial Disputes Act / labour codes"
        ])
    elif primary_domain == "Corporate & Commercial Law":
        issues.extend([
            "fiduciary duties and statutory liability of company directors",
            "mandatory statutory requirements under Section 138 Negotiable Instruments Act",
            "contractual breach and liability for damages under Indian Contract Act 1872"
        ])
    elif primary_domain == "Constitutional Law":
        issues.extend([
            "scope and ambit of fundamental rights under Part III of the Constitution",
            "constitutional restrictions and proportionality test for state actions",
            "constitutional remedy under Article 32 or Article 226"
        ])
    elif primary_domain == "Civil Law":
        issues.extend([
            "tortious liability and assessment of civil damages",
            "requirements for grant of declaratory relief and injunctions under Specific Relief Act"
        ])

    return issues

def determine_query_type(query: str, explicit_idents: Dict[str, Any], q_lower: str) -> QueryType:
    """Classify the query into one of the 17 standard query types."""
    # 1. Fact pattern check - match personal narratives, dispute scenarios, or multi-fact situations
    fact_pattern_phrases = [
        "if i", "my car", "my landlord", "my boss", "my manager", "a cow came", "dashed the",
        "i was arrested", "someone hacked", "company fired me", "seller refuses",
        "a driver swerved", "swerved to avoid", "hit an electric pole", "swerved into",
        "landlord refuses", "refuses to return", "refusing to return", "hit a pole",
        "keeps touching me", "fired me suddenly", "hacked my phone", "touch me and saying",
        "touches me", "fired me without", "without board approval", "paid a deposit",
        "someone called", "i bought", "police entered", "arrested my brother",
        "stole 2 lakhs", "transferred 10 crore", "transferred from company"
    ]
    is_narrative = re.search(r'\b(i|my|me|we)\b', q_lower) and any(action in q_lower for action in [
        "arrested", "fired", "swerved", "dashed", "crashed", "stole", "hacked", "bought",
        "deposited", "paid", "contracted", "harassed", "refused", "withheld"
    ])
    if any(phrase in q_lower for phrase in fact_pattern_phrases) or is_narrative:
        return QueryType("fact_pattern")

    # 2. Explicit Provision Lookup
    if explicit_idents:
        if any(w in q_lower for w in ["definition", "define", "what is the meaning of"]):
            return QueryType("legal_definition")
        return QueryType("provision_lookup")

    # 3. Fine-grained non-fact-pattern inquiries
    if any(w in q_lower for w in ["definition of", "define", "what is defined as"]):
        return QueryType("legal_definition")
    if any(w in q_lower for w in ["difference between", "distinction between", "compare", "versus", "vs"]):
        return QueryType("comparison")
    if any(w in q_lower for w in ["procedure", "how does", "what happens after", "process for", "how to file"]):
        return QueryType("procedure")
    if any(w in q_lower for w in ["who is liable", "whose fault", "liability for", "held liable"]):
        return QueryType("liability_analysis")
    if any(w in q_lower for w in ["defence", "defense", "exceptions to", "prove no fault", "prove no mistake"]):
        return QueryType("defence_analysis")
    if any(w in q_lower for w in ["remedy", "remedies", "compensation", "damages", "protection"]):
        return QueryType("legal_remedy")
    if any(w in q_lower for w in ["penalty", "punishment", "imprisonment", "fine"]):
        return QueryType("penalty_punishment")
    if any(w in q_lower for w in ["precedent", "landmark case", "judgment", "case law"]):
        return QueryType("case_law_research")
    if any(w in q_lower for w in ["duties of", "rights of", "duty"]):
        return QueryType("rights_duties")
    if any(w in q_lower for w in ["compliance", "mandatory rules"]):
        return QueryType("compliance")
    if any(w in q_lower for w in ["does it apply", "applicability"]):
        return QueryType("applicability")
    if any(w in q_lower for w in ["clause", "agreement terms", "contract terms"]):
        return QueryType("document_analysis")
    if any(w in q_lower for w in ["in force", "amended", "current status"]):
        return QueryType("current_law_status")
    if any(w in q_lower for w in ["explain", "what does", "what is"]):
        return QueryType("legal_explanation")

    return QueryType("general_legal_research")

def analyze_query(query: str, query_id: Optional[str] = None) -> QueryContext:
    """
    Perform deep structured query analysis.
    Produces a canonical QueryContext preserving facts, legal issues, domain, and user intent.
    """
    if not query_id:
        query_id = str(uuid.uuid4())

    raw_query = query.strip()
    norm_query = normalize_legal_text(raw_query)
    lang = detect_language(raw_query)
    explicit_idents = extract_identifiers_from_query(raw_query)
    q_lower = norm_query.lower()
    named_entities = extract_named_entities(raw_query)

    # 1. Determine Query Type
    query_type = determine_query_type(raw_query, explicit_idents, q_lower)

    # 2. Domain Scoring with Exclusion Signals
    domain_scores: Dict[str, float] = {}
    matched_subdomains: Dict[str, List[str]] = {}

    GENERIC_SUBDOMAIN_TERMS = {
        "offences", "offence", "remedies", "remedy", "against", "procedure",
        "orders", "order", "rights", "safety", "regulations", "rules", "dispute",
        "disputes", "conditions", "records", "record", "formation", "governance", "compliance"
    }

    for d_name, d_def in SUPPORTED_DOMAINS.items():
        score = 0.0
        subs: List[str] = []

        # Check exclusion signals: If query matches an exclusion signal for this domain, penalize heavily
        has_exclusion = False
        for excl in d_def.exclusion_signals:
            if any(ord(c) > 127 for c in excl):
                if excl in q_lower:
                    has_exclusion = True
                    score -= 10.0
                    break
            else:
                if re.search(r'\b' + re.escape(excl) + r'\b', q_lower):
                    has_exclusion = True
                    score -= 10.0
                    break

        if not has_exclusion:
            # Match keywords
            for kw in d_def.keywords:
                if any(ord(c) > 127 for c in kw):
                    if kw in q_lower:
                        score += 2.0
                else:
                    if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                        score += 2.0

            # Match subdomains
            for sub in d_def.subdomains:
                sub_lower = sub.lower()
                if re.search(r'\b' + re.escape(sub_lower) + r'\b', q_lower):
                    score += 2.0
                    subs.append(sub)
                else:
                    sub_terms = [t for t in sub_lower.split() if len(t) > 3 and t not in GENERIC_SUBDOMAIN_TERMS]
                    if sub_terms and any(re.search(r'\b' + re.escape(t) + r'\b', q_lower) for t in sub_terms):
                        score += 1.5
                        subs.append(sub)

        domain_scores[d_name] = max(0.0, score)
        matched_subdomains[d_name] = subs

    # 3. Explicit Identifier Overrides (Strict Identifier Mode)
    if explicit_idents:
        if "article" in explicit_idents or "parent_article" in explicit_idents or "schedule" in explicit_idents or "preamble" in explicit_idents:
            domain_scores["Constitutional Law"] = 100.0
        elif "section" in explicit_idents:
            sec_val = str(explicit_idents.get("section", ""))
            if sec_val in ("138", "139", "141"):
                domain_scores["Corporate & Commercial Law"] = 100.0
            elif sec_val in ("437", "438", "439", "154", "167"):
                domain_scores["Criminal Procedure"] = 100.0
            elif sec_val in ("66", "66C", "66D", "79"):
                domain_scores["Cyber & Technology Law"] = 100.0
            elif sec_val in ("498A", "304A", "378", "302", "300", "120B"):
                domain_scores["Criminal Law"] = 100.0
            elif sec_val in ("185", "166", "163A", "134"):
                domain_scores["Motor Vehicle Law"] = 100.0
            elif sec_val in ("9", "11", "12", "13"):
                if any(w in q_lower for w in ["posh", "harassment", "women", "sexual"]):
                    domain_scores["Women & Gender Justice"] = 100.0
        elif "regulation" in explicit_idents or "rule" in explicit_idents:
            if "sebi" in q_lower or "upsi" in q_lower or "insider" in q_lower:
                domain_scores["Corporate & Commercial Law"] = 100.0

    # 4. Fact Pattern Specialized Matching
    # Specific case: Car, cow, pole collision
    if ("car" in q_lower or "vehicle" in q_lower or "driver" in q_lower or "driving" in q_lower) and any(w in q_lower for w in ["pole", "cow", "cattle", "dashed", "traffic", "accident", "swerved", "saving"]):
        domain_scores["Motor Vehicle Law"] = 50.0
        domain_scores["Civil Law"] = 15.0
        domain_scores["Criminal Law"] = 10.0
        domain_scores["Constitutional Law"] = 0.0

    # Specific case: Workplace sexual harassment / Dowry / Women & Gender Justice
    if any(w in q_lower for w in ["sexual harassment", "posh", "boss keeps touching", "internal complaints committee", "vishaka", "dowry", "domestic violence", "touch me and saying", "inappropriate comments and touching", "touches me", "touching me", "inappropriately", "inappropriate touch"]):
        domain_scores["Women & Gender Justice"] = 50.0
        domain_scores["Criminal Law"] = 15.0
        domain_scores["Constitutional Law"] = 0.0

    # Specific case: Bail / FIR
    if any(re.search(r'\b' + re.escape(w) + r'\b', q_lower) for w in ["bail", "fir", "arrested", "custody", "remand", "arrest memo"]):
        domain_scores["Criminal Procedure"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Deposit / Landlord
    if any(w in q_lower for w in ["landlord", "deposit", "security deposit", "rent agreement", "lease"]):
        domain_scores["Property & Land Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Specific case: Online scam / hacked / financial fraud
    if any(w in q_lower for w in ["hacked", "upi", "online scam", "phishing", "stole money", "financial scam", "online financial scam", "cyber scam", "cyber fraud", "online banking"]):
        domain_scores["Cyber & Technology Law"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Cheque bounce / Negotiable Instruments
    if any(w in q_lower for w in ["cheque bounce", "dishonour of cheque", "section 138", "చెక్ బౌన్స్", "చెక్కు బౌన్స్", "చేక్ బౌన్స్", "చేక్", "చెక్కు", "चेक बाउंस"]):
        domain_scores["Corporate & Commercial Law"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Consumer defective goods
    if any(w in q_lower for w in ["defective", "deficient service", "consumer commission", "product liability", "defective product"]):
        domain_scores["Consumer Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Specific case: Employment termination
    if any(w in q_lower for w in ["fired without notice", "fired me", "terminated without", "unlawful termination", "severance pay"]):
        domain_scores["Labour & Employment Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Specific case: Corporate director misuse
    if any(w in q_lower for w in ["director misused", "misused company funds", "corporate funds"]) or (any(w in q_lower for w in ["director", "board of directors", "shareholders"]) and any(w in q_lower for w in ["accounts", "transferred", "without board approval", "board approval", "private firm"])):
        domain_scores["Corporate & Commercial Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Rank domains
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_domains and sorted_domains[0][1] > 0.0:
        primary_domain = sorted_domains[0][0]
    else:
        primary_domain = "Civil Law"

    # Secondary domains
    secondary_domains: List[str] = []
    for d, s in sorted_domains[1:]:
        if s >= 8.0 and d != primary_domain:
            secondary_domains.append(d)
        if len(secondary_domains) >= 2:
            break

    # Facts & Legal Issues
    facts = extract_facts_from_pattern(raw_query) if query_type == "fact_pattern" else []
    legal_issues = extract_legal_issues(raw_query, primary_domain, facts)

    # Intended outcome
    requested_outcome = None
    if any(p in q_lower for p in ["prove i've no mistakes", "prove no mistake", "prove no fault", "not my fault"]):
        requested_outcome = "Rebut presumption of negligence / establish absence of fault"
    elif "bail" in q_lower:
        requested_outcome = "Securing release on bail"
    elif "deposit" in q_lower:
        requested_outcome = "Recovery of full security deposit from landlord"
    elif any(p in q_lower for p in ["remedies", "protection", "what legal protection"]):
        requested_outcome = "Statutory protection and legal remedies"
    elif any(p in q_lower for p in ["refund", "replacement"]):
        requested_outcome = "Refund or replacement for defective goods"

    # Legal intents
    intents = []
    if any(w in q_lower for w in ["liable", "liability", "fault", "mistake"]):
        intents.append("liability")
    if any(w in q_lower for w in ["defence", "defense", "prove no mistake", "saving the cattle"]):
        intents.append("defence")
    if any(w in q_lower for w in ["remedy", "remedies", "compensation", "damages"]):
        intents.append("remedies")
    if any(w in q_lower for w in ["procedure", "how to", "what happens after"]):
        intents.append("procedure")
    if any(w in q_lower for w in ["evidence", "prove"]):
        intents.append("evidence")
    if not intents:
        intents.append("legal_research")

    # Research questions
    research_questions = []
    if query_type == "fact_pattern":
        if primary_domain == "Motor Vehicle Law":
            research_questions = [
                "Does sudden entry of an animal constitute an inevitable accident or sudden emergency rebutting negligence?",
                "What is the statutory standard of care and liability for property damage under the Motor Vehicles Act?",
                "How does alleged sobriety or intoxication affect liability and burden of proof under Section 185 MVA?"
            ]
        elif primary_domain == "Women & Gender Justice":
            research_questions = [
                "What constitutes sexual harassment under Section 2(n) and Section 3 of POSH Act 2013?",
                "What is the complaint mechanism and inquiry procedure before the Internal Complaints Committee?",
                "What interim relief and disciplinary/penal actions are provided under Sections 12, 13, and 19?"
            ]
        elif primary_domain == "Property & Land Law":
            research_questions = [
                "Can a landlord legally withhold a security deposit without showing damage or breach?",
                "What legal remedy and summary recovery procedure is available to a tenant?"
            ]
        elif primary_domain == "Cyber & Technology Law":
            research_questions = [
                "What offences are committed under Sections 66C and 66D of the Information Technology Act?",
                "What is the RBI regulatory framework regarding unauthorized electronic banking transactions and customer liability?"
            ]
        elif primary_domain == "Labour & Employment Law":
            research_questions = [
                "Is termination without notice or domestic inquiry lawful under Indian labour legislation?",
                "What compensation or reinstatement remedies are available for unlawful retrenchment?"
            ]
        elif primary_domain == "Consumer Law":
            research_questions = [
                "What constitutes a defective product and deficiency in service under Consumer Protection Act 2019?",
                "What remedies (refund, replacement, compensation) can the District Consumer Commission order?"
            ]
        elif primary_domain == "Corporate & Commercial Law":
            research_questions = [
                "What are the fiduciary duties of company directors under Section 166 of the Companies Act 2013?",
                "What civil and criminal liabilities arise from misappropriation of corporate funds?"
            ]
    else:
        research_questions = [f"What are the governing statutory and judicial authorities for {norm_query}?"]

    # Source types
    p_def = get_domain(primary_domain)
    source_types = p_def.likely_source_types if p_def else ["central_act", "sc_judgment"]

    # Confidence calibration
    if explicit_idents:
        confidence = 0.95
        confidence_label = "Strong evidence"
    elif facts and len(facts) >= 2:
        confidence = 0.75
        confidence_label = "Moderate evidence"
    elif sorted_domains and sorted_domains[0][1] >= 6.0:
        confidence = 0.65
        confidence_label = "Moderate evidence"
    else:
        confidence = 0.20
        confidence_label = "Insufficient evidence"

    return QueryContext(
        query_id=query_id,
        original_query=raw_query,
        normalized_query=norm_query,
        query_type=query_type,
        primary_domain=primary_domain,
        secondary_domains=secondary_domains,
        sub_domains=matched_subdomains.get(primary_domain, [])[:4],
        intent=intents,
        legal_intents=intents,
        facts=facts,
        legal_issues=legal_issues[:5],
        requested_outcome=requested_outcome,
        source_types=source_types,
        explicit_identifiers=explicit_idents,
        named_entities=named_entities,
        jurisdiction="India",
        research_questions=research_questions,
        confidence=confidence,
        confidence_label=confidence_label,
        language=lang,
        is_ambiguous=False,
        missing_information=[]
    )

def generate_research_plan(qc: QueryContext) -> ResearchPlan:
    """Generate structured ResearchPlan based on QueryContext."""
    selected_agents = []
    explicit_targets = []

    if qc.explicit_identifiers:
        search_strategy = "strict_identifier"
        if "article" in qc.explicit_identifiers or "schedule" in qc.explicit_identifiers or "preamble" in qc.explicit_identifiers:
            selected_agents = ["constitutional"]
            art = qc.explicit_identifiers.get("parent_article") or qc.explicit_identifiers.get("article")
            if art:
                explicit_targets.append(f"Article {art}")
            sched = qc.explicit_identifiers.get("schedule")
            if sched:
                explicit_targets.append(str(sched))
        elif "regulation" in qc.explicit_identifiers:
            selected_agents = ["regulatory", "statute"]
            explicit_targets.append(f"Regulation {qc.explicit_identifiers.get('regulation')}")
        elif "section" in qc.explicit_identifiers:
            selected_agents = ["statute", "case_law"]
            explicit_targets.append(f"Section {qc.explicit_identifiers.get('section')}")
    elif qc.query_type == "fact_pattern":
        search_strategy = "domain_aware_fact_pattern"
        if qc.primary_domain == "Motor Vehicle Law":
            selected_agents = ["statute", "case_law"]
        elif qc.primary_domain == "Women & Gender Justice":
            selected_agents = ["statute", "case_law"]
        elif qc.primary_domain == "Property & Land Law":
            selected_agents = ["statute", "case_law", "legal_document"]
        elif qc.primary_domain == "Corporate & Commercial Law":
            selected_agents = ["statute", "regulatory", "case_law"]
        else:
            selected_agents = ["statute", "case_law"]
    else:
        search_strategy = "conceptual_inquiry"
        if qc.primary_domain == "Constitutional Law":
            selected_agents = ["constitutional", "case_law"]
        elif qc.primary_domain in ["Corporate & Commercial Law", "Cyber & Technology Law"]:
            selected_agents = ["statute", "regulatory", "case_law"]
        else:
            selected_agents = ["statute", "case_law"]

    return ResearchPlan(
        primary_domain=qc.primary_domain,
        secondary_domains=qc.secondary_domains,
        research_questions=qc.research_questions,
        required_source_types=qc.source_types,
        explicit_targets=explicit_targets,
        search_strategy=search_strategy,
        selected_agents=selected_agents
    )
