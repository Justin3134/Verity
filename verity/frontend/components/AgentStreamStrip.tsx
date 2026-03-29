"use client";

import type { JobStatus, AnalysisResults } from "@/app/analysis/[jobId]/page";
import { getAgentConclusion, type AgentKey } from "@/lib/agentOutputs";

type Agents = JobStatus["agents"];

const STREAMS: { key: AgentKey; label: string; accent: string; icon: string }[] = [
  { key: "breaking_news",    label: "Breaking News",    accent: "#3b82f6", icon: "◉" },
  { key: "historical",       label: "Historical Intel", accent: "#a855f7", icon: "◎" },
  { key: "official_docs",    label: "Official Docs",    accent: "#eab308", icon: "◈" },
  { key: "visual_intel",     label: "Visual Intel",     accent: "#22c55e", icon: "◆" },
  { key: "financial_market", label: "Financial Markets",accent: "#f97316", icon: "◐" },
  { key: "social_pulse",     label: "Public Reaction",  accent: "#ec4899", icon: "◉" },
  { key: "legal",            label: "Legal Authority",  accent: "#f59e0b", icon: "⚖" },
  { key: "synthesizer",      label: "Synthesis",        accent: "#ef4444", icon: "✦" },
];

function statusColor(status: string, accent: string): string {
  if (status === "complete") return "#22c55e";
  if (status === "running")  return accent;
  if (status === "error")    return "#ef4444";
  return "#52525b";
}

function statusLabel(status: string): string {
  switch (status) {
    case "running":  return "Running";
    case "complete": return "Done";
    case "waiting":  return "Waiting";
    case "error":    return "Error";
    default:         return "Pending";
  }
}

interface Props {
  agents: Agents;
  results: AnalysisResults | null;
  jobStatus: JobStatus["status"];
  sensoLogLength: number;
  isCollapsed: boolean;
  onToggle: () => void;
}

export default function AgentStreamStrip({ agents, isCollapsed, onToggle }: Props) {
  return (
    <div style={{ flexShrink: 0, borderTop: "1px solid var(--border)", background: "var(--bg-card)" }}>
      {/* Header — click anywhere to expand/collapse */}
      <button
        onClick={onToggle}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "5px 12px",
          background: "transparent",
          border: "none",
          borderBottom: isCollapsed ? "none" : "1px solid var(--border)",
          cursor: "pointer",
          textAlign: "left",
          transition: "background 0.15s",
        }}
        onMouseEnter={(e) => (e.currentTarget.style.background = "var(--bg-elevated)")}
        onMouseLeave={(e) => (e.currentTarget.style.background = "transparent")}
      >
        <span style={{ fontSize: 10, fontWeight: 600, color: "var(--text-muted)", letterSpacing: "0.06em", textTransform: "uppercase" }}>
          Agent Logs
        </span>
        <span style={{ fontSize: 9, color: "var(--text-muted)" }}>click to expand</span>
        <span style={{ marginLeft: "auto", fontSize: 9, color: "var(--text-muted)" }}>
          {isCollapsed ? "▼" : "▲"}
        </span>
      </button>

      {/* Expanded: unified flat log — one row per agent, no individual boxes */}
      {!isCollapsed && (
        <div style={{ overflowY: "auto", maxHeight: 180 }}>
          {STREAMS.map((s) => {
            const agent = agents[s.key];
            if (!agent) return null;

            const color      = statusColor(agent.status, s.accent);
            const isRunning  = agent.status === "running";
            const isComplete = agent.status === "complete";
            const logs       = (agent as { logs?: string[] }).logs ?? [];
            const conclusion = getAgentConclusion(agent);

            const displayText = isComplete && conclusion
              ? conclusion
              : logs.length > 0
                ? logs[logs.length - 1]
                : agent.status === "waiting" || agent.status === "idle"
                  ? "Queued…"
                  : agent.action || "Working…";

            return (
              <div
                key={s.key}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: 8,
                  padding: "4px 12px",
                  borderBottom: "1px solid var(--border)",
                  borderLeft: `2px solid ${s.accent}`,
                }}
              >
                {/* Agent icon + name */}
                <span style={{
                  fontSize: 9, color: s.accent, flexShrink: 0,
                  fontWeight: 600, width: 116, whiteSpace: "nowrap",
                  overflow: "hidden", textOverflow: "ellipsis",
                }}>
                  {s.icon} {s.label}
                </span>

                {/* Status badge */}
                <span style={{
                  fontSize: 8, color, flexShrink: 0,
                  background: `${color}1a`, border: `1px solid ${color}35`,
                  borderRadius: 3, padding: "1px 5px", fontFamily: "monospace",
                  display: "flex", alignItems: "center", gap: 3,
                }}>
                  {isRunning && (
                    <span style={{ width: 4, height: 4, borderRadius: "50%", background: color, flexShrink: 0 }} className="pulse-glow" />
                  )}
                  {statusLabel(agent.status)}
                </span>

                {/* Log text */}
                <span style={{
                  fontSize: 9, color: "var(--text-secondary)",
                  lineHeight: 1.4, flex: 1,
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                }}>
                  {displayText}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
