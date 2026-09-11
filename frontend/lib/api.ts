import { ResearchResponse, SessionObservabilityResponse, EvaluationRunResult } from "./types";

function getApiBase(): string {
  const url = process.env.NEXT_PUBLIC_API_URL;
  if (url && url.trim()) {
    return url.trim().replace(/\/+$/, "");
  }
  if (process.env.NODE_ENV === "production" && typeof window !== "undefined") {
    console.warn(
      "NEXT_PUBLIC_API_URL is not set. Requests will fall back to http://127.0.0.1:8000. Set NEXT_PUBLIC_API_URL in Vercel settings to your Render backend URL."
    );
  }
  return "http://127.0.0.1:8000";
}


export async function conductResearch(
  query: string,
  sessionId?: string,
  useWeb: boolean = true,
  language: string = "en"
): Promise<ResearchResponse> {
  const response = await fetch(`${getApiBase()}/api/research`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ query, session_id: sessionId, use_web: useWeb, language }),
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

  const response = await fetch(`${getApiBase()}/api/documents/upload`, {
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
  const response = await fetch(`${getApiBase()}/api/sessions/${sessionId}/observability`);
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
  const response = await fetch(`${getApiBase()}/api/evaluate`, { method: "POST" });
  if (!response.ok) {
    throw new Error("Failed to execute benchmark evaluation");
  }
  return response.json();
}

export async function getEvaluationResults(): Promise<EvaluationRunResult[]> {
  const response = await fetch(`${getApiBase()}/api/evaluation/results`);
  if (!response.ok) {
    throw new Error("Failed to fetch evaluation runs");
  }
  return response.json();
}
