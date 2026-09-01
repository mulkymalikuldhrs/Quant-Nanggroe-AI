"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import { useRouter } from "next/navigation";
import {
  LayoutDashboard, Bot, FlaskConical, Briefcase, ArrowLeftRight, Shield,
  BarChart3, Sigma, Radio, Settings, Building2, Activity, GitBranch,
  Search, X, ArrowRight, Shrink, MemoryStick, Network, Box,
} from "lucide-react";
import { cn } from "@/lib/utils";

interface CommandItem {
  id: string;
  label: string;
  description: string;
  icon: React.ComponentType<{ className?: string }>;
  href: string;
  category: string;
  keywords: string[];
}

const commands: CommandItem[] = [
  { id: "dashboard", label: "Dashboard", description: "Command center overview", icon: LayoutDashboard, href: "/", category: "Navigation", keywords: ["home", "overview", "main"] },
  { id: "trading", label: "Trading", description: "Live orders & positions", icon: ArrowLeftRight, href: "/trading", category: "Navigation", keywords: ["orders", "positions", "trade"] },
  { id: "portfolio", label: "Portfolio", description: "Cross-broker portfolio view", icon: Briefcase, href: "/portfolio", category: "Navigation", keywords: ["portfolio", "holdings", "allocation"] },
  { id: "brokers", label: "Brokers", description: "MT5 broker accounts", icon: Building2, href: "/brokers", category: "Navigation", keywords: ["broker", "mt5", "account"] },
  { id: "risk", label: "Risk Management", description: "VaR, CVaR, Kelly, kill switch", icon: Shield, href: "/risk", category: "Navigation", keywords: ["risk", "var", "kelly", "kill"] },
  { id: "market", label: "Market Data", description: "Real-time market sentiment", icon: BarChart3, href: "/market", category: "Navigation", keywords: ["market", "sentiment", "price"] },
  { id: "vector", label: "Vector Manifold", description: "Currency 3D, mispricing, grid", icon: Box, href: "/vector", category: "Navigation", keywords: ["vector", "manifold", "3d", "grid", "euclid"] },
  { id: "pipeline", label: "Pipeline", description: "15-stage autonomous pipeline", icon: GitBranch, href: "/pipeline", category: "Navigation", keywords: ["pipeline", "stages", "autonomous"] },
  { id: "agents", label: "Agents", description: "Council & decision agents", icon: Bot, href: "/agents", category: "Navigation", keywords: ["agents", "council", "decision"] },
  { id: "backtest", label: "Backtest", description: "Strategy backtesting engine", icon: FlaskConical, href: "/backtest", category: "Navigation", keywords: ["backtest", "test", "simulate"] },
  { id: "strategies", label: "Strategies", description: "78 registered strategies", icon: Sigma, href: "/strategies", category: "Navigation", keywords: ["strategies", "alpha", "models"] },
  { id: "walkforward", label: "Walk-Forward", description: "Rolling window validation", icon: FlaskConical, href: "/walkforward", category: "Navigation", keywords: ["walk", "forward", "validation", "rolling"] },
  { id: "factors", label: "Factors", description: "Factor zoo & analysis", icon: Shrink, href: "/factors", category: "Navigation", keywords: ["factors", "alpha", "zoo"] },
  { id: "memory", label: "Memory", description: "Agent memory & knowledge", icon: MemoryStick, href: "/memory", category: "Navigation", keywords: ["memory", "knowledge", "learn"] },
  { id: "colony", label: "Colony", description: "Multi-agent colony", icon: Network, href: "/colony", category: "Navigation", keywords: ["colony", "swarm", "multi"] },
  { id: "qna-status", label: "QNA Status", description: "System health monitoring", icon: Activity, href: "/qna-status", category: "Navigation", keywords: ["status", "health", "monitor"] },
  { id: "orderflow", label: "Order Flow", description: "Order flow analysis", icon: BarChart3, href: "/orderflow", category: "Navigation", keywords: ["order", "flow", "depth"] },
  { id: "security", label: "Security", description: "Security events & rules", icon: Shield, href: "/security", category: "Navigation", keywords: ["security", "audit", "rules"] },
  { id: "tools", label: "Tools", description: "Agent tools & execution", icon: Settings, href: "/tools", category: "Navigation", keywords: ["tools", "execute", "actions"] },
  { id: "channels", label: "Channels", description: "Communication channels", icon: Radio, href: "/channels", category: "Navigation", keywords: ["channels", "telegram", "notify"] },
  { id: "settings", label: "Settings", description: "Configuration & credentials", icon: Settings, href: "/settings", category: "Navigation", keywords: ["settings", "config", "credentials"] },
];

