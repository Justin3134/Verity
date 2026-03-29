"use client";

import { useEffect, useRef } from "react";
import { useChat } from "@ai-sdk/react";
import type { UIMessage } from "ai";
import {
  AssistantRuntimeProvider,
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  ActionBarPrimitive,
  BranchPickerPrimitive,
} from "@assistant-ui/react";
import { useAISDKRuntime, AssistantChatTransport } from "@assistant-ui/react-ai-sdk";
import type { JobStatus } from "@/app/analysis/[jobId]/page";

interface Props {
  jobId: string;
  job: JobStatus;
}

const SUGGESTED_QUESTIONS = [
  "Which source is most reliable?",
  "What happened last time this pattern occurred?",
  "What are the most likely outcomes?",
  "What is the strongest contradicting evidence?",
  "Summarize what is known vs. unknown",
];

function makeTextMessage(id: string, role: "user" | "assistant", text: string): UIMessage {
  return {
    id,
    role,
    parts: [{ type: "text", text }],
  };
}

export default function ChatPanel({ jobId, job }: Props) {
  const narrated = useRef(false);

  const greetingText = job.query
    ? `Working on **"${job.query}"**.\n\nUse the **graph** for the flow, the **Agent outputs** row for live facts, and **Intelligence report** when done. Ask me anything here.`
    : null;

  const chat = useChat({
    transport: new AssistantChatTransport({ api: "/api/chat", body: { jobId } }),
    messages: greetingText
      ? [makeTextMessage("greeting", "assistant", greetingText)]
      : [],
  });

  const runtime = useAISDKRuntime(chat);

  // Auto-narrate a summary once analysis completes
  useEffect(() => {
    const userMsgs = chat.messages.filter((m) => m.role === "user");
    if (job.status === "complete" && job.results && !narrated.current && userMsgs.length === 0) {
      narrated.current = true;
      const { verified, contested, hidden, propaganda, executive_summary } = job.results;
      const summary = [
        "**Analysis complete.**",
        "",
        executive_summary,
        "",
        "**Summary:**",
        `- ${verified?.length || 0} verified findings`,
        `- ${contested?.length || 0} contested claims`,
        `- ${hidden?.length || 0} unreported findings`,
        `- ${propaganda?.length || 0} propaganda signals`,
        "",
        "What would you like to examine further?",
      ].join("\n");
      chat.setMessages((prev) => [
        ...prev,
        makeTextMessage("complete-" + Date.now(), "assistant", summary),
      ]);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [job.status, job.results]);

  const userMessageCount = chat.messages.filter((m) => m.role === "user").length;
  const isStreaming = chat.status === "streaming" || chat.status === "submitted";

  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          height: "100%",
          minHeight: 0,
          overflow: "hidden",
        }}
      >
        {/* ── Header ── */}
        <div
          style={{
            padding: "0 14px",
            height: 44,
            borderBottom: "1px solid var(--border)",
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexShrink: 0,
            background: "color-mix(in srgb, var(--bg-base) 55%, var(--bg-card))",
          }}
        >
          <div style={{ display: "flex", flexDirection: "column", gap: 2 }}>
            <span style={{ fontSize: 12, fontWeight: 600, color: "var(--text-primary)" }}>
              Chat
            </span>
            <span style={{ fontSize: 10, color: "var(--text-muted)" }}>Ask about this run</span>
          </div>
          <span style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "monospace" }}>
            llama3.3-70b
          </span>
        </div>

        {/* ── Thread ── */}
        <ThreadPrimitive.Root
          style={{
            flex: 1,
            minHeight: 0,
            display: "flex",
            flexDirection: "column",
            overflow: "hidden",
          }}
        >
          {/* Messages viewport — assistant-ui handles auto-scroll */}
          <ThreadPrimitive.Viewport
            style={{
              flex: 1,
              minHeight: 0,
              overflowY: "auto",
              overflowX: "hidden",
              padding: "12px 14px 14px",
              display: "flex",
              flexDirection: "column",
              gap: 10,
            }}
          >
            <ThreadPrimitive.Messages
              components={{
                UserMessage: UserMessage,
                AssistantMessage: AssistantMessage,
              }}
            />
          </ThreadPrimitive.Viewport>

          {/* ── Suggested questions — shown until the user sends their first message ── */}
          {userMessageCount === 0 && !isStreaming && (
            <div
              style={{
                padding: "8px 14px 10px",
                borderTop: "1px solid var(--border)",
                flexShrink: 0,
                background: "color-mix(in srgb, var(--bg-base) 40%, var(--bg-card))",
                maxHeight: 140,
                overflowY: "auto",
              }}
            >
              <p style={{ fontSize: 10, color: "var(--text-muted)", marginBottom: 6 }}>
                Suggested
              </p>
              <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
                {SUGGESTED_QUESTIONS.map((q) => (
                  <button
                    key={q}
                    type="button"
                    onClick={() => chat.sendMessage({ text: q })}
                    style={{
                      fontSize: 11,
                      padding: "6px 10px",
                      textAlign: "left",
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      borderRadius: 8,
                      cursor: "pointer",
                      color: "var(--text-secondary)",
                      fontFamily: "inherit",
                      lineHeight: 1.35,
                    }}
                  >
                    {q}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* ── Composer ── */}
          <ComposerPrimitive.Root
            style={{
              flexShrink: 0,
              borderTop: "1px solid var(--border)",
              padding: "10px 12px 12px",
              background: "color-mix(in srgb, var(--bg-base) 55%, var(--bg-card))",
            }}
          >
            <div
              style={{
                display: "flex",
                alignItems: "flex-end",
                gap: 8,
                background: "var(--bg-card)",
                border: "1px solid var(--border)",
                borderRadius: 10,
                padding: "4px 4px 4px 10px",
              }}
            >
              <ComposerPrimitive.Input
                placeholder="Message…"
                rows={2}
                style={{
                  flex: 1,
                  background: "transparent",
                  border: "none",
                  outline: "none",
                  resize: "none",
                  padding: "8px 4px 8px 0",
                  fontSize: 13,
                  color: "var(--text-primary)",
                  fontFamily: "inherit",
                  lineHeight: 1.45,
                  overflowY: "auto",
                }}
              />

              {/* Send / Stop */}
              {isStreaming ? (
                <button
                  type="button"
                  onClick={() => chat.stop()}
                  title="Stop generating"
                  style={{
                    flexShrink: 0,
                    marginBottom: 4,
                    marginRight: 4,
                    padding: "8px 12px",
                    background: "var(--bg-elevated)",
                    border: "1px solid var(--border)",
                    borderRadius: 8,
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "var(--text-secondary)",
                    fontFamily: "inherit",
                    display: "flex",
                    alignItems: "center",
                    gap: 5,
                  }}
                >
                  <span
                    style={{
                      display: "inline-block",
                      width: 10,
                      height: 10,
                      background: "var(--stream-red)",
                      borderRadius: 2,
                    }}
                  />
                  Stop
                </button>
              ) : (
                <ComposerPrimitive.Send
                  style={{
                    flexShrink: 0,
                    marginBottom: 4,
                    marginRight: 4,
                    padding: "8px 14px",
                    background: "var(--stream-blue)",
                    border: "none",
                    borderRadius: 8,
                    cursor: "pointer",
                    fontSize: 12,
                    fontWeight: 600,
                    color: "#ffffff",
                    fontFamily: "inherit",
                  }}
                >
                  Send
                </ComposerPrimitive.Send>
              )}
            </div>
            <p
              style={{
                fontSize: 10,
                color: "var(--text-muted)",
                marginTop: 6,
                textAlign: "center",
              }}
            >
              Enter to send · Shift+Enter new line
            </p>
          </ComposerPrimitive.Root>
        </ThreadPrimitive.Root>
      </div>
    </AssistantRuntimeProvider>
  );
}

// ── User message bubble ──────────────────────────────────────────────────────

function UserMessage() {
  return (
    <MessagePrimitive.Root style={{ display: "flex", justifyContent: "flex-end", gap: 6 }}>
      <div
        style={{
          display: "flex",
          flexDirection: "column",
          alignItems: "flex-end",
          gap: 4,
          maxWidth: "90%",
        }}
      >
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            fontSize: 13,
            lineHeight: 1.55,
            background: "color-mix(in srgb, var(--stream-blue) 10%, var(--bg-card))",
            border: "1px solid color-mix(in srgb, var(--stream-blue) 28%, transparent)",
            color: "var(--text-secondary)",
          }}
        >
          <MessagePrimitive.Content />
        </div>

        {/* Branch navigation + edit button */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <BranchPickerPrimitive.Root hideWhenSingleBranch>
            <BranchPickerPrimitive.Previous>
              <IconButton title="Previous version">‹</IconButton>
            </BranchPickerPrimitive.Previous>
            <span
              style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "monospace", padding: "0 2px" }}
            >
              <BranchPickerPrimitive.Number />
              {" / "}
              <BranchPickerPrimitive.Count />
            </span>
            <BranchPickerPrimitive.Next>
              <IconButton title="Next version">›</IconButton>
            </BranchPickerPrimitive.Next>
          </BranchPickerPrimitive.Root>

          <ActionBarPrimitive.Root hideWhenRunning autohide="not-last">
            <ActionBarPrimitive.Edit>
              <IconButton title="Edit message">
                <PencilIcon />
              </IconButton>
            </ActionBarPrimitive.Edit>
          </ActionBarPrimitive.Root>
        </div>
      </div>
    </MessagePrimitive.Root>
  );
}

