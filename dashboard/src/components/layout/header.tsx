"use client";

import { useAppStore } from "@/lib/store";
import { Bell, Moon, Sun, Wifi, WifiOff, Search } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import { useRealtimeData } from "@/lib/websocket";
import { useTheme } from "next-themes";

export function Header() {
  const { sidebarOpen, killSwitch } = useAppStore();
  const { isConnected } = useRealtimeData();
  const { theme, setTheme } = useTheme();

  return (
    <header
      className={cn(
        "fixed top-0 right-0 z-30 h-14 border-b border-white/[0.06] bg-[#0a0a1a]/90 backdrop-blur-xl flex items-center justify-between px-4 transition-all duration-300",
        sidebarOpen ? "left-60" : "left-16",
      )}
    >
      <div className="flex items-center gap-3">
        <div className="relative w-64">
          <Input
            placeholder="Search symbols, agents..."
            icon={<Search className="w-3.5 h-3.5" />}
            className="h-8 text-xs"
          />
        </div>
      </div>

      <div className="flex items-center gap-3">
        {/* Connection Status */}
        <div className="flex items-center gap-1.5">
          {isConnected ? (
            <>
              <Wifi className="w-3.5 h-3.5 text-emerald-400" />
              <span className="text-xs text-emerald-400 hidden sm:inline">Live</span>
            </>
          ) : (
            <>
              <WifiOff className="w-3.5 h-3.5 text-white/30" />
              <span className="text-xs text-white/30 hidden sm:inline">Offline</span>
            </>
          )}
        </div>

        {/* Kill Switch Indicator */}
        {killSwitch && (
          <Badge variant="danger" className="animate-pulse">
            KILL
          </Badge>
        )}

        {/* Theme Toggle */}
        <Button
          variant="ghost"
          size="icon"
          className="h-8 w-8"
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
        >
          {theme === "dark" ? <Sun className="w-3.5 h-3.5" /> : <Moon className="w-3.5 h-3.5" />}
        </Button>

        {/* Notifications */}
        <Button variant="ghost" size="icon" className="h-8 w-8 relative">
          <Bell className="w-3.5 h-3.5" />
          <span className="absolute -top-0.5 -right-0.5 w-3.5 h-3.5 bg-red-500 rounded-full text-[8px] flex items-center justify-center text-white">
            3
          </span>
        </Button>

        {/* System Status */}
        <div className="hidden md:flex items-center gap-2 pl-2 border-l border-white/[0.06]">
          <div className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse shadow-[0_0_6px_rgba(16,185,129,0.5)]" />
          <span className="text-xs text-white/40">System Online</span>
        </div>
      </div>
    </header>
  );
}
