"use client";

import { useEffect } from "react";
import ReactFlow, {
  Background,
  Handle,
  Position,
  NodeTypes,
  EdgeTypes,
  BaseEdge,
  EdgeProps,
  getBezierPath,
  MarkerType,
  Node,
  Edge,
  useNodesState,
  useEdgesState,
} from "reactflow";
import "reactflow/dist/style.css";
import { JobStatus, AgentStatus, AnalysisResults, SensoFactCheck } from "@/app/analysis/[jobId]/page";
import { getFactsForAgent, type AgentKey } from "@/lib/agentOutputs";

// ─── Color maps ───────────────────────────────────────────────────────────────
const ACCENT: Record<string, string> = {
  breaking_news:    "#3b82f6",
  historical:       "#a855f7",
  official_docs:    "#eab308",
  visual_intel:     "#22c55e",
  financial_market: "#f97316",
  social_pulse:     "#ec4899",
  legal:            "#f59e0b",
  synthesizer:      "#ef4444",
  query:            "#e4e4e7",
};

// Maps the stream prefix in party names ("Breaking News · Reuters") to accent color
const STREAM_NAME_TO_ACCENT: Record<string, string> = {
  "breaking news":     "#3b82f6",
  "historical intel":  "#a855f7",
  "official docs":     "#eab308",
  "visual intel":      "#22c55e",
  "financial markets": "#f97316",
  "social pulse":      "#ec4899",
  "legal":             "#f59e0b",
};

const STATUS_CFG: Record<string, { color: string; bg: string; label: string; glow: string }> = {
  idle:     { color: "#52525b", bg: "rgba(82,82,91,0.12)",    label: "Idle",     glow: "none" },
  waiting:  { color: "#71717a", bg: "rgba(113,113,122,0.14)", label: "Waiting",  glow: "none" },
  running:  { color: "#3b82f6", bg: "rgba(59,130,246,0.14)",  label: "Running",  glow: "0 0 28px rgba(59,130,246,0.28)" },
  complete: { color: "#22c55e", bg: "rgba(34,197,94,0.14)",   label: "Complete", glow: "0 0 18px rgba(34,197,94,0.22)" },
  error:    { color: "#ef4444", bg: "rgba(239,68,68,0.14)",   label: "Error",    glow: "0 0 18px rgba(239,68,68,0.22)" },
};

const AGENT_META: Record<string, { icon: string; subtitle: string; itemLabel: string; description: string }> = {
  breaking_news:    { icon: "◉", subtitle: "Tavily · Live News",             itemLabel: "Claims",    description: "Scanning live news feeds and extracting real-time claims" },
  historical:       { icon: "◎", subtitle: "Senso KB · History",             itemLabel: "Precedents", description: "Searching historical knowledge base for past precedents" },
  official_docs:    { icon: "◈", subtitle: "Tavily · Gov Sources",           itemLabel: "Positions", description: "Analyzing government and official source documents" },
  visual_intel:     { icon: "◆", subtitle: "OSINT · Markets",                itemLabel: "Signals",   description: "Extracting economic signals and OSINT imagery data" },
  financial_market: { icon: "◐", subtitle: "CoinGecko · Yahoo Finance",      itemLabel: "Signals",   description: "Fetching live crypto, VIX, oil and correlating with geopolitics" },
  social_pulse:     { icon: "◉", subtitle: "Reddit · X · Social",            itemLabel: "Signals",   description: "Reading public reaction — what citizens on the ground actually know" },
  legal:            { icon: "⚖", subtitle: "Congress · SCOTUS · Intl Law",   itemLabel: "Actions",   description: "Checking constitutional authority, War Powers Act, and international law" },
  synthesizer:      { icon: "✦", subtitle: "Fact Check · Cross-Reference",   itemLabel: "Findings",  description: "Cross-referencing all streams for final verdict" },
};

// ─── Helpers ──────────────────────────────────────────────────────────────────
function hostname(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return url; }
}

function faviconUrl(url: string): string {
  try { return `https://www.google.com/s2/favicons?domain=${new URL(url).origin}&sz=32`; }
  catch { return ""; }
}

function streamAccentFromPartyName(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, color] of Object.entries(STREAM_NAME_TO_ACCENT)) {
    if (lower.startsWith(key)) return color;
  }
  return "#71717a";
}

function parsePartyName(name: string): { stream: string; source: string } {
  const sep = name.indexOf("·");
  if (sep !== -1) return { stream: name.slice(0, sep).trim(), source: name.slice(sep + 1).trim() };
  return { stream: name, source: "" };
}

// ─── Source item extracted from each agent ────────────────────────────────────
interface AgentSourceItem {
  id: string;
  agentKey: string;
  title: string;
  url: string;
  domain: string;
}

