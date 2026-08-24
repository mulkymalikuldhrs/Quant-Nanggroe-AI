"use client";

/**
 * QNA Assistant Widget — draggable, resizable floating AI trading copilot.
 *
 * Features:
 *   - Drag by header bar
 *   - Resize from bottom-right corner
 *   - Minimize to header-only bar
 *   - Chat interface with intent-based commands
 *   - Quick action buttons for common queries
 *   - Real API integration (status, positions, scorecard, allocation, close)
 */

import React, { useState, useRef, useCallback, useEffect } from "react";
import { apiRequest } from "@/lib/api-client";
import {
  Bot, X, Minus, Square, GripVertical,
  Send, Loader2, BarChart3, DollarSign, Target, Globe,
} from "lucide-react";
import { cn } from "@/lib/utils";

const QUICK_ACTIONS = [
  { label: "Status", icon: BarChart3, msg: "status" },
  { label: "Positions", icon: DollarSign, msg: "positions" },
  { label: "Scorecard", icon: Target, msg: "scorecard" },
  { label: "Allocation", icon: Globe, msg: "allocation" },
];

interface ChatMsg {
  role: "user" | "assistant";
  text: string;
  ts: number;
}

export function AssistantWidget() {
  // ── Panel state ──
  const [visible, setVisible] = useState(false);
  const [minimized, setMinimized] = useState(false);
  const [pos, setPos] = useState({ x: window.innerWidth - 420, y: 80 });
  const [size, setSize] = useState({ w: 380, h: 520 });
  const dragRef = useRef<{ startX: number; startY: number; posX: number; posY: number } | null>(null);
  const resizeRef = useRef<{ startX: number; startY: number; startW: number; startH: number } | null>(null);

  // ── Chat state ──
  const [messages, setMessages] = useState<ChatMsg[]>([
    { role: "assistant", text: "🤖 QNA Assistant ready.\nType a command or use quick buttons below.", ts: Date.now() },
  ]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);

  // ── Drag handler ──
  const onDragStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault();
    dragRef.current = { startX: e.clientX, startY: e.clientY, posX: pos.x, posY: pos.y };
    const onMove = (ev: MouseEvent) => {
      if (!dragRef.current) return;
      const dx = ev.clientX - dragRef.current.startX;
      const dy = ev.clientY - dragRef.current.startY;
      setPos({
        x: Math.max(0, Math.min(window.innerWidth - size.w, dragRef.current.posX + dx)),
        y: Math.max(0, Math.min(window.innerHeight - 40, dragRef.current.posY + dy)),
      });
    };
    const onUp = () => {
      dragRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [pos.x, pos.y, size.w]);

  // ── Resize handler ──
  const onResizeStart = useCallback((e: React.MouseEvent) => {
    e.preventDefault(); e.stopPropagation();
    resizeRef.current = { startX: e.clientX, startY: e.clientY, startW: size.w, startH: size.h };
    const onMove = (ev: MouseEvent) => {
      if (!resizeRef.current) return;
      setSize({
        w: Math.max(300, Math.min(window.innerWidth - pos.x - 10, resizeRef.current.startW + ev.clientX - resizeRef.current.startX)),
        h: Math.max(350, Math.min(window.innerHeight - pos.y - 10, resizeRef.current.startH + ev.clientY - resizeRef.current.startY)),
      });
    };
    const onUp = () => {
      resizeRef.current = null;
      document.removeEventListener("mousemove", onMove);
      document.removeEventListener("mouseup", onUp);
    };
    document.addEventListener("mousemove", onMove);
    document.addEventListener("mouseup", onUp);
  }, [pos.x, pos.y, size.w, size.h]);

  // ── Send message ──
  const send = useCallback(async (msg?: string) => {
    const text = (msg || input).trim();
    if (!text || loading) return;
    setInput("");
    setMessages(prev => [...prev, { role: "user", text, ts: Date.now() }]);
    setLoading(true);
    try {
      const res = await apiRequest<{ reply: string }>("/api/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ message: text }),
      });
      setMessages(prev => [...prev, { role: "assistant", text: res.reply ?? "No response", ts: Date.now() }]);
    } catch (e) {
      setMessages(prev => [...prev, {
        role: "assistant",
        text: `❌ ${e instanceof Error ? e.message : "Backend unavailable"}`,
        ts: Date.now(),
      }]);
    } finally {
      setLoading(false);
    }
  }, [input, loading]);

  // ── Auto-scroll chat ──
  const chatEndRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  if (!visible) {
    return (
      <button onClick={() => setVisible(true)}
        className="fixed bottom-6 right-6 z-[9999] w-12 h-12 rounded-full bg-gradient-to-br from-cyan-500 to-blue-600 shadow-lg shadow-cyan-500/30 flex items-center justify-center hover:scale-110 transition-transform cursor-pointer"
        aria-label="Open QNA Assistant">
        <Bot className="w-6 h-6 text-white" />
      </button>
    );
  }

  return (
    <div
      style={{ left: pos.x, top: pos.y, width: size.w, height: minimized ? 36 : size.h }}
      className={cn(
        "fixed z-[9999] rounded-xl border border-white/10 shadow-2xl shadow-black/50",
        "bg-[#0a0a0f]/95 backdrop-blur-lg flex flex-col overflow-hidden select-none",
      )}
    >
      {/* Header — draggable */}
      <div onMouseDown={onDragStart}
        className="flex items-center justify-between px-3 h-9 bg-gradient-to-r from-cyan-500/10 to-blue-500/10 border-b border-white/10 cursor-grab active:cursor-grabbing shrink-0">
        <div className="flex items-center gap-2 pointer-events-none">
          <Bot className="w-4 h-4 text-cyan-400" />
          <span className="text-xs font-semibold text-white/80">QNA Assistant</span>
        </div>
        <div className="flex items-center gap-1">
          <button onClick={() => setMinimized(m => !m)} className="p-1 rounded hover:bg-white/10">
            <Minus className="w-3.5 h-3.5 text-white/40" />
          </button>
          <button onClick={() => setVisible(false)} className="p-1 rounded hover:bg-white/10">
            <X className="w-3.5 h-3.5 text-red-400/60" />
          </button>
        </div>
      </div>

      {!minimized && (
        <>
          {/* Quick actions */}
          <div className="flex gap-1 px-2 py-1.5 border-b border-white/[0.06] shrink-0 flex-wrap">
            {QUICK_ACTIONS.map(({ label, icon: Icon, msg }) => (
              <button key={label} onClick={() => send(msg)}
                disabled={loading}
                className="flex items-center gap-1 px-2 py-1 rounded-md bg-white/[0.04] border border-white/[0.06] text-[10px] text-white/60 hover:bg-white/[0.08] hover:text-white/90 transition-colors disabled:opacity-40">
                <Icon className="w-3 h-3" /> {label}
              </button>
            ))}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-3 space-y-2 min-h-0">
            {messages.map((m, i) => (
              <div key={i} className={cn(
                "max-w-[85%] rounded-lg px-3 py-2 text-xs whitespace-pre-wrap leading-relaxed",
                m.role === "user"
                  ? "ml-auto bg-cyan-500/15 text-cyan-100 border border-cyan-500/20"
                  : "mr-auto bg-white/[0.03] text-white/70 border border-white/[0.05]",
              )}>
                {m.text}
              </div>
            ))}
            {loading && (
              <div className="flex items-center gap-2 text-white/40 text-xs px-2">
                <Loader2 className="w-3.5 h-3.5 animate-spin" /> Thinking…
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Input */}
          <form onSubmit={(e) => { e.preventDefault(); send(); }}
            className="flex gap-2 p-2 border-t border-white/[0.06] shrink-0">
            <input
              value={input} onChange={(e) => setInput(e.target.value)}
              placeholder="Type command… (status, positions, close EURUSD)"
              disabled={loading}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
              className="flex-1 bg-white/[0.04] border border-white/[0.08] rounded-lg px-3 py-1.5 text-xs text-white/80 placeholder:text-white/20 focus:outline-none focus:border-cyan-500/40"
            />
            <button type="submit" disabled={loading || !input.trim()}
              className="px-2.5 rounded-lg bg-cyan-500/20 text-cyan-400 hover:bg-cyan-500/30 transition-colors disabled:opacity-30">
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        </>
      )}

      {/* Resize handle */}
      {!minimized && (
        <div onMouseDown={onResizeStart}
          className="absolute bottom-0 right-0 w-4 h-4 cursor-nwse-resize opacity-30 hover:opacity-70">
          <Square className="w-3 h-3 text-white/30 rotate-45" />
        </div>
      )}
    </div>
  );
}
