"use client";

import { useAppStore } from "@/lib/store";
import { useRealtimeData } from "@/lib/websocket";
import { useTheme } from "@/components/providers/theme-provider";
import { Bell, Search, Sun, Moon, Wifi, WifiOff, RefreshCw } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";

export function Header() {
  const { sidebarOpen, killSwitch, notifications, clearNotifications, refreshAll } = useAppStore();
  const { isConnected, connectionError } = useRealtimeData();
  const { resolved, toggle } = useTheme();

  const unreadCount = notifications.length;

  return (
    <header
      className={cn(
        "fixed top-0 right-0 z-30 h-14 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]",
        sidebarOpen ? "left-64" : "left-[68px]",
      )}
    >
      {/* Glass background */}
      <div className="absolute inset-0 glass rounded-bl-2xl shadow-glass">
        {/* Top highlight line */}
        <div className="absolute top-0 left-0 right-0 h-[1px] bg-gradient-to-r from-transparent via-white/[0.08] to-transparent" />
      </div>

      {/* Content */}
      <div className="relative z-10 flex items-center justify-between h-full px-4 gap-3">
        {/* Left: Search */}
        <div className="flex items-center gap-3 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20" />
            <input
              placeholder="Search symbols, agents, commands... (Cmd+K)"
              className="w-full h-8 pl-9 pr-3 text-xs rounded-xl bg-white/[0.04] border border-white/[0.06] text-white/70 placeholder:text-white/20 focus:outline-none focus:border-emerald-500/30 focus:bg-white/[0.06] transition-all duration-200"
            />
            <kbd className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-white/20 font-mono px-1.5 py-0.5 rounded-md bg-white/[0.04] border border-white/[0.06] hidden md:inline">
              ⌘K
            </kbd>
          </div>
        </div>

        {/* Right: Actions */}
        <div className="flex items-center gap-2">
          {/* Connection Status */}
          <div className={cn(
            "flex items-center gap-1.5 px-2.5 py-1 rounded-lg border transition-all duration-300",
            isConnected
              ? "bg-emerald-500/8 border-emerald-500/15"
              : "bg-amber-500/8 border-amber-500/15",
          )}>
            {isConnected ? (
              <>
                <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)] animate-pulse" />
                <span className="text-[10px] font-medium text-emerald-400 font-mono">LIVE</span>
              </>
            ) : (
              <>
                <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
                <span className="text-[10px] font-medium text-amber-400 font-mono">
                  {connectionError ? "RECONNECT" : "OFFLINE"}
                </span>
              </>
            )}
          </div>

          {/* Kill Switch */}
          {killSwitch && (
            <Badge variant="danger" className="animate-pulse text-[10px] px-2 py-0.5">
              KILL
            </Badge>
          )}

          {/* Refresh */}
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={() => refreshAll()} title="Refresh data">
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>

          {/* Theme Toggle */}
          <Button variant="ghost" size="icon" className="h-8 w-8" onClick={toggle} title={`Switch to ${resolved === "dark" ? "light" : "dark"} mode`}>
            {resolved === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
          </Button>

          {/* Notifications */}
          <Button variant="ghost" size="icon" className="h-8 w-8 relative" title="Notifications">
            <Bell className="w-3.5 h-3.5" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 min-w-[14px] h-3.5 px-1 bg-red-500 rounded-full text-[8px] font-bold flex items-center justify-center text-white shadow-[0_0_8px_rgba(239,68,68,0.4)]">
                {unreadCount > 9 ? "9+" : unreadCount}
              </span>
            )}
          </Button>

          {/* System Status Dot */}
          <div className="hidden md:flex items-center gap-2 pl-2 border-l border-white/[0.06]">
            <div className={cn(
              "w-2 h-2 rounded-full transition-colors duration-300",
              isConnected ? "bg-emerald-500 animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.4)]" : "bg-white/20",
            )} />
            <span className="text-[11px] text-white/30 font-mono">ONLINE</span>
          </div>
        </div>
      </div>
    </header>
  );
}
