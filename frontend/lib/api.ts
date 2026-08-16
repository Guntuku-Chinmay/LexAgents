import { ResearchResponse, SessionObservabilityResponse, EvaluationRunResult } from "./types";

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000";

export async function conductResearch(
  query: string,
  sessionId?: string,
  useWeb: boolean = true
): Promise<ResearchResponse> {
  const response = await fetch(`${API_BASE}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId, use_web: useWeb }),
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Unknown error" }));
    throw new Error(err.detail || "Server error conducting research");
  }
  return response.json();
}

export async function uploadDocument(file: File): Promise<{
  filename: string;
  chunks_ingested: number;
  status: string;
  message: string;
}> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${API_BASE}/api/documents/upload`, {
    method: "POST",
    body: formData,
  });
  if (!response.ok) {
    const err = await response.json().catch(() => ({ detail: "Failed to upload document" }));
    throw new Error(err.detail || "Server error uploading file");
  }
  return response.json();
}

export async function getSessionObservability(
  sessionId: string
): Promise<SessionObservabilityResponse> {
  const response = await fetch(`${API_BASE}/api/sessions/${sessionId}/observability`);
  if (!response.ok) {
    throw new Error("Failed to fetch session observability data");
  }
  return response.json();
}

export async function runEvaluation(): Promise<{
  status: string;
  message: string;
  results: Record<string, any>[];
}> {
  const response = await fetch(`${API_BASE}/api/evaluate`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to execute benchmark evaluation");
  }
  return response.json();
}

export async function getEvaluationResults(): Promise<EvaluationRunResult[]> {
  const response = await fetch(`${API_BASE}/api/evaluation/results`);
  if (!response.ok) {
    throw new Error("Failed to fetch evaluation runs");
  }
  return response.json();
}
