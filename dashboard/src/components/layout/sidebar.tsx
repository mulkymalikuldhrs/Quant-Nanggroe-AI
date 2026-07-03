"use client";

import React from "react";
import {
  LayoutDashboard,
  Bot,
  FlaskConical,
  Briefcase,
  ArrowLeftRight,
  Shield,
  BarChart3,
  Sigma,
  Settings,
  ChevronLeft,
  ChevronRight,
  Zap,
  Radio,
} from "lucide-react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { Badge } from "@/components/ui/badge";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/agents", label: "Agents", icon: Bot },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/trading", label: "Trading", icon: ArrowLeftRight },
  { href: "/risk", label: "Risk", icon: Shield },
  { href: "/market", label: "Market", icon: BarChart3 },
  { href: "/factors", label: "Factors", icon: Sigma },
  { href: "/strategies", label: "Strategies", icon: Zap },
  { href: "/memory", label: "Memory", icon: Zap },
  { href: "/colony", label: "Colony", icon: Zap },
  { href: "/security", label: "Security", icon: Shield },
  { href: "/tools", label: "Tools", icon: Zap },
  { href: "/channels", label: "Channels", icon: Radio },
  { href: "/settings", label: "Settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, killSwitch } = useAppStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen border-r border-white/[0.06] bg-[#0a0a1a]/95 backdrop-blur-xl transition-all duration-300 flex flex-col",
        sidebarOpen ? "w-60" : "w-16",
      )}
    >
      {/* Logo */}
      <div className="flex items-center h-14 px-3 border-b border-white/[0.06]">
        <div className="flex items-center gap-2.5 min-w-0">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-emerald-500 to-blue-600 flex items-center justify-center flex-shrink-0 shadow-[0_0_12px_rgba(16,185,129,0.3)]">
            <Radio className="w-4 h-4 text-white" />
          </div>
          {sidebarOpen && (
            <div className="min-w-0">
              <h1 className="text-sm font-bold text-white truncate tracking-tight">Quant-Nanggroe</h1>
              <p className="text-[10px] text-white/30 truncate">Agentic Trading OS</p>
            </div>
          )}
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 px-2 space-y-0.5 overflow-y-auto custom-scrollbar">
        {navItems.map((item) => {
          const isActive = pathname === item.href || (item.href !== "/" && pathname.startsWith(item.href));
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-sm font-medium transition-all duration-200 group",
                isActive
                  ? "bg-white/[0.08] text-white shadow-[0_0_15px_rgba(255,255,255,0.03)]"
                  : "text-white/40 hover:text-white/70 hover:bg-white/[0.04]",
              )}
            >
              <item.icon
                className={cn(
                  "w-4 h-4 flex-shrink-0 transition-colors",
                  isActive ? "text-emerald-400" : "text-white/40 group-hover:text-white/60",
                )}
              />
              {sidebarOpen && <span className="truncate">{item.label}</span>}
              {sidebarOpen && item.href === "/agents" && (
                <Badge variant="success" className="ml-auto text-[10px] px-1.5 py-0">11</Badge>
              )}
            </Link>
          );
        })}
      </nav>

      {/* Kill Switch */}
      {sidebarOpen && killSwitch && (
        <div className="mx-2 mb-2 px-3 py-2 rounded-lg bg-red-500/10 border border-red-500/20">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
            <span className="text-xs font-medium text-red-400">Kill Switch Active</span>
          </div>
        </div>
      )}

      {/* Toggle */}
      <div className="border-t border-white/[0.06] p-2">
        <button
          onClick={toggleSidebar}
          className="w-full flex items-center justify-center py-1.5 rounded-lg text-white/30 hover:text-white/60 hover:bg-white/[0.04] transition-colors"
        >
          {sidebarOpen ? <ChevronLeft className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
        </button>
      </div>
    </aside>
  );
}
