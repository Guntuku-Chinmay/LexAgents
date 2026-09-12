from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    use_web: bool = True
    language: Optional[str] = "en"


class QueryContext(BaseModel):
    query_id: str
    original_query: str
    normalized_query: str
    language: str = "en"
    query_type: Any  # e.g., 'fact_pattern', 'provision_lookup', 'legal_explanation', etc.
    primary_domain: str
    secondary_domains: List[str] = Field(default_factory=list)
    sub_domains: List[str] = Field(default_factory=list)
    intent: List[str] = Field(default_factory=list)
    legal_intents: List[str] = Field(default_factory=list)
    facts: List[str] = Field(default_factory=list)
    legal_issues: List[str] = Field(default_factory=list)
    requested_outcome: Optional[str] = None
    explicit_identifiers: Dict[str, Any] = Field(default_factory=dict)
    named_entities: List[str] = Field(default_factory=list)
    jurisdiction: str = "India"
    research_questions: List[str] = Field(default_factory=list)
    confidence: float = 0.0
    confidence_label: str = "Limited evidence"  # "Strong evidence" | "Moderate evidence" | "Limited evidence" | "Insufficient evidence"
    source_types: List[str] = Field(default_factory=list)
    is_ambiguous: bool = False
    missing_information: List[str] = Field(default_factory=list)

# Backward-compatible subclass/alias for QueryAnalysis
class QueryAnalysis(QueryContext):
    pass

class ResearchPlan(BaseModel):
    primary_domain: str
    secondary_domains: List[str] = Field(default_factory=list)
    research_questions: List[str] = Field(default_factory=list)
    required_source_types: List[str] = Field(default_factory=list)
    explicit_targets: List[str] = Field(default_factory=list)
    search_strategy: str = "domain_aware_fact_pattern"
    selected_agents: List[str] = Field(default_factory=list)

class AnswerQualityResult(BaseModel):
    is_relevant: bool = True
    addresses_query: bool = True
    addresses_outcome: bool = True
    addresses_issues: bool = True
    uses_relevant_evidence: bool = True
    no_unrelated_law: bool = True
    rejection_reasons: List[str] = Field(default_factory=list)

class Evidence(BaseModel):
    id: str
    text: str
    source: str
    doc_type: str  # e.g., 'constitutional', 'central_act', 'sc_judgment', 'user_upload', 'web'
    score: float
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_id: Optional[str] = None
    authority_level: Optional[str] = "TIER 4"
    retrieval_method: Optional[str] = "hybrid"
    url: Optional[str] = None
    domain: Optional[str] = None
    sub_domain: Optional[str] = None
    legal_identifier: Optional[str] = None
    relationship_to_query: Optional[str] = "relevant"
    relevance_status: Optional[str] = "accepted"  # "accepted" | "rejected"
    content: Optional[str] = None

class TaskDecomposition(BaseModel):
    query: str
    agent: str  # 'case_law', 'statute', 'legal_document', 'web_research'
    reason: str

class CoordinatorOutput(BaseModel):
    tasks: List[TaskDecomposition]
    research_plan: Optional[ResearchPlan] = None

class VerificationResult(BaseModel):
    claim: str
    supported: bool
    evidence_ids: List[str]
    citation_correct: bool
    confidence: float
    issues: List[str] = Field(default_factory=list)
    claim_id: Optional[str] = None
    importance: Optional[str] = "medium"  # 'high' | 'medium' | 'low'
    verification_status: Optional[str] = "supported"  # 'supported', 'partially_supported', 'unsupported', 'contradicted', 'insufficient_evidence'
    evidence_links: Optional[List[Dict[str, str]]] = None  # List of {"evidence_id": "...", "relationship": "supports"}
    confidence_label: Optional[str] = "Moderate evidence"

class ResearchTraceStep(BaseModel):
    step_name: str
    timestamp: str
    payload: Dict[str, Any]

class ResearchResponse(BaseModel):
    session_id: str
    answer: str
    citations: List[Evidence]
    verification_results: List[VerificationResult]
    iterations: int
    trace: List[ResearchTraceStep] = Field(default_factory=list)
    language: Optional[str] = "en"
    query_context: Optional[QueryContext] = None
    research_plan: Optional[ResearchPlan] = None
    overall_status: Optional[str] = "supported"  # "supported" | "unsupported" | "insufficient_evidence"
    confidence_label: Optional[str] = "Moderate evidence"


class EvaluationRunResult(BaseModel):
    eval_id: str
    run_timestamp: str
    system_type: str
    metrics: Dict[str, Any]
    config: Dict[str, Any]

