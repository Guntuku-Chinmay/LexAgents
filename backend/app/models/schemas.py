from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class QueryRequest(BaseModel):
    query: str
    session_id: Optional[str] = None
    use_web: bool = True

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

class TaskDecomposition(BaseModel):
    query: str
    agent: str  # 'case_law', 'statute', 'legal_document', 'web_research'
    reason: str

class CoordinatorOutput(BaseModel):
    tasks: List[TaskDecomposition]

class VerificationResult(BaseModel):
    claim: str
    supported: bool
    evidence_ids: List[str]
    citation_correct: bool
    confidence: float
    issues: List[str] = Field(default_factory=list)

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

class EvaluationRunResult(BaseModel):
    eval_id: str
    run_timestamp: str
    system_type: str
    metrics: Dict[str, Any]
    config: Dict[str, Any]
