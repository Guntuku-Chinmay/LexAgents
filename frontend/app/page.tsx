"use client";

import React, { useState } from "react";
import Navbar from "../components/Navbar";
import ResearchWorkspace from "../components/ResearchWorkspace";
import AgentTimeline from "../components/AgentTimeline";
import ClaimVerification from "../components/ClaimVerification";
import EvidencePanel from "../components/EvidencePanel";
import EvaluationDashboard from "../components/EvaluationDashboard";
import { ResearchResponse, Evidence, VerificationResult, AgentTask, AgentRun } from "../lib/types";
import { getSessionObservability } from "../lib/api";

export default function Home() {
  const [activeTab, setActiveTab] = useState<"research" | "evaluation">("research");
  const [sessionId, setSessionId] = useState<string | null>(null);
  
  // Research State
  const [isResearching, setIsResearching] = useState(false);
  const [answer, setAnswer] = useState("");
  const [citations, setCitations] = useState<Evidence[]>([]);
  const [verifications, setVerifications] = useState<VerificationResult[]>([]);
  const [trace, setTrace] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  
  // Highlighting footnoted items
  const [selectedEvidenceId, setSelectedEvidenceId] = useState<string | null>(null);
  
  // Relational Observability State
  const [tasks, setTasks] = useState<AgentTask[]>([]);
  const [runs, setRuns] = useState<AgentRun[]>([]);
  const [reflections, setReflections] = useState<any[]>([]);

  const handleResearchStart = (query: string) => {
    setIsResearching(true);
    setAnswer("");
    setCitations([]);
    setVerifications([]);
    setTrace([]);
    setTasks([]);
    setRuns([]);
    setReflections([]);
    setError(null);
    setSelectedEvidenceId(null);
  };

  const handleResearchSuccess = async (res: ResearchResponse) => {
    setAnswer(res.answer);
    setCitations(res.citations);
    setVerifications(res.verification_results);
    setTrace(res.trace);
    setIsResearching(false);
    setSessionId(res.session_id);

    // Fetch the structured PostgreSQL relational trace details recorded by the backend
    try {
      const obsRes = await getSessionObservability(res.session_id);
      setTasks(obsRes.observability.tasks);
      setRuns(obsRes.observability.runs);
      setReflections(obsRes.observability.reflections);
    } catch (obsError) {
      console.warn("Could not retrieve PostgreSQL observability metrics:", obsError);
    }
  };

  const handleResearchError = (errMsg: string) => {
    setError(errMsg);
    setIsResearching(false);
  };

  const handleSelectCitation = (id: string) => {
    setSelectedEvidenceId(id);
  };

  return (
    <div className="min-h-screen bg-[#090d16] flex flex-col text-gray-200">
      <Navbar
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        sessionId={sessionId}
      />

      <main className="flex-1 w-full max-w-7xl mx-auto p-4 md:p-6">
        {activeTab === "research" ? (
          <div className="space-y-6">
            {error && (
              <div className="p-4 bg-rose-950/20 border border-rose-900 rounded-xl text-xs text-rose-300">
                {error}
              </div>
            )}
            
            <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
              {/* Left Column: Input and Answer Panel */}
              <div className="lg:col-span-2 space-y-6">
                <ResearchWorkspace
                  onResearchStart={handleResearchStart}
                  onResearchSuccess={handleResearchSuccess}
                  onResearchError={handleResearchError}
                  isResearching={isResearching}
                  answer={answer}
                  citations={citations}
                  onSelectCitation={handleSelectCitation}
                />

                {/* Evidence Panel (Spans bottom under the answer) */}
                <EvidencePanel
                  citations={citations}
                  selectedEvidenceId={selectedEvidenceId}
                />
              </div>

              {/* Right Column: Observability Timeline and Claim verification status */}
              <div className="space-y-6">
                <ClaimVerification
                  verifications={verifications}
                  onSelectEvidence={handleSelectCitation}
                />

                <AgentTimeline
                  tasks={tasks}
                  runs={runs}
                  reflections={reflections}
                  rawTrace={trace}
                />
              </div>
            </div>
          </div>
        ) : (
          <EvaluationDashboard />
        )}
      </main>

      <footer className="border-t border-gray-850 py-4 text-center text-[10px] text-gray-650 bg-[#070b13]">
        <div className="max-w-7xl mx-auto px-4">
          <p>© 2026 LexAgents legal RAG. Structured claim verification and multi-agent loops.</p>
        </div>
      </footer>
    </div>
  );
}
