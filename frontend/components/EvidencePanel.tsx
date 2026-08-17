"use client";

import React, { useEffect, useRef } from "react";
import { BookOpen, FileText, Gavel, Globe, Award } from "lucide-react";
import { Evidence } from "../lib/types";

interface EvidencePanelProps {
  citations: Evidence[];
  selectedEvidenceId: string | null;
}

export default function EvidencePanel({ citations, selectedEvidenceId }: EvidencePanelProps) {
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (selectedEvidenceId && containerRef.current) {
      const element = document.getElementById(`evidence-card-${selectedEvidenceId}`);
      if (element) {
        element.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedEvidenceId]);

  if (citations.length === 0) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
          <BookOpen className="h-5 w-5 text-teal-400" />
          <h2 className="text-sm font-bold text-white">Retrieved Evidence Pool</h2>
        </div>
        <div className="py-6 text-center text-xs text-gray-500 italic">
          Submit a research query to view evidence corpus...
        </div>
      </div>
    );
  }

  const getDocIcon = (type: string) => {
    switch (type) {
      case "sc_judgment":
      case "hc_judgment":
      case "case":
        return <Gavel className="h-4 w-4 text-cyan-400" />;
      case "constitutional":
      case "constitutional_amendment":
        return <Award className="h-4 w-4 text-amber-400" />;
      case "central_act":
      case "state_act":
      case "rules":
      case "regulation":
      case "government_circular":
      case "statute":
        return <FileText className="h-4 w-4 text-emerald-400" />;
      case "external_source":
      case "web":
        return <Globe className="h-4 w-4 text-blue-400" />;
      default:
        return <BookOpen className="h-4 w-4 text-teal-400" />;
    }
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center justify-between border-b border-gray-800 pb-3">
        <div className="flex items-center space-x-2">
          <BookOpen className="h-5 w-5 text-teal-400" />
          <h2 className="text-sm font-bold text-white">Retrieved Evidence Pool</h2>
        </div>
        <span className="text-xs text-gray-500 font-mono">
          {citations.length} sources fused
        </span>
      </div>

      <div
        ref={containerRef}
        className="max-h-[600px] overflow-y-auto space-y-3 pr-1"
      >
        {citations.map((item, idx) => {
          const isSelected = selectedEvidenceId === item.id;
          const displayScore = item.score && item.score > 0 ? item.score.toFixed(3) : null;
          
          return (
            <div
              key={item.id}
              id={`evidence-card-${item.id}`}
              className={`border rounded-lg p-4 space-y-2 transition-all ${
                isSelected
                  ? "bg-teal-950/20 border-teal-500 shadow-[0_0_12px_rgba(20,184,166,0.15)]"
                  : "bg-gray-900 border-gray-850 hover:border-gray-800"
              }`}
            >
              <div className="flex items-center justify-between border-b border-gray-850 pb-2 flex-wrap gap-2">
                <div className="flex items-center space-x-2">
                  {getDocIcon(item.doc_type)}
                  <span className="text-xs font-bold text-white truncate max-w-[180px] md:max-w-[220px]">
                    {item.source}
                  </span>
                </div>
                <div className="flex items-center space-x-1.5 flex-wrap gap-1">
                  {item.authority_level && (
                    <span className={`text-[9px] font-mono font-bold px-1.5 py-0.5 rounded border ${
                      item.authority_level === "TIER 1" ? "border-amber-500/30 bg-amber-950/20 text-amber-400" :
                      item.authority_level === "TIER 2" ? "border-emerald-500/30 bg-emerald-950/20 text-emerald-400" :
                      item.authority_level === "TIER 3" ? "border-sky-500/30 bg-sky-950/20 text-sky-400" :
                      "border-gray-800 bg-gray-950 text-gray-400"
                    }`}>
                      {item.authority_level}
                    </span>
                  )}
                  <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-gray-950 text-gray-400 uppercase border border-gray-850">
                    {item.doc_type.replace("_", " ")}
                  </span>
                  {item.retrieval_method && (
                    <span className="text-[9px] font-mono px-1.5 py-0.5 rounded bg-gray-900 border border-gray-850 text-gray-500 uppercase">
                      {item.retrieval_method.replace("_", " ")}
                    </span>
                  )}
                  {displayScore && (
                    <span className="text-[9px] font-mono font-bold text-teal-400 flex items-center space-x-0.5">
                      <Award className="h-3 w-3" />
                      <span>{displayScore}</span>
                    </span>
                  )}
                </div>
              </div>

              <p className="text-xs text-gray-300 leading-relaxed font-sans whitespace-pre-wrap">
                {item.text}
              </p>

              {item.metadata && Object.keys(item.metadata).length > 0 && (
                <div className="flex flex-wrap gap-1.5 pt-1">
                  {Object.entries(item.metadata)
                    .filter(([key]) => !["text", "filename", "doc_type"].includes(key))
                    .map(([key, value]) => (
                      <span
                        key={key}
                        className="text-[9px] font-mono bg-gray-950 border border-gray-850 text-gray-500 px-1.5 py-0.5 rounded"
                      >
                        {key}: {String(value)}
                      </span>
                    ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