// ── Assistant message bubble ─────────────────────────────────────────────────

function AssistantMessage() {
  return (
    <MessagePrimitive.Root style={{ display: "flex", justifyContent: "flex-start", gap: 8 }}>
      {/* V avatar */}
      <div
        style={{
          width: 22,
          height: 22,
          borderRadius: "50%",
          background: "color-mix(in srgb, var(--stream-blue) 14%, transparent)",
          border: "1px solid color-mix(in srgb, var(--stream-blue) 45%, transparent)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          marginTop: 2,
        }}
      >
        <span
          style={{
            fontSize: 9,
            fontWeight: 800,
            color: "var(--stream-blue)",
            fontFamily: "monospace",
          }}
        >
          V
        </span>
      </div>

      <div style={{ maxWidth: "90%", display: "flex", flexDirection: "column", gap: 4 }}>
        <div
          style={{
            padding: "10px 12px",
            borderRadius: 12,
            fontSize: 13,
            lineHeight: 1.55,
            background: "var(--bg-base)",
            border: "1px solid var(--border)",
            color: "var(--text-secondary)",
          }}
        >
          <MessagePrimitive.Content
            components={{
              Text: ({ text, status }) => (
                <>
                  {text === "" && status.type === "running" ? (
                    // Waiting for first token — bouncing dots
                    <div style={{ display: "flex", gap: 4, padding: "2px 0" }}>
                      {[0, 1, 2].map((i) => (
                        <div
                          key={i}
                          className="animate-bounce"
                          style={{
                            width: 6,
                            height: 6,
                            borderRadius: "50%",
                            background: "var(--stream-blue)",
                            animationDelay: `${i * 0.15}s`,
                          }}
                        />
                      ))}
                    </div>
                  ) : (
                    <>
                      <FormattedMessage content={text} />
                      {/* Blinking cursor while streaming */}
                      {status.type === "running" && text && (
                        <span
                          className="cursor-blink"
                          style={{
                            display: "inline-block",
                            width: 8,
                            height: 14,
                            background: "var(--stream-blue)",
                            marginLeft: 2,
                            verticalAlign: "middle",
                          }}
                        />
                      )}
                    </>
                  )}
                </>
              ),
            }}
          />
        </div>

        {/* Branch navigation + copy + retry */}
        <div style={{ display: "flex", alignItems: "center", gap: 4 }}>
          <BranchPickerPrimitive.Root hideWhenSingleBranch>
            <BranchPickerPrimitive.Previous>
              <IconButton title="Previous response">‹</IconButton>
            </BranchPickerPrimitive.Previous>
            <span
              style={{ fontSize: 9, color: "var(--text-muted)", fontFamily: "monospace", padding: "0 2px" }}
            >
              <BranchPickerPrimitive.Number />
              {" / "}
              <BranchPickerPrimitive.Count />
            </span>
            <BranchPickerPrimitive.Next>
              <IconButton title="Next response">›</IconButton>
            </BranchPickerPrimitive.Next>
          </BranchPickerPrimitive.Root>

          <ActionBarPrimitive.Root hideWhenRunning autohide="not-last">
            <ActionBarPrimitive.Copy>
              <IconButton title="Copy message">
                <CopyIcon />
              </IconButton>
            </ActionBarPrimitive.Copy>
            <ActionBarPrimitive.Reload>
              <IconButton title="Regenerate response">
                <ReloadIcon />
              </IconButton>
            </ActionBarPrimitive.Reload>
          </ActionBarPrimitive.Root>
        </div>
      </div>
    </MessagePrimitive.Root>
  );
}

