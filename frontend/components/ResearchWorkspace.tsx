"use client";

import React, { useState, useEffect, useRef } from "react";
import {
  Search,
  Globe,
  RefreshCw,
  Send,
  HelpCircle,
  BookOpen,
  Mic,
  MicOff,
  Volume2,
  Square,
  Languages,
  AlertCircle
} from "lucide-react";
import { conductResearch } from "../lib/api";
import { ResearchResponse, Evidence } from "../lib/types";

export type SupportedLanguage = "en" | "hi" | "te";

interface ResearchWorkspaceProps {
  onResearchStart: (query: string) => void;
  onResearchSuccess: (res: ResearchResponse) => void;
  onResearchError: (err: string) => void;
  isResearching: boolean;
  answer: string;
  citations: Evidence[];
  onSelectCitation: (id: string) => void;
  overallStatus?: string;
  confidenceLabel?: string;
}

const LANGUAGES: { code: SupportedLanguage; label: string; nativeLabel: string; speechCode: string }[] = [
  { code: "en", label: "English", nativeLabel: "EN", speechCode: "en-IN" },
  { code: "hi", label: "Hindi", nativeLabel: "हिन्दी", speechCode: "hi-IN" },
  { code: "te", label: "Telugu", nativeLabel: "తెలుగు", speechCode: "te-IN" },
];

const PLACEHOLDERS: Record<SupportedLanguage, string> = {
  en: "Ask a legal query in English (e.g. Article 21 privacy rights, SEBI insider trading UPSI rules, Section 138 cheque bounce timelines)...",
  hi: "हिन्दी में कानूनी प्रश्न पूछें (उदा. अनुच्छेद 21 निजता का अधिकार, धारा 138 चेक बाउंस नोटिस, सेबी इनसाइडर ट्रेडिंग नियम)...",
  te: "తెలుగులో చట్టపరమైన ప్రశ్న అడగండి (ఉదా. ఆర్టికల్ 21 గోప్యతా హక్కు, సెక్షన్ 138 చెక్ బౌన్స్ నోటీసు, సెబీ నిబంధనలు)...",
};

const SAMPLE_QUERIES_BY_LANG: Record<SupportedLanguage, string[]> = {
  en: [
    "Does the right to privacy under Article 21 of the Indian Constitution extend to digital data protection, and what legal test must state surveillance satisfy to comply with it?",
    "Under Regulation 3 and 4 of SEBI (Prohibition of Insider Trading) Regulations 2015, what constitutes Unpublished Price Sensitive Information (UPSI), and can communications be made to joint venture partners during due diligence?",
    "In the provided lease agreement, the landlord Rajesh Kumar has a clause saying he can issue a cheque bounce notice within 60 days of dishonour. Does this comply with Section 138 of the Negotiable Instruments Act?",
  ],
  hi: [
    "क्या भारतीय संविधान के अनुच्छेद 21 के तहत निजता का अधिकार डिजिटल डेटा सुरक्षा तक विस्तृत है, और राज्य निगरानी के लिए सर्वोच्च न्यायालय का आनुपातिकता परीक्षण क्या है?",
    "परक्राम्य लिखत अधिनियम की धारा 138 के तहत चेक बाउंस नोटिस की समयसीमा 30 दिन है, क्या लीज एग्रीमेंट का 60 दिन का नोटिस क्लॉज वैध है?",
    "सेबी (इंसाइडर ट्रेडिंग निषेध) विनियम 2015 के विनियम 3 और 4 के तहत अप्रकाशित मूल्य संवेदनशील जानकारी (UPSI) के प्रकटीकरण नियम क्या हैं?",
  ],
  te: [
    "భారత రాజ్యాంగంలోని ఆర్టికల్ 21 ప్రకారం గోప్యతా హక్కు డిజిటల్ డేటా రక్షణకు వర్తిస్తుందా, మరియు సుప్రీంకోర్టు మార్గదర్శకాలు ఏమిటి?",
    "నెగోషియబుల్ ఇన్‌స్ట్రుమెంట్స్ యాక్ట్ లోని సెక్షన్ 138 ప్రకారం చెక్ బౌన్స్ నోటీసు 30 రోజుల పరిమితిని ప్రైవేట్ లీజు ఒప్పందం మార్చవచ్చా?",
    "సెబీ ఇన్‌సైడర్ ట్రేడింగ్ నిబంధనలు 2015 లోని రెగ్యులేషన్ 3 & 4 ప్రకారం యూపీఎస్ఐ (UPSI) సమాచార మార్పిడి నిబంధనలు ఏమిటి?",
  ],
};

