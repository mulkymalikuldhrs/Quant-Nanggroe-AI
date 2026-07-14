"use client";

import React from "react";
import {
  LayoutDashboard, Bot, FlaskConical, Briefcase, ArrowLeftRight, Shield,
  BarChart3, Sigma, Zap, Radio, Settings, ChevronLeft, ChevronRight,
  MemoryStick as Memory, Network, Cog, Shrink, Building2,
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
  // Main
  { href: "/", label: "Dashboard", icon: LayoutDashboard, category: "main" },

  // Trading
  { href: "/trading", label: "Trading", icon: ArrowLeftRight, category: "trading" },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase, category: "trading" },
  { href: "/brokers", label: "Brokers", icon: Building2, category: "trading" },
  { href: "/risk", label: "Risk", icon: Shield, category: "trading" },
  { href: "/market", label: "Market", icon: BarChart3, category: "trading" },

  // Analysis
  { href: "/agents", label: "Agents", icon: Bot, category: "analysis", badge: "11" },
  { href: "/backtest", label: "Backtest", icon: FlaskConical, category: "analysis" },
  { href: "/strategies", label: "Strategies", icon: Sigma, category: "analysis" },
  { href: "/factors", label: "Factors", icon: Shrink, category: "analysis" },
  { href: "/memory", label: "Memory", icon: Memory, category: "analysis" },
  { href: "/colony", label: "Colony", icon: Network, category: "analysis" },

  // System
  { href: "/security", label: "Security", icon: Shield, category: "system" },
  { href: "/tools", label: "Tools", icon: Cog, category: "system" },
  { href: "/channels", label: "Channels", icon: Radio, category: "system" },
  { href: "/settings", label: "Settings", icon: Settings, category: "system" },
];

const categories = [
  { id: "main", label: "" },
  { id: "trading", label: "TRADING" },
  { id: "analysis", label: "ANALYSIS" },
  { id: "system", label: "SYSTEM" },
] as const;

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, killSwitch } = useAppStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] flex flex-col",
        sidebarOpen ? "w-64" : "w-[68px]",
      )}
    >
      {/* Sidebar background */}
      <div className="absolute inset-0 glass-strong rounded-r-2xl shadow-glass" />

      {/* Content */}
      <div className="relative z-10 flex flex-col h-full">
        {/* Logo */}
        <div className="flex items-center h-14 px-4 border-b border-white/[0.06]">
          <div className={cn("flex items-center gap-3", !sidebarOpen && "justify-center w-full")}>
            <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-[0_0_16px_rgba(16,185,129,0.25)]">
              <span className="text-xs font-bold text-white">Q</span>
            </div>
            {sidebarOpen && (
              <div className="min-w-0">
                <h1 className="text-sm font-bold text-white truncate tracking-tight">Quant-Nanggroe</h1>
                <p className="text-[10px] text-white/30 truncate font-mono">v4.3.4 · Agentic OS</p>
              </div>
            )}
          </div>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2 space-y-3 overflow-y-auto custom-scrollbar">
          {categories.map((cat) => {
            const items = navItems.filter((i) => i.category === cat.id);
            if (items.length === 0) return null;

            return (
              <div key={cat.id}>
                {sidebarOpen && cat.label && (
                  <p className="px-3 py-1.5 text-[10px] font-medium text-white/20 uppercase tracking-[0.15em]">
                    {cat.label}
                  </p>
                )}
                <div className="space-y-0.5">
                  {items.map((item) => {
                    const isActive =
                      pathname === item.href ||
                      (item.href !== "/" && pathname.startsWith(item.href));
                    const Icon = item.icon;

                    return (
                      <Link
                        key={item.href}
                        href={item.href}
                        className={cn(
                          "flex items-center gap-3 px-3 py-2 rounded-xl text-sm font-medium transition-all duration-200 group relative",
                          sidebarOpen ? "justify-start" : "justify-center",
                          isActive
                            ? "bg-white/[0.08] text-white shadow-[0_0_20px_rgba(255,255,255,0.03)]"
                            : "text-white/30 hover:text-white/60 hover:bg-white/[0.04]",
                        )}
                        title={!sidebarOpen ? item.label : undefined}
                      >
                        <Icon
                          className={cn(
                            "w-[18px] h-[18px] flex-shrink-0 transition-colors",
                            isActive ? "text-emerald-400" : "text-white/30 group-hover:text-white/50",
                          )}
                        />
                        {sidebarOpen && (
                          <>
                            <span className="truncate">{item.label}</span>
                            {item.badge && (
                              <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded-full bg-emerald-500/15 text-emerald-400 border border-emerald-500/20">
                                {item.badge}
                              </span>
                            )}
                          </>
                        )}
                        {isActive && sidebarOpen && (
                          <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 rounded-full bg-emerald-500 shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                        )}
                      </Link>
                    );
                  })}
                </div>
              </div>
            );
          })}
        </nav>

        {/* Kill Switch */}
        {killSwitch && sidebarOpen && (
          <div className="mx-2 mb-2 px-3 py-2 rounded-xl bg-red-500/10 border border-red-500/20 animate-pulse">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 rounded-full bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]" />
              <span className="text-xs font-medium text-red-400">Kill Switch Active</span>
            </div>
          </div>
        )}

        {/* Toggle */}
        <div className="border-t border-white/[0.06] p-2">
          <button
            onClick={toggleSidebar}
            className={cn(
              "flex items-center py-1.5 rounded-xl text-white/20 hover:text-white/50 hover:bg-white/[0.04] transition-all duration-200",
              sidebarOpen ? "justify-end px-3 w-full" : "justify-center w-full",
            )}
            title={sidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {sidebarOpen ? (
              <ChevronLeft className="w-4 h-4" />
            ) : (
              <ChevronRight className="w-4 h-4" />
            )}
          </button>
        </div>
      </div>
    </aside>
  );
}
