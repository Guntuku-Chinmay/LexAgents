"use client";

import React, { useRef, useState } from "react";
import { Scale, Upload, Check, AlertCircle, RefreshCw } from "lucide-react";
import { uploadDocument } from "../lib/api";

interface NavbarProps {
  activeTab: "research" | "evaluation";
  setActiveTab: (tab: "research" | "evaluation") => void;
  sessionId: string | null;
}

export default function Navbar({ activeTab, setActiveTab, sessionId }: NavbarProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [status, setStatus] = useState<{ type: "success" | "error"; msg: string } | null>(null);

  const handleUploadClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setIsUploading(true);
    setStatus(null);

    try {
      const res = await uploadDocument(file);
      setStatus({
        type: "success",
        msg: `Successfully indexed ${res.filename} (${res.chunks_ingested} chunks).`,
      });
    } catch (err: any) {
      setStatus({
        type: "error",
        msg: err.message || "Failed to upload document.",
      });
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  };

  return (
    <header className="border-b border-gray-800 bg-[#0d1527] sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <div className="flex items-center space-x-3">
          <Scale className="h-6 w-6 text-teal-400" />
          <span className="text-xl font-bold tracking-tight text-white">
            Lex<span className="text-teal-400">Agents</span>
          </span>
          <span className="text-xs px-2 py-0.5 rounded-full bg-teal-950/50 border border-teal-800 text-teal-300 font-mono hidden md:inline-block">
            Multi-Agent RAG v1.1
          </span>
        </div>

        <nav className="flex items-center space-x-4">
          <button
            onClick={() => setActiveTab("research")}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
              activeTab === "research"
                ? "bg-teal-950/40 border border-teal-800 text-teal-300"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            Research Workspace
          </button>
          <button
            onClick={() => setActiveTab("evaluation")}
            className={`px-4 py-2 text-sm font-medium rounded-md transition-all ${
              activeTab === "evaluation"
                ? "bg-teal-950/40 border border-teal-800 text-teal-300"
                : "text-gray-400 hover:text-gray-200"
            }`}
          >
            Evaluation Dashboard
          </button>
          
          <div className="h-6 w-px bg-gray-800"></div>

          <div className="flex items-center space-x-2">
            <input
              type="file"
              ref={fileInputRef}
              onChange={handleFileChange}
              accept=".txt,.md,.json"
              className="hidden"
            />
            <button
              onClick={handleUploadClick}
              disabled={isUploading}
              className="flex items-center space-x-2 px-3 py-1.5 text-xs bg-gray-900 border border-gray-800 hover:bg-gray-800 text-gray-200 rounded-md transition-all disabled:opacity-50"
            >
              {isUploading ? (
                <RefreshCw className="h-3 w-3 animate-spin text-teal-400" />
              ) : (
                <Upload className="h-3 w-3 text-teal-400" />
              )}
              <span>Upload Agreement</span>
            </button>
          </div>
        </nav>
      </div>
      
      {status && (
        <div
          className={`px-4 py-2 text-xs border-t text-center flex items-center justify-center space-x-2 ${
            status.type === "success"
              ? "bg-emerald-950/30 border-emerald-900 text-emerald-300"
              : "bg-rose-950/30 border-rose-900 text-rose-300"
          }`}
        >
          {status.type === "success" ? (
            <Check className="h-3 w-3" />
          ) : (
            <AlertCircle className="h-3 w-3" />
          )}
          <span>{status.msg}</span>
        </div>
      )}
    </header>
  );
}
