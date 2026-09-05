"use client";

import { useRef, useState } from "react";
import { usePathname } from "next/navigation";
import { Bot, Send, X, Loader2, Shield } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface AgentEvent {
  event_type: string;
  message: string;
  tool?: string;
}

interface AgentResponse {
  run_id: string;
  intent: "QUESTION" | "TASK";
  status: "RUNNING" | "COMPLETED" | "FAILED";
  answer?: string;
  events?: AgentEvent[];
  summary?: { executed?: number; staged?: number; denied?: number };
}

interface ChatItem {
  id: number;
  role: "user" | "assistant";
  text: string;
  intent?: string;
  status?: string;
  summary?: AgentResponse["summary"];
  error?: boolean;
}

function sessionId(): string {
  if (typeof window === "undefined") return "agent-default";
  const key = "closepilot_agent_session";
  let id = window.localStorage.getItem(key);
  if (!id) {
    id = `session-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`;
    window.localStorage.setItem(key, id);
  }
  return id;
}

export function AssistantWidget() {
  const pathname = usePathname();
  const [open, setOpen] = useState(false);
  const [input, setInput] = useState("");
  const [items, setItems] = useState<ChatItem[]>([]);
  const [busy, setBusy] = useState(false);
  const listRef = useRef<HTMLDivElement>(null);

  if (pathname === "/") return null;

  const scrollBottom = () => {
    requestAnimationFrame(() => {
      if (listRef.current) listRef.current.scrollTop = listRef.current.scrollHeight;
    });
  };

  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setInput("");
    const userItem: ChatItem = { id: Date.now(), role: "user", text };
    setItems((prev) => [...prev, userItem]);
    setBusy(true);
    try {
      const res = await api.post<AgentResponse>("/agent/chat", {
        request: text,
        session_id: sessionId(),
        role: "FINANCE_CONTROLLER",
      });
      const reply: ChatItem = {
        id: Date.now() + 1,
        role: "assistant",
        text: res.answer || "(no response)",
        intent: res.intent,
        status: res.status,
        summary: res.summary,
      };
      setItems((prev) => [...prev, reply]);
    } catch (e) {
      setItems((prev) => [
        ...prev,
        {
          id: Date.now() + 1,
          role: "assistant",
          text: `Request failed: ${e instanceof Error ? e.message : String(e)}`,
          error: true,
        },
      ]);
    } finally {
      setBusy(false);
      scrollBottom();
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-label={open ? "Close assistant" : "Open assistant"}
        className="fixed bottom-5 right-5 z-50 flex h-14 w-14 items-center justify-center rounded-full bg-emerald-600 text-white shadow-lg transition-transform hover:scale-105"
      >
        {open ? <X className="h-6 w-6" /> : <Bot className="h-6 w-6" />}
      </button>

      {open && (
        <div className="fixed bottom-24 right-5 z-50 flex h-[480px] w-[360px] flex-col overflow-hidden rounded-xl border bg-white shadow-2xl">
          <div className="flex items-center gap-2 border-b bg-emerald-600 px-4 py-3 text-white">
            <Bot className="h-5 w-5" />
            <div>
              <p className="text-sm font-semibold leading-none">ClosePilot Agent</p>
              <p className="mt-0.5 text-[10px] text-emerald-100">
                Models investigate · Rules authorize · Evidence proves
              </p>
            </div>
          </div>

          <div ref={listRef} className="flex-1 space-y-3 overflow-y-auto p-3">
            {items.length === 0 && (
              <p className="mt-4 rounded-lg bg-gray-50 p-3 text-xs text-gray-500">
                Ask anything about your platform, or give a task like{" "}
                <span className="font-semibold text-gray-700">
                  &ldquo;handle all the mismatched transactions&rdquo;
                </span>
                . Note: actions are only applied when the policy engine authorizes
                them (LOW risk, within tolerance); everything else is staged for a human.
              </p>
            )}
            {items.map((it) => (
              <div
                key={it.id}
                className={cn(
                  "max-w-[85%] rounded-lg px-3 py-2 text-sm",
                  it.role === "user"
                    ? "ml-auto bg-emerald-600 text-white"
                    : it.error
                      ? "bg-red-50 text-red-800"
                      : "bg-gray-100 text-gray-800",
                )}
              >
                <pre className="whitespace-pre-wrap font-sans">{it.text}</pre>
                {(it.intent || it.status) && (
                  <div className="mt-2 flex flex-wrap gap-1 text-[10px]">
                    {it.intent && (
                      <span className="rounded bg-white/70 px-1.5 py-0.5 font-semibold">
                        {it.intent}
                      </span>
                    )}
                    {it.status && (
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 font-semibold",
                          it.status === "COMPLETED" ? "bg-emerald-100 text-emerald-700" : "bg-amber-100 text-amber-700",
                        )}
                      >
                        {it.status}
                      </span>
                    )}
                  </div>
                )}
                {it.summary && (
                  <div className="mt-2 flex items-center gap-1 text-[10px] text-gray-500">
                    <Shield className="h-3 w-3" />
                    <span>Auto-closed: {it.summary.executed ?? 0}</span>
                    <span>· Staged for human: {it.summary.staged ?? 0}</span>
                  </div>
                )}
              </div>
            ))}
            {busy && (
              <div className="flex items-center gap-2 rounded-lg bg-gray-100 px-3 py-2 text-sm text-gray-500">
                <Loader2 className="h-4 w-4 animate-spin" />
                Authorizing and executing…
              </div>
            )}
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              send();
            }}
            className="flex items-center gap-2 border-t p-2"
          >
            <input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              placeholder="Ask or command the agent…"
              className="flex-1 rounded-md border px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-emerald-500"
            />
            <button
              type="submit"
              disabled={busy || !input.trim()}
              className="flex h-9 w-9 items-center justify-center rounded-md bg-emerald-600 text-white disabled:opacity-40"
              aria-label="Send"
            >
              <Send className="h-4 w-4" />
            </button>
          </form>
        </div>
      )}
    </>
  );
}

export default AssistantWidget;