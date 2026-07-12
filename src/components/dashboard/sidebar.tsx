"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  Bot,
  LineChart,
  FlaskConical,
  FileCode2,
  ShieldAlert,
  Globe,
  Brain,
  Settings,
  ChevronLeft,
  ChevronRight,
  Activity,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import { Tooltip, TooltipTrigger, TooltipContent } from "@/components/ui/tooltip";

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, color: "text-cyan" },
  { href: "/agents", label: "Agents", icon: Bot, color: "text-purple" },
  { href: "/trading", label: "Trading", icon: LineChart, color: "text-emerald" },
  { href: "/backtest", label: "Backtest", icon: FlaskConical, color: "text-amber" },
  { href: "/strategies", label: "Strategies", icon: FileCode2, color: "text-cyan" },
  { href: "/risk", label: "Risk", icon: ShieldAlert, color: "text-rose" },
  { href: "/market", label: "Market", icon: Globe, color: "text-sky" },
  { href: "/memory", label: "Memory", icon: Brain, color: "text-purple" },
  { href: "/settings", label: "Settings", icon: Settings, color: "text-muted-foreground" },
];

export function Sidebar() {
  const pathname = usePathname();
  const { sidebarOpen, toggleSidebar, wsConnected } = useAppStore();

  return (
    <aside
      className={cn(
        "fixed left-0 top-0 z-40 h-screen bg-sidebar border-r border-border/50 transition-all duration-300 flex flex-col glass-card !border-t-0 !border-l-0 !border-b-0 !rounded-none",
        sidebarOpen ? "w-64" : "w-16"
      )}
    >
      {/* Logo / Brand */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-border/50 shrink-0">
        <div className="flex items-center justify-center w-8 h-8 rounded-lg bg-gradient-to-br from-cyan/20 to-purple/20 border border-cyan/30 shadow-[0_0_10px_rgba(6,182,212,0.2)]">
          <Activity className="w-4 h-4 text-cyan animate-pulse" />
        </div>
        {sidebarOpen && (
          <div className="overflow-hidden animate-slide-in-right">
            <h1 className="text-sm font-bold text-foreground whitespace-nowrap gradient-text">
              Quant Nanggroe
            </h1>
            <p className="text-[10px] text-muted-foreground whitespace-nowrap uppercase tracking-widest mt-0.5">
              Trading OS
            </p>
          </div>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 py-4 px-2 space-y-1 overflow-y-auto custom-scroll relative">
        {navItems.map((item) => {
          const isActive =
            pathname === item.href ||
            (item.href !== "/" && pathname.startsWith(item.href));
          
          const NavContent = (
            <Link
              href={item.href}
              className={cn(
                "flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200 group relative",
                isActive
                  ? "bg-secondary/40 text-foreground"
                  : "text-muted-foreground hover:text-foreground hover:bg-secondary/30"
              )}
            >
              {isActive && <div className="nav-active-bar" />}
              <item.icon
                className={cn(
                  "w-5 h-5 shrink-0 transition-all duration-300 group-hover:scale-110",
                  isActive ? item.color : "text-muted-foreground group-hover:text-foreground"
                )}
              />
              {sidebarOpen && (
                <span className="whitespace-nowrap transition-transform duration-200 group-hover:translate-x-1">
                  {item.label}
                </span>
              )}
            </Link>
          );

          if (!sidebarOpen) {
            return (
              <Tooltip key={item.href}>
                <TooltipTrigger asChild>{NavContent}</TooltipTrigger>
                <TooltipContent side="right" className="border-border/50 bg-card/90 backdrop-blur-md">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            );
          }

          return <React.Fragment key={item.href}>{NavContent}</React.Fragment>;
        })}
      </nav>

      {/* Footer */}
      <div className="p-3 space-y-3 shrink-0 border-t border-border/50 bg-background/20">
        {/* WebSocket status */}
        <div className="flex items-center gap-3 px-3 py-2.5 rounded-lg bg-card-flat border border-border/30">
          <span
            className={cn(
              "status-dot",
              wsConnected ? "status-dot-active" : "status-dot-error"
            )}
          />
          {sidebarOpen && (
            <div className="flex flex-col overflow-hidden">
              <span className="text-[11px] font-medium text-foreground whitespace-nowrap">
                {wsConnected ? "System Online" : "Connection Lost"}
              </span>
              <span className="text-[9px] text-muted-foreground whitespace-nowrap font-mono">
                WS // DHAHER LABS
              </span>
            </div>
          )}
        </div>

        {/* Toggle button */}
        <button
          onClick={toggleSidebar}
          className="flex items-center justify-center w-full py-2.5 rounded-lg hover:bg-secondary/50 text-muted-foreground hover:text-foreground transition-all cursor-pointer scale-tap border border-transparent hover:border-border/50"
        >
          {sidebarOpen ? (
            <div className="flex items-center gap-2 text-xs font-medium">
              <ChevronLeft className="w-4 h-4" />
              Collapse Sidebar
            </div>
          ) : (
            <ChevronRight className="w-4 h-4" />
          )}
        </button>
      </div>
    </aside>
  );
}
