"use client";

import React, { useState, useEffect, useRef, useCallback } from "react";
import {
  LayoutDashboard, Bot, FlaskConical, Briefcase, ArrowLeftRight, Shield,
  BarChart3, Sigma, Radio, Settings, ChevronLeft, ChevronRight,
  MemoryStick as Memory, Network, Cog, Shrink, Building2, Activity, GitBranch,
  Menu, X, ChevronRight as ArrowRight, Brain, Download, FileCode,
  Flame, Bell, History, Vote, Database, Box,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";

interface NavItem {
  href: string;
  label: string;
  icon: React.ComponentType<{ className?: string }>;
  category: "main" | "trading" | "analysis" | "system";
  badge?: string;
}

const navItems: NavItem[] = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, category: "main" },
  { href: "/trading", label: "Trading", icon: ArrowLeftRight, category: "trading" },
  { href: "/trading/history", label: "Trade History", icon: History, category: "trading", badge: "NEW" },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase, category: "trading" },
  { href: "/brokers", label: "Brokers", icon: Building2, category: "trading" },
  { href: "/risk", label: "Risk", icon: Shield, category: "trading" },
  { href: "/market", label: "Market", icon: BarChart3, category: "trading" },
  { href: "/vector", label: "Vector", icon: Box, category: "analysis", badge: "NEW" },
  { href: "/pipeline", label: "Pipeline", icon: GitBranch, category: "analysis", badge: "15" },
  { href: "/agents", label: "Agents", icon: Bot, category: "analysis", badge: "11" },
  { href: "/backtest", label: "Backtest", icon: FlaskConical, category: "analysis" },
  { href: "/walkforward", label: "Walk-Forward", icon: FlaskConical, category: "analysis", badge: "WF" },
  { href: "/strategies", label: "Strategies", icon: Sigma, category: "analysis" },
  { href: "/factors", label: "Factors", icon: Shrink, category: "analysis" },
  { href: "/evolution", label: "Evolution", icon: GitBranch, category: "analysis" },
  { href: "/memory", label: "Memory", icon: Memory, category: "analysis" },
  { href: "/colony", label: "Colony", icon: Network, category: "analysis" },
  { href: "/committee", label: "Committee", icon: Vote, category: "analysis", badge: "NEW" },
  { href: "/evaluator", label: "Evaluator", icon: Sigma, category: "analysis", badge: "NEW" },
  { href: "/data-pipeline", label: "Data Pipeline", icon: Database, category: "analysis", badge: "NEW" },
  { href: "/qna-status", label: "QNA Status", icon: Activity, category: "analysis" },
  { href: "/autonomous", label: "Autonomous", icon: Brain, category: "analysis", badge: "AI" },
  { href: "/candle-monitor", label: "Candle Monitor", icon: Flame, category: "trading", badge: "NEW" },
  { href: "/notifications", label: "Notifications", icon: Bell, category: "system", badge: "NEW" },
  { href: "/orderflow", label: "Order Flow", icon: BarChart3, category: "trading", badge: "🔥" },
  { href: "/security", label: "Security", icon: Shield, category: "system" },
  { href: "/tools", label: "Tools", icon: Cog, category: "system" },
  { href: "/channels", label: "Channels", icon: Radio, category: "system" },
  { href: "/export", label: "Export", icon: Download, category: "system" },
  { href: "/config", label: "Config", icon: FileCode, category: "system" },
  { href: "/settings", label: "Settings", icon: Settings, category: "system" },
];

const categories = [
  { id: "main" as const, label: "" },
  { id: "trading" as const, label: "TRADING" },
  { id: "analysis" as const, label: "ANALYSIS" },
  { id: "system" as const, label: "SYSTEM" },
];

