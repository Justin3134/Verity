"use client";

export default function RailVizButton() {
  return (
    <a
      href="http://localhost:3030"
      target="_blank"
      rel="noopener noreferrer"
      title="Railtracks Observability"
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: 5,
        padding: "3px 9px",
        background: "transparent",
        border: "1px solid rgba(168,85,247,0.22)",
        borderRadius: 6,
        color: "#a855f7",
        fontSize: 11,
        fontFamily: "monospace",
        cursor: "pointer",
        letterSpacing: "0.04em",
        textDecoration: "none",
        transition: "all 0.15s",
      }}
    >
      <span style={{ fontSize: 10 }}>🚂</span>
      Railtracks
    </a>
  );
}
