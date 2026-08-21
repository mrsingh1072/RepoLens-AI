import { useEffect, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { ArrowUp, ChevronDown, Loader2 } from "lucide-react";
import { useNavigate } from "react-router-dom";

import { streamAgentChat } from "@/api/agent";
import { CitationPanel } from "@/components/chat/CitationPanel";
import { FollowUpChips } from "@/components/chat/FollowUpChips";
import { MarkdownMessage } from "@/components/chat/MarkdownMessage";
import { Overline } from "@/components/common/Overline";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/input";
import { useRepoStore } from "@/store/repoStore";
import { cn } from "@/utils/cn";
import { settle } from "@/utils/motion";
import type { ChatMessage } from "@/types";

const SUGGESTIONS = [
  "How does authentication work?",
  "Where is the database connection configured?",
  "Explain the request lifecycle",
  "What are the main API endpoints?",
];

/** Breathing ember dot — the AI's presence. Hot while working, still at rest. */
function EmberDot({ live }: { live?: boolean }) {
  return (
    <span
      className={cn(
        "mt-2 h-2.5 w-2.5 shrink-0 rounded-full",
        live ? "animate-breathe bg-ember shadow-ember-glow" : "bg-ember/70",
      )}
      aria-hidden
    />
  );
}

export function ChatPage() {
  const navigate = useNavigate();
  const repositories = useRepoStore((s) => s.repositories);
  const selectedId = useRepoStore((s) => s.selectedRepoId);
  const activeRepo = repositories.find((r) => r.id === selectedId) ?? repositories[0];

  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [thinking, setThinking] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [sessionId, setSessionId] = useState<string | undefined>(undefined);
  const scrollRef = useRef<HTMLDivElement>(null);
  const abortRef = useRef<AbortController | null>(null);

  useEffect(() => {
    setSessionId(undefined);
    setMessages([]);
  }, [activeRepo?.id]);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages, thinking]);

  useEffect(() => () => abortRef.current?.abort(), []);

  const openFile = (path: string, line?: number) => {
    if (!activeRepo) return;
    const params = new URLSearchParams({ file: path });
    if (line) params.set("line", String(line));
    navigate(`/repository/${activeRepo.id}?${params.toString()}`);
  };

  const send = async (text: string) => {
    const content = text.trim();
    if (!content || thinking) return;
    if (!activeRepo) {
      setError("Select or ingest a repository before asking questions.");
      return;
    }

    abortRef.current?.abort();
    const controller = new AbortController();
    abortRef.current = controller;

    const userMsg: ChatMessage = {
      id: crypto.randomUUID(),
      role: "user",
      content,
      createdAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    const assistantId = crypto.randomUUID();
    const assistantPlaceholder: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      isStreaming: true,
      statusLabel: "Analyzing repository context…",
      createdAt: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((m) => [...m, userMsg, assistantPlaceholder]);
    setInput("");
    setThinking(true);
    setError(null);

    try {
      const repoId = `${activeRepo.owner}/${activeRepo.name}`;

      await streamAgentChat(
        { repo_id: repoId, question: content, session_id: sessionId },
        (event) => {
          if (event.type === "status") {
            setMessages((m) =>
              m.map((msg) => (msg.id === assistantId ? { ...msg, statusLabel: event.message } : msg)),
            );
            return;
          }

          if (event.type === "error") {
            setError(event.message);
            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: event.message, isStreaming: false }
                  : msg,
              ),
            );
            return;
          }

          if (event.type === "meta") {
            setSessionId(event.data.session_id);
            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantId
                  ? {
                      ...msg,
                      statusLabel: undefined,
                      confidence: event.data.confidence,
                      reasoningSummary: event.data.reasoning_summary,
                      reasoningSteps: event.data.reasoning_steps,
                      plan: event.data.plan,
                      toolsUsed: event.data.tools_used,
                      fileReferences: event.data.file_references,
                      functionReferences: event.data.function_references,
                      followUpSuggestions: event.data.follow_up_suggestions,
                      citations: event.data.citations.map((c) => ({
                        path: c.file_path,
                        startLine: c.start_line,
                        endLine: c.end_line,
                        snippet: c.snippet,
                        functionName: c.function_name,
                        source: c.source,
                        score: c.score,
                      })),
                    }
                  : msg,
              ),
            );
            return;
          }

          if (event.type === "token") {
            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantId ? { ...msg, content: msg.content + event.text } : msg,
              ),
            );
            return;
          }

          if (event.type === "done") {
            setMessages((m) =>
              m.map((msg) =>
                msg.id === assistantId
                  ? { ...msg, content: event.answer || msg.content, isStreaming: false }
                  : msg,
              ),
            );
          }
        },
        controller.signal,
      );
    } catch (err) {
      const message = err instanceof Error ? err.message : "Query failed.";
      setError(message);
    } finally {
      setThinking(false);
    }
  };

  const hasMessages = messages.length > 0;
  const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant" && !m.isStreaming);

  return (
    <div className="mx-auto flex h-[calc(100vh-8rem)] max-w-3xl flex-col">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-edge pb-4">
        <div className="flex items-center gap-3">
          <EmberDot live={thinking} />
          <div className="-mt-1">
            <Overline>Repository chat</Overline>
            <p className="mt-1 font-mono text-[13px] text-ink">
              {activeRepo ? `${activeRepo.owner}/${activeRepo.name}` : "no repository selected"}
            </p>
          </div>
        </div>
        {sessionId && (
          <span className="font-mono text-[10px] tracking-[0.14em] text-ink-3">SESSION ACTIVE</span>
        )}
      </div>

      {/* Conversation */}
      <div ref={scrollRef} className="flex-1 space-y-8 overflow-y-auto py-8">
        {!hasMessages ? (
          <div className="flex h-full flex-col items-center justify-center text-center">
            <motion.span
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={settle}
              className="h-3 w-3 rounded-full bg-ember shadow-ember-glow"
            />
            <h2 className="mt-6 font-display text-2xl font-semibold text-ink">
              Ask anything about this codebase
            </h2>
            <p className="mt-2 max-w-md text-sm leading-relaxed text-ink-2">
              Grounded answers with file citations, reasoning summaries, and follow-up suggestions.
            </p>
            <div className="mt-10 grid w-full max-w-xl gap-2.5 sm:grid-cols-2">
              {SUGGESTIONS.map((s) => (
                <button
                  key={s}
                  onClick={() => send(s)}
                  className="group rounded-md border border-edge bg-surface p-4 text-left text-sm text-ink-2 shadow-stratum transition-[transform,border-color,color] duration-200 hover:-translate-y-0.5 hover:border-edge-strong hover:text-ink active:scale-[0.99]"
                >
                  {s}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {messages.map((msg) => (
              <Message key={msg.id} message={msg} onFileClick={openFile} />
            ))}
          </AnimatePresence>
        )}
      </div>

      {lastAssistant?.followUpSuggestions && lastAssistant.followUpSuggestions.length > 0 && (
        <div className="border-t border-edge px-1 py-3">
          <FollowUpChips
            suggestions={lastAssistant.followUpSuggestions}
            onSelect={send}
            disabled={thinking}
          />
        </div>
      )}

      {/* Composer */}
      <div className="border-t border-edge pt-4">
        {error && <p className="mb-2 text-center font-mono text-xs text-rust">{error}</p>}
        <div className="relative">
          <Textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                send(input);
              }
            }}
            placeholder="Ask about functions, files, architecture…"
            className="min-h-[56px] bg-surface pr-14 shadow-stratum"
            disabled={thinking}
          />
          <Button
            size="icon"
            className="absolute bottom-2.5 right-2.5 h-9 w-9"
            onClick={() => send(input)}
            disabled={!input.trim() || thinking}
            aria-label="Send message"
          >
            {thinking ? <Loader2 className="animate-spin" /> : <ArrowUp />}
          </Button>
        </div>
        <p className="mt-2 text-center font-mono text-[10px] tracking-[0.14em] text-ink-3">
          ENTER TO SEND · SHIFT+ENTER FOR NEW LINE
        </p>
      </div>
    </div>
  );
}