export default function ResearchWorkspace({
  onResearchStart,
  onResearchSuccess,
  onResearchError,
  isResearching,
  answer,
  citations,
  onSelectCitation,
  overallStatus,
  confidenceLabel,
}: ResearchWorkspaceProps) {
  const [inputQuery, setInputQuery] = useState("");
  const [useWeb, setUseWeb] = useState(true);
  const [language, setLanguage] = useState<SupportedLanguage>("en");
  const [isListening, setIsListening] = useState(false);
  const [speechError, setSpeechError] = useState<string | null>(null);
  const [isSpeaking, setIsSpeaking] = useState(false);

  const recognitionRef = useRef<any>(null);

  // Clean up speech and recognition on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== "undefined" && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
      if (recognitionRef.current) {
        try {
          recognitionRef.current.abort();
        } catch (_) {}
      }
    };
  }, []);

  // Speech-to-Text (STT) via Web Speech API
  const startSpeechRecognition = () => {
    setSpeechError(null);
    const SpeechRecognition =
      (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setSpeechError(
        "Speech recognition is not supported in this browser. Please use Google Chrome or Microsoft Edge for voice input."
      );
      return;
    }

    try {
      if (recognitionRef.current) {
        recognitionRef.current.abort();
      }

      const recognition = new SpeechRecognition();
      recognition.continuous = false;
      recognition.interimResults = true;

      const langConfig = LANGUAGES.find((l) => l.code === language);
      recognition.lang = langConfig?.speechCode || "en-IN";

      recognition.onstart = () => {
        setIsListening(true);
      };

      recognition.onresult = (event: any) => {
        let interim = "";
        let final = "";
        for (let i = event.resultIndex; i < event.results.length; ++i) {
          if (event.results[i].isFinal) {
            final += event.results[i][0].transcript;
          } else {
            interim += event.results[i][0].transcript;
          }
        }
        const transcript = (final || interim).trim();
        if (transcript) {
          setInputQuery((prev) => {
            const cleanPrev = prev.trim();
            return cleanPrev ? `${cleanPrev} ${transcript}` : transcript;
          });
        }
      };

      recognition.onerror = (event: any) => {
        setIsListening(false);
        if (event.error === "not-allowed") {
          setSpeechError("Microphone access was denied. Please allow microphone permissions in browser settings.");
        } else if (event.error !== "no-speech") {
          setSpeechError(`Voice input error: ${event.error}`);
        }
      };

      recognition.onend = () => {
        setIsListening(false);
      };

      recognitionRef.current = recognition;
      recognition.start();
    } catch (err: any) {
      setIsListening(false);
      setSpeechError(`Microphone failed to start: ${err.message || "Unknown error"}`);
    }
  };

  const stopSpeechRecognition = () => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch (_) {}
      setIsListening(false);
    }
  };

  const toggleSpeechRecognition = () => {
    if (isListening) {
      stopSpeechRecognition();
    } else {
      startSpeechRecognition();
    }
  };

  // Text-to-Speech (TTS) via window.speechSynthesis
  const cleanTextForSpeech = (raw: string): string => {
    if (!raw) return "";
    return raw
      // Remove inline citation brackets like [1], [2], [1, 2] so speech is natural
      .replace(/\[\d+(?:,\s*\d+)*\]/g, "")
      // Remove markdown bold, italic, headings
      .replace(/[*#_`~]/g, "")
      // Remove bullet dashes
      .replace(/^[ \t]*[-*+][ \t]+/gm, "")
      // Normalize multiple spaces and newlines
      .replace(/\s+/g, " ")
      .trim();
  };

  const toggleSpeechSynthesis = () => {
    if (typeof window === "undefined" || !("speechSynthesis" in window)) {
      alert("Text-to-speech is not supported in this browser.");
      return;
    }

    if (isSpeaking) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
      return;
    }

    const textToSpeak = cleanTextForSpeech(answer);
    if (!textToSpeak) return;

    window.speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance(textToSpeak);

    // Pick matching Indic voice if installed in browser
    const voices = window.speechSynthesis.getVoices();
    const targetPrefix = language === "hi" ? "hi" : language === "te" ? "te" : "en";
    const matchedVoice = voices.find((v) => v.lang.toLowerCase().startsWith(targetPrefix));
    if (matchedVoice) {
      utterance.voice = matchedVoice;
    }
    utterance.lang = language === "hi" ? "hi-IN" : language === "te" ? "te-IN" : "en-IN";
    utterance.rate = 0.95; // Slightly measured rate for legal precision

    utterance.onstart = () => setIsSpeaking(true);
    utterance.onend = () => setIsSpeaking(false);
    utterance.onerror = () => setIsSpeaking(false);

    window.speechSynthesis.speak(utterance);
  };

  const handleSubmit = async (e?: React.FormEvent) => {
    if (e) e.preventDefault();
    if (!inputQuery.trim() || isResearching) return;

    if (isListening) stopSpeechRecognition();
    if (isSpeaking && typeof window !== "undefined" && "speechSynthesis" in window) {
      window.speechSynthesis.cancel();
      setIsSpeaking(false);
    }

    onResearchStart(inputQuery);

    try {
      const res = await conductResearch(inputQuery, undefined, useWeb, language);
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
          {/* Top Controls Toolbar: Language Selector + Web Toggle */}
          <div className="flex flex-wrap items-center justify-between gap-3 pb-1 border-b border-gray-850">
            {/* Language Selector */}
            <div className="flex items-center space-x-1.5 bg-gray-900/80 p-1 rounded-lg border border-gray-800">
              <Languages className="h-3.5 w-3.5 text-teal-400 ml-1.5 mr-0.5" />
              {LANGUAGES.map((lang) => (
                <button
                  key={lang.code}
                  type="button"
                  onClick={() => setLanguage(lang.code)}
                  className={`px-2.5 py-1 rounded text-xs font-medium transition-all ${
                    language === lang.code
                      ? "bg-teal-700 text-white shadow-sm font-semibold"
                      : "text-gray-400 hover:text-gray-200 hover:bg-gray-800/60"
                  }`}
                >
                  {lang.nativeLabel}
                  <span className="ml-1 text-[10px] opacity-70">({lang.label})</span>
                </button>
              ))}
            </div>

            {/* Web Search Agent Toggle */}
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
          </div>

          {/* Query Input Box with Voice and Submit Buttons */}
          <div className="relative">
            <textarea
              value={inputQuery}
              onChange={(e) => setInputQuery(e.target.value)}
              placeholder={PLACEHOLDERS[language]}
              disabled={isResearching}
              rows={3}
              className="w-full bg-[#090d16] border border-gray-800 rounded-lg py-3 pl-4 pr-24 text-sm text-gray-200 placeholder-gray-500 focus:outline-none focus:border-teal-500 transition-colors resize-none"
            />
            
            <div className="absolute bottom-4 right-4 flex items-center space-x-2">
              {/* Speech-to-Text Microphone Button */}
              <button
                type="button"
                onClick={toggleSpeechRecognition}
                disabled={isResearching}
                title={
                  isListening
                    ? `Listening in ${LANGUAGES.find((l) => l.code === language)?.label}... Click to stop`
                    : `Speak query in ${LANGUAGES.find((l) => l.code === language)?.label}`
                }
                className={`p-2 rounded-lg border transition-all ${
                  isListening
                    ? "bg-red-950/80 border-red-600 text-red-400 animate-pulse"
                    : "bg-gray-900 border-gray-750 text-gray-400 hover:text-teal-300 hover:bg-gray-800"
                } disabled:opacity-50`}
              >
                {isListening ? (
                  <MicOff className="h-4 w-4 text-red-400" />
                ) : (
                  <Mic className="h-4 w-4" />
                )}
              </button>

              {/* Submit Button */}
              <button
                type="submit"
                disabled={isResearching || !inputQuery.trim()}
                title="Conduct Multi-Agent Research"
                className="p-2 bg-teal-600 hover:bg-teal-500 text-white rounded-lg transition-all disabled:opacity-50 disabled:bg-gray-800"
              >
                {isResearching ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Send className="h-4 w-4" />
                )}
              </button>
            </div>
          </div>

          {/* Voice Input Notification / Error Banner */}
          {speechError && (
            <div className="flex items-center space-x-2 p-2.5 rounded-lg bg-red-950/40 border border-red-900/60 text-xs text-red-300">
              <AlertCircle className="h-3.5 w-3.5 flex-shrink-0 text-red-400" />
              <span>{speechError}</span>
            </div>
          )}

          {isListening && (
            <div className="flex items-center space-x-2 p-2 rounded-lg bg-teal-950/30 border border-teal-800/40 text-xs text-teal-300">
              <span className="inline-block w-2 h-2 rounded-full bg-red-500 animate-ping" />
              <span>
                Listening ({LANGUAGES.find((l) => l.code === language)?.label} - {LANGUAGES.find((l) => l.code === language)?.speechCode})... Speak clearly into your microphone.
              </span>
            </div>
          )}

          {/* Benchmark Queries Section */}
          <div className="flex items-center justify-between pt-1">
            <div className="flex items-center space-x-1 text-xs text-gray-400">
              <HelpCircle className="h-3.5 w-3.5 text-teal-400" />
              <span>Benchmark Indian legal queries ({LANGUAGES.find((l) => l.code === language)?.label}):</span>
            </div>
          </div>
        </form>

        {/* Sample Queries */}
        {!isResearching && (
          <div className="mt-3 space-y-2">
            {SAMPLE_QUERIES_BY_LANG[language].map((q, idx) => (
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
            <h3 className="text-sm font-semibold text-white">Orchestrating Indian Legal Search Agents</h3>
            <p className="text-xs text-gray-400 max-w-md mx-auto">
              Decomposing query across specialized agents, retrieving statutory provisions and judicial precedents, performing claim verification, and synthesizing legal opinion...
            </p>
          </div>
        </div>
      )}

      {answer && !isResearching && (
        <div className="bg-[#111827] border border-gray-800 rounded-xl p-6 shadow-2xl space-y-4">
          <div className="flex items-center justify-between border-b border-gray-800 pb-3 flex-wrap gap-2">
            <div className="flex items-center space-x-2">
              <BookOpen className="h-5 w-5 text-teal-400" />
              <h2 className="text-base font-bold text-white">Synthesized Legal Opinion</h2>
            </div>

            <div className="flex items-center space-x-2">
              {/* Text-to-Speech (TTS) Listen / Stop Button */}
              <button
                type="button"
                onClick={toggleSpeechSynthesis}
                className={`flex items-center space-x-1.5 px-3 py-1 rounded-lg border text-xs font-medium transition-all ${
                  isSpeaking
                    ? "bg-amber-950/50 border-amber-600 text-amber-300 animate-pulse"
                    : "bg-gray-900 border-gray-750 text-gray-300 hover:text-teal-300 hover:bg-gray-850"
                }`}
                title={isSpeaking ? "Stop speech" : "Read synthesized legal opinion aloud"}
              >
                {isSpeaking ? (
                  <>
                    <Square className="h-3.5 w-3.5 text-amber-400 fill-amber-400" />
                    <span>Stop Audio</span>
                  </>
                ) : (
                  <>
                    <Volume2 className="h-3.5 w-3.5 text-teal-400" />
                    <span>Listen</span>
                  </>
                )}
              </button>

              {overallStatus === "verified" ? (
                <span className="text-xs px-2.5 py-0.5 bg-emerald-950/80 text-emerald-300 border border-emerald-700/60 font-mono rounded flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                  <span>Grounded & Verified</span>
                  {confidenceLabel && <span className="text-[10px] text-emerald-400 font-sans">({confidenceLabel})</span>}
                </span>
              ) : overallStatus === "insufficient_evidence" || answer.toLowerCase().includes("insufficient") || answer.includes("अपर्याप्त") || answer.includes("సరిపడా") ? (
                <span className="text-xs px-2.5 py-0.5 bg-amber-950/80 text-amber-300 border border-amber-700/60 font-mono rounded flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-amber-400" />
                  <span>Insufficient Evidence</span>
                </span>
              ) : overallStatus === "unsupported" ? (
                <span className="text-xs px-2.5 py-0.5 bg-rose-950/80 text-rose-300 border border-rose-700/60 font-mono rounded flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-rose-400" />
                  <span>Unverified / Domain Mismatch</span>
                </span>
              ) : (
                <span className="text-xs px-2.5 py-0.5 bg-teal-950/80 text-teal-300 border border-teal-800/50 font-mono rounded flex items-center space-x-1">
                  <span>Synthesized Output</span>
                </span>
              )}
            </div>
          </div>

          <div className="text-sm text-gray-300 leading-relaxed whitespace-pre-wrap font-sans">
            {renderAnswerText(answer)}
          </div>
        </div>
      )}
    </div>
  );
}