function extractAgentSources(agents: JobStatus["agents"]): AgentSourceItem[] {
  const items: AgentSourceItem[] = [];

  function add(agentKey: string, list: { title?: string; url?: string }[]) {
    for (const item of list.slice(0, 5)) {
      if (!item.url) continue;
      const domain = hostname(item.url);
      items.push({ id: `source_${agentKey}_${items.length}`, agentKey, title: item.title || domain, url: item.url, domain });
    }
  }

  const streamKeys = ["breaking_news", "historical", "official_docs", "visual_intel", "financial_market", "social_pulse", "legal"] as const;
  const fieldMap: Record<string, string> = {
    breaking_news: "articles",
    historical: "sources",
    official_docs: "documents",
    visual_intel: "sources",
    financial_market: "sources",
    social_pulse: "posts",
    legal: "sources",
  };

  for (const key of streamKeys) {
    const agent = agents[key] as unknown as Record<string, unknown>;
    const field = fieldMap[key];
    add(key, (agent[field] as { title?: string; url?: string }[]) ?? []);
  }

  return items;
}

// ─── Reusable sub-components ──────────────────────────────────────────────────
const HANDLE_STYLE = { background: "#3f3f46", border: "1px solid #52525b", width: 8, height: 8 };
const HANDLE_SM    = { background: "#3f3f46", border: "1px solid #52525b", width: 6, height: 6 };

function StatusBadge({ status, color, bg, label }: { status: string; color: string; bg: string; label: string }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 4,
      fontSize: 9, color, background: bg,
      border: `1px solid ${color}40`, borderRadius: 4,
      padding: "2px 6px", fontFamily: "monospace",
      textTransform: "uppercase", letterSpacing: "0.06em", flexShrink: 0,
    }}>
      <span style={{ width: 5, height: 5, borderRadius: "50%", background: color }}
        className={status === "running" ? "pulse-glow" : ""} />
      {label}
    </span>
  );
}

function FindingItem({ text, accent }: { text: string; accent: string }) {
  return (
    <div style={{ display: "flex", gap: 6, padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.04)" }}>
      <div style={{ width: 2, borderRadius: 1, background: accent, flexShrink: 0, marginTop: 2, alignSelf: "stretch" }} />
      <span style={{ fontSize: 10, color: "#a1a1aa", lineHeight: 1.5, wordBreak: "break-word" }}>{text}</span>
    </div>
  );
}

function RunningIndicator({ accent, action }: { accent: string; action: string }) {
  return (
    <div style={{ padding: "8px 12px" }}>
      <div style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
        <div style={{ width: 6, height: 6, borderRadius: "50%", background: accent, marginTop: 3, flexShrink: 0 }}
          className="pulse-glow" />
        <span style={{ fontSize: 10, color: accent, lineHeight: 1.5, fontFamily: "monospace", wordBreak: "break-word" }}>
          {action || "Working..."}
        </span>
      </div>
    </div>
  );
}

// ─── QueryNode ────────────────────────────────────────────────────────────────
function QueryNode({ data }: { data: { query: string; status: string } }) {
  const s = STATUS_CFG[data.status] ?? STATUS_CFG.idle;
  return (
    <div style={{
      background: "linear-gradient(135deg, #1c1c20 0%, #141416 100%)",
      border: "1px solid #3a3a40", borderTop: "3px solid #e4e4e7",
      borderRadius: 12, width: 360,
      boxShadow: "0 6px 32px rgba(0,0,0,0.5)", fontFamily: "inherit", overflow: "hidden",
    }}>
      <div style={{
        padding: "10px 14px", borderBottom: "1px solid #2a2a2e",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "linear-gradient(90deg, rgba(228,228,231,0.06) 0%, transparent 60%)",
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: "#f4f4f5", letterSpacing: "0.12em", textTransform: "uppercase" }}>VERITY</span>
          <span style={{ fontSize: 9, color: "#52525b", fontFamily: "monospace", letterSpacing: "0.06em" }}>INTEL ANALYSIS</span>
        </div>
        <StatusBadge status={data.status} {...s} />
      </div>
      <div style={{ padding: "12px 14px 14px 14px" }}>
        <div style={{ fontSize: 9, color: "#52525b", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 7 }}>Query</div>
        <div style={{ fontSize: 13, color: "#e4e4e7", lineHeight: 1.55, wordBreak: "break-word", fontStyle: "italic" }}>
          &ldquo;{data.query}&rdquo;
        </div>
      </div>
      <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} />
    </div>
  );
}