// Quick-access items shown in the island bar
const islandPrimaryItems = navItems.filter(i =>
  ["/", "/trading", "/portfolio", "/pipeline", "/agents"].includes(i.href)
);

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, killSwitch } = useAppStore();
  const [panelOpen, setPanelOpen] = useState(false);
  const panelRef = useRef<HTMLDivElement>(null);
  const hamburgerRef = useRef<HTMLButtonElement>(null);

  // Close panel on escape
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "Escape") setPanelOpen(false);
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  // Close panel on route change
  const prevPath = useRef(pathname);
  useEffect(() => {
    if (pathname !== prevPath.current) {
      setPanelOpen(false);
      prevPath.current = pathname;
    }
  }, [pathname]);

  // Close panel on click outside
  useEffect(() => {
    if (!panelOpen) return;
    const handler = (e: MouseEvent) => {
      if (
        panelRef.current &&
        !panelRef.current.contains(e.target as Node) &&
        hamburgerRef.current &&
        !hamburgerRef.current.contains(e.target as Node)
      ) {
        setPanelOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [panelOpen]);

  const isActive = (href: string) =>
    pathname === href || (href !== "/" && pathname.startsWith(href));

  return (
    <>
      {/* ── Fluid Island Navigation ─────────────────────────────── */}
      <nav className="fluid-island">
        <div className="flex items-center gap-1">
          {/* Logo */}
          <Link
            href="/"
            className="flex items-center justify-center w-8 h-8 rounded-full overflow-hidden flex-shrink-0 shadow-[0_0_16px_rgba(255,215,0,0.2)] mr-1 border border-amber-500/30"
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img src="/icon-192.png" alt="QNA" className="w-full h-full object-cover" />
          </Link>

          {/* Primary nav items (visible on desktop) */}
          <div className="hidden md:flex items-center gap-0.5 ml-1">
            {islandPrimaryItems.map((item) => {
              const Icon = item.icon;
              const active = isActive(item.href);
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn("island-item", active && "active")}
                >
                  <Icon className={cn("w-3.5 h-3.5", active ? "text-emerald-400" : "")} />
                  <span>{item.label}</span>
                </Link>
              );
            })}
          </div>
        </div>

        {/* Right side: status + hamburger */}
        <div className="flex items-center gap-2 ml-auto">
          {/* Kill Switch indicator */}
          {killSwitch && (
            <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-red-500/15 border border-red-500/20">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500 animate-pulse shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
              <span className="text-[9px] font-medium text-red-400 hidden sm:inline">KILL</span>
            </div>
          )}

          {/* Menu toggle (hamburger morph) */}
          <button
            ref={hamburgerRef}
            onClick={() => setPanelOpen(!panelOpen)}
            className={cn(
              "flex items-center justify-center w-8 h-8 rounded-full transition-all duration-300",
              panelOpen
                ? "bg-white/[0.08] text-white"
                : "hover:bg-white/[0.04] text-white/40 hover:text-white/70",
            )}
            aria-label="Toggle navigation menu"
          >
            {panelOpen ? (
              <X className="w-4 h-4" />
            ) : (
              <div className={cn("hamburger", panelOpen && "open")}>
                <span className="hamburger-line" />
                <span className="hamburger-line" />
                <span className="hamburger-line" />
              </div>
            )}
          </button>
        </div>
      </nav>

      {/* ── Expanded Navigation Panel ───────────────────────────── */}
      {panelOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm"
            onClick={() => setPanelOpen(false)}
          />

          {/* Panel */}
          <div
            ref={panelRef}
            className="island-panel"
          >
            <div className="p-6">
              {/* Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-lg font-bold text-white">Navigation</h2>
                  <p className="text-xs text-white/30 mt-0.5">Quant-Nanggroe AI v8.0.9</p>
                </div>
                <button
                  onClick={() => setPanelOpen(false)}
                  className="flex items-center justify-center w-8 h-8 rounded-full hover:bg-white/[0.06] transition-colors"
                >
                  <X className="w-4 h-4 text-white/50" />
                </button>
              </div>

              {/* Nav grid */}
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-2">
                {categories.map((cat) => {
                  const items = navItems.filter((i) => i.category === cat.id);
                  if (items.length === 0) return null;

                  return (
                    <div key={cat.id} className="island-panel-item">
                      {cat.label && (
                        <p className="text-[10px] font-medium text-white/20 uppercase tracking-[0.15em] mb-2 px-1">
                          {cat.label}
                        </p>
                      )}
                      <div className="space-y-0.5">
                        {items.map((item) => {
                          const Icon = item.icon;
                          const active = isActive(item.href);
                          return (
                            <Link
                              key={item.href}
                              href={item.href}
                              className={cn(
                                "flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 group",
                                active
                                  ? "bg-emerald-500/10 text-white border border-emerald-500/15"
                                  : "text-white/40 hover:text-white/70 hover:bg-white/[0.04] border border-transparent",
                              )}
                            >
                              <Icon className={cn(
                                "w-4 h-4 flex-shrink-0 transition-colors",
                                active ? "text-emerald-400" : "text-white/30 group-hover:text-white/50",
                              )} />
                              <span className="flex-1">{item.label}</span>
                              {item.badge && (
                                <span className="text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                                  {item.badge}
                                </span>
                              )}
                              <ArrowRight className={cn(
                                "w-3.5 h-3.5 transition-all duration-200",
                                active ? "text-emerald-400/50 opacity-100" : "opacity-0 group-hover:opacity-40",
                              )} />
                            </Link>
                          );
                        })}
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Bottom info */}
              <div className="mt-6 pt-4 border-t border-white/[0.06] flex items-center justify-between text-[11px] text-white/20">
                <span>{navItems.length} modules • Autonomous HF</span>
                <span className="font-mono">Pipeline: 15/15 wired</span>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
}