export function CommandPalette() {
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  // Keyboard shortcut: Cmd/Ctrl+K
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        setOpen((prev) => !prev);
      }
      if (e.key === "Escape" && open) {
        setOpen(false);
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [open]);

  // Focus input when opened
  useEffect(() => {
    if (open) {
      setTimeout(() => inputRef.current?.focus(), 50);
      setQuery("");
      setSelectedIndex(0);
    }
  }, [open]);

  // Filter commands
  const filtered = query.trim() === ""
    ? commands
    : commands.filter((cmd) => {
        const q = query.toLowerCase();
        return (
          cmd.label.toLowerCase().includes(q) ||
          cmd.description.toLowerCase().includes(q) ||
          cmd.keywords.some((k) => k.includes(q))
        );
      });

  // Keyboard navigation
  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "ArrowDown") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, filtered.length - 1));
      } else if (e.key === "ArrowUp") {
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
      } else if (e.key === "Enter" && filtered[selectedIndex]) {
        e.preventDefault();
        router.push(filtered[selectedIndex].href);
        setOpen(false);
      }
    },
    [filtered, selectedIndex, router],
  );

  // Scroll selected item into view
  useEffect(() => {
    if (listRef.current) {
      const items = listRef.current.querySelectorAll("[data-command-item]");
      items[selectedIndex]?.scrollIntoView({ block: "nearest" });
    }
  }, [selectedIndex]);

  if (!open) return null;

  return (
    <>
      {/* Backdrop */}
      <div className="fixed inset-0 z-[200] bg-black/70 backdrop-blur-sm" onClick={() => setOpen(false)} />

      {/* Palette */}
      <div className="fixed top-[15%] left-1/2 -translate-x-1/2 z-[201] w-full max-w-2xl">
        <div className="bg-[#0d0d24]/95 border border-white/10 rounded-2xl shadow-2xl overflow-hidden animate-scale-in">
          {/* Search Input */}
          <div className="flex items-center gap-3 px-4 py-3 border-b border-white/10">
            <Search className="w-5 h-5 text-white/40 flex-shrink-0" />
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => {
                setQuery(e.target.value);
                setSelectedIndex(0);
              }}
              onKeyDown={handleKeyDown}
              placeholder="Type a command or search..."
              className="flex-1 bg-transparent text-sm text-white placeholder-white/30 outline-none"
            />
            {query && (
              <button onClick={() => setQuery("")} className="p-1 hover:bg-white/10 rounded transition-colors">
                <X className="w-4 h-4 text-white/40" />
              </button>
            )}
            <kbd className="hidden sm:inline-flex items-center gap-1 px-2 py-1 rounded bg-white/5 border border-white/10 text-[10px] text-white/40 font-mono">
              ESC
            </kbd>
          </div>

          {/* Results */}
          <div ref={listRef} className="max-h-[400px] overflow-y-auto custom-scrollbar p-2">
            {filtered.length === 0 ? (
              <div className="text-center py-8 text-white/30">
                <p className="text-sm">No results found</p>
                <p className="text-xs mt-1">Try a different search term</p>
              </div>
            ) : (
              filtered.map((cmd, i) => {
                const Icon = cmd.icon;
                const isSelected = i === selectedIndex;
                return (
                  <button
                    key={cmd.id}
                    data-command-item
                    onClick={() => {
                      router.push(cmd.href);
                      setOpen(false);
                    }}
                    onMouseEnter={() => setSelectedIndex(i)}
                    className={cn(
                      "w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-left transition-all duration-150",
                      isSelected
                        ? "bg-emerald-500/10 border border-emerald-500/20"
                        : "hover:bg-white/5 border border-transparent",
                    )}
                  >
                    <div className={cn(
                      "flex items-center justify-center w-8 h-8 rounded-lg transition-colors",
                      isSelected ? "bg-emerald-500/20" : "bg-white/5",
                    )}>
                      <Icon className={cn("w-4 h-4", isSelected ? "text-emerald-400" : "text-white/40")} />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className={cn("text-sm font-medium", isSelected ? "text-white" : "text-white/70")}>
                        {cmd.label}
                      </p>
                      <p className="text-xs text-white/40 truncate">{cmd.description}</p>
                    </div>
                    <ArrowRight className={cn(
                      "w-4 h-4 transition-opacity",
                      isSelected ? "opacity-100 text-emerald-400" : "opacity-0",
                    )} />
                  </button>
                );
              })
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-4 py-2 border-t border-white/10 bg-white/[0.02]">
            <div className="flex items-center gap-3 text-[10px] text-white/30">
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 font-mono">↑↓</kbd>
                Navigate
              </span>
              <span className="flex items-center gap-1">
                <kbd className="px-1.5 py-0.5 rounded bg-white/5 border border-white/10 font-mono">↵</kbd>
                Select
              </span>
            </div>
            <span className="text-[10px] text-white/20 font-mono">{filtered.length} commands</span>
          </div>
        </div>
      </div>
    </>
  );
}
