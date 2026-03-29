import type { AgentStatus } from "@/app/analysis/[jobId]/page";

export function pickText(item: unknown, keys: string[]): string {
  if (typeof item === "string") return item.trim();
  if (!item || typeof item !== "object") return "";
  const o = item as Record<string, unknown>;
  for (const k of keys) {
    const v = o[k];
    if (typeof v === "string" && v.trim()) return v.trim();
  }
  return "";
}

export type AgentKey =
  | "breaking_news"
  | "historical"
  | "official_docs"
  | "visual_intel"
  | "financial_market"
  | "social_pulse"
  | "legal"
  | "synthesizer";

export function getFactsForAgent(
  agent: AgentStatus,
  key: AgentKey,
  maxItems: number = 4,
  maxLen: number = 115
): string[] {
  const out: string[] = [];

  if (key === "breaking_news") {
    const claims = (agent as { claims?: unknown[] }).claims;
    for (const c of claims ?? []) {
      if (out.length >= maxItems) break;
      const t = pickText(c, ["claim", "text"]);
      if (t) out.push(truncate(t, maxLen));
    }
  } else if (key === "visual_intel") {
    const obs = (agent as { observations?: unknown[] }).observations;
    for (const o of obs ?? []) {
      if (out.length >= maxItems) break;
      const t = pickText(o, ["observation", "text"]);
      if (t) out.push(truncate(t, maxLen));
    }
  } else if (key === "financial_market") {
    const findings = (agent as { findings?: unknown[] }).findings;
    for (const f of findings ?? []) {
      if (out.length >= maxItems) break;
      const t = pickText(f as Record<string, unknown>, ["signal", "observation", "text"]);
      if (t) out.push(truncate(t, maxLen));
    }
    // Fall back to market_data strings
    if (out.length === 0) {
      const md = (agent as { market_data?: string[] }).market_data;
      for (const s of md ?? []) {
        if (out.length >= maxItems) break;
        if (s) out.push(truncate(s, maxLen));
      }
    }
  } else if (key === "social_pulse") {
    const signals = (agent as { signals?: unknown[] }).signals;
    for (const s of signals ?? []) {
      if (out.length >= maxItems) break;
      const t = pickText(s as Record<string, unknown>, ["signal", "report", "text"]);
      if (t) out.push(truncate(t, maxLen));
    }
  } else if (key === "legal") {
    const actions = (agent as { actions?: unknown[] }).actions;
    for (const a of actions ?? []) {
      if (out.length >= maxItems) break;
      const rec = a as Record<string, unknown>;
      const verdict = typeof rec["verdict"] === "string" ? rec["verdict"].trim() : "";
      const action = typeof rec["action"] === "string" ? rec["action"].trim() : "";
      const auth = typeof rec["constitutional_authority"] === "string" ? rec["constitutional_authority"] : "";
      if (verdict) out.push(truncate(`[${auth}] ${verdict}`, maxLen));
      else if (action) out.push(truncate(action, maxLen));
    }
  } else if (key === "historical" || key === "official_docs") {
    const findings = (agent as { findings?: unknown[] }).findings;
    for (const f of findings ?? []) {
      if (out.length >= maxItems) break;
      const t =
        typeof f === "string"
          ? f.trim()
          : pickText(f, ["event", "official_statement", "finding", "statement", "text"]);
      if (t) out.push(truncate(t, maxLen));
    }
  } else {
    const a = agent.action?.trim();
    if (a) out.push(truncate(a, maxLen));
  }

  return out;
}

function truncate(s: string, max: number): string {
  const t = s.trim();
  return t.length > max ? `${t.slice(0, max)}…` : t;
}

export function countAgentItems(agent: AgentStatus, key: AgentKey): number | null {
  if (key === "breaking_news") return (agent as { claims?: unknown[] }).claims?.length ?? null;
  if (key === "visual_intel") return (agent as { observations?: unknown[] }).observations?.length ?? null;
  if (key === "financial_market") return (agent as { findings?: unknown[] }).findings?.length ?? null;
  if (key === "historical" || key === "official_docs") return (agent as { findings?: unknown[] }).findings?.length ?? null;
  if (key === "social_pulse") return (agent as { signals?: unknown[] }).signals?.length ?? null;
  if (key === "legal") return (agent as { actions?: unknown[] }).actions?.length ?? null;
  return null;
}

export function getAgentConclusion(agent: AgentStatus): string | null {
  if (agent.status !== "complete") return null;
  if (typeof agent.result === "string" && agent.result.trim()) {
    return agent.result.trim();
  }
  if (agent.result && typeof agent.result === "object") {
    const r = agent.result as Record<string, unknown>;
    for (const k of ["executive_summary", "summary"]) {
      if (typeof r[k] === "string" && (r[k] as string).trim()) return (r[k] as string).trim();
    }
  }
  return null;
}

export function getAgentLinks(agent: AgentStatus, key: AgentKey): { title: string; url: string }[] {
  if (key === "breaking_news") {
    const articles = (agent as { articles?: { title: string; url: string }[] }).articles ?? [];
    return articles.filter((a) => a.url).slice(0, 4);
  }
  if (key === "official_docs") {
    const docs = (agent as { documents?: { title: string; url: string }[] }).documents ?? [];
    return docs.filter((d) => d.url).slice(0, 4);
  }
  if (key === "social_pulse") {
    const posts = (agent as { posts?: { title: string; url: string; platform?: string }[] }).posts ?? [];
    return posts.filter((p) => p.url).slice(0, 4).map((p) => ({
      title: p.title || p.platform || "Social post",
      url: p.url,
    }));
  }
  return [];
}
