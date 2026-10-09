"use client";

import { useCallback, useEffect, useId, useRef, useState } from "react";
import { Bot, Loader2, Send, Sparkles, X } from "lucide-react";
import { clsx } from "clsx";
import { askAssistant } from "@/lib/api";
import { loadLastTestRun, type LastTestRun } from "@/lib/run-store";

type ChatRole = "user" | "assistant" | "system";

type ChatMessage = {
  id: string;
  role: ChatRole;
  content: string;
  meta?: string;
};

const SESSION_KEY = "floodtail.assistant.session.v1";

function sessionId(): string {
  if (typeof window === "undefined") return "ui-ssr";
  try {
    const existing = window.localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const id =
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? `ui-${crypto.randomUUID()}`
        : `ui-${Date.now().toString(36)}`;
    window.localStorage.setItem(SESSION_KEY, id);
    return id;
  } catch {
    return `ui-${Date.now().toString(36)}`;
  }
}

function welcomeFor(run: LastTestRun | null): ChatMessage {
  if (run?.runId && run.metrics) {
    const place = run.place || run.portfolio.location_label || "this portfolio";
    const n = run.metrics.n_insured_houses ?? run.portfolio.n_rows;
    return {
      id: "welcome",
      role: "assistant",
      content:
        `I can answer questions about your last run for ${place}` +
        (n != null ? ` (${n} locations)` : "") +
        ". Ask about AAL, TIV, capital set-aside, hotspots, or ingested documents. " +
        "Money figures come only from frozen run metrics — I will not invent losses.",
      meta: `Grounded on run ${run.runId.slice(0, 8)}… · Qwen`,
    };
  }
  return {
    id: "welcome",
    role: "assistant",
    content:
      "Ask about FLOODTAIL, Nairobi flood assumptions, or documents in the knowledge base. " +
      "Run a portfolio test first to ground answers on AAL, EP, and capital figures.",
    meta: "RAG + Qwen · no run loaded yet",
  };
}

const SUGGESTIONS_WITH_RUN = [
  "What is the discrete AAL?",
  "How many insured houses are in this run?",
  "What capital set-aside band should we use?",
  "Summarise concentration risk from the knowledge base",
];

const SUGGESTIONS_NO_RUN = [
  "What does FLOODTAIL model for Nairobi?",
  "What documents are in the knowledge base?",
  "How should I start a portfolio test?",
];

