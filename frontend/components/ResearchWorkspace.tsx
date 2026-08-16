"use client";

import React, { useState } from "react";
import { Search, Globe, RefreshCw, Send, HelpCircle, BookOpen } from "lucide-react";
import { conductResearch } from "../lib/api";
import { ResearchResponse, Evidence } from "../lib/types";

interface ResearchWorkspaceProps {
  onResearchStart: (query: string) => void;
  onResearchSuccess: (res: ResearchResponse) => void;
  onResearchError: (err: string) => void;
  isResearching: boolean;
  answer: string;
  citations: Evidence[];
  onSelectCitation: (id: string) => void;
}

const SAMPLE_QUERIES = [
  "If a landlord in California fails to provide an itemized security deposit deduction list within 21 days, does he lose the right to make deductions for damages, and can he still sue the tenant?",
  "Is a tenant entitled to double statutory damages automatically if the landlord makes excessive deductions from a security deposit under California law?",
  "In the provided lease agreement for 456 Oak Street, the landlord claims they have 30 days to return the security deposit. Is this clause legally enforceable under California law?",
];

export default function ResearchWorkspace({
  onResearchStart,
  onResearchSuccess,
  onResearchError,
  isResearching,
  answer,
  citations,
  onSelectCitation,
}: ResearchWorkspaceProps) {
  const [inputQuery, setInputQuery] = useState("");
  const [useWeb, setUseWeb] = useState(true);

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim() || isResearching) return;

    onResearchStart(inputQuery);

    try {
      const res = await conductResearch(inputQuery, undefined, useWeb);
      onResearchSuccess(res);
    } catch (err: any) {
      onResearchError(err.message || "Failed to retrieve legal findings.");
    }
  };

  const handleSelectSample = (q: string) => {
    setInputQuery(q);
  };

  const formatAnswerText = (text: string) => {
    const regex = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const matchIndex = match.index;
      const citationIndex = parseInt(match[1], 10);

      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      const evidenceItem = citations[citationIndex - 1];
      if (evidenceItem) {
        parts.push(
          <button
            key={`cit-${matchIndex}`}
            onClick={() => onSelectCitation(evidenceItem.id)}
            className="mx-0.5 px-1.5 py-0.5 text-xs font-mono font-bold bg-teal-950/60 hover:bg-teal-900 border border-teal-800 text-teal-300 rounded hover:scale-105 transition-all cursor-pointer"
            title={evidenceItem.source}
          >
            [{citationIndex}]
          </button>
        );
      } else {
        parts.push(match[0]);
      }

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < text.length) {
      parts.push(text.substring(lastIndex));
    }

    return parts.length > 0 ? parts : text;
  };

  return (
    <div className="space-y-6">
      {/* Search Console */}
      <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-2xl">
        <form onSubmit={handleSubmit} className="space-y-4">
          <div className="relative">
            <textarea
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder="Ask a legal query (e.g. California Civil Code Section 1950.5 timelines, landlord deduction rights, lease conflicts)..."
              disabled={isResearching}
              rows={3}
              className="w-full bg-[#090d16] border border-gray-800 rounded-lg py-3 pl-4 pr-12 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-teal-500 transition-colors resize-none"
            />
            <button
              type="submit"
              disabled={isResearching || !inputQuery.trim()}
              className="absolute bottom-4 right-4 p-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition-all disabled:opacity-50 disabled:bg-gray-800"
            >
              {isResearching ? (
                <RefreshCw className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </div>

          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <button
                type="button"
                onClick={() => setUseWeb(!useWeb)}
                className={`flex items-center space-x-1.5 px-3 py-1.5 rounded-lg border text-xs font-medium transition-all ${
                  useWeb
                    ? "bg-teal-950/30 border-teal-800 text-teal-300"
                    : "bg-gray-900 border-gray-800 text-gray-400"
                }`}
              >
                <Globe className="h-3.5 w-3.5" />
                <span>Web Research Agent</span>
              </button>
            </div>

            <div className="flex items-center space-x-1 text-xs text-gray-500">
              <HelpCircle className="h-3 w-3" />
              <span>Select below to test benchmark queries</span>
            </div>
          </div>
        </form>

        {/* Sample Queries */}
        {!isResearching && (
          <div className="mt-4 pt-4 border-t border-gray-850 space-y-2">
            {SAMPLE_QUERIES.map((q, idx) => (
              <button
                key={idx}
                onClick={() => handleSelectSample(q)}
                className="w-full text-left p-2.5 rounded-lg bg-gray-900/50 hover:bg-gray-900 border border-gray-850 hover:border-gray-800 text-xs text-gray-400 hover:text-gray-300 transition-all truncate"
              >
                {q}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Answer Console */}
      {isResearching && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-8 text-center space-y-4">
          <RefreshCw className="h-8 w-8 animate-spin text-teal-400 mx-auto" />
          <div className="space-y-1">
            <h3 className="text-sm font-semibold text-white">Orchestrating Search Agents</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto">
              Decomposing query, retrieving statues and opinions, performing claim-by-claim verification, and executing self-reflection loops...
            </p>
          </div>
        </div>
      )}

      {answer && !isResearching && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3">
            <div className="flex items-center space-x-2">
              <BookOpen className="h-5 w-5 text-teal-400" />
              <h2 className="text-base font-bold text-white">Synthesized Legal Opinion</h2>
            </div>
            <span className="text-xs px-2 py-0.5 bg-teal-950 text-teal-300 border border-teal-800/50 font-mono rounded">
              Grounded & Verified
            </span>
          </div>

          <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap font-sans">
            {formatAnswerText(answer)}
          </div>
        </div>
      )}
    </div>
  );
}
