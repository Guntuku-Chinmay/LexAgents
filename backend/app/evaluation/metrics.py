from typing import List, Set, Dict, Any

def compute_retrieval_metrics(retrieved_files: List[str], expected_files: List[str]) -> Dict[str, float]:
    """
    Compute Precision@K and Recall@K of the retrieval system compared to ground truth.
    """
    if not expected_files:
        return {"precision": 0.0, "recall": 0.0}
    if not retrieved_files:
        return {"precision": 0.0, "recall": 0.0}

    retrieved_set = set(retrieved_files)
    expected_set = set(expected_files)

    intersection = retrieved_set.intersection(expected_set)
    
    precision = len(intersection) / len(retrieved_set)
    recall = len(intersection) / len(expected_set)

    return {
        "precision": float(round(precision, 4)),
        "recall": float(round(recall, 4))
    }

def compute_citation_metrics(
    verification_results: List[Any], 
    expected_files: List[str], 
    evidence_id_to_filename: Dict[str, str]
) -> Dict[str, float]:
    """
    Compute Citation Precision, Citation Recall, and Unsupported Claim Rate.
    - Citation Precision: proportion of verified/supported claims among all checked claims.
    - Citation Recall: proportion of expected sources cited in the final supported claims.
    - Unsupported Claim Rate: proportion of unsupported/contradicted claims.
    """
    if not verification_results:
        return {
            "citation_precision": 0.0,
            "citation_recall": 0.0,
            "unsupported_claim_rate": 0.0
        }

    total_claims = len(verification_results)
    supported_claims_count = 0
    cited_filenames = set()

    for v in verification_results:
        # Pydantic or dict check
        supported = getattr(v, "supported", False) if not isinstance(v, dict) else v.get("supported", False)
        evidence_ids = getattr(v, "evidence_ids", []) if not isinstance(v, dict) else v.get("evidence_ids", [])
        
        if supported:
            supported_claims_count += 1
            for ev_id in evidence_ids:
                if ev_id in evidence_id_to_filename:
                    cited_filenames.add(evidence_id_to_filename[ev_id])

    citation_precision = supported_claims_count / total_claims
    unsupported_claim_rate = (total_claims - supported_claims_count) / total_claims

    # Citation Recall compared to expected documents
    expected_set = set(expected_files)
    if expected_set:
        citation_recall = len(cited_filenames.intersection(expected_set)) / len(expected_set)
    else:
        citation_recall = 0.0

    return {
        "citation_precision": float(round(citation_precision, 4)),
        "citation_recall": float(round(citation_recall, 4)),
        "unsupported_claim_rate": float(round(unsupported_claim_rate, 4))
    }
