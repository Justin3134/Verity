"use client";

import { AnalysisResults } from "@/app/analysis/[jobId]/page";
import type { SourceArticle } from "@/app/analysis/[jobId]/page";

interface Props {
  results: AnalysisResults | null;
  status: string;
  query: string;
}

// ─── Loading skeleton ────────────────────────────────────────────────────────
function Skeleton() {
  return (
    <div style={{ padding: 20, display: "flex", flexDirection: "column", gap: 12 }}>
      {[1, 2, 3].map((k) => (
        <div key={k} style={{ background: "#0d1117", border: "1px solid #161b22", borderRadius: 8, padding: 16 }}>
          <div style={{ height: 8, background: "#161b22", borderRadius: 4, width: "30%", marginBottom: 12 }} className="pulse-glow" />
          <div style={{ height: 10, background: "#161b22", borderRadius: 4, width: "85%", marginBottom: 6 }} className="pulse-glow" />
          <div style={{ height: 10, background: "#161b22", borderRadius: 4, width: "60%" }} className="pulse-glow" />
        </div>
      ))}
      <p style={{ textAlign: "center", fontSize: 11, color: "#30363d", fontFamily: "monospace" }}>
        Agents processing — intelligence report generates on completion
      </p>
    </div>
  );
}

// ─── Main ────────────────────────────────────────────────────────────────────
export default function ResultsPanel({ results, status }: Props) {
  if (status === "starting" || status === "running") return <Skeleton />;

  if (status === "error") {
    return (
      <div style={{ padding: 20 }}>
        <div style={{ background: "#0d1117", border: "1px solid #da3633", borderRadius: 8, padding: 20, textAlign: "center" }}>
          <p style={{ color: "#f85149", fontSize: 13, fontWeight: 600, marginBottom: 6 }}>Analysis failed</p>
          <p style={{ color: "#7d8590", fontSize: 12 }}>Check backend logs for details</p>
        </div>
      </div>
    );
  }

  if (!results) return null;

  const prob       = results.escalation_assessment?.probability ?? "unknown";
  const riskColor  = { low: "#22c55e", medium: "#eab308", high: "#ef4444", critical: "#ef4444", unknown: "#71717a" }[prob] ?? "#71717a";
  const timeline   = results.escalation_assessment?.timeline ?? "";
  const triggers   = results.escalation_assessment?.key_triggers ?? results.escalation_assessment?.indicators ?? [];
  const histMatch  = results.escalation_assessment?.historical_comparison ?? results.escalation_assessment?.historical_match ?? "";

  return (
    <div style={{ padding: "16px 20px 28px", display: "flex", flexDirection: "column", gap: 14 }}>

      {/* ── 1. Executive Summary ─────────────────────────────────── */}
      {results.executive_summary && (
        <div style={{
          background: "#0d1117",
          border: "1px solid #1f6feb",
          borderTop: "3px solid #3b82f6",
          borderRadius: 10,
          padding: "14px 18px",
        }}>
          <p style={{
            fontSize: 9, color: "#3b82f6", fontFamily: "monospace",
            textTransform: "uppercase", letterSpacing: "0.1em",
            marginBottom: 10, fontWeight: 700,
          }}>
            Intelligence Briefing
          </p>
          <p style={{ fontSize: 14, color: "#c9d1d9", lineHeight: 1.7, margin: 0 }}>
            {results.executive_summary}
          </p>
        </div>
      )}

      {/* ── 2. Escalation Risk ────────────────────────────────────── */}
      {results.escalation_assessment && (
        <div style={{
          background: "#0d1117",
          border: `1px solid ${riskColor}30`,
          borderLeft: `3px solid ${riskColor}`,
          borderRadius: 10,
          padding: "14px 18px",
        }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", marginBottom: histMatch || timeline || triggers.length > 0 ? 12 : 0 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <p style={{ fontSize: 9, color: riskColor, fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em", fontWeight: 700, margin: 0 }}>
                Escalation Assessment
              </p>
            </div>
            <span style={{
              fontSize: 12, fontWeight: 700, textTransform: "uppercase",
              padding: "3px 12px", borderRadius: 5,
              background: `${riskColor}15`, border: `1px solid ${riskColor}40`,
              color: riskColor, fontFamily: "monospace",
            }}>
              {prob}
            </span>
          </div>

          {histMatch && (
            <p style={{ fontSize: 12, color: "#7d8590", marginBottom: timeline || triggers.length > 0 ? 8 : 0, lineHeight: 1.5 }}>
              {histMatch}
            </p>
          )}

          {timeline && (
            <p style={{ fontSize: 11, color: "#484f58", marginBottom: triggers.length > 0 ? 8 : 0 }}>
              Timeline: <span style={{ color: "#7d8590" }}>{timeline}</span>
            </p>
          )}

          {triggers.length > 0 && (
            <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
              {triggers.map((t, i) => (
                <div key={i} style={{ display: "flex", gap: 8, fontSize: 11, color: "#7d8590" }}>
                  <span style={{ color: "#30363d", flexShrink: 0 }}>—</span>
                  <span>{t}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {/* ── 3. Watch Signals ──────────────────────────────────────── */}
      {(results.recommended_watch_signals?.length ?? 0) > 0 && (
        <div style={{
          background: "#0d1117", border: "1px solid #21262d", borderRadius: 10, padding: "14px 18px",
        }}>
          <p style={{ fontSize: 9, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, fontWeight: 700 }}>
            Monitor Next 24–48h
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {results.recommended_watch_signals!.map((item, i) => (
              <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, color: "#7d8590" }}>
                <span style={{ color: "#3b82f6", flexShrink: 0 }}>→</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* ── 5. Sources & Citations ────────────────────────────────── */}
      {(results.source_articles?.length ?? 0) > 0 && (
        <div style={{
          background: "#0d1117", border: "1px solid #21262d", borderRadius: 10, padding: "14px 18px",
        }}>
          <p style={{ fontSize: 9, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 12, fontWeight: 700 }}>
            Sources & Citations
          </p>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 6 }}>
            {results.source_articles!.filter((a: SourceArticle) => a.url).map((article: SourceArticle, i: number) => {
              const sourceName =
                typeof article.source === "object" && article.source !== null
                  ? (article.source as { name: string }).name
                  : (article.source as string) || "";
              let host = "";
              try { host = new URL(article.url).hostname.replace("www.", ""); } catch { host = article.url; }
              const fav = `https://www.google.com/s2/favicons?domain=${host}&sz=16`;
              return (
                <a
                  key={i}
                  href={article.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  style={{
                    background: "#161b22", border: "1px solid #21262d", borderRadius: 7,
                    padding: "8px 10px", textDecoration: "none", display: "flex",
                    alignItems: "flex-start", gap: 7, transition: "border-color 0.15s",
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.borderColor = "#30363d")}
                  onMouseLeave={(e) => (e.currentTarget.style.borderColor = "#21262d")}
                >
                  <img src={fav} alt="" width={12} height={12} style={{ borderRadius: 2, marginTop: 2, flexShrink: 0 }}
                    onError={(e) => { (e.currentTarget as HTMLImageElement).style.display = "none"; }} />
                  <div style={{ minWidth: 0 }}>
                    <p style={{
                      fontSize: 11, color: "#58a6ff", margin: "0 0 2px 0",
                      lineHeight: 1.4, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap",
                    }}>
                      {article.title || host}
                    </p>
                    <p style={{ fontSize: 9, color: "#484f58", margin: 0 }}>
                      {sourceName || host}
                    </p>
                  </div>
                  <span style={{ fontSize: 9, color: "#484f58", marginLeft: "auto", flexShrink: 0, marginTop: 2 }}>↗</span>
                </a>
              );
            })}
          </div>
        </div>
      )}

      {/* ── 6. Key Unknowns ────────────────────────────────────────── */}
      {results.key_unknowns?.length > 0 && (
        <div style={{
          background: "#0d1117", border: "1px solid #21262d", borderRadius: 10, padding: "14px 18px",
        }}>
          <p style={{ fontSize: 9, color: "#484f58", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, fontWeight: 700 }}>
            Critical Unknowns
          </p>
          <div style={{ display: "flex", flexDirection: "column", gap: 5 }}>
            {results.key_unknowns.map((item, i) => (
              <div key={i} style={{ display: "flex", gap: 8, fontSize: 12, color: "#7d8590" }}>
                <span style={{ color: "#484f58", flexShrink: 0 }}>?</span>
                <span>{item}</span>
              </div>
            ))}
          </div>
        </div>
      )}

    </div>
  );
}
