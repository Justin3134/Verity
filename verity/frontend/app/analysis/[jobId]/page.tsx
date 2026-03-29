"use client";

import { useEffect, useRef, useState, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import ResultsPanel from "@/components/ResultsPanel";
import ChatPanel from "@/components/ChatPanel";
import RailVizButton from "@/components/RailVizButton";
import AgentDebates from "@/components/AgentDebates";

// React Flow must be client-only
const AgentFlowGraph = dynamic(() => import("@/components/AgentFlowGraph"), {
  ssr: false,
});

export interface SensoFactCheck {
  claim: string;
  source: string;
  url?: string;
  verdict: "CORRECT" | "INCORRECT" | "UNVERIFIED";
  senso_says: string;
  senso_excerpt?: string;
}

export interface SensoStreamCheck {
  status?: string;
  action?: string;
  summary?: string;
  fact_checks?: SensoFactCheck[];
  tensions?: { label?: string; detail?: string; senso_excerpt?: string }[];
  senso_queries?: number;
}

export interface AgentStatus {
  name: string;
  description: string;
  status: "idle" | "running" | "complete" | "waiting" | "error";
  action: string;
  result: string | Record<string, unknown> | null;
  claims?: unknown[];
  observations?: unknown[];
  findings?: unknown[];
  senso_stream?: SensoStreamCheck;
}

export interface JobStatus {
  job_id: string;
  query: string;
  status: "starting" | "running" | "complete" | "error";
  agents: {
    breaking_news: AgentStatus;
    historical: AgentStatus;
    official_docs: AgentStatus;
    visual_intel: AgentStatus;
    financial_market: AgentStatus;
    social_pulse: AgentStatus;
    legal: AgentStatus;
    synthesizer: AgentStatus;
  };
  senso_log: string[];
  results: AnalysisResults | null;
  error: string | null;
}

export interface AnalysisResults {
  executive_summary: string;
  verified: VerifiedFinding[];
  contested: ContestedFinding[];
  unverified?: UnverifiedFinding[];
  hidden: HiddenFinding[];
  propaganda: PropagandaSignal[];
  escalation_assessment: EscalationAssessment;
  source_reliability_ranking?: SourceReliability[];
  key_unknowns: string[];
  recommended_watch_signals?: string[];
  streams: StreamsSummary;
  source_articles?: SourceArticle[];
  debate_clusters?: DebateCluster[];
}

export interface DebateClusterParty {
  name: string;
  stance: string;
  url?: string;
  quote?: string;
}

export interface DebateCluster {
  topic: string;
  domain: string;
  parties: DebateClusterParty[];
  assessment: string;
  confidence: string;
  evidence_gaps: string[];
}


interface VerifiedFinding {
  finding: string;
  sources?: string[];
  confidence?: string;
  evidence?: string;
}

export interface ContestedSource {
  name: string;
  stance: string;
  url?: string;
}

export interface ContestedFinding {
  claim?: string;
  topic?: string;
  sources?: ContestedSource[];
  /** Legacy fallback — pre-overhaul format */
  positions?: Record<string, string> | { source: string; claim: string }[];
  resolution?: string;
  likely_truth?: string;
  confidence?: string;
}

interface UnverifiedFinding {
  claim: string;
  source?: string;
  verification_needed?: string;
}

interface HiddenFinding {
  signal?: string;
  finding?: string;
  basis?: string;
  source?: string;
  significance?: string;
  why_not_reported?: string;
}

interface PropagandaSignal {
  pattern?: string;
  signal?: string;
  outlets?: string[];
  actors?: string[];
  likely_origin?: string;
  evidence?: string;
}

interface SourceReliability {
  source: string;
  reliability?: string;
  reliability_score?: string;
  note?: string;
  notes?: string;
}

interface EscalationAssessment {
  probability: string;
  timeline?: string;
  key_triggers?: string[];
  indicators?: string[];
  historical_comparison?: string;
  historical_match?: string;
}

interface StreamsSummary {
  breaking_news?: { summary: string; claims_count: number; source?: string; article_count?: number };
  historical?: { summary: string; precedents_count: number; senso_queries?: number };
  official_docs?: { summary: string; positions_count: number; docs_found?: number };
  visual_intel?: { summary: string; observations_count: number; economic_signals_count?: number; images_analyzed?: number };
  financial_markets?: { summary: string; signals_count: number; risk_level?: string };
}

export interface SourceArticle {
  title: string;
  url: string;
  source?: string | { name: string };
  image?: string | null;
}

type ActivePanel = "graph" | "debates" | "results";

export default function AnalysisPage() {
  const { jobId } = useParams<{ jobId: string }>();
  const router = useRouter();
  const [job, setJob] = useState<JobStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [activePanel, setActivePanel] = useState<ActivePanel>("graph");
  const [chatCollapsed, setChatCollapsed] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL ?? "";

  const fetchStatus = useCallback(async () => {
    try {
      const res = await fetch(`${BACKEND}/status/${jobId}`);
      if (!res.ok) {
        if (res.status === 404) {
          if (pollRef.current) clearInterval(pollRef.current);
          setError("Analysis not found.");
          return;
        }
        throw new Error(`HTTP ${res.status}`);
      }
      const data: JobStatus = await res.json();
      setJob(data);
      if (data.status === "complete" || data.status === "error") {
        if (pollRef.current) clearInterval(pollRef.current);
        if (data.status === "complete") setActivePanel("debates");
      }
    } catch (err: unknown) {
      if (pollRef.current) clearInterval(pollRef.current);
      setError(err instanceof Error ? err.message : String(err));
    }
  }, [jobId, BACKEND]);

  useEffect(() => {
    fetchStatus();
    pollRef.current = setInterval(fetchStatus, 1000);
    return () => { if (pollRef.current) clearInterval(pollRef.current); };
  }, [fetchStatus]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border-bright)",
            borderRadius: 12,
            padding: "32px 40px",
            textAlign: "center",
            maxWidth: 400,
          }}
        >
          <h2 style={{ color: "var(--stream-red)", fontWeight: 600, marginBottom: 8 }}>Analysis Error</h2>
          <p style={{ color: "var(--text-secondary)", fontSize: 14, marginBottom: 20 }}>{error}</p>
          <button
            onClick={() => router.push("/")}
            style={{
              padding: "8px 20px",
              background: "var(--bg-elevated)",
              border: "1px solid var(--border-bright)",
              borderRadius: 6,
              color: "var(--text-primary)",
              fontSize: 13,
              cursor: "pointer",
            }}
          >
            New Analysis
          </button>
        </div>
      </div>
    );
  }

  if (!job) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div style={{ display: "flex", alignItems: "center", gap: 10, color: "var(--text-secondary)", fontSize: 14 }}>
          <div
            className="w-4 h-4 border-2 rounded-full animate-spin"
            style={{ borderColor: "color-mix(in srgb, var(--stream-blue) 35%, transparent)", borderTopColor: "var(--stream-blue)" }}
          />
          Loading...
        </div>
      </div>
    );
  }

  const completeCount = Object.values(job.agents).filter((a) => a.status === "complete").length;

  return (
    <div className="flex h-screen flex-col overflow-hidden" style={{ background: "var(--bg-base)" }}>
      {/* Header */}
      <header
        style={{
          borderBottom: "1px solid var(--border)",
          padding: "0 20px",
          height: 48,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          flexShrink: 0,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <button
            onClick={() => router.push("/")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: 8,
              background: "none",
              border: "none",
              cursor: "pointer",
              color: "var(--text-secondary)",
            }}
          >
            <span style={{ fontSize: 12 }}>←</span>
            <span style={{ fontSize: 13, fontWeight: 700, color: "var(--text-primary)", letterSpacing: "0.08em" }}>VERITY</span>
          </button>
          <div style={{ width: 1, height: 16, background: "var(--border)" }} />
          <span
            style={{
              fontSize: 12,
              color: "var(--text-muted)",
              maxWidth: 460,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {job.query}
          </span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <span style={{ fontSize: 11, color: "var(--text-muted)", fontFamily: "monospace" }}>
            {completeCount}/{Object.keys(job.agents).length} agents
          </span>
          <RailVizButton />
          <StatusPill status={job.status} />
        </div>
      </header>

      {/* Body */}
      <div style={{ flex: 1, display: "flex", overflow: "hidden", minHeight: 0 }}>
        {/* Main column — graph + compact outputs + Senso */}
        <div
          style={{
            flex: "1 1 0",
            minWidth: 0,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            borderRight: "1px solid var(--border)",
            overflow: "hidden",
          }}
        >

          {/* Panel tab bar */}
          <div
            style={{
              borderBottom: "1px solid var(--border)",
              display: "flex",
              alignItems: "center",
              padding: "0 16px",
              height: 38,
              gap: 2,
              flexShrink: 0,
            }}
          >
            {(["graph", "debates", "results"] as ActivePanel[]).map((tab) => {
              const labels: Record<ActivePanel, string> = {
                graph: "Execution graph",
                debates: "Debates",
                results: "Intelligence report",
              };
              return (
                <button
                  key={tab}
                  onClick={() => setActivePanel(tab)}
                  style={{
                    padding: "4px 12px",
                    borderRadius: 6,
                    border: "none",
                    cursor: "pointer",
                    fontSize: 11,
                    fontWeight: activePanel === tab ? 600 : 400,
                    color: activePanel === tab ? "var(--text-primary)" : "var(--text-muted)",
                    background: activePanel === tab ? "var(--bg-elevated)" : "transparent",
                    letterSpacing: "0.03em",
                    transition: "all 0.15s",
                  }}
                >
                  {labels[tab]}
                </button>
              );
            })}
            <div style={{ flex: 1 }} />
            {/* Live indicator */}
            {job.status === "running" && (
              <div style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 10, color: "var(--text-secondary)" }}>
                <div
                  style={{
                    width: 6,
                    height: 6,
                    borderRadius: "50%",
                    background: "var(--stream-blue)",
                  }}
                  className="pulse-glow"
                />
                Live
              </div>
            )}
          </div>

          {/* Panel content */}
          <div style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
            {activePanel === "graph" ? (
              <div style={{ flex: 1, minHeight: 0, display: "flex", flexDirection: "column" }}>
                <div style={{ flex: "3 1 0", minHeight: 200, position: "relative" }}>
                  <AgentFlowGraph agents={job.agents} status={job.status} query={job.query} results={job.results} jobId={jobId} backendUrl={BACKEND} />
                </div>
              </div>
            ) : activePanel === "debates" ? (
              <div style={{ flex: 1, minHeight: 0, overflow: "hidden", display: "flex", flexDirection: "column" }}>
                <AgentDebates agents={job.agents} results={job.results} status={job.status} />
              </div>
            ) : (
              <div style={{ flex: 1, minHeight: 0, overflowY: "auto" }}>
                <ResultsPanel results={job.results} status={job.status} query={job.query} />
              </div>
            )}
          </div>
        </div>

        {/* Chat — collapsible sidebar */}
        <div
          style={{
            flex: chatCollapsed ? "0 0 32px" : "0 0 clamp(280px, 28vw, 340px)",
            maxWidth: chatCollapsed ? 32 : 360,
            minHeight: 0,
            display: "flex",
            flexDirection: chatCollapsed ? "column" : "column",
            overflow: "hidden",
            background: "var(--bg-card)",
            borderLeft: "1px solid var(--border)",
            transition: "flex 0.2s ease, max-width 0.2s ease",
          }}
        >
          {/* Chat toggle strip */}
          <button
            onClick={() => setChatCollapsed((v) => !v)}
            title={chatCollapsed ? "Open chat" : "Close chat"}
            style={{
              flexShrink: 0,
              width: "100%",
              padding: chatCollapsed ? "12px 0" : "5px 14px",
              background: "transparent",
              border: "none",
              borderBottom: chatCollapsed ? "none" : "1px solid var(--border)",
              cursor: "pointer",
              display: "flex",
              alignItems: "center",
              justifyContent: chatCollapsed ? "center" : "space-between",
              gap: 6,
              fontSize: 10,
              color: "var(--text-muted)",
              transition: "background 0.15s",
              writingMode: chatCollapsed ? "vertical-rl" : "horizontal-tb",
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
            onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
          >
            {chatCollapsed ? (
              <span style={{ writingMode: "vertical-rl", fontSize: 10, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
                Chat ›
              </span>
            ) : (
              <>
                <span style={{ fontWeight: 600, letterSpacing: "0.04em", textTransform: "uppercase" }}>Chat</span>
                <span style={{ fontSize: 12 }}>‹</span>
              </>
            )}
          </button>
          {!chatCollapsed && <ChatPanel jobId={jobId} job={job} />}
        </div>
      </div>
    </div>
  );
}

function StatusPill({ status }: { status: string }) {
  const cfg: Record<string, { color: string; dot: string; label: string }> = {
    starting: { color: "var(--text-secondary)", dot: "var(--text-muted)", label: "Starting" },
    running: { color: "var(--stream-blue)", dot: "var(--stream-blue)", label: "Running" },
    complete: { color: "var(--stream-green)", dot: "var(--stream-green)", label: "Complete" },
    error: { color: "var(--stream-red)", dot: "var(--stream-red)", label: "Error" },
  };
  const c = cfg[status] ?? cfg.starting;
  return (
    <div
      style={{
        display: "flex",
        alignItems: "center",
        gap: 5,
        fontSize: 11,
        color: c.color,
        background: `color-mix(in srgb, ${c.color} 14%, transparent)`,
        border: `1px solid color-mix(in srgb, ${c.color} 32%, transparent)`,
        borderRadius: 6,
        padding: "3px 8px",
        fontFamily: "monospace",
      }}
    >
      <div
        style={{ width: 5, height: 5, borderRadius: "50%", background: c.dot }}
        className={status === "running" ? "pulse-glow" : ""}
      />
      {c.label}
    </div>
  );
}
