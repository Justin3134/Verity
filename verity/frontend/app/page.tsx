"use client";

import { useState, useCallback } from "react";
import { useRouter } from "next/navigation";

const EXAMPLE_QUERIES = [
  "Trump Iran policy — 2018 vs 2025",
  "Ukraine Russia war frontline update",
  "Gaza ceasefire negotiations",
  "Taiwan China military tensions",
  "Trump NATO Article 5 2025",
  "Biden Afghanistan withdrawal",
];

export default function HomePage() {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit = Boolean(query.trim());

  const handleSubmit = useCallback(async () => {
    const q = query.trim();
    if (!q) {
      setError("Enter a topic to analyze.");
      return;
    }
    setError(null);
    setIsAnalyzing(true);

    try {
      const formData = new FormData();
      formData.append("query", q);

      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL ?? "";
      const res = await fetch(`${backendUrl}/analyze`, {
        method: "POST",
        body: formData,
      });

      if (!res.ok) throw new Error(`Server error: ${res.status}`);
      const data = await res.json();
      router.push(`/analysis/${data.job_id}`);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : String(err));
      setIsAnalyzing(false);
    }
  }, [query, router]);

  const onKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div
      style={{
        minHeight: "100vh",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: "32px 20px 48px",
        background: "var(--bg-base)",
      }}
    >
      <div style={{ width: "100%", maxWidth: 520 }}>
        <h1
          style={{
            margin: "0 0 20px",
            fontSize: 22,
            fontWeight: 600,
            letterSpacing: "0.06em",
            color: "var(--text-primary)",
            textAlign: "center",
            fontFamily: "inherit",
          }}
        >
          VERITY
        </h1>

        <div
          style={{
            background: "var(--bg-card)",
            border: "1px solid var(--border)",
            borderRadius: 12,
            overflow: "hidden",
          }}
        >
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={onKeyDown}
            placeholder="Ask anything or describe what to analyze…"
            rows={5}
            disabled={isAnalyzing}
            style={{
              width: "100%",
              background: "transparent",
              border: "none",
              outline: "none",
              resize: "vertical",
              minHeight: 120,
              padding: "16px 18px",
              fontSize: 15,
              color: "var(--text-primary)",
              lineHeight: 1.55,
              fontFamily: "inherit",
            }}
          />

          <div
            style={{
              borderTop: "1px solid var(--border)",
              padding: "12px 16px",
              display: "flex",
              alignItems: "center",
              justifyContent: "space-between",
              gap: 12,
            }}
          >
            <span style={{ fontSize: 11, color: "var(--text-muted)" }}>⌘↵ to run</span>
            <button
              type="button"
              onClick={handleSubmit}
              disabled={isAnalyzing || !canSubmit}
              style={{
                padding: "8px 20px",
                background: isAnalyzing || !canSubmit ? "var(--bg-elevated)" : "var(--stream-blue)",
                border: "none",
                borderRadius: 8,
                cursor: isAnalyzing || !canSubmit ? "not-allowed" : "pointer",
                fontSize: 13,
                fontWeight: 600,
                color: isAnalyzing || !canSubmit ? "var(--text-muted)" : "#fff",
                fontFamily: "inherit",
              }}
            >
              {isAnalyzing ? "Starting…" : "Analyze"}
            </button>
          </div>
        </div>

        {error && (
          <div
            style={{
              marginTop: 12,
              padding: "10px 14px",
              background: "color-mix(in srgb, var(--stream-red) 10%, transparent)",
              border: "1px solid color-mix(in srgb, var(--stream-red) 25%, transparent)",
              borderRadius: 8,
              fontSize: 13,
              color: "var(--stream-red)",
            }}
          >
            {error}
          </div>
        )}

        <div style={{ marginTop: 28 }}>
          <p
            style={{
              margin: "0 0 10px",
              textAlign: "center",
              fontSize: 11,
              color: "var(--text-muted)",
              letterSpacing: "0.06em",
            }}
          >
            Examples
          </p>
          <div style={{ display: "flex", flexWrap: "wrap", gap: 8, justifyContent: "center" }}>
            {EXAMPLE_QUERIES.map((q) => (
              <button
                key={q}
                type="button"
                onClick={() => {
                  setQuery(q);
                  setError(null);
                }}
                disabled={isAnalyzing}
                style={{
                  padding: "6px 14px",
                  background: "transparent",
                  border: "1px solid var(--border)",
                  borderRadius: 999,
                  cursor: isAnalyzing ? "not-allowed" : "pointer",
                  fontSize: 12,
                  color: "var(--text-secondary)",
                  fontFamily: "inherit",
                }}
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
