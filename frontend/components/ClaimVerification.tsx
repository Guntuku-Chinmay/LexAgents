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

  return (
    <div className="bg-[#111827] border border-gray-800 rounded-xl p-5 shadow-lg space-y-4">
      <div className="flex items-center space-x-2 border-b border-gray-800 pb-3">
        <ShieldCheck className="h-5 w-5 text-teal-400" />
        <h2 className="text-sm font-bold text-white">Citation Claim Verification</h2>
      </div>

      <div className="space-y-4">
        {verifications.map((ver, idx) => {
          const isSupported = ver.supported;
          return (
            <div
              key={idx}
              className={`border rounded-lg p-4 space-y-2.5 transition-all ${
                isSupported
                  ? "bg-emerald-950/10 border-emerald-900/60 hover:bg-emerald-950/20"
                  : "bg-rose-950/10 border-rose-900/60 hover:bg-rose-950/20"
              }`}
            >
              <div className="flex justify-between items-start space-x-3">
                <p className="text-xs text-gray-200 font-semibold leading-relaxed">
                  “ {ver.claim} ”
                </p>
                <span
                  className={`flex items-center space-x-1 text-[10px] font-bold px-2.5 py-0.5 rounded font-mono uppercase ${
                    isSupported
                      ? "bg-emerald-950 text-emerald-400 border border-emerald-800"
                      : "bg-rose-950 text-rose-400 border border-rose-800"
                  }`}
                >
                  {isSupported ? (
                    <CheckCircle className="h-3 w-3" />
                  ) : (
                    <AlertTriangle className="h-3 w-3" />
                  )}
                  <span>{isSupported ? "Supported" : "Unsupported"}</span>
                </span>
              </div>

              {/* Contradiction details */}
              {ver.issues && ver.issues.length > 0 && (
                <div className="bg-rose-950/30 border border-rose-900/50 rounded p-2.5 text-[10px] text-rose-300 space-y-1">
                  <span className="font-bold uppercase tracking-wider block">Verification Issues:</span>
                  <ul className="list-disc pl-4 space-y-0.5">
                    {ver.issues.map((issue, iIdx) => (
                      <li key={iIdx}>{issue}</li>
                    ))}
                  </ul>
                </div>
              )}

              {/* Mapped evidence targets */}
              <div className="flex items-center justify-between pt-1 text-[10px]">
                <div className="flex items-center space-x-1 text-gray-400">
                  <span>Confidence:</span>
                  <span className="font-mono font-bold text-gray-200">
                    {(ver.confidence * 100).toFixed(0)}%
                  </span>
                </div>
                
                {ver.evidence_ids && ver.evidence_ids.length > 0 && (
                  <div className="flex items-center space-x-1.5">
                    <span className="text-gray-500">Cites:</span>
                    {ver.evidence_ids.map((evId, evIdx) => (
                      <button
                        key={evIdx}
                        onClick={() => onSelectEvidence(evId)}
                        className="px-2 py-0.5 bg-gray-900 hover:bg-teal-900 hover:text-teal-300 border border-gray-800 hover:border-teal-700 text-gray-400 font-mono rounded cursor-pointer transition-all"
                      >
                        Source #{evIdx + 1}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
