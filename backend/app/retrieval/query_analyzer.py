"""
Structured Legal Query Analyzer for LexAgents.
Parses natural-language queries into structured QueryAnalysis objects.
Enforces strict distinction between Explicit Legal References (Type A)
and Fact-Pattern / Natural-Language questions (Type B).
"""

import re
from typing import Dict, List, Any, Optional
from backend.app.models.schemas import QueryAnalysis
from backend.app.retrieval.canonical_taxonomy import SUPPORTED_DOMAINS, get_domain
from backend.app.retrieval.vector_bm25 import extract_identifiers_from_query

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
    if any(w in q_lower for w in ["employer", "boss", "workplace", "colleague"]):
        if any(w in q_lower for w in ["touching", "sexual", "harassing", "comments", "harassment"]):
            facts.append("employee is experiencing unwelcome sexual conduct/comments in workplace")

    # Cyber fraud facts
    if any(w in q_lower for w in ["hacked", "stole money", "upi", "online scam", "phishing", "account"]):
        facts.append("unauthorized party accessed electronic account and transferred funds")

    # Employment termination facts
    if any(w in q_lower for w in ["fired", "terminated", "dismissed"]):
        if any(w in q_lower for w in ["suddenly", "without notice", "no notice", "unlawful"]):
            facts.append("employee was terminated without statutory or contractual notice")

    # Defective product facts
    if any(w in q_lower for w in ["purchase", "defective", "seller refuses", "product"]):
        facts.append("consumer received defective goods and seller refused refund/replacement")

    # Arrest facts
    if "arrested" in q_lower or "police" in q_lower:
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
            "mandatory statutory requirements under Section 138 Negotiable Instruments Act",
            "statutory timeline of 30 days for issuing demand notice upon cheque dishonour",
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

