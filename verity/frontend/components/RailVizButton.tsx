"use client";

import { useState, useRef, useEffect } from "react";

export default function RailVizButton() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handler(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    }
    if (open) document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [open]);

  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button
        onClick={() => setOpen((v) => !v)}
        title="Railtracks Observability"
        style={{
          display: "flex",
          alignItems: "center",
          gap: 5,
          padding: "3px 9px",
          background: open ? "rgba(168,85,247,0.14)" : "transparent",
          border: `1px solid ${open ? "rgba(168,85,247,0.4)" : "rgba(168,85,247,0.22)"}`,
          borderRadius: 6,
          color: "#a855f7",
          fontSize: 11,
          fontFamily: "monospace",
          cursor: "pointer",
          letterSpacing: "0.04em",
          transition: "all 0.15s",
        }}
      >
        <span style={{ fontSize: 10 }}>🚂</span>
        Railtracks
      </button>

      {open && (
        <div style={{
          position: "absolute",
          top: "calc(100% + 8px)",
          right: 0,
          width: 300,
          background: "#161618",
          border: "1px solid #2a2a2e",
          borderTop: "2px solid #a855f7",
          borderRadius: 10,
          boxShadow: "0 8px 32px rgba(0,0,0,0.6)",
          zIndex: 999,
          overflow: "hidden",
        }}>
          <div style={{ padding: "10px 14px", borderBottom: "1px solid #2a2a2e" }}>
            <div style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 4 }}>
              <span style={{ fontSize: 11 }}>🚂</span>
              <span style={{ fontSize: 11, fontWeight: 600, color: "#f4f4f5", letterSpacing: "0.04em" }}>
                Railtracks Observability
              </span>
            </div>
            <p style={{ fontSize: 10, color: "#71717a", margin: 0, lineHeight: 1.5 }}>
              Dive deep into agent runs — token usage, step-by-step traces, and more.
            </p>
          </div>

          <div style={{ padding: "10px 14px" }}>
            <div style={{ fontSize: 9, color: "#52525b", fontFamily: "monospace", textTransform: "uppercase", letterSpacing: "0.08em", marginBottom: 8 }}>
              Setup
            </div>

            {[
              { label: "Install CLI", cmd: "pip install 'railtracks[cli]'" },
              { label: "Initialize", cmd: "railtracks init" },
              { label: "Launch UI", cmd: "railtracks viz" },
            ].map(({ label, cmd }) => (
              <div key={cmd} style={{ marginBottom: 8 }}>
                <div style={{ fontSize: 9, color: "#71717a", marginBottom: 3 }}>{label}</div>
                <code style={{
                  display: "block",
                  fontSize: 10,
                  color: "#a855f7",
                  background: "rgba(168,85,247,0.08)",
                  border: "1px solid rgba(168,85,247,0.18)",
                  borderRadius: 5,
                  padding: "5px 8px",
                  fontFamily: "monospace",
                  userSelect: "all",
                }}>
                  {cmd}
                </code>
              </div>
            ))}

            <a
              href="http://localhost:3030"
              target="_blank"
              rel="noopener noreferrer"
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                gap: 5,
                marginTop: 10,
                padding: "6px 12px",
                background: "rgba(168,85,247,0.12)",
                border: "1px solid rgba(168,85,247,0.3)",
                borderRadius: 6,
                color: "#a855f7",
                fontSize: 11,
                fontFamily: "monospace",
                textDecoration: "none",
                cursor: "pointer",
                transition: "background 0.15s",
              }}
            >
              Open Railtracks Viz →
            </a>

            <div style={{ marginTop: 8, fontSize: 9, color: "#3f3f46", textAlign: "center", fontFamily: "monospace" }}>
              Runs locally at http://localhost:3030
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
