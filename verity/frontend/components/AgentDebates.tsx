"use client";

import { useState } from "react";
import type {
  JobStatus,
  AnalysisResults,
  ContestedSource,
  DebateCluster,
  DebateClusterParty,
} from "@/app/analysis/[jobId]/page";

interface Props {
  agents: JobStatus["agents"];
  results: AnalysisResults | null;
  status: string;
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function hostname(url: string): string {
  try { return new URL(url).hostname.replace(/^www\./, ""); }
  catch { return url; }
}

function faviconUrl(url: string): string {
  try {
    const h = new URL(url).origin;
    return `https://www.google.com/s2/favicons?domain=${h}&sz=32`;
  } catch { return ""; }
}

// ─── Agent stream definitions ──────────────────────────────────────────────
const STREAMS = [
  { key: "breaking_news",    label: "Breaking News",    accent: "#3b82f6", icon: "◉" },
  { key: "historical",       label: "Historical Intel", accent: "#a855f7", icon: "◎" },
  { key: "official_docs",    label: "Official Docs",    accent: "#eab308", icon: "◈" },
  { key: "visual_intel",     label: "Visual Intel",     accent: "#22c55e", icon: "◆" },
  { key: "financial_market", label: "Fin. Markets",     accent: "#f97316", icon: "◐" },
  { key: "social_pulse",     label: "Social Pulse",     accent: "#ec4899", icon: "◇" },
  { key: "legal",            label: "Legal",            accent: "#f59e0b", icon: "⚖" },
] as const;

type StreamKey = (typeof STREAMS)[number]["key"];

// ─── Source card ───────────────────────────────────────────────────────────
function SourceCard({
  title, url, image, source, claim, accent,
}: {
  title: string;
  url: string;
  image?: string | null;
  source?: string;
  claim?: string;
  accent: string;
}) {
  const displayHost = source || hostname(url);
  const fav = url ? faviconUrl(url) : "";

  return (
    <a
      href={url || undefined}
      target="_blank"
      rel="noopener noreferrer"
      style={{ textDecoration: "none", display: "block" }}
      onClick={(e) => { if (!url) e.preventDefault(); }}
    >
      <div style={{
        background: "#0d1117",
        border: `1px solid ${accent}25`,
        borderRadius: 10,
        overflow: "hidden",
        cursor: url ? "pointer" : "default",
        transition: "border-color 0.15s",
      }}
        onMouseEnter={(e) => { if (url) (e.currentTarget as HTMLDivElement).style.borderColor = `${accent}70`; }}
        onMouseLeave={(e) => { (e.currentTarget as HTMLDivElement).style.borderColor = `${accent}25`; }}
      >
        {/* Thumbnail */}
        {image && (
          <div style={{ height: 110, overflow: "hidden", background: "#161b22" }}>
            <img
              src={image}
              alt=""
              style={{ width: "100%", height: "100%", objectFit: "cover", display: "block" }}
              onError={(e) => { (e.currentTarget.parentElement as HTMLDivElement).style.display = "none"; }}
            />
          </div>
        )}

        <div style={{ padding: "10px 12px" }}>
          {/* Source line */}
          <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 6 }}>
            {fav && (
              <img src={fav} alt="" width={12} height={12} style={{ borderRadius: 2, flexShrink: 0 }}
                onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
            )}
            <span style={{ fontSize: 9, color: accent, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.05em" }}>
              {displayHost}
            </span>
            {url && <span style={{ fontSize: 9, color: "#484f58", marginLeft: "auto" }}>↗</span>}
          </div>

          {/* Title */}
          <p style={{
            fontSize: 11, color: "#c9d1d9", lineHeight: 1.45,
            margin: "0 0 7px 0", fontWeight: 500,
            display: "-webkit-box", WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>
            {title || displayHost}
          </p>

          {/* Claim */}
          {claim && (
            <p style={{
              fontSize: 10, color: "#7d8590", lineHeight: 1.5,
              margin: 0, fontStyle: "italic",
              display: "-webkit-box", WebkitLineClamp: 3,
              WebkitBoxOrient: "vertical", overflow: "hidden",
            }}>
              "{claim}"
            </p>
          )}
        </div>
      </div>
    </a>
  );
}

// ─── Per-agent views ────────────────────────────────────────────────────────
function BreakingNewsView({ agent, accent }: { agent: JobStatus["agents"]["breaking_news"]; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const articles = (raw.articles as { title: string; url: string; image?: string | null; source?: string }[] | undefined) ?? [];
  const claims = (raw.claims as { claim: string; source: string; url?: string; credibility?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (articles.length === 0 && claims.length === 0) {
    return <EmptyAgent label="Breaking News" status={agent.status} />;
  }

  // Match claims to articles by source name
  const claimMap: Record<string, string[]> = {};
  for (const c of claims) {
    const key = (c.source || "").toLowerCase();
    if (!claimMap[key]) claimMap[key] = [];
    claimMap[key].push(c.claim);
  }

  return (
    <div>
      <p style={{ fontSize: 11, color: "#484f58", marginBottom: 14, lineHeight: 1.5 }}>
        Searched {articles.length} live news sources. Here is what each outlet reported:
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10, marginBottom: 16 }}>
        {articles.map((a, i) => {
          const srcKey = (a.source || "").toLowerCase();
          const relatedClaims = claimMap[srcKey] ?? [];
          return (
            <SourceCard
              key={i}
              title={a.title}
              url={a.url}
              image={a.image}
              source={a.source}
              claim={relatedClaims[0]}
              accent={accent}
            />
          );
        })}
      </div>
      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Breaking News Agent Conclusion" />}
    </div>
  );
}

function HistoricalView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const precedents = (raw.precedents as { date?: string; event?: string; outcome?: string; source?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (precedents.length === 0) {
    return <EmptyAgent label="Historical Intel" status={agent.status} />;
  }

  return (
    <div>
      <p style={{ fontSize: 11, color: "#484f58", marginBottom: 14 }}>
        Searched knowledge base for historical precedents. Found {precedents.length} relevant events:
      </p>
      <div style={{ display: "flex", flexDirection: "column", gap: 8, marginBottom: 16 }}>
        {precedents.slice(0, 8).map((p, i) => (
          <div key={i} style={{
            background: "#0d1117", border: `1px solid ${accent}25`,
            borderLeft: `3px solid ${accent}`, borderRadius: 8, padding: "10px 14px",
          }}>
            <div style={{ display: "flex", gap: 8, alignItems: "baseline", marginBottom: 4 }}>
              {p.date && <span style={{ fontSize: 9, color: accent, fontFamily: "monospace", flexShrink: 0 }}>{p.date}</span>}
              <span style={{ fontSize: 12, color: "#c9d1d9", fontWeight: 500 }}>{p.event}</span>
            </div>
            {p.outcome && <p style={{ fontSize: 11, color: "#7d8590", margin: 0 }}>Outcome: {p.outcome}</p>}
          </div>
        ))}
      </div>
      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Historical Intel Agent Conclusion" />}
    </div>
  );
}

type AgentStatus = JobStatus["agents"]["breaking_news"];

function OfficialDocsView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const docs = (raw.documents as { title: string; url: string; image?: string | null; source?: string }[] | undefined) ?? [];
  const positions = (raw.official_positions as { actor?: string; tone?: string; official_statement?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (docs.length === 0 && positions.length === 0) {
    return <EmptyAgent label="Official Docs" status={agent.status} />;
  }

  const posMap: Record<string, string> = {};
  for (const p of positions) {
    if (p.actor && p.official_statement) {
      posMap[p.actor.toLowerCase()] = p.official_statement;
    }
  }

  return (
    <div>
      <p style={{ fontSize: 11, color: "#484f58", marginBottom: 14 }}>
        Searched {docs.length} official documents and government sources:
      </p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10, marginBottom: 16 }}>
        {docs.map((d, i) => {
          const docKey = hostname(d.url).toLowerCase();
          const claim = posMap[docKey] ?? positions[i]?.official_statement;
          return (
            <SourceCard key={i} title={d.title} url={d.url} image={d.image} source={d.source} claim={claim} accent={accent} />
          );
        })}
      </div>
      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Official Docs Agent Conclusion" />}
    </div>
  );
}

function VisualIntelView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const observations = (raw.observations as { type?: string; observation?: string; significance?: string; source_url?: string }[] | undefined) ?? [];
  const economicSignals = (raw.economic_signals as { indicator?: string; movement?: string; interpretation?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (observations.length === 0 && economicSignals.length === 0) {
    return <EmptyAgent label="Visual Intel" status={agent.status} />;
  }

  return (
    <div>
      {observations.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>
            OSINT & imagery signals ({observations.length} observations):
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {observations.slice(0, 6).map((o, i) => (
              <div key={i} style={{
                background: "#0d1117", border: `1px solid ${accent}25`,
                borderLeft: `3px solid ${accent}`, borderRadius: 8, padding: "9px 12px",
              }}>
                {o.type && <span style={{ fontSize: 9, color: accent, fontFamily: "monospace", display: "block", marginBottom: 3 }}>{o.type}</span>}
                <p style={{ fontSize: 12, color: "#c9d1d9", margin: "0 0 4px 0" }}>{o.observation}</p>
                {o.significance && <p style={{ fontSize: 10, color: "#7d8590", margin: 0 }}>{o.significance}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {economicSignals.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>Economic signals:</p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 7 }}>
            {economicSignals.slice(0, 4).map((s, i) => (
              <div key={i} style={{
                background: "#0d1117", border: `1px solid ${accent}25`, borderRadius: 8, padding: "9px 12px",
              }}>
                <p style={{ fontSize: 11, color: accent, fontFamily: "monospace", margin: "0 0 3px 0" }}>{s.indicator}</p>
                <p style={{ fontSize: 12, color: "#c9d1d9", margin: "0 0 4px 0" }}>{s.movement}</p>
                {s.interpretation && <p style={{ fontSize: 10, color: "#7d8590", margin: 0 }}>{s.interpretation}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Visual Intel Agent Conclusion" />}
    </div>
  );
}

function FinancialMarketsView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const marketData = raw.market_data as string | undefined;
  const signals = (raw.geopolitical_signals as { signal?: string; confidence?: string; basis?: string }[] | undefined) ??
    (raw.findings as { signal?: string; confidence?: string; basis?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (!marketData && signals.length === 0) {
    return <EmptyAgent label="Financial Markets" status={agent.status} />;
  }

  return (
    <div>
      {marketData && (
        <div style={{
          background: "#0d1117", border: `1px solid ${accent}25`,
          borderRadius: 8, padding: "12px 14px", marginBottom: 14,
          fontFamily: "monospace", fontSize: 11, color: "#c9d1d9", whiteSpace: "pre-line",
        }}>
          <p style={{ fontSize: 9, color: accent, textTransform: "uppercase", letterSpacing: "0.06em", margin: "0 0 8px 0" }}>Live Market Snapshot</p>
          {marketData}
        </div>
      )}

      {signals.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>Geopolitical signals from market data:</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {signals.slice(0, 5).map((s, i) => (
              <div key={i} style={{
                background: "#0d1117", border: `1px solid ${accent}25`,
                borderLeft: `3px solid ${accent}`, borderRadius: 8, padding: "9px 12px",
              }}>
                <p style={{ fontSize: 12, color: "#c9d1d9", margin: "0 0 4px 0" }}>{s.signal}</p>
                {s.basis && <p style={{ fontSize: 10, color: "#7d8590", margin: 0 }}>Basis: {s.basis}</p>}
              </div>
            ))}
          </div>
        </div>
      )}

      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Financial Markets Agent Conclusion" />}
    </div>
  );
}

function SocialPulseView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const posts = (raw.posts as { title?: string; url?: string; source?: string; snippet?: string }[] | undefined) ?? [];
  const reports = (raw.citizen_reports as { report?: string; platform?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (posts.length === 0 && reports.length === 0) {
    return <EmptyAgent label="Social Pulse" status={agent.status} />;
  }

  return (
    <div>
      {posts.length > 0 && (
        <p style={{ fontSize: 11, color: "#484f58", marginBottom: 12 }}>
          {posts.length} posts / threads sampled from public social:
        </p>
      )}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(200px, 1fr))", gap: 10, marginBottom: 16 }}>
        {posts.slice(0, 8).map((p, i) => (
          <SourceCard
            key={i}
            title={p.title || p.snippet || "Post"}
            url={p.url || ""}
            source={p.source}
            claim={p.snippet}
            accent={accent}
          />
        ))}
      </div>
      {reports.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>Citizen reports:</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {reports.slice(0, 6).map((r, i) => (
              <div key={i} style={{
                background: "#0d1117", border: `1px solid ${accent}25`,
                borderLeft: `3px solid ${accent}`, borderRadius: 8, padding: "9px 12px",
              }}>
                {r.platform && <span style={{ fontSize: 9, color: accent, fontFamily: "monospace" }}>{r.platform}</span>}
                <p style={{ fontSize: 12, color: "#c9d1d9", margin: "4px 0 0 0" }}>{r.report}</p>
              </div>
            ))}
          </div>
        </div>
      )}
      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Social Pulse Conclusion" />}
    </div>
  );
}

function LegalView({ agent, accent }: { agent: AgentStatus; accent: string }) {
  const raw = agent as unknown as Record<string, unknown>;
  const actions = (raw.actions as { action?: string; verdict?: string; constitutional_authority?: string }[] | undefined) ?? [];
  const cases = (raw.cases as { case?: string; ruling_summary?: string }[] | undefined) ?? [];
  const conclusion = (agent.result as string) || "";

  if (actions.length === 0 && cases.length === 0) {
    return <EmptyAgent label="Legal Authority" status={agent.status} />;
  }

  return (
    <div>
      {actions.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>Actions analyzed:</p>
          <div style={{ display: "flex", flexDirection: "column", gap: 7 }}>
            {actions.slice(0, 6).map((a, i) => (
              <div key={i} style={{
                background: "#0d1117", border: `1px solid ${accent}25`,
                borderLeft: `3px solid ${accent}`, borderRadius: 8, padding: "9px 12px",
              }}>
                <p style={{ fontSize: 12, color: "#c9d1d9", margin: "0 0 4px 0" }}>{a.action}</p>
                {a.verdict && <p style={{ fontSize: 10, color: "#7d8590", margin: 0 }}>Verdict: {a.verdict}</p>}
                {a.constitutional_authority && (
                  <p style={{ fontSize: 10, color: "#7d8590", margin: "4px 0 0 0" }}>Constitution: {a.constitutional_authority}</p>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
      {cases.length > 0 && (
        <div style={{ marginBottom: 16 }}>
          <p style={{ fontSize: 11, color: "#484f58", marginBottom: 10 }}>Relevant cases:</p>
          {cases.slice(0, 4).map((c, i) => (
            <div key={i} style={{
              background: "#0d1117", border: `1px solid ${accent}22`, borderRadius: 8, padding: "9px 12px", marginBottom: 7,
            }}>
              <p style={{ fontSize: 11, color: accent, margin: "0 0 4px 0" }}>{c.case}</p>
              <p style={{ fontSize: 10, color: "#a1a1aa", margin: 0 }}>{c.ruling_summary}</p>
            </div>
          ))}
        </div>
      )}
      {conclusion && <ConclusionBlock text={conclusion} accent={accent} label="Legal Authority Conclusion" />}
    </div>
  );
}

// ─── Reusable sub-components ────────────────────────────────────────────────
function ConclusionBlock({ text, accent, label }: { text: string; accent: string; label: string }) {
  return (
    <div style={{
      background: `${accent}0a`, border: `1px solid ${accent}30`,
      borderRadius: 8, padding: "12px 14px",
    }}>
      <p style={{ fontSize: 9, color: accent, textTransform: "uppercase", letterSpacing: "0.07em", margin: "0 0 7px 0", fontWeight: 700, fontFamily: "monospace" }}>
        {label}
      </p>
      <p style={{ fontSize: 13, color: "#c9d1d9", lineHeight: 1.6, margin: 0 }}>{text}</p>
    </div>
  );
}

function EmptyAgent({ label, status }: { label: string; status: string }) {
  const isWaiting = status === "waiting" || status === "idle";
  return (
    <div style={{ display: "flex", alignItems: "center", justifyContent: "center", height: 120, flexDirection: "column", gap: 8 }}>
      {!isWaiting && status === "running" && (
        <div style={{ width: 20, height: 20, borderRadius: "50%", border: "2px solid #21262d", borderTop: "2px solid #3b82f6" }} className="animate-spin" />
      )}
      <p style={{ fontSize: 12, color: "#484f58", margin: 0 }}>
        {isWaiting ? `${label} waiting for previous agents...` : `${label} processing...`}
      </p>
    </div>
  );
}

// ─── Section B — Inter-agent synthesis ────────────────────────────────────
function AgentSummaryPill({
  label, icon, accent, summary, status,
}: {
  label: string; icon: string; accent: string; summary: string; status: string;
}) {
  const isDone = status === "complete";
  return (
    <div style={{
      background: "#0d1117",
      border: `1px solid ${isDone ? accent + "40" : "#21262d"}`,
      borderTop: `2px solid ${isDone ? accent : "#21262d"}`,
      borderRadius: 8,
      padding: "12px 14px",
      flex: "1 1 180px",
    }}>
      <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8 }}>
        <span style={{ fontSize: 11, color: accent }}>{icon}</span>
        <span style={{ fontSize: 10, color: isDone ? accent : "#484f58", fontWeight: 700, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          {label}
        </span>
        {!isDone && (
          <span style={{ marginLeft: "auto", fontSize: 9, color: "#484f58" }}>
            {status === "running" ? "Running…" : "Waiting…"}
          </span>
        )}
      </div>
      <p style={{ fontSize: 11, color: isDone ? "#a1a1aa" : "#484f58", lineHeight: 1.5, margin: 0 }}>
        {isDone && summary ? summary : "Awaiting completion…"}
      </p>
    </div>
  );
}

// ─── Source debate cards (used in inter-agent section) ─────────────────────
function SourceDebateCard({ item }: { item: { claim?: string; topic?: string; sources?: ContestedSource[]; resolution?: string; positions?: Record<string, string> | { source: string; claim: string }[] } }) {
  const topic = item.claim ?? item.topic ?? "Disputed Claim";
  const resolution = item.resolution ?? "";

  // Normalise to ContestedSource[]
  let sources: ContestedSource[] = [];
  if (Array.isArray(item.sources) && item.sources.length > 0) {
    sources = item.sources;
  } else if (item.positions) {
    if (Array.isArray(item.positions)) {
      sources = (item.positions as { source?: string; claim?: string }[]).map((p) => ({
        name: p.source ?? "Source",
        stance: p.claim ?? "",
      }));
    } else {
      sources = Object.entries(item.positions as Record<string, string>).map(([k, v]) => ({
        name: k.replace(/_/g, " "),
        stance: v,
      }));
    }
  }

  if (sources.length === 0) return null;

  return (
    <div style={{
      background: "#0d1117", border: "1px solid #21262d",
      borderRadius: 10, overflow: "hidden", marginBottom: 14,
    }}>
      {/* Header */}
      <div style={{
        padding: "9px 14px", borderBottom: "1px solid #21262d",
        background: "linear-gradient(90deg, #eab30808 0%, transparent 60%)",
        display: "flex", alignItems: "center", gap: 8,
      }}>
        <span style={{ fontSize: 11, color: "#eab308" }}>⚡</span>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#c9d1d9" }}>{topic}</span>
      </div>

      {/* Sources grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: sources.length === 1 ? "1fr" : `repeat(${Math.min(sources.length, 3)}, 1fr)`,
        gap: 0,
      }}>
        {sources.map((s, i) => {
          const colors = ["#3b82f6", "#f97316", "#a855f7", "#22c55e", "#ef4444"];
          const c = colors[i % colors.length];
          const fav = s.url ? faviconUrl(s.url) : "";
          return (
            <div key={i} style={{
              padding: "12px 14px",
              borderRight: i < sources.length - 1 ? "1px solid #21262d" : undefined,
            }}>
              <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 7 }}>
                {fav && (
                  <img src={fav} alt="" width={12} height={12} style={{ borderRadius: 2, flexShrink: 0 }}
                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                )}
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 10, color: c, fontFamily: "monospace", fontWeight: 700, textDecoration: "none" }}
                    onClick={(e) => e.stopPropagation()}
                  >
                    {s.name} ↗
                  </a>
                ) : (
                  <span style={{ fontSize: 10, color: c, fontFamily: "monospace", fontWeight: 700 }}>{s.name}</span>
                )}
              </div>
              <p style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.55, margin: 0 }}>{s.stance}</p>
            </div>
          );
        })}
      </div>

      {/* VERITY verdict */}
      {resolution && (
        <div style={{
          padding: "11px 14px", borderTop: "1px solid #238636",
          background: "linear-gradient(90deg, #22c55e0a 0%, transparent 70%)",
        }}>
          <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
            <span style={{ color: "#22c55e", fontSize: 13, flexShrink: 0 }}>✓</span>
            <div>
              <span style={{ fontSize: 9, color: "#238636", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 700, display: "block", marginBottom: 4 }}>
                VERITY Assessment
              </span>
              <p style={{ fontSize: 12, color: "#c9d1d9", lineHeight: 1.6, margin: 0 }}>{resolution}</p>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

// Stream accent colors — keyed by lowercase prefix of the party name
const STREAM_COLORS: Record<string, string> = {
  "breaking news":      "#3b82f6",
  "historical intel":   "#a855f7",
  "official docs":      "#eab308",
  "visual intel":       "#22c55e",
  "financial markets":  "#f97316",
  "social pulse":       "#ec4899",
  "legal":              "#f59e0b",
};

function partyStreamColor(name: string, fallback: string): string {
  const lower = name.toLowerCase();
  for (const [key, color] of Object.entries(STREAM_COLORS)) {
    if (lower.startsWith(key)) return color;
  }
  return fallback;
}

function parsePartyName(name: string): { stream: string; source: string } {
  const sep = name.indexOf("·");
  if (sep !== -1) {
    return { stream: name.slice(0, sep).trim(), source: name.slice(sep + 1).trim() };
  }
  return { stream: name, source: "" };
}

function DebateClusterCard({ cluster }: { cluster: DebateCluster }) {
  const parties: DebateClusterParty[] = cluster.parties ?? [];
  const domainColors: Record<string, string> = {
    news: "#3b82f6",
    official: "#eab308",
    mixed: "#a855f7",
  };
  const dc = domainColors[cluster.domain] ?? "#71717a";
  const cols = Math.min(Math.max(parties.length, 1), 4);
  const fallbackColors = ["#3b82f6", "#f97316", "#a855f7", "#22c55e", "#ef4444", "#06b6d4"];

  return (
    <div style={{
      background: "#0d1117", border: "1px solid #21262d",
      borderRadius: 10, overflow: "hidden", marginBottom: 16,
      borderTop: `3px solid ${dc}`,
    }}>
      {/* Header */}
      <div style={{
        padding: "9px 14px", borderBottom: "1px solid #21262d",
        background: `linear-gradient(90deg, ${dc}10 0%, transparent 60%)`,
      }}>
        <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 5 }}>
          <span style={{ fontSize: 9, color: "#eab308", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.06em" }}>
            ⚡ Conflicting reports
          </span>
          {cluster.confidence && (
            <span style={{
              fontSize: 8, padding: "2px 6px", borderRadius: 4, marginLeft: "auto",
              background: "#21262d", color: "#a1a1aa", fontFamily: "monospace", textTransform: "uppercase",
            }}>
              {cluster.confidence} confidence
            </span>
          )}
        </div>
        <span style={{ fontSize: 13, fontWeight: 600, color: "#c9d1d9" }}>{cluster.topic}</span>
      </div>

      {/* Parties grid */}
      <div style={{
        display: "grid",
        gridTemplateColumns: parties.length <= 1 ? "1fr" : `repeat(${cols}, minmax(0, 1fr))`,
        gap: 0,
      }}>
        {parties.map((p, i) => {
          const { stream, source } = parsePartyName(p.name);
          const c = partyStreamColor(p.name, fallbackColors[i % fallbackColors.length]);
          const fav = p.url ? faviconUrl(p.url) : "";
          return (
            <div
              key={i}
              style={{
                padding: "12px 14px",
                borderRight: i < parties.length - 1 ? "1px solid #21262d" : undefined,
                borderLeft: `2px solid ${c}30`,
              }}
            >
              {/* Stream badge */}
              <div style={{ marginBottom: 5 }}>
                <span style={{
                  fontSize: 8, padding: "2px 6px", borderRadius: 3,
                  background: `${c}15`, border: `1px solid ${c}30`,
                  color: c, fontFamily: "monospace", textTransform: "uppercase",
                  letterSpacing: "0.05em", fontWeight: 700,
                }}>
                  {stream}
                </span>
              </div>

              {/* Source name */}
              <div style={{ display: "flex", alignItems: "center", gap: 5, marginBottom: 7 }}>
                {fav && (
                  <img src={fav} alt="" width={11} height={11} style={{ borderRadius: 2, flexShrink: 0 }}
                    onError={(e) => { (e.target as HTMLImageElement).style.display = "none"; }} />
                )}
                {source && (p.url ? (
                  <a href={p.url} target="_blank" rel="noopener noreferrer"
                    style={{ fontSize: 10, color: "#7d8590", fontWeight: 600, textDecoration: "none" }}
                  >
                    {source} ↗
                  </a>
                ) : (
                  <span style={{ fontSize: 10, color: "#7d8590", fontWeight: 600 }}>{source}</span>
                ))}
              </div>

              <p style={{ fontSize: 12, color: "#a1a1aa", lineHeight: 1.55, margin: "0 0 6px 0" }}>{p.stance}</p>
              {p.quote && (
                <p style={{ fontSize: 10, color: "#52525b", fontStyle: "italic", margin: 0, lineHeight: 1.45 }}>
                  &ldquo;{p.quote}&rdquo;
                </p>
              )}
            </div>
          );
        })}
      </div>

      {/* VERITY assessment */}
      {cluster.assessment && (
        <div style={{
          padding: "11px 14px", borderTop: "1px solid #238636",
          background: "linear-gradient(90deg, #22c55e0a 0%, transparent 70%)",
        }}>
          <span style={{ fontSize: 9, color: "#238636", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.07em", fontWeight: 700, display: "block", marginBottom: 6 }}>
            VERITY verdict — which version is more credible
          </span>
          <p style={{ fontSize: 12, color: "#c9d1d9", lineHeight: 1.6, margin: 0 }}>{cluster.assessment}</p>
        </div>
      )}

      {(cluster.evidence_gaps?.length ?? 0) > 0 && (
        <div style={{ padding: "10px 14px 12px", borderTop: "1px solid #21262d" }}>
          <span style={{ fontSize: 9, color: "#71717a", fontFamily: "monospace", textTransform: "uppercase" }}>What information would settle this conflict</span>
          <ul style={{ margin: "6px 0 0 0", paddingLeft: 18, color: "#7d8590", fontSize: 10, lineHeight: 1.5 }}>
            {cluster.evidence_gaps!.map((g, i) => (
              <li key={i}>{g}</li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

// ─── Main ──────────────────────────────────────────────────────────────────
export default function AgentDebates({ agents, results, status }: Props) {
  const [activeStream, setActiveStream] = useState<StreamKey>("breaking_news");

  const activeMeta = STREAMS.find((s) => s.key === activeStream)!;

  const renderAgentContent = () => {
    const placeholder = (label: string) => (
      <div style={{ padding: 24, color: "#484f58", fontSize: 12 }}>{label} — waiting for data…</div>
    );
    switch (activeStream) {
      case "breaking_news":    return agents.breaking_news    ? <BreakingNewsView agent={agents.breaking_news} accent={activeMeta.accent} />                            : placeholder("Breaking News");
      case "historical":       return agents.historical       ? <HistoricalView agent={agents.historical as AgentStatus} accent={activeMeta.accent} />                  : placeholder("Historical Intel");
      case "official_docs":    return agents.official_docs    ? <OfficialDocsView agent={agents.official_docs as AgentStatus} accent={activeMeta.accent} />             : placeholder("Official Docs");
      case "visual_intel":     return agents.visual_intel     ? <VisualIntelView agent={agents.visual_intel as AgentStatus} accent={activeMeta.accent} />               : placeholder("Visual Intel");
      case "financial_market": return agents.financial_market ? <FinancialMarketsView agent={agents.financial_market as AgentStatus} accent={activeMeta.accent} />      : placeholder("Financial Markets");
      case "social_pulse":     return agents.social_pulse     ? <SocialPulseView agent={agents.social_pulse as AgentStatus} accent={activeMeta.accent} />               : placeholder("Social Pulse");
      case "legal":            return agents.legal            ? <LegalView agent={agents.legal as AgentStatus} accent={activeMeta.accent} />                            : placeholder("Legal");
    }
  };

  const allDone = status === "complete";
  const execSummary = results?.executive_summary ?? "";
  const debateClusters = results?.debate_clusters ?? [];

  return (
    <div style={{ height: "100%", overflow: "hidden", display: "flex", flexDirection: "column" }}>

      {/* ── Section A: Per-agent source exploration ─────────────────── */}
      <div style={{ borderBottom: "1px solid #21262d", flexShrink: 0 }}>
        {/* Section header */}
        <div style={{
          padding: "10px 16px 0",
          display: "flex", alignItems: "center", gap: 8,
        }}>
          <span style={{ fontSize: 9, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em" }}>
            Agent Intelligence Streams
          </span>
          <div style={{ flex: 1, height: 1, background: "#21262d" }} />
        </div>

        {/* Stream selector tabs */}
        <div style={{ display: "flex", padding: "6px 16px 0", gap: 2 }}>
          {STREAMS.map((s) => {
            const agent = agents[s.key] as AgentStatus | undefined;
            const isDone = agent?.status === "complete";
            const isActive = activeStream === s.key;
            return (
              <button
                key={s.key}
                onClick={() => setActiveStream(s.key)}
                style={{
                  padding: "5px 10px",
                  borderRadius: "6px 6px 0 0",
                  border: "1px solid transparent",
                  borderBottom: isActive ? `2px solid ${s.accent}` : "none",
                  background: isActive ? `${s.accent}10` : "transparent",
                  cursor: "pointer",
                  fontSize: 10,
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? s.accent : isDone ? "#7d8590" : "#484f58",
                  transition: "all 0.15s",
                  display: "flex", alignItems: "center", gap: 4,
                }}
              >
                <span>{s.icon}</span>
                <span>{s.label}</span>
                {isDone && (
                  <span style={{ width: 5, height: 5, borderRadius: "50%", background: "#22c55e", flexShrink: 0 }} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Scrollable body */}
      <div style={{ flex: 1, overflow: "hidden", display: "flex", flexDirection: "column" }}>
        <div style={{ flex: 1, overflowY: "auto", padding: "14px 16px" }}>

          {/* Active agent content */}
          {renderAgentContent()}

          {/* ── Section B: Inter-agent debate + final verdict ──────── */}
          <div style={{ marginTop: 28 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 16 }}>
              <span style={{ fontSize: 9, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                Where sources contradict each other
              </span>
              <div style={{ flex: 1, height: 1, background: "#21262d" }} />
            </div>

            {/* Multi-party debate clusters (A vs B vs C …) */}
            {allDone && debateClusters.length > 0 && (
              <div style={{ marginBottom: 20 }}>
                <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 6 }}>
                  <span style={{ fontSize: 10, color: "#eab308" }}>⚡</span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: "#eab308", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                    Source Conflicts
                  </span>
                  <div style={{ flex: 1, height: 1, background: "#eab30830" }} />
                </div>
                <p style={{ fontSize: 11, color: "#52525b", margin: "0 0 14px 0", lineHeight: 1.5 }}>
                  VERITY detected topics where different news outlets, governments, or intelligence streams report conflicting facts.
                  Each card below shows what each source claims and how the claims contradict each other.
                </p>
                {debateClusters.map((cl, i) => (
                  <DebateClusterCard key={i} cluster={cl} />
                ))}
              </div>
            )}

            {/* VERITY Final Verdict */}
            {allDone && execSummary && (
              <div style={{
                background: "linear-gradient(135deg, #0d1117 0%, #0a0f1a 100%)",
                border: "1px solid #3b82f640",
                borderTop: "3px solid #3b82f6",
                borderRadius: 10,
                padding: "18px 20px",
              }}>
                <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 4 }}>
                  <div style={{ width: 7, height: 7, borderRadius: "50%", background: "#3b82f6", flexShrink: 0 }} />
                  <span style={{ fontSize: 11, fontWeight: 700, color: "#3b82f6", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em" }}>
                    Best Available Truth
                  </span>
                </div>
                <p style={{ fontSize: 10, color: "#484f58", margin: "0 0 14px 22px" }}>
                  Synthesized across all intelligence streams · weighted by source credibility
                </p>
                <p style={{ fontSize: 14, color: "#c9d1d9", lineHeight: 1.7, margin: 0 }}>{execSummary}</p>
              </div>
            )}

            {!allDone && (
              <div style={{
                background: "#0d1117", border: "1px dashed #21262d",
                borderRadius: 10, padding: "20px 18px",
                display: "flex", alignItems: "center", justifyContent: "center",
                flexDirection: "column", gap: 8,
              }}>
                <div style={{ width: 24, height: 24, borderRadius: "50%", border: "2px solid #21262d", borderTop: "2px solid #3b82f6" }} className="animate-spin" />
                <p style={{ fontSize: 11, color: "#52525b", margin: 0 }}>
                  Awaiting all agent streams to complete final synthesis…
                </p>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