def analyze_query(query: str) -> QueryAnalysis:
    """
    Perform deep structured query analysis.
    Distinguishes Explicit Reference vs Fact Pattern vs Conceptual Inquiry.
    Determines primary domain and secondary domains without overclassification.
    """
    raw_query = query.strip()
    norm_query = normalize_legal_text(raw_query)
    lang = detect_language(raw_query)
    explicit_idents = extract_identifiers_from_query(raw_query)
    q_lower = norm_query.lower()
    named_entities = extract_named_entities(raw_query)

    # 1. Determine Query Type
    if explicit_idents:
        query_type = "explicit_reference"
    elif any(phrase in q_lower for phrase in [
        "if i", "my car", "my landlord", "my boss", "a cow came", "dashed the",
        "i was arrested", "someone hacked", "company fired me", "seller refuses",
        "a driver swerved", "swerved to avoid", "hit an electric pole",
        "landlord refuses", "refuses to return", "refusing to return", "hit a pole",
        "keeps touching me", "fired me suddenly", "hacked my phone"
    ]) or ("?" in query and len(query.split()) > 12 and any(p in q_lower for p in ["i ", "my ", "me ", "we "])):
        query_type = "fact_pattern"
    else:
        query_type = "conceptual_inquiry"

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
            # Match keywords (Indic non-ASCII characters don't use ASCII word boundary \b)
            for kw in d_def.keywords:
                if any(ord(c) > 127 for c in kw):
                    if kw in q_lower:
                        score += 2.0
                else:
                    if re.search(r'\b' + re.escape(kw) + r'\b', q_lower):
                        score += 2.0

            # Match subdomains (avoid false positives on isolated generic structural terms like 'offences' or 'remedies')
            for sub in d_def.subdomains:
                sub_lower = sub.lower()
                if sub_lower in q_lower:
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
            elif sec_val in ("185", "166", "163A"):
                domain_scores["Motor Vehicle Law"] = 100.0
            elif sec_val in ("9", "11", "12", "13"):
                if any(w in q_lower for w in ["posh", "harassment", "women", "sexual"]):
                    domain_scores["Women & Gender Justice"] = 100.0
        elif "regulation" in explicit_idents or "rule" in explicit_idents:
            if "sebi" in q_lower or "upsi" in q_lower or "insider" in q_lower:
                domain_scores["Corporate & Commercial Law"] = 100.0

    # 4. Fact Pattern Specialized Matching
    # Specific case: Car, cow, pole collision
    if ("car" in q_lower or "vehicle" in q_lower or "driver" in q_lower) and any(w in q_lower for w in ["pole", "cow", "cattle", "dashed", "traffic", "accident", "swerved"]):
        domain_scores["Motor Vehicle Law"] = 50.0
        domain_scores["Civil Law"] = 15.0
        domain_scores["Criminal Law"] = 10.0
        domain_scores["Constitutional Law"] = 0.0

    # Specific case: Workplace sexual harassment / Dowry / Women & Gender Justice
    if any(w in q_lower for w in ["sexual harassment", "posh", "boss keeps touching", "internal complaints committee", "vishaka", "dowry", "domestic violence"]):
        domain_scores["Women & Gender Justice"] = 50.0
        domain_scores["Criminal Law"] = 15.0
        domain_scores["Constitutional Law"] = 0.0

    # Specific case: Bail / FIR
    if any(w in q_lower for w in ["bail", "fir", "arrested", "custody", "remand"]):
        domain_scores["Criminal Procedure"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Deposit / Landlord
    if any(w in q_lower for w in ["landlord", "deposit", "security deposit", "rent agreement", "lease"]):
        domain_scores["Property & Land Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Specific case: Online scam / hacked / financial fraud
    if any(w in q_lower for w in ["hacked", "upi", "online scam", "phishing", "stole money", "financial scam", "online financial scam", "cyber scam", "cyber fraud"]):
        domain_scores["Cyber & Technology Law"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Cheque bounce / Negotiable Instruments
    if any(w in q_lower for w in ["cheque bounce", "dishonour of cheque", "section 138", "చెక్ బౌన్స్", "చెక్కు బౌన్స్", "చేక్ బౌన్స్", "చేక్", "చెక్కు", "चेक बाउंस"]):
        domain_scores["Corporate & Commercial Law"] = 50.0
        domain_scores["Criminal Law"] = 15.0

    # Specific case: Consumer defective goods
    if any(w in q_lower for w in ["defective", "deficient service", "consumer commission", "product liability"]):
        domain_scores["Consumer Law"] = 50.0
        domain_scores["Civil Law"] = 15.0

    # Rank domains
    sorted_domains = sorted(domain_scores.items(), key=lambda x: x[1], reverse=True)
    if sorted_domains and sorted_domains[0][1] > 0.0:
        primary_domain = sorted_domains[0][0]
    else:
        # Conservative fallback
        primary_domain = "Civil Law"

    # Secondary domains: only include if score > 0 and closely related, max 2
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
    if "prove i've no mistakes" in q_lower or "not my fault" in q_lower:
        requested_outcome = "Rebut presumption of negligence / establish absence of fault"
    elif "bail" in q_lower:
        requested_outcome = "Securing release on bail"
    elif "deposit" in q_lower:
        requested_outcome = "Recovery of full security deposit from landlord"
    elif "remedies" in q_lower or "protection" in q_lower:
        requested_outcome = "Statutory protection and legal remedies"

    # Legal intents
    legal_intents = []
    if any(w in q_lower for w in ["liable", "liability", "fault", "mistake"]):
        legal_intents.append("liability_assessment")
    if any(w in q_lower for w in ["remedy", "remedies", "compensation", "damages"]):
        legal_intents.append("remedies_and_compensation")
    if any(w in q_lower for w in ["procedure", "how to", "what happens after"]):
        legal_intents.append("procedural_guidance")
    if any(w in q_lower for w in ["rights", "protection"]):
        legal_intents.append("statutory_rights")
    if explicit_idents:
        legal_intents.append("statutory_interpretation")
    if not legal_intents:
        legal_intents.append("legal_research")

    # Source types
    p_def = get_domain(primary_domain)
    source_types = p_def.likely_source_types if p_def else ["central_act", "sc_judgment"]

    # Calibrate confidence
    if explicit_idents:
        confidence = "high"
    elif facts and len(facts) >= 2:
        confidence = "high"
    elif sorted_domains and sorted_domains[0][1] >= 6.0:
        confidence = "medium"
    else:
        confidence = "low"

    return QueryAnalysis(
        original_query=raw_query,
        normalized_query=norm_query,
        query_type=query_type,
        primary_domain=primary_domain,
        secondary_domains=secondary_domains,
        sub_domains=matched_subdomains.get(primary_domain, [])[:4],
        legal_intents=legal_intents,
        facts=facts,
        legal_issues=legal_issues[:5],
        requested_outcome=requested_outcome,
        source_types=source_types,
        explicit_identifiers=explicit_idents,
        named_entities=named_entities,
        jurisdiction="India",
        language=lang,
        confidence=confidence
    )
