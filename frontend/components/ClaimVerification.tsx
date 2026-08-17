"use client";

import React from "react";
import { CheckCircle, AlertTriangle, ShieldCheck, HelpCircle } from "lucide-react";
import { VerificationResult } from "../lib/types";

interface ClaimVerificationProps {
  verifications: VerificationResult[];
  onSelectEvidence: (id: string) => void;
}

export default function ClaimVerification({ verifications, onSelectEvidence }: ClaimVerificationProps) {
  if (verifications.length === 0) {
    return (
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
        <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
          <ShieldCheck className="h-5 w-5 text-teal-400" />
          <h2 className="text-sm font-bold text-white">Citation Claim Verification</h2>
        </div>
        <div className="py-6 text-center text-xs text-gray-500 italic">
          Submit a research query to view claims verification matrix...
        </div>
      </div>
    );
  }

  const getStatusColorClass = (status: string) => {
    switch (status) {
      case "supported":
        return "bg-emerald-950/20 border-emerald-800 text-emerald-400";
      case "partially_supported":
        return "bg-amber-950/20 border-amber-800 text-amber-400";
      case "contradicted":
        return "bg-purple-950/20 border-purple-800 text-purple-400";
      case "unsupported":
        return "bg-rose-950/20 border-rose-800 text-rose-400";
      case "insufficient_evidence":
        return "bg-gray-950/20 border-gray-800 text-gray-400";
      default:
        return "bg-gray-900 border-gray-800 text-gray-300";
    }
  };

  const getStatusLabel = (status: string) => {
    switch (status) {
      case "supported":
        return "Supported";
      case "partially_supported":
        return "Partially Supported";
      case "contradicted":
        return "Contradicted";
      case "unsupported":
        return "Unsupported";
      case "insufficient_evidence":
        return "Insufficient Evidence";
      default:
        return status;
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case "supported":
        return <CheckCircle className="h-3 w-3" />;
      case "partially_supported":
        return <HelpCircle className="h-3 w-3" />;
      default:
        return <AlertTriangle className="h-3 w-3" />;
    }
  };

  const getImportanceColorClass = (imp: string) => {
    switch (imp) {
      case "high":
        return "border-rose-500/30 text-rose-400 bg-rose-950/10";
      case "medium":
        return "border-amber-500/30 text-amber-400 bg-amber-950/10";
      case "low":
        return "border-blue-500/30 text-blue-400 bg-blue-950/10";
      default:
        return "border-gray-800 text-gray-400 bg-gray-950";
    }
  };

  const getRelColorClass = (rel: string) => {
    switch (rel) {
      case "supports":
        return "text-emerald-400";
      case "contradicts":
        return "text-rose-400";
      case "insufficient":
        return "text-yellow-400";
      case "context_only":
        return "text-sky-400";
      default:
        return "text-gray-400";
    }
  };

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
        <ShieldCheck className="h-5 w-5 text-teal-400" />
        <h2 className="text-sm font-bold text-white">Citation Claim Verification</h2>
      </div>

      <div className="space-y-4">
        {verifications.map((ver, idx) => {
          const status = ver.verification_status || (ver.supported ? "supported" : "unsupported");
          const importance = ver.importance || "medium";
          const cardBorderColor = 
            status === "supported" ? "border-emerald-900/60 bg-emerald-950/5 hover:bg-emerald-950/10" :
            status === "partially_supported" ? "border-amber-900/60 bg-amber-950/5 hover:bg-amber-950/10" :
            status === "contradicted" ? "border-purple-900/60 bg-purple-950/5 hover:bg-purple-950/10" :
            "border-rose-900/60 bg-rose-950/5 hover:bg-rose-950/10";

          return (
            <div
              key={idx}
              className={`border rounded-lg p-4 space-y-3 transition-all ${cardBorderColor}`}
            >
              <div className="flex flex-col space-y-2 md:flex-row md:justify-between md:items-start md:space-x-3 md:space-y-0">
                <p className="text-xs text-gray-200 font-semibold leading-relaxed">
                  “ {ver.claim} ”
                </p>
                <div className="flex items-center space-x-1.5 shrink-0 self-start">
                  <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded border uppercase tracking-wider ${getImportanceColorClass(importance)}`}>
                    {importance} priority
                  </span>
                  <span className={`flex items-center space-x-1 text-[9px] font-bold px-2 py-0.5 rounded font-mono border uppercase tracking-wider ${getStatusColorClass(status)}`}>
                    {getStatusIcon(status)}
                    <span>{getStatusLabel(status)}</span>
                  </span>
                </div>
              </div>

              {/* Issues details */}
              {ver.issues && ver.issues.length > 0 && (
                <div className="bg-rose-950/20 border border-rose-950/60 rounded p-2.5 text-[10px] text-rose-300 space-y-1">
                  <span className="font-bold uppercase tracking-wider block">Verification Issues:</span>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {ver.issues.map((issue, iIdx) => (
                      <li key={iIdx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Mapped evidence targets */}
              <div className="flex flex-col space-y-2 pt-1 border-t border-gray-850/50 md:flex-row md:justify-between md:items-center md:space-y-0 text-[10px]">
                <div className="flex items-center space-x-1 text-gray-400">
                  <span>Confidence:</span>
                  <span className="font-mono font-bold text-gray-200">
                    {(ver.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                
                {ver.evidence_links && ver.evidence_links.length > 0 ? (
                  <div className="flex items-center space-x-1.5 flex-wrap gap-1">
                    <span className="text-gray-500">Links:</span>
                    {ver.evidence_links.map((link, lIdx) => (
                      <button
                        key={lIdx}
                        onClick={() => onSelectEvidence(link.evidence_id)}
                        className="px-2 py-0.5 bg-gray-900 hover:bg-teal-900 border border-gray-850 hover:border-teal-700 text-gray-300 font-mono rounded cursor-pointer transition-all flex items-center space-x-1"
                      >
                        <span>Src {lIdx + 1}</span>
                        <span className={`text-[8px] uppercase font-bold ${getRelColorClass(link.relationship)}`}>
                          ({link.relationship.replace("_", " ")})
                        </span>
                      </button>
                    ))}
                  </div>
                ) : (
                  ver.evidence_ids && ver.evidence_ids.length > 0 && (
                    <div className="flex items-center space-x-1.5">
                      <span className="text-gray-500">Cites:</span>
                      {ver.evidence_ids.map((evId, evIdx) => (
                        <button
                          key={evIdx}
                          onClick={() => onSelectEvidence(evId)}
                          className="px-2 py-0.5 bg-gray-900 hover:bg-teal-900 border border-gray-850 hover:border-teal-700 text-gray-400 font-mono rounded cursor-pointer transition-all"
                        >
                          Source #{evIdx + 1}
                        </button>
                      ))}
                    </div>
                  )
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
