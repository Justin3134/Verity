type UIMessagePart = { type: string; text?: string };
type UIMessage = { id: string; role: string; parts: UIMessagePart[] };

export async function POST(req: Request) {
  const body = await req.json();
  const messages: UIMessage[] = body.messages ?? [];
  const jobId: string | undefined = body.jobId;

  // Filter synthetic UI-only messages, convert UIMessage parts → simple {role, content}
  const simpleMessages = messages
    .filter((m) => m.id !== "greeting" && !m.id.startsWith("complete-"))
    .map((m) => ({
      role: m.role as "user" | "assistant",
      content: m.parts
        .filter((p): p is { type: "text"; text: string } => p.type === "text" && typeof p.text === "string")
        .map((p) => p.text)
        .join(""),
    }))
    .filter((m) => m.content.trim().length > 0);

  const BACKEND = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8001";

  const resp = await fetch(`${BACKEND}/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages: simpleMessages, job_id: jobId }),
  });

  if (!resp.ok || !resp.body) {
    return new Response(`Backend error: ${resp.status}`, { status: resp.status });
  }

  const encoder = new TextEncoder();
  const decoder = new TextDecoder();
  const textPartId = `text-${Date.now()}`;
  let textStarted = false;

  // Convert OpenAI SSE from FastAPI → AI SDK v6 UI message chunk stream format
  // Each SSE event must be a JSON object conforming to uiMessageChunkSchema:
  // text-start → text-delta (per token) → text-end
  const stream = new ReadableStream({
    async start(controller) {
      const enqueue = (obj: object) => {
        controller.enqueue(encoder.encode(`data: ${JSON.stringify(obj)}\n\n`));
      };

      const reader = resp.body!.getReader();
      try {
        outer: while (true) {
          const { done, value } = await reader.read();
          if (done) break;
          const text = decoder.decode(value, { stream: true });
          for (const line of text.split("\n")) {
            const trimmed = line.trim();
            if (!trimmed.startsWith("data: ")) continue;
            const data = trimmed.slice(6).trim();
            if (data === "[DONE]") break outer;
            try {
              const parsed = JSON.parse(data);
              const content = parsed?.choices?.[0]?.delta?.content;
              if (content) {
                if (!textStarted) {
                  enqueue({ type: "text-start", id: textPartId });
                  textStarted = true;
                }
                enqueue({ type: "text-delta", id: textPartId, delta: content });
              }
            } catch {
              // skip non-JSON lines
            }
          }
        }
      } finally {
        if (textStarted) {
          enqueue({ type: "text-end", id: textPartId });
        }
        controller.close();
      }
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "x-vercel-ai-ui-message-stream": "v1",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
