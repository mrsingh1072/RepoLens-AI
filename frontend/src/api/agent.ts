import { apiClient, toApiErrorMessage } from "@/api/client";

const baseURL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export interface AgentCitation {
  file_path: string;
  function_name: string | null;
  class_name: string | null;
  start_line: number;
  end_line: number;
  snippet: string;
  source: string;
  score: number;
}

export interface AgentChatRequest {
  repo_id: string;
  question: string;
  session_id?: string;
}

export interface AgentChatResponse {
  repo_id: string;
  session_id: string;
  question: string;
  answer: string;
  confidence: number;
  reasoning_steps: string[];
  reasoning_summary: string;
  plan: string[];
  tools_used: string[];
  file_references: string[];
  function_references: string[];
  follow_up_suggestions: string[];
  citations: AgentCitation[];
}

export type AgentStreamEvent =
  | { type: "status"; message: string }
  | { type: "meta"; data: Omit<AgentChatResponse, "answer"> & { citations: AgentCitation[] } }
  | { type: "token"; text: string }
  | { type: "done"; answer: string }
  | { type: "error"; message: string };

export async function chatWithAgent(body: AgentChatRequest): Promise<AgentChatResponse> {
  const { data } = await apiClient.post<AgentChatResponse>("/agent/chat", body, {
    timeout: 180_000,
  });
  return data;
}

function parseSseBlock(block: string): AgentStreamEvent | null {
  let eventType = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) {
      eventType = line.slice(6).trim();
    } else if (line.startsWith("data:")) {
      data += line.slice(5).trim();
    }
  }
  if (!data) return null;

  try {
    const payload = JSON.parse(data) as Record<string, unknown>;
    switch (eventType) {
      case "status":
        return { type: "status", message: String(payload.message ?? "") };
      case "meta":
        return { type: "meta", data: payload as AgentStreamEvent extends { type: "meta"; data: infer D } ? D : never };
      case "token":
        return { type: "token", text: String(payload.text ?? "") };
      case "done":
        return { type: "done", answer: String(payload.answer ?? "") };
      default:
        return null;
    }
  } catch {
    return null;
  }
}

export async function streamAgentChat(
  body: AgentChatRequest,
  onEvent: (event: AgentStreamEvent) => void,
  signal?: AbortSignal,
): Promise<void> {
  try {
    const response = await fetch(`${baseURL}/agent/chat/stream`, {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify(body),
      signal,
    });

    if (!response.ok) {
      let message = `Stream failed (${response.status})`;
      try {
        const errBody = (await response.json()) as { error?: { message?: string } };
        if (errBody.error?.message) message = errBody.error.message;
      } catch {
        // ignore
      }
      onEvent({ type: "error", message });
      return;
    }

    const reader = response.body?.getReader();
    if (!reader) {
      onEvent({ type: "error", message: "Streaming is not supported in this browser." });
      return;
    }

    const decoder = new TextDecoder();
    let buffer = "";

    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const parts = buffer.split("\n\n");
      buffer = parts.pop() ?? "";

      for (const part of parts) {
        const event = parseSseBlock(part.trim());
        if (event) onEvent(event);
      }
    }

    if (buffer.trim()) {
      const event = parseSseBlock(buffer.trim());
      if (event) onEvent(event);
    }
  } catch (error) {
    if (signal?.aborted) return;
    onEvent({ type: "error", message: toApiErrorMessage(error) });
  }
}