export function AssistantChat() {
  const panelId = useId();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [run, setRun] = useState<LastTestRun | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const sidRef = useRef<string>("");

  const refreshRun = useCallback(() => {
    const next = loadLastTestRun();
    setRun(next);
    return next;
  }, []);

  useEffect(() => {
    sidRef.current = sessionId();
    const next = refreshRun();
    setMessages([welcomeFor(next)]);

    const onSaved = () => {
      const r = refreshRun();
      setMessages((prev) => {
        if (prev.length <= 1) return [welcomeFor(r)];
        return prev;
      });
    };
    window.addEventListener("floodtail:last-run", onSaved);
    window.addEventListener("storage", onSaved);
    return () => {
      window.removeEventListener("floodtail:last-run", onSaved);
      window.removeEventListener("storage", onSaved);
    };
  }, [refreshRun]);

  useEffect(() => {
    if (!open) return;
    const el = listRef.current;
    if (el) el.scrollTop = el.scrollHeight;
    const t = window.setTimeout(() => inputRef.current?.focus(), 80);
    return () => window.clearTimeout(t);
  }, [open, messages, busy]);

  const send = async (raw: string) => {
    const question = raw.trim();
    if (!question || busy) return;

    const userMsg: ChatMessage = {
      id: `u-${Date.now()}`,
      role: "user",
      content: question,
    };
    setMessages((m) => [...m, userMsg]);
    setInput("");
    setBusy(true);

    try {
      const current = refreshRun();
      const result = await askAssistant({
        question,
        runId: current?.runId ?? null,
        sessionId: sidRef.current,
        useRag: true,
        useMemory: true,
        clientMetrics: current?.metrics ?? null,
      });
      const bits: string[] = [];
      if (result.model) bits.push(result.model);
      if (result.source) bits.push(result.source);
      if (result.rag_used) bits.push("RAG");
      if (result.memory_used) bits.push("memory");
      if (result.grounded_on_run) bits.push("run metrics");
      if (result.degraded) bits.push("degraded");

      setMessages((m) => [
        ...m,
        {
          id: `a-${Date.now()}`,
          role: "assistant",
          content:
            result.answer?.trim() ||
            "No answer returned. Check Ollama (Qwen) and try again.",
          meta: bits.join(" · ") || undefined,
        },
      ]);
    } catch (err) {
      setMessages((m) => [
        ...m,
        {
          id: `e-${Date.now()}`,
          role: "assistant",
          content:
            err instanceof Error
              ? err.message
              : "Assistant request failed. Is the API and Ollama running?",
          meta: "error",
        },
      ]);
    } finally {
      setBusy(false);
    }
  };

  const suggestions =
    run?.runId && run.metrics ? SUGGESTIONS_WITH_RUN : SUGGESTIONS_NO_RUN;

  return (
    <div className="pointer-events-none fixed bottom-4 right-4 z-50 flex flex-col items-end gap-3 sm:bottom-6 sm:right-6">
      {open && (
        <div
          id={panelId}
          role="dialog"
          aria-label="FLOODTAIL AI assistant"
          className="pointer-events-auto flex w-[min(100vw-2rem,24rem)] flex-col overflow-hidden rounded-2xl border border-accent/25 bg-panel-grad shadow-glass backdrop-blur-xl animate-fade-up sm:w-[26rem]"
          style={{ maxHeight: "min(70vh, 36rem)" }}
        >
          <header className="flex items-start justify-between gap-3 border-b border-white/10 px-4 py-3">
            <div className="min-w-0">
              <div className="flex items-center gap-2">
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-accent/15 text-accent">
                  <Sparkles className="h-4 w-4" aria-hidden />
                </span>
                <div>
                  <p className="font-display text-sm font-semibold tracking-wide text-white">
                    FLOODTAIL Assistant
                  </p>
                  <p className="text-[11px] text-white/45">
                    Ollama · Qwen · portfolio RAG
                  </p>
                </div>
              </div>
              {run?.runId ? (
                <p className="mt-2 truncate text-[11px] text-accent/80">
                  Context: {run.place || "last run"} ·{" "}
                  {run.runId.slice(0, 8)}…
                </p>
              ) : (
                <p className="mt-2 text-[11px] text-white/40">
                  No run loaded — qualitative / RAG answers only
                </p>
              )}
            </div>
            <button
              type="button"
              className="rounded-lg p-1.5 text-white/50 transition hover:bg-white/10 hover:text-white"
              aria-label="Close assistant"
              onClick={() => setOpen(false)}
            >
              <X className="h-4 w-4" />
            </button>
          </header>

          <div
            ref={listRef}
            className="flex-1 space-y-3 overflow-y-auto px-3 py-3"
          >
            {messages.map((msg) => (
              <div
                key={msg.id}
                className={clsx(
                  "flex",
                  msg.role === "user" ? "justify-end" : "justify-start",
                )}
              >
                <div
                  className={clsx(
                    "max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-relaxed",
                    msg.role === "user"
                      ? "rounded-br-md bg-accent/90 text-night-950"
                      : "rounded-bl-md border border-white/10 bg-night-950/55 text-white/90",
                  )}
                >
                  {msg.role === "assistant" && (
                    <Bot
                      className="mb-1 inline h-3.5 w-3.5 text-accent"
                      aria-hidden
                    />
                  )}
                  <p className="whitespace-pre-wrap">{msg.content}</p>
                  {msg.meta && (
                    <p className="mt-1.5 text-[10px] uppercase tracking-wide text-white/35">
                      {msg.meta}
                    </p>
                  )}
                </div>
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 px-1 text-xs text-white/45">
                <Loader2 className="h-3.5 w-3.5 animate-spin text-accent" />
                Thinking with Qwen…
              </div>
            )}
          </div>

          {messages.length <= 2 && !busy && (
            <div className="flex flex-wrap gap-1.5 border-t border-white/5 px-3 py-2">
              {suggestions.map((s) => (
                <button
                  key={s}
                  type="button"
                  disabled={busy}
                  onClick={() => void send(s)}
                  className="rounded-full border border-white/10 bg-white/5 px-2.5 py-1 text-[11px] text-white/70 transition hover:border-accent/40 hover:text-accent"
                >
                  {s}
                </button>
              ))}
            </div>
          )}

          <form
            className="flex items-end gap-2 border-t border-white/10 p-3"
            onSubmit={(e) => {
              e.preventDefault();
              void send(input);
            }}
          >
            <textarea
              ref={inputRef}
              rows={1}
              value={input}
              disabled={busy}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  void send(input);
                }
              }}
              placeholder="Ask about this portfolio or run…"
              className="input-field max-h-28 min-h-[2.5rem] flex-1 resize-none py-2.5"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="btn-primary shrink-0 !rounded-xl !px-3 !py-2.5 disabled:opacity-40"
              aria-label="Send message"
            >
              {busy ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Send className="h-4 w-4" />
              )}
            </button>
          </form>
        </div>
      )}

      <button
        type="button"
        aria-expanded={open}
        aria-controls={panelId}
        aria-label={open ? "Close AI assistant" : "Open AI assistant"}
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          "pointer-events-auto group relative flex h-14 w-14 items-center justify-center rounded-full",
          "bg-accent text-night-950 shadow-glow transition",
          "hover:brightness-110 active:scale-95",
          open && "ring-2 ring-accent/40 ring-offset-2 ring-offset-night-950",
        )}
      >
        <span
          className="absolute inset-0 rounded-full bg-accent/40 animate-pulse-soft"
          aria-hidden
        />
        {open ? (
          <X className="relative h-6 w-6" />
        ) : (
          <Sparkles className="relative h-6 w-6" />
        )}
      </button>
    </div>
  );
}
