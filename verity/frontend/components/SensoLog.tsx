"use client";

import { useEffect, useRef } from "react";

interface Props {
  entries: string[];
}

export default function SensoLog({ entries }: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [entries.length]);

  if (entries.length === 0) {
    return (
      <div style={{ padding: "10px 16px", fontSize: 11, color: "var(--border-bright)", fontFamily: "monospace" }}>
        Senso lookups appear here as the document and synthesis agents query the knowledge base.
      </div>
    );
  }

  return (
    <div style={{ padding: "8px 16px 12px", overflowY: "auto", height: "100%" }}>
      <div style={{ display: "flex", flexDirection: "column", gap: 4 }}>
        {entries.map((entry, i) => {
          let color = "var(--text-secondary)";
          if (entry.includes("credibility") || entry.includes("score")) color = "var(--stream-yellow)";
          else if (entry.includes("pattern") || entry.includes("historical")) color = "var(--stream-purple)";
          else if (entry.includes("error") || entry.includes("failed")) color = "var(--stream-red)";
          else if (entry.includes("returned") || entry.includes("Retrieved") || entry.includes("Found"))
            color = "var(--stream-green)";
          return (
            <div key={i} style={{ display: "flex", alignItems: "flex-start", gap: 8 }}>
              <span
                style={{
                  color: "var(--text-muted)",
                  fontSize: 10,
                  fontFamily: "monospace",
                  flexShrink: 0,
                  marginTop: 1,
                }}
              >
                ›
              </span>
              <span style={{ fontSize: 11, color, fontFamily: "monospace", lineHeight: 1.5 }}>{entry}</span>
            </div>
          );
        })}
        <div ref={bottomRef} />
      </div>
    </div>
  );
}
