"use client";

import type { AnalysisResults } from "@/app/analysis/[jobId]/page";

interface Props {
  results: AnalysisResults | null;
  status: string;
}

export default function TruthMap({ results, status }: Props) {
  if (!results) {
    if (status === "running" || status === "starting") {
      return (
        <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 14 }}>
          <div style={{ width: 36, height: 36, borderRadius: "50%", border: "2px solid #3b82f620", borderTop: "2px solid #3b82f6" }} className="animate-spin" />
          <p style={{ fontSize: 12, color: "#52525b", fontFamily: "monospace" }}>Agents processing — analysis available after synthesis</p>
        </div>
      );
    }
    return (
      <div style={{ display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center", height: 300, gap: 8 }}>
        <p style={{ fontSize: 13, color: "#52525b" }}>No analysis results yet.</p>
      </div>
    );
  }

  return (
    <div style={{ padding: "16px 16px 24px", overflowY: "auto", height: "100%" }}>
      {results.executive_summary && (
        <div style={{
          background: "#0d1117",
          border: "1px solid #1f6feb",
          borderTop: "3px solid #3b82f6",
          borderRadius: 10,
          padding: "14px 18px",
        }}>
          <p style={{ fontSize: 9, color: "#3b82f6", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.1em", marginBottom: 10, fontWeight: 700 }}>
            Intelligence Briefing
          </p>
          <p style={{ fontSize: 14, color: "#c9d1d9", lineHeight: 1.7, margin: 0 }}>
            {results.executive_summary}
          </p>
        </div>
      )}
    </div>
  );
}
