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
  "Does the right to privacy under Article 21 of the Indian Constitution extend to digital data protection, and what legal test must state surveillance satisfy to comply with it?",
  "Under Regulation 3 and 4 of SEBI (Prohibition of Insider Trading) Regulations 2015, what constitutes Unpublished Price Sensitive Information (UPSI), and can communications be made to joint venture partners during due diligence?",
  "In the provided lease agreement, the landlord Rajesh Kumar has a clause saying he can issue a cheque bounce notice within 60 days of dishonour. Does this comply with Section 138 of the Negotiable Instruments Act?",
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

  const renderAnswerText = (text: string) => {
    if (!text) return null;
    
    // Convert inline citations like [1] to clickable buttons
    const regex = /\[(\d+)\]/g;
    const parts = [];
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(text)) !== null) {
      const matchIndex = match.index;
      const citationNumber = match[1];
      const citationIdx = parseInt(citationNumber, 10) - 1;

      if (matchIndex > lastIndex) {
        parts.push(text.substring(lastIndex, matchIndex));
      }

      if (citations[citationIdx]) {
        parts.push(
          <button
            key={matchIndex}
            onClick={() => onSelectCitation(citations[citationIdx].id)}
            className="inline-flex items-center px-1.5 py-0.2 mx-0.5 text-[10px] font-bold bg-teal-950 border border-teal-800 text-teal-300 hover:bg-teal-900 rounded font-mono cursor-pointer transition-colors align-middle"
          >
            {citationNumber}
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
              placeholder="Ask a legal query (e.g. Article 21 privacy rights, SEBI insider trading UPSI rules, Section 138 cheque bounce timelines)..."
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
            {renderAnswerText(answer)}
          </div>
        </div>
      )}
    </div>
  );
}
