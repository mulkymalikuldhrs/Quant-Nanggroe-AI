"use client";

import { useAppStore } from "@/lib/store";
import { useRealtimeData } from "@/lib/websocket";
import { useTheme } from "@/components/providers/theme-provider";
import { Bell, Sun, Moon, Wifi, WifiOff, RefreshCw, Search } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function Header() {
  const { killSwitch, notifications, refreshAll } = useAppStore();
  const { isConnected, connectionError } = useRealtimeData();
  const { resolved, toggle } = useTheme();

  const unreadCount = notifications.length;

  return (
    <header className="sticky top-[68px] z-20">
      <div className="flex items-center justify-between h-12 px-4">
        {/* Spacer - island nav handles navigation */}
        <div className="flex-1" />

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

          {/* Kill Switch Badge */}
          {killSwitch && (
            <div className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-red-500/10 border border-red-500/20 animate-pulse">
              <div className="w-1.5 h-1.5 rounded-full bg-red-500 shadow-[0_0_6px_rgba(239,68,68,0.5)]" />
              <span className="text-[10px] font-medium text-red-400 font-mono">KILL</span>
            </div>
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

          {/* Connection error tooltip */}
          {connectionError && (
            <span className="hidden md:inline text-[10px] text-amber-400/60 font-mono max-w-[200px] truncate" title={connectionError}>
              {connectionError}
            </span>
          )}
        </div>
      </div>
    </header>
  );
}