// ── Simple markdown renderer ─────────────────────────────────────────────────

function FormattedMessage({ content }: { content: string }) {
  if (!content) return null;
  const lines = content.split("\n");
  return (
    <div className="space-y-1">
      {lines.map((line, i) => {
        const formatted = line.replace(
          /\*\*([^*]+)\*\*/g,
          (_, text) =>
            `<strong style="font-weight:600;color:var(--text-primary)">${text}</strong>`,
        );
        if (line.startsWith("- ") || line.startsWith("• ")) {
          return (
            <div key={i} className="flex gap-2">
              <span style={{ color: "var(--text-muted)", flexShrink: 0 }}>•</span>
              <span dangerouslySetInnerHTML={{ __html: formatted.slice(2) }} />
            </div>
          );
        }
        if (line === "") return <div key={i} style={{ height: 4 }} />;
        return <p key={i} dangerouslySetInnerHTML={{ __html: formatted }} />;
      })}
    </div>
  );
}

// ── Shared icon button ───────────────────────────────────────────────────────

function IconButton({ children, title }: { children: React.ReactNode; title?: string }) {
  return (
    <span
      title={title}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: 22,
        height: 22,
        borderRadius: 5,
        border: "1px solid var(--border)",
        background: "var(--bg-card)",
        cursor: "pointer",
        color: "var(--text-muted)",
        fontSize: 12,
        lineHeight: 1,
      }}
    >
      {children}
    </span>
  );
}

// ── SVG icons ────────────────────────────────────────────────────────────────

function CopyIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <rect x="9" y="9" width="13" height="13" rx="2" ry="2" />
      <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" />
    </svg>
  );
}

function ReloadIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <polyline points="23 4 23 10 17 10" />
      <path d="M20.49 15a9 9 0 1 1-2.12-9.36L23 10" />
    </svg>
  );
}

function PencilIcon() {
  return (
    <svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
      <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7" />
      <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z" />
    </svg>
  );
}