// ─── AgentNode ────────────────────────────────────────────────────────────────
function AgentNode({ data }: { data: { agent: AgentStatus; agentKey: string; streamAccent: string } }) {
  const { agent, agentKey, streamAccent } = data;
  const accent = streamAccent ?? ACCENT.breaking_news;
  const s = STATUS_CFG[agent.status] ?? STATUS_CFG.idle;
  const meta = AGENT_META[agentKey] ?? { icon: "●", subtitle: "", itemLabel: "Items", description: "" };
  const facts = agent.status === "complete" ? getFactsForAgent(agent, agentKey as AgentKey, 4, 115) : [];
  const statCount =
    (agent as AgentStatus & { claims?: unknown[] }).claims?.length ??
    (agent as AgentStatus & { observations?: unknown[] }).observations?.length ??
    (agent as AgentStatus & { findings?: unknown[] }).findings?.length ??
    (agent as AgentStatus & { signals?: unknown[] }).signals?.length ??
    (agent as AgentStatus & { actions?: unknown[] }).actions?.length ?? null;
  const isRunning  = agent.status === "running";
  const isComplete = agent.status === "complete";
  const isWaiting  = agent.status === "idle" || agent.status === "waiting";

  return (
    <div style={{
      position: "relative",
      background: "linear-gradient(160deg, #181820 0%, #121214 100%)",
      border: "1px solid #2e2e34", borderLeft: `3px solid ${accent}`,
      borderRadius: 12, width: 230,
      boxShadow: s.glow !== "none" ? s.glow : "0 4px 20px rgba(0,0,0,0.35)",
      fontFamily: "inherit", overflow: "hidden", transition: "box-shadow 0.4s",
    }}>
      <Handle type="target" position={Position.Top} style={HANDLE_STYLE} />
      <div style={{
        padding: "8px 10px 7px 10px", borderBottom: "1px solid #2a2a2e",
        display: "flex", alignItems: "center", justifyContent: "space-between", gap: 6,
        background: `linear-gradient(90deg, ${accent}12 0%, transparent 70%)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6, minWidth: 0 }}>
          <span style={{ fontSize: 13, color: accent, flexShrink: 0 }}>{meta.icon}</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#f4f4f5", letterSpacing: "0.02em", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {agent.name}
          </span>
        </div>
        <StatusBadge status={agent.status} {...s} />
      </div>
      <div style={{ padding: "5px 10px 0 10px" }}>
        <span style={{ fontSize: 9, color: "#4a4a52", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em" }}>{meta.subtitle}</span>
      </div>
      {isWaiting && (
        <div style={{ padding: "6px 10px 8px 10px" }}>
          <span style={{ fontSize: 10, color: "#52525b", lineHeight: 1.4 }}>{meta.description}</span>
        </div>
      )}
      {isRunning && <RunningIndicator accent={accent} action={agent.action} />}
      {isComplete && facts.length > 0 && (
        <div style={{ padding: "8px 10px 4px 10px" }}>
          <div style={{ fontSize: 9, color: "#4a4a52", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>
            {meta.itemLabel} Found
          </div>
          {facts.map((fact, i) => <FindingItem key={i} text={fact} accent={accent} />)}
        </div>
      )}
      {isComplete && facts.length === 0 && (
        <div style={{ padding: "8px 10px" }}>
          <span style={{ fontSize: 10, color: "#52525b", fontFamily: "monospace" }}>{agent.action}</span>
        </div>
      )}
      {isComplete && statCount !== null && (
        <div style={{ padding: "5px 10px 8px 10px", display: "flex", alignItems: "center", gap: 4 }}>
          <span style={{ fontSize: 10, color: accent, fontFamily: "monospace", fontWeight: 700 }}>{statCount}</span>
          <span style={{ fontSize: 10, color: "#4a4a52", fontFamily: "monospace" }}>{meta.itemLabel.toLowerCase()} extracted</span>
        </div>
      )}
      {isRunning && (
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, borderRadius: "0 0 12px 12px" }} className="scan-line" />
      )}
      <Handle type="source" position={Position.Bottom} style={HANDLE_STYLE} />
    </div>
  );
}

// ─── SourceNode — one node per article/document/post found by an agent ────────
function SourceNode({ data }: {
  data: { title: string; url: string; domain: string; agentKey: string; accent: string; inDebate: boolean }
}) {
  const { title, url, domain, accent, inDebate } = data;
  const fav = faviconUrl(url);
  const borderColor = inDebate ? "#eab308" : `${accent}40`;
  const glowStyle = inDebate ? "0 0 14px rgba(234,179,8,0.25)" : "none";

  return (
    <div style={{
      background: "#0d1117",
      border: `1px solid ${borderColor}`,
      borderLeft: `2px solid ${inDebate ? "#eab308" : accent}`,
      borderRadius: 8, width: 200,
      boxShadow: glowStyle,
      fontFamily: "inherit", overflow: "hidden",
      transition: "box-shadow 0.3s",
    }}>
      <Handle type="target" position={Position.Top} style={HANDLE_SM} />
      <a
        href={url}
        target="_blank"
        rel="noopener noreferrer"
        style={{ textDecoration: "none", display: "block", padding: "8px 10px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 5 }}>
          {fav && (
            <img src={fav} alt="" width={11} height={11}
              style={{ borderRadius: 2, flexShrink: 0 }}
              onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
            />
          )}
          <span style={{
            fontSize: 9, color: inDebate ? "#eab308" : accent,
            fontFamily: "monospace", textTransform: "uppercase",
            letterSpacing: "0.05em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1,
          }}>
            {domain}
          </span>
          {inDebate && (
            <span style={{ fontSize: 8, color: "#eab308", flexShrink: 0 }}>⚡</span>
          )}
          <span style={{ fontSize: 9, color: "#484f58", flexShrink: 0 }}>↗</span>
        </div>
        <p style={{
          fontSize: 10, color: "#a1a1aa", lineHeight: 1.4, margin: 0,
          overflow: "hidden", display: "-webkit-box",
          WebkitLineClamp: 2, WebkitBoxOrient: "vertical",
        }}>
          {title}
        </p>
      </a>
      <Handle type="source" position={Position.Bottom} style={HANDLE_SM} />
    </div>
  );
}


// ─── SourceGroupNode — all sources for one agent in a single compact card ─────
function SourceGroupNode({ data }: {
  data: { sources: AgentSourceItem[]; agentKey: string; accent: string; active: boolean }
}) {
  const { sources, accent, active } = data;
  return (
    <div style={{
      background: "#0d1117",
      border: `1px solid ${active ? accent + "30" : "#1e1e22"}`,
      borderLeft: `2px solid ${active ? accent : "#2a2a2e"}`,
      borderRadius: 8, width: 230,
      fontFamily: "inherit", overflow: "hidden",
      boxShadow: active ? `0 0 14px ${accent}14` : "none",
      transition: "border-color 0.3s, box-shadow 0.3s",
    }}>
      <Handle type="target" position={Position.Top} style={HANDLE_SM} />
      <div style={{
        padding: "4px 8px 4px 10px",
        borderBottom: `1px solid ${accent}14`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: `linear-gradient(90deg, ${accent}08 0%, transparent 70%)`,
      }}>
        <span style={{ fontSize: 8, color: active ? accent : "#52525b", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.07em" }}>
          Web Sources
        </span>
        {sources.length > 0 && (
          <span style={{ fontSize: 8, color: "#484f58", fontFamily: "monospace" }}>{sources.length} found</span>
        )}
      </div>
      {sources.length === 0 ? (
        <div style={{ padding: "5px 10px" }}>
          <span style={{ fontSize: 9, color: "#3f3f46", fontFamily: "monospace" }}>No sources yet</span>
        </div>
      ) : (
        <div style={{ padding: "3px 5px 4px 5px", display: "flex", flexDirection: "column", gap: 1 }}>
          {sources.map((src) => {
            const fav = faviconUrl(src.url);
            return (
              <a
                key={src.id}
                href={src.url}
                target="_blank"
                rel="noopener noreferrer"
                style={{
                  display: "flex", alignItems: "center", gap: 5,
                  padding: "3px 5px",
                  borderRadius: 4,
                  textDecoration: "none",
                  background: "transparent",
                  transition: "background 0.12s",
                }}
                onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.background = `${accent}14`)}
                onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.background = "transparent")}
              >
                {fav && (
                  <img src={fav} alt="" width={10} height={10}
                    style={{ borderRadius: 2, flexShrink: 0 }}
                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }}
                  />
                )}
                <span style={{
                  fontSize: 9, color: active ? accent : "#4a4a52",
                  fontFamily: "monospace", textTransform: "uppercase",
                  letterSpacing: "0.04em",
                  overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", flex: 1,
                }}>
                  {src.domain}
                </span>
                <span style={{ fontSize: 8, color: "#484f58", flexShrink: 0 }}>↗</span>
              </a>
            );
          })}
        </div>
      )}
      <Handle type="source" position={Position.Bottom} style={HANDLE_SM} />
    </div>
  );
}

// ─── SynthesizerNode ──────────────────────────────────────────────────────────
function SynthesizerNode({ data }: { data: { agent: AgentStatus; jobResults: AnalysisResults | null } }) {
  const { agent, jobResults } = data;
  const accent = ACCENT.synthesizer;
  const s = STATUS_CFG[agent.status] ?? STATUS_CFG.idle;
  const isRunning  = agent.status === "running";
  const isComplete = agent.status === "complete";
  const previewFacts = isComplete ? getFactsForAgent(agent, "synthesizer", 2, 115) : [];

  return (
    <div style={{
      position: "relative",
      background: "linear-gradient(160deg, #1c1214 0%, #121214 100%)",
      border: "1px solid #2e2e34", borderBottom: `3px solid ${accent}`,
      borderRadius: 12, width: 360,
      boxShadow: s.glow !== "none" ? s.glow : "0 4px 24px rgba(0,0,0,0.4)",
      fontFamily: "inherit", overflow: "hidden", transition: "box-shadow 0.4s",
    }}>
      <Handle type="target" position={Position.Top} style={HANDLE_STYLE} />
      <div style={{
        padding: "8px 12px 7px 12px", borderBottom: "1px solid #2a2a2e",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: `linear-gradient(90deg, ${accent}12 0%, transparent 70%)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
          <span style={{ fontSize: 13, color: accent }}>✦</span>
          <span style={{ fontSize: 11, fontWeight: 600, color: "#f4f4f5", letterSpacing: "0.02em" }}>{agent.name}</span>
        </div>
        <StatusBadge status={agent.status} {...s} />
      </div>
      <div style={{ padding: "5px 12px 0 12px" }}>
        <span style={{ fontSize: 9, color: "#4a4a52", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em" }}>
          Fact Check · Cross-Reference · Senso · Final Verdict
        </span>
      </div>
      {(agent.status === "waiting" || agent.status === "idle") && (
        <div style={{ padding: "8px 12px 10px 12px" }}>
          <span style={{ fontSize: 10, color: "#52525b", lineHeight: 1.4 }}>
            Waiting for all agent streams before final synthesis.
          </span>
        </div>
      )}
      {isRunning && <RunningIndicator accent={accent} action={agent.action} />}
      {isComplete && (
        <div style={{ padding: "10px 12px 4px 12px" }}>
          {previewFacts.length > 0 && (
            <>
              <div style={{ fontSize: 9, color: "#4a4a52", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 6 }}>Key Intelligence Findings</div>
              {previewFacts.map((f, i) => <FindingItem key={i} text={f} accent={accent} />)}
            </>
          )}
          <div style={{ height: 8 }} />
        </div>
      )}
      {isComplete && jobResults?.executive_summary && (
        <div style={{ padding: "0 12px 12px 12px" }}>
          <div style={{ borderTop: "1px solid #2a2a2e", paddingTop: 10 }}>
            <div style={{ fontSize: 9, color: accent, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 7, opacity: 0.85 }}>
              ✦ Verity Answer
            </div>
            <div style={{
              borderLeft: `2px solid ${accent}`,
              paddingLeft: 9,
              fontSize: 10.5,
              color: "#d4d4d8",
              lineHeight: 1.65,
              background: `linear-gradient(90deg, ${accent}08 0%, transparent 80%)`,
              borderRadius: "0 4px 4px 0",
              padding: "6px 8px 6px 9px",
            }}>
              {jobResults.executive_summary}
            </div>
          </div>
        </div>
      )}
      {isRunning && (
        <div style={{ position: "absolute", bottom: 0, left: 0, right: 0, height: 2, background: `linear-gradient(90deg, transparent, ${accent}, transparent)`, borderRadius: "0 0 12px 12px" }} className="scan-line" />
      )}
    </div>
  );
}

// ─── SensoNode — one per stream, shows per-claim Senso fact-check results ─────
const VERDICT_CFG = {
  CORRECT:    { icon: "✓", label: "Confirmed",       color: "#22c55e", bg: "rgba(34,197,94,0.08)",   border: "rgba(34,197,94,0.22)"   },
  INCORRECT:  { icon: "✗", label: "Contradicted",    color: "#ef4444", bg: "rgba(239,68,68,0.08)",   border: "rgba(239,68,68,0.22)"   },
  UNVERIFIED: { icon: "○", label: "Not in Senso KB", color: "#52525b", bg: "rgba(82,82,91,0.06)",    border: "rgba(82,82,91,0.18)"    },
};

function SensoNode({ data }: { data: { senso: Record<string, unknown> | null | undefined; accent: string } }) {
  const { senso, accent } = data;
  const isRunning  = senso?.status === "running";
  const isComplete = senso?.status === "complete";
  const factChecks = (senso?.fact_checks as SensoFactCheck[] | undefined) ?? [];
  const action     = (senso?.action as string) ?? "Fact-checking claims…";

  const correctCount    = factChecks.filter(f => f.verdict === "CORRECT").length;
  const incorrectCount  = factChecks.filter(f => f.verdict === "INCORRECT").length;
  const unverifiedCount = factChecks.filter(f => f.verdict === "UNVERIFIED").length;

  return (
    <div style={{
      position: "relative",
      background: "linear-gradient(160deg, #0d1117 0%, #090d12 100%)",
      border: `1px solid ${accent}28`,
      borderTop: `2px solid ${accent}`,
      borderRadius: 8,
      width: 240,
      fontFamily: "inherit",
      overflow: "hidden",
    }}>
      <Handle type="target" position={Position.Top} style={HANDLE_SM} />

      {/* Header */}
      <div style={{
        padding: "4px 8px",
        borderBottom: `1px solid ${accent}18`,
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: `linear-gradient(90deg, ${accent}08 0%, transparent 70%)`,
      }}>
        <span style={{ fontSize: 8, color: accent, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em" }}>
          ⬡ Senso Fact-Check
        </span>
        {isRunning && (
          <span style={{ display: "flex", alignItems: "center", gap: 3, fontSize: 8, color: accent }}>
            <span style={{ width: 4, height: 4, borderRadius: "50%", background: accent }} className="pulse-glow" />
            Checking
          </span>
        )}
        {isComplete && (
          <span style={{ display: "flex", alignItems: "center", gap: 4, fontSize: 8, fontFamily: "monospace" }}>
            {correctCount > 0    && <span style={{ color: "#22c55e" }}>✓ {correctCount} confirmed</span>}
            {incorrectCount > 0  && <span style={{ color: "#ef4444" }}>✗ {incorrectCount} wrong</span>}
            {incorrectCount === 0 && correctCount === 0 && unverifiedCount > 0 && (
              <span style={{ color: "#52525b" }}>No Senso record</span>
            )}
            {(correctCount > 0 || incorrectCount > 0) && unverifiedCount > 0 && (
              <span style={{ color: "#52525b" }}>○ {unverifiedCount} no record</span>
            )}
          </span>
        )}
        {!isRunning && !isComplete && <span style={{ fontSize: 8, color: "#52525b", fontFamily: "monospace" }}>Pending</span>}
      </div>

      {/* Running body */}
      {isRunning && (
        <div style={{ padding: "5px 8px" }}>
          <span style={{ fontSize: 9, color: accent, fontFamily: "monospace", lineHeight: 1.4, wordBreak: "break-word" }}>
            {action}
          </span>
        </div>
      )}

      {/* Complete body — per-claim rows */}
      {isComplete && factChecks.length > 0 && (
        <div style={{ padding: "5px 6px", display: "flex", flexDirection: "column", gap: 3, maxHeight: 260, overflowY: "auto" }}>
          {factChecks.map((fc, i) => {
            const cfg = VERDICT_CFG[fc.verdict] ?? VERDICT_CFG.UNVERIFIED;
            const isUnverified = fc.verdict === "UNVERIFIED";
            return (
              <div key={i} style={{
                background: cfg.bg,
                border: `1px solid ${cfg.border}`,
                borderRadius: 4,
                padding: "4px 6px",
              }}>
                {/* Verdict label + source */}
                <div style={{ display: "flex", alignItems: "center", gap: 4, marginBottom: 2 }}>
                  <span style={{ fontSize: 8, color: cfg.color, fontFamily: "monospace", fontWeight: 700, flexShrink: 0 }}>
                    {cfg.icon} {cfg.label}
                  </span>
                  {fc.url ? (
                    <a
                      href={fc.url}
                      target="_blank"
                      rel="noopener noreferrer"
                      style={{ fontSize: 8, color: "#6b7280", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.03em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginLeft: "auto", textDecoration: "none" }}
                      onMouseEnter={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "#a1a1aa")}
                      onMouseLeave={(e) => ((e.currentTarget as HTMLAnchorElement).style.color = "#6b7280")}
                    >
                      {fc.source.length > 18 ? fc.source.slice(0, 18) + "…" : fc.source} ↗
                    </a>
                  ) : (
                    <span style={{ fontSize: 8, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.03em", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap", marginLeft: "auto" }}>
                      {fc.source.length > 18 ? fc.source.slice(0, 18) + "…" : fc.source}
                    </span>
                  )}
                </div>
                {/* Claim text */}
                <p style={{ fontSize: 9, color: isUnverified ? "#52525b" : "#a1a1aa", lineHeight: 1.35, margin: "0 0 2px 0" }}>
                  {fc.claim}
                </p>
                {/* What Senso says — skip generic "no data" messages for unverified */}
                {fc.senso_says && !isUnverified && (
                  <p style={{ fontSize: 8, color: fc.verdict === "INCORRECT" ? "#fca5a5" : "#22c55e80", lineHeight: 1.3, margin: 0, fontStyle: "italic" }}>
                    {fc.senso_says}
                  </p>
                )}
              </div>
            );
          })}
          {/* Footer note when all unverified */}
          {unverifiedCount === factChecks.length && factChecks.length > 0 && (
            <p style={{ fontSize: 8, color: "#484f58", lineHeight: 1.4, margin: "2px 2px 0", fontStyle: "italic" }}>
              Senso covers historical data. Breaking news may not have a record yet.
            </p>
          )}
        </div>
      )}

      {/* Complete but no fact_checks fallback */}
      {isComplete && factChecks.length === 0 && (
        <div style={{ padding: "5px 8px" }}>
          <span style={{ fontSize: 9, color: "#52525b", fontFamily: "monospace" }}>No claims checked</span>
        </div>
      )}

      {/* Idle/pending body */}
      {!isRunning && !isComplete && (
        <div style={{ padding: "5px 8px" }}>
          <span style={{ fontSize: 9, color: "#52525b", fontFamily: "monospace" }}>Waiting for stream…</span>
        </div>
      )}

      <Handle type="source" position={Position.Bottom} style={HANDLE_SM} />
    </div>
  );
}

// ─── AnimatedEdge ─────────────────────────────────────────────────────────────
function AnimatedEdge({ id, sourceX, sourceY, targetX, targetY, sourcePosition, targetPosition, data }: EdgeProps & { data?: { active?: boolean; color?: string; dashed?: boolean } }) {
  const [edgePath] = getBezierPath({ sourceX, sourceY, sourcePosition, targetX, targetY, targetPosition });
  const isActive = data?.active;
  const color = data?.color ?? "#3f3f46";
  const dashed = data?.dashed;
  return (
    <>
      <BaseEdge id={id} path={edgePath} style={{
        stroke: isActive ? color : "rgba(255,255,255,0.07)",
        strokeWidth: isActive ? 2 : 1,
        strokeDasharray: dashed ? "5 4" : undefined,
        transition: "stroke 0.5s, stroke-width 0.4s",
      }} />
      {isActive && (
        <circle r="3.5" fill={color} opacity="0.9">
          <animateMotion dur="1.6s" repeatCount="indefinite" path={edgePath} />
        </circle>
      )}
    </>
  );
}

// ─── Node + edge type registries ──────────────────────────────────────────────
const nodeTypes: NodeTypes = {
  query:       QueryNode       as unknown as NodeTypes[string],
  agent:       AgentNode       as unknown as NodeTypes[string],
  senso:       SensoNode       as unknown as NodeTypes[string],
  source:      SourceNode      as unknown as NodeTypes[string],
  sourceGroup: SourceGroupNode as unknown as NodeTypes[string],
  synthesizer: SynthesizerNode as unknown as NodeTypes[string],
};

const edgeTypes: EdgeTypes = {
  animated: AnimatedEdge as unknown as EdgeTypes[string],
};

// ─── Layout constants ─────────────────────────────────────────────────────────
// 7 agents at 260px/col, canvas ~1790px wide, center at 895px
const AGENT_COLS    = [0, 260, 520, 780, 1040, 1300, 1560];
const QUERY_X       = 715;   // center 360px node: 895 − 180
const SYNTH_X       = 715;
const ROW_AGENTS    = 180;
const ROW_SOURCES   = 440;   // source group nodes (one compact box per agent)
const ROW_SENSO     = 640;   // per-stream Senso fact-check boxes (one per agent)
const ROW_SYNTH     = 1060;

// ─── Build nodes ──────────────────────────────────────────────────────────────
function buildNodes(
  agents: JobStatus["agents"],
  query: string,
  status: JobStatus["status"],
  jobResults: AnalysisResults | null,
  posMap?: Map<string, { x: number; y: number }>,
): Node[] {
  const pos = (id: string, def: { x: number; y: number }) => posMap?.get(id) ?? def;
  const streamKeys = ["breaking_news", "historical", "official_docs", "visual_intel", "financial_market", "social_pulse", "legal"] as const;

  const nodes: Node[] = [
    { id: "query", type: "query", position: pos("query", { x: QUERY_X, y: 0 }), data: { query, status }, draggable: true },
    // 7 agent nodes
    ...streamKeys.map((key, i) => ({
      id: key,
      type: "agent",
      position: pos(key, { x: AGENT_COLS[i], y: ROW_AGENTS }),
      data: { agent: agents[key], agentKey: key, streamAccent: ACCENT[key] },
      draggable: true,
    })),
    // 7 Senso fact-check nodes — one per stream
    ...streamKeys.map((key, i) => ({
      id: `senso_${key}`,
      type: "senso",
      position: pos(`senso_${key}`, { x: AGENT_COLS[i] + 10, y: ROW_SENSO }),
      data: { senso: (agents[key] as AgentStatus & { senso_stream?: Record<string, unknown> }).senso_stream ?? null, accent: ACCENT[key] },
      draggable: true,
    })),
  ];

  // Source group nodes — one compact box per agent column
  const allSources = extractAgentSources(agents);
  const sourcesByAgent: Record<string, AgentSourceItem[]> = {};
  for (const s of allSources) {
    if (!sourcesByAgent[s.agentKey]) sourcesByAgent[s.agentKey] = [];
    sourcesByAgent[s.agentKey].push(s);
  }

  for (const [agentKeyStr, i] of streamKeys.map((k, i) => [k, i] as const)) {
    const colX = AGENT_COLS[i];
    const sources = sourcesByAgent[agentKeyStr] ?? [];
    nodes.push({
      id: `sources_${agentKeyStr}`,
      type: "sourceGroup",
      position: pos(`sources_${agentKeyStr}`, { x: colX, y: ROW_SOURCES }),
      data: {
        sources,
        agentKey: agentKeyStr,
        accent: ACCENT[agentKeyStr] ?? "#71717a",
        active: agents[agentKeyStr as keyof typeof agents]?.status === "complete",
      },
      draggable: true,
    });
  }

  // Synthesizer node
  nodes.push({
    id: "synthesizer",
    type: "synthesizer",
    position: pos("synthesizer", { x: SYNTH_X, y: ROW_SYNTH }),
    data: { agent: agents.synthesizer, jobResults },
    draggable: true,
  });

  return nodes;
}

// ─── Build edges ──────────────────────────────────────────────────────────────
function buildEdges(
  agents: JobStatus["agents"],
  jobResults: AnalysisResults | null,
): Edge[] {
  const streamKeys = ["breaking_news", "historical", "official_docs", "visual_intel", "financial_market", "social_pulse", "legal"] as const;
  const synthActive = agents.synthesizer.status === "running" || agents.synthesizer.status === "complete";

  const isActive = (key: string) => {
    const a = agents[key as keyof typeof agents];
    return a?.status === "running" || a?.status === "complete";
  };

  const edges: Edge[] = [
    // Query → each agent
    ...streamKeys.map((key) => ({
      id: `q-${key}`,
      source: "query",
      target: key,
      type: "animated",
      data: { active: isActive(key), color: ACCENT[key] },
      markerEnd: { type: MarkerType.ArrowClosed, color: isActive(key) ? ACCENT[key] : "rgba(255,255,255,0.1)", width: 10, height: 10 },
    })),
    // Agent → SourceGroup (one per stream)
    ...streamKeys.map((key) => {
      const agentDone = isActive(key);
      return {
        id: `${key}-sources_${key}`,
        source: key,
        target: `sources_${key}`,
        type: "animated",
        data: { active: agentDone, color: ACCENT[key] },
        markerEnd: { type: MarkerType.ArrowClosed, color: agentDone ? ACCENT[key] : "rgba(255,255,255,0.1)", width: 8, height: 8 },
      };
    }),
    // SourceGroup → Senso (sources feed into fact-check)
    ...streamKeys.map((key) => {
      const sensoActive = isActive(key);
      return {
        id: `sources_${key}-senso_${key}`,
        source: `sources_${key}`,
        target: `senso_${key}`,
        type: "animated",
        data: { active: sensoActive, color: ACCENT[key] },
        markerEnd: { type: MarkerType.ArrowClosed, color: sensoActive ? ACCENT[key] : "rgba(255,255,255,0.1)", width: 8, height: 8 },
      };
    }),
  ];

  // Senso → Synthesizer (all 7 streams)
  for (const key of streamKeys) {
    const sensoStatus = (agents[key] as AgentStatus & { senso_stream?: { status?: string } }).senso_stream?.status;
    const sensoActive = (sensoStatus === "running" || sensoStatus === "complete") && synthActive;
    edges.push({
      id: `senso_${key}-synth`,
      source: `senso_${key}`,
      target: "synthesizer",
      type: "animated",
      data: { active: sensoActive, color: ACCENT[key] },
      markerEnd: { type: MarkerType.ArrowClosed, color: sensoActive ? ACCENT[key] : "rgba(255,255,255,0.1)", width: 8, height: 8 },
    });
  }

  return edges;
}

// ─── Main graph component ─────────────────────────────────────────────────────
interface Props {
  agents: JobStatus["agents"];
  status: JobStatus["status"];
  query: string;
  results: JobStatus["results"];
}

export default function AgentFlowGraph({ agents, status, query, results }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState(
    buildNodes(agents, query, status, results ?? null)
  );
  const [edges, setEdges, onEdgesChange] = useEdgesState(buildEdges(agents, results ?? null));

  useEffect(() => {
    setNodes((prev) => {
      const posMap = new Map(prev.map((n) => [n.id, n.position]));
      return buildNodes(agents, query, status, results ?? null, posMap);
    });
  }, [agents, query, status, results, setNodes]);

  useEffect(() => {
    setEdges(buildEdges(agents, results ?? null));
  }, [agents, results, setEdges]);

  return (
    <div style={{ width: "100%", height: "100%", background: "var(--bg-base)" }}>
      <ReactFlow
        nodes={nodes} edges={edges}
        nodeTypes={nodeTypes} edgeTypes={edgeTypes}
        onNodesChange={onNodesChange} onEdgesChange={onEdgesChange}
        fitView fitViewOptions={{ padding: 0.12, minZoom: 0.15, maxZoom: 1.5 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={true} nodesConnectable={false}
        elementsSelectable={true} panOnDrag={true}
        minZoom={0.1} maxZoom={2.5}
      >
        <Background color="rgba(255,255,255,0.035)" gap={24} size={1} style={{ background: "var(--bg-base)" }} />
      </ReactFlow>
    </div>
  );
}
