export interface Evidence {
  id: string;
  text: string;
  source: string;
  doc_type: string; // 'case' | 'statute' | 'user_upload' | 'web'
  score: number;
  metadata: Record<string, any>;
}

export interface VerificationResult {
  claim: string;
  supported: boolean;
  evidence_ids: string[];
  confidence: number;
  issues: string[];
}

export interface ResearchTraceStep {
  step_name: string;
  timestamp: string;
  payload: Record<string, any>;
}

export interface ResearchResponse {
  session_id: string;
  answer: string;
  citations: Evidence[];
  verification_results: VerificationResult[];
  iterations: number;
  trace: ResearchTraceStep[];
}

export interface EvaluationRunResult {
  eval_id: string;
  run_timestamp: string;
  system_type: string;
  metrics: Record<string, any>;
  config: Record<string, any>;
}

export interface AgentTask {
  task_id: string;
  agent_name: string;
  query_text: string;
  reason: string;
  created_at: string;
}

export interface AgentRun {
  run_id: string;
  agent_name: string;
  status: string; // 'started' | 'completed' | 'failed'
  started_at: string;
  completed_at: string;
  duration: number;
  retrieval_iteration: number;
  source_count: number;
  error: string | null;
}

export interface ObservabilityData {
  tasks: AgentTask[];
  runs: AgentRun[];
  queries: { query_id: string; query_text: string; created_at: string }[];
  claims: { claim_id: string; claim_text: string; created_at: string }[];
  verifications: {
    verification_id: string;
    claim_text: string;
    supported: boolean;
    confidence: number;
    issues: string[];
    created_at: string;
  }[];
  reflections: {
    cycle_id: string;
    iteration: number;
    reasoning: string;
    sufficient: boolean;
    created_at: string;
  }[];
}

export interface SessionObservabilityResponse {
  session: {
    session_id: string;
    query: string;
    final_answer: string | null;
    iterations: number;
    created_at: string;
  };
  observability: ObservabilityData;
}
