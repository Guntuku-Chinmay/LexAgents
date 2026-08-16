"use client";

import React from "react";
import { GitBranch, Clock, AlertTriangle, CheckCircle, HelpCircle, Activity } from "lucide-react";
import { AgentRun, AgentTask } from "../lib/types";

interface AgentTimelineProps {
  tasks: AgentTask[];
  runs: AgentRun[];
  reflections: { cycle_id: string; iteration: number; reasoning: string; sufficient: boolean }[];
  rawTrace: any[];
}

export default function AgentTimeline({ tasks, runs, reflections, rawTrace }: AgentTimelineProps) {
  // If we don't have relational runs/tasks (e.g. SQLite database didn't record them or page just loaded raw), 
  // we can reconstruct baseline logs from rawTrace array for retro-compatibility.
  const hasStructured = tasks.length > 0 || runs.length > 0;

  const renderStructured = () => {
    return (
      <div className="space-y-6">
        {/* Decomposed Tasks */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <GitBranch className="h-4 w-4 text-teal-400" />
            <h3 className="text-sm font-bold text-white">Task Decomposition</h3>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {tasks.map((task, idx) => (
              <div key={idx} className="bg-gray-900 border border-gray-800 rounded-lg p-3 space-y-1">
                <div className="flex justify-between items-center">
                  <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-teal-950 border border-teal-800 text-teal-300">
                    {task.agent_name.toUpperCase()}
                  </span>
                  <span className="text-[10px] text-gray-500 font-mono">Task #{idx + 1}</span>
                </div>
                <p className="text-xs text-gray-300 font-semibold">{task.query_text}</p>
                {task.reason && (
                  <p className="text-[10px] text-gray-500 italic">Rationale: {task.reason}</p>
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Specialized Agent Runs */}
        <div className="space-y-3">
          <div className="flex items-center space-x-2">
            <Activity className="h-4 w-4 text-teal-400" />
            <h3 className="text-sm font-bold text-white">Agent Execution Log</h3>
          </div>
          <div className="space-y-2">
            {runs.map((run, idx) => (
              <div
                key={idx}
                className="flex items-center justify-between bg-gray-900 border border-gray-850 rounded-lg px-4 py-3"
              >
                <div className="flex items-center space-x-3">
                  <div
                    className={`h-2 w-2 rounded-full ${
                      run.status === "completed" ? "bg-emerald-400" : "bg-rose-400"
                    }`}
                  />
                  <div>
                    <h4 className="text-xs font-semibold text-gray-200">
                      {run.agent_name === "coordinator_search" ? "Hybrid Search Dispatcher" : run.agent_name}
                    </h4>
                    <p className="text-[10px] text-gray-500 font-mono">
                      Iteration {run.retrieval_iteration} • {run.source_count} items retrieved
                    </p>
                  </div>
                </div>
                <div className="flex items-center space-x-2 text-[10px] text-gray-400">
                  <Clock className="h-3 w-3" />
                  <span>{run.duration.toFixed(2)}s</span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Reflection Timeline */}
        {reflections.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center space-x-2">
              <CheckCircle className="h-4 w-4 text-teal-400" />
              <h3 className="text-sm font-bold text-white">Self-Reflection Cycles</h3>
            </div>
            <div className="space-y-3">
              {reflections.map((ref, idx) => (
                <div
                  key={idx}
                  className={`border rounded-lg p-4 space-y-2 ${
                    ref.sufficient
                      ? "bg-emerald-950/20 border-emerald-900"
                      : "bg-amber-950/20 border-amber-900"
                  }`}
                >
                  <div className="flex justify-between items-center">
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded font-mono ${
                        ref.sufficient
                          ? "bg-emerald-950 border border-emerald-800 text-emerald-300"
                          : "bg-amber-950 border border-amber-800 text-amber-300"
                      }`}
                    >
                      {ref.sufficient ? "EVIDENCE SUFFICIENT" : "RE-RETRIEVAL REQUIRED"}
                    </span>
                    <span className="text-[10px] text-gray-500 font-mono">Cycle #{ref.iteration}</span>
                  </div>
                  <p className="text-xs text-gray-300 italic">“ {ref.reasoning} ”</p>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  };

  const renderRawFallback = () => {
    return (
      <div className="space-y-4">
        <div className="flex items-center space-x-2 text-gray-400 text-xs">
          <HelpCircle className="h-3 w-3 text-teal-400" />
          <span>Showing log trace events</span>
        </div>
        <div className="space-y-3 border-l-2 border-gray-800 pl-4 ml-2">
          {rawTrace.map((step, idx) => {
            const isStart = step.step_name.includes("Start");
            const isDecomp = step.step_name.includes("Decomposition");
            const isReflect = step.step_name.includes("Reflection");
            
            return (
              <div key={idx} className="relative space-y-1 pb-3">
                <div className="absolute -left-[21px] top-1 h-2 w-2 rounded-full bg-teal-500" />
                <div className="flex items-center justify-between">
                  <h4 className="text-xs font-bold text-gray-200">{step.step_name}</h4>
                  <span className="text-[9px] font-mono text-gray-500">
                    {new Date(step.timestamp).toLocaleTimeString()}
                  </span>
                </div>
                
                {isDecomp && step.payload?.tasks && (
                  <div className="space-y-1.5 mt-1">
                    {step.payload.tasks.map((task: any, tIdx: number) => (
                      <div key={tIdx} className="bg-gray-900 border border-gray-850 p-2 rounded text-[11px] text-gray-300">
                        <span className="font-mono text-teal-400 mr-2">[{task.agent}]</span>
                        {task.query}
                      </div>
                    ))}
                  </div>
                )}
                
                {isReflect && (
                  <div className="bg-gray-900/60 border border-gray-850 p-2.5 rounded text-[11px] text-gray-400 mt-1 italic">
                    Sufficient: {String(step.payload?.sufficient)} • {step.payload?.reasoning}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </div>
    );
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
        <GitBranch className="h-5 w-5 text-teal-400" />
        <h2 className="text-sm font-bold text-white">Agent Timeline Observability</h2>
      </div>

      {hasStructured ? renderStructured() : rawTrace.length > 0 ? renderRawFallback() : (
        <div className="py-6 text-center text-xs text-gray-500 italic">
          Submit a research query to monitor timeline traces...
        </div>
      )}
    </div>
  );
}
