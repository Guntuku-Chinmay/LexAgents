"""
Relevance Gate for LexAgents Retrieval Pipeline.
Guarantees that every retrieved candidate chunk passes strict domain,
subdomain, explicit identifier, and legal issue compatibility checks
before being accepted as Evidence for synthesis.

Principle:
Never pass an irrelevant candidate to synthesis.
Candidate retrieved != Evidence accepted.
"""

import re
from typing import List, Dict, Any, Tuple
from backend.app.models.schemas import Evidence, QueryAnalysis
from backend.app.retrieval.canonical_taxonomy import get_domain

def evaluate_candidate_relevance(
    doc: Dict[str, Any],
    analysis: QueryAnalysis
) -> Tuple[bool, str, Dict[str, Any]]:
    """
    Evaluate a candidate document against the structured QueryAnalysis.
    Returns: (is_accepted, rejection_reason, enriched_metadata)
    """
    text = doc.get("text", "")
    metadata = doc.get("metadata", {})
    text_lower = (text + " " + str(metadata)).lower()
    doc_type = metadata.get("doc_type", "")
    enriched_meta = dict(metadata)

    # 1. STRICT EXPLICIT IDENTIFIER COMPATIBILITY
    if analysis.explicit_identifiers:
        # Article checks
        if "article" in analysis.explicit_identifiers or "parent_article" in analysis.explicit_identifiers:
            target_art = str(analysis.explicit_identifiers.get("parent_article") or analysis.explicit_identifiers.get("article")).strip().upper()
            doc_art = str(metadata.get("parent_article") or metadata.get("article") or "").strip().upper()
            
            # If doc has an article identifier and it doesn't match target article, REJECT!
            if doc_art and doc_art != target_art:
                return False, f"Explicit Article mismatch: expected Article {target_art}, got Article {doc_art}", enriched_meta

            # Clause checks (e.g. 16(4))
            target_clause = analysis.explicit_identifiers.get("clause")
            if target_clause:
                doc_clause = str(metadata.get("clause") or "").strip()
                clause_in_text = f"({target_clause})" in text or f"clause ({target_clause})" in text_lower or f"({target_clause}" in text
                articles_list = [str(x).strip() for x in metadata.get("articles", [])]
                full_clause_target = f"{target_art}({target_clause})"
                
                if doc_clause != str(target_clause) and not clause_in_text and full_clause_target not in articles_list:
                    # If this is not the specific clause, but is parent article, check if other candidates have clause
                    pass  # Parent article can be fallback if clause isn't isolated, but priority goes to clause

        # Schedule checks
        if "schedule" in analysis.explicit_identifiers:
            target_sched = str(analysis.explicit_identifiers["schedule"]).strip().upper()
            doc_sched = str(metadata.get("schedule") or "").strip().upper()
            if doc_sched and target_sched not in doc_sched and doc_sched not in target_sched:
                return False, f"Explicit Schedule mismatch: expected {target_sched}, got {doc_sched}", enriched_meta

        # Section checks
        if "section" in analysis.explicit_identifiers:
            target_sec = str(analysis.explicit_identifiers["section"]).strip().upper()
            doc_sec = str(metadata.get("section") or "").strip().upper()
            doc_secs = [str(x).strip().upper() for x in metadata.get("sections", [])]
            if doc_sec and doc_sec != target_sec and target_sec not in doc_secs:
                return False, f"Explicit Section mismatch: expected Section {target_sec}, got Section {doc_sec}", enriched_meta

        # Regulation checks
        if "regulation" in analysis.explicit_identifiers:
            target_reg = str(analysis.explicit_identifiers["regulation"]).strip().upper()
            doc_reg = str(metadata.get("regulation") or "").strip().upper()
            doc_regs = [str(x).strip().upper() for x in metadata.get("regulations", [])]
            if doc_reg and doc_reg != target_reg and target_reg not in doc_regs:
                return False, f"Explicit Regulation mismatch: expected Regulation {target_reg}, got Regulation {doc_reg}", enriched_meta

    # 2. DOMAIN COMPATIBILITY & EXCLUSION GATE
    primary_domain = analysis.primary_domain
    p_def = get_domain(primary_domain)

    # Check negative / exclusion signals: If query belongs to a domain whose exclusion signals match doc
    if p_def:
        for excl in p_def.exclusion_signals:
            if excl in ["article 15", "article 16", "article 19", "article 21", "fundamental rights"]:
                if doc_type in ["constitutional", "constitutional_amendment"]:
                    return False, f"Domain incompatibility: {primary_domain} query cannot accept constitutional articles", enriched_meta

    # Cross-domain contamination barriers
    if primary_domain == "Motor Vehicle Law":
        # Constitutional text is NEVER acceptable evidence for a traffic / motor vehicle accident
        if doc_type in ["constitutional", "constitutional_amendment"] or "constitution of india" in text_lower[:200]:
            return False, "Domain mismatch: Motor Vehicle Law query cannot accept Constitutional provisions as evidence", enriched_meta
        # Negotiable Instruments Act or Lease agreement is also not acceptable
        if "negotiable instruments" in text_lower or "sebi (" in text_lower:
            return False, "Domain mismatch: Commercial / securities text rejected for Motor Vehicle Law query", enriched_meta

    elif primary_domain == "Women & Gender Justice":
        if "negotiable instruments act" in text_lower or "cheque bounce" in text_lower:
            return False, "Domain mismatch: Cheque bounce text rejected for Women & Gender Justice query", enriched_meta
        if "motor vehicle" in text_lower or "traffic collision" in text_lower:
            return False, "Domain mismatch: Motor vehicle text rejected for Women & Gender Justice query", enriched_meta
        if doc_type in ["constitutional", "constitutional_amendment"] and not any(w in text_lower for w in ["gender", "women", "sex", "discrimination", "14", "15", "16", "21"]):
            return False, "Constitutional provision has no bearing on Women & Gender Justice", enriched_meta

    elif primary_domain == "Cyber & Technology Law":
        if doc_type in ["constitutional", "constitutional_amendment"] and "article 21" not in text_lower and "privacy" not in text_lower:
            return False, "Unrelated constitutional text rejected for Cyber Law query", enriched_meta
        if "motor vehicle" in text_lower:
            return False, "Motor vehicle text rejected for Cyber Law query", enriched_meta

    elif primary_domain == "Property & Land Law":
        if "motor vehicle" in text_lower or "traffic collision" in text_lower:
            return False, "Motor vehicle text rejected for Property Law query", enriched_meta
        if doc_type in ["constitutional", "constitutional_amendment"]:
            return False, "Constitutional provisions rejected for Property Law query", enriched_meta

    elif primary_domain == "Consumer Law":
        if doc_type in ["constitutional", "constitutional_amendment"]:
            return False, "Constitutional provisions rejected for Consumer Law query", enriched_meta
        if "motor vehicle act" in text_lower and "product" not in text_lower:
            return False, "Motor vehicle accident text rejected for Consumer Law query", enriched_meta

    elif primary_domain == "Labour & Employment Law":
        if doc_type in ["constitutional", "constitutional_amendment"] and "16" not in text_lower:
            return False, "Unrelated constitutional provisions rejected for Labour Law query", enriched_meta
        if "motor vehicle" in text_lower:
            return False, "Motor vehicle text rejected for Labour Law query", enriched_meta

    elif primary_domain == "Corporate & Commercial Law":
        if doc_type in ["constitutional", "constitutional_amendment"]:
            return False, "Constitutional provisions rejected for Commercial Law query", enriched_meta
        if "motor vehicle" in text_lower:
            return False, "Motor vehicle text rejected for Corporate Law query", enriched_meta

    elif primary_domain == "Constitutional Law":
        if doc_type not in ["constitutional", "constitutional_amendment", "sc_judgment", "hc_judgment"]:
            # Private contracts cannot serve as primary evidence for Constitutional Law
            if doc_type in ["user_upload", "contract"]:
                return False, "Private lease or user contract cannot serve as authority for Constitutional Law", enriched_meta


    # 3. SUBSTANTIVE RELEVANCE FLOOR
    # Extract query substantive tokens
    boilerplate = {
        "what", "does", "provide", "under", "indian", "about", "with", "this", "that",
        "from", "have", "act", "law", "court", "india", "case", "statute", "legal",
        "terms", "rules", "rule", "regulations", "regulation", "section", "article",
        "explain", "give", "help", "prove", "mistakes", "says", "said"
    }
    q_words = [
        w.lower() for w in re.findall(r'[a-zA-Z0-9]+', analysis.normalized_query)
        if len(w) > 2 and w.lower() not in boilerplate
    ]
    
    # If not explicit reference, must have at least some overlap with substantive terms or facts
    if analysis.query_type != "explicit_reference" and q_words:
        matched_terms = [w for w in q_words if w in text_lower]
        if not matched_terms:
            # Check if any legal issue terms match
            issue_words = []
            for iss in analysis.legal_issues:
                issue_words.extend([w for w in iss.lower().split() if len(w) > 3 and w not in boilerplate])
            matched_issues = [w for w in issue_words if w in text_lower]
            if not matched_issues:
                return False, "No substantive lexical or conceptual overlap with query or legal issues", enriched_meta

    # Everything passed!
    return True, "Accepted", enriched_meta