function Message({
  message,
  onFileClick,
}: {
  message: ChatMessage;
  onFileClick: (path: string, line?: number) => void;
}) {
  const isUser = message.role === "user";
  const [reasoningOpen, setReasoningOpen] = useState(false);

  /* User: a compact raised bubble, right-aligned.
     Assistant: full-width prose on the bedrock — no bubble, just the ember dot. */
  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={settle}
        className="flex justify-end"
      >
        <div className="max-w-[85%] rounded-lg rounded-br-sm border border-edge bg-raised px-4 py-2.5 text-sm leading-relaxed text-ink shadow-stratum">
          {message.content}
        </div>
      </motion.div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={settle}
      className="flex gap-3.5"
    >
      <EmberDot live={message.isStreaming} />

      <div className="min-w-0 flex-1 space-y-4">
        {message.content ? (
          <div>
            <MarkdownMessage
              content={message.content}
              citations={message.citations}
              fileReferences={message.fileReferences}
              functionReferences={message.functionReferences}
              onFileClick={onFileClick}
            />
            {message.isStreaming && (
              <span className="ml-0.5 inline-block h-4 w-[7px] animate-caret-blink bg-ember align-middle" aria-hidden />
            )}
          </div>
        ) : message.isStreaming ? (
          <p className="animate-breathe font-mono text-[13px] text-ember" aria-live="polite">
            {message.statusLabel ?? "Working…"}
          </p>
        ) : null}

        {!message.isStreaming && (message.confidence !== undefined || message.toolsUsed?.length) && (
          <div className="flex flex-wrap items-center gap-1.5 font-mono text-[11px] text-ink-3">
            {message.confidence !== undefined && (
              <span className="tnum rounded-sm border border-edge bg-raised px-2 py-0.5">
                confidence {(message.confidence * 100).toFixed(0)}%
              </span>
            )}
            {message.toolsUsed?.map((tool) => (
              <span key={tool} className="rounded-sm border border-edge bg-raised px-2 py-0.5">
                {tool}
              </span>
            ))}
          </div>
        )}

        {!message.isStreaming && message.reasoningSummary && (
          <div className="rounded-md border border-edge bg-surface px-3.5 py-3 shadow-stratum">
            <button
              type="button"
              onClick={() => setReasoningOpen((o) => !o)}
              className="flex w-full items-center justify-between text-left"
            >
              <Overline>Reasoning</Overline>
              {message.reasoningSteps && message.reasoningSteps.length > 1 && (
                <ChevronDown
                  className={cn("h-3.5 w-3.5 text-ink-3 transition-transform", reasoningOpen && "rotate-180")}
                />
              )}
            </button>
            <p className="mt-2 text-[13px] leading-relaxed text-ink-2">{message.reasoningSummary}</p>
            <AnimatePresence initial={false}>
              {reasoningOpen && message.reasoningSteps && message.reasoningSteps.length > 1 && (
                <motion.ol
                  initial={{ height: 0, opacity: 0 }}
                  animate={{ height: "auto", opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }}
                  transition={{ duration: 0.2, ease: "easeOut" }}
                  className="mt-3 list-decimal space-y-1.5 overflow-hidden border-t border-edge pl-4 pt-3 text-[13px] text-ink-2"
                >
                  {message.reasoningSteps.map((step, i) => (
                    <li key={i}>{step}</li>
                  ))}
                </motion.ol>
              )}
            </AnimatePresence>
          </div>
        )}

        {!message.isStreaming && (message.citations?.length || message.fileReferences?.length) ? (
          <CitationPanel
            citations={message.citations ?? []}
            fileReferences={message.fileReferences}
            functionReferences={message.functionReferences}
            onFileClick={onFileClick}
          />
        ) : null}
      </div>
    </motion.div>
  );
}