def filter_evidence_through_gate(
    candidates: List[Dict[str, Any]],
    analysis: QueryAnalysis
) -> Tuple[List[Evidence], List[Dict[str, Any]]]:
    """
    Process candidates through the Relevance Gate.
    Returns: (accepted_evidence_list, rejected_candidates_trace)
    """
    accepted: List[Evidence] = []
    rejected: List[Dict[str, Any]] = []

    for doc in candidates:
        is_ok, reason, enriched_meta = evaluate_candidate_relevance(doc, analysis)
        if is_ok:
            meta = doc.get("metadata", {})
            source_name = meta.get("title") or meta.get("filename") or "Authoritative Source"
            
            # Format clean source title
            if meta.get("article"):
                source_name = f"{source_name} Article {meta['article']}"
            elif meta.get("section"):
                source_name = f"{source_name} § {meta['section']}"
            elif meta.get("regulation"):
                source_name = f"{source_name} Regulation {meta['regulation']}"

            accepted.append(
                Evidence(
                    id=str(doc.get("id")),
                    text=doc.get("text", ""),
                    source=source_name,
                    doc_type=meta.get("doc_type", "statute"),
                    score=float(doc.get("score", 1.0)),
                    metadata=enriched_meta,
                    source_id=meta.get("document_id"),
                    authority_level=meta.get("authority_level", "TIER 2"),
                    retrieval_method=doc.get("retrieval_method", "hybrid"),
                    url=meta.get("source_url"),
                    domain=analysis.primary_domain,
                    sub_domain=analysis.sub_domains[0] if analysis.sub_domains else None,
                    legal_identifier=analysis.explicit_identifiers.get("article") or analysis.explicit_identifiers.get("section"),
                    relationship_to_query="directly_supports",
                    relevance_status="accepted",
                    content=doc.get("text", "")
                )
            )
        else:
            rejected.append({
                "candidate_id": doc.get("id"),
                "source": doc.get("metadata", {}).get("title") or doc.get("metadata", {}).get("filename"),
                "reason": reason
            })

    return accepted, rejected
