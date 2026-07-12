"use client";

import React, { useState, useEffect } from "react";
import { Sidebar } from "@/components/dashboard/sidebar";
import { useWebSocket } from "@/lib/use-websocket";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { TooltipProvider } from "@/components/ui/tooltip";
import { Search, Clock, Bell } from "lucide-react";

function TopBar() {
  const [time, setTime] = useState<Date | null>(null);

  useEffect(() => {
    setTime(new Date());
    const timer = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <header className="h-16 border-b border-border/50 bg-background/50 backdrop-blur-xl flex items-center justify-between px-6 sticky top-0 z-30">
      <div className="flex items-center gap-4">
        <div className="relative group">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground group-focus-within:text-cyan transition-colors" />
          <input
            type="text"
            placeholder="Search commands, agents, markets..."
            className="bg-secondary/30 border border-border/50 rounded-full pl-9 pr-4 py-1.5 text-sm focus:outline-none focus:border-cyan/50 focus:ring-1 focus:ring-cyan/50 w-64 transition-all duration-300 focus:w-80"
          />
        </div>
      </div>
      <div className="flex items-center gap-4">
        <div className="flex items-center gap-2 text-sm font-mono text-muted-foreground bg-secondary/20 px-3 py-1.5 rounded-lg border border-border/50">
          <Clock className="w-4 h-4 text-cyan" />
          {time ? time.toLocaleTimeString() : "--:--:--"}
        </div>
        <button className="relative p-2 rounded-full hover:bg-secondary/50 transition-colors scale-tap">
          <Bell className="w-4 h-4 text-muted-foreground" />
          <span className="absolute top-1 right-1 w-2 h-2 bg-rose rounded-full animate-pulse-glow" />
        </button>
      </div>
    </header>
  );
}

export function AppShell({ children }: { children: React.ReactNode }) {
  const { sidebarOpen, setWsConnected, addEvent } = useAppStore();

  useWebSocket({
    onConnect: () => setWsConnected(true),
    onDisconnect: () => setWsConnected(false),
    onMessage: (msg) => {
      addEvent({
        id: `ws-${Date.now()}`,
        type: msg.type || "system",
        message:
          typeof msg.data === "string" ? msg.data : JSON.stringify(msg.data),
        timestamp: msg.timestamp || new Date().toISOString(),
        severity: "info",
      });
    },
  });

  return (
    <TooltipProvider delayDuration={200}>
      <div className="flex min-h-screen grid-bg relative overflow-hidden">
        {/* Ambient background particles/glows */}
        <div className="ambient-glow ambient-glow-cyan" />
        <div className="ambient-glow ambient-glow-purple" />
        
        <Sidebar />
        
        <main
          className={cn(
            "flex-1 transition-all duration-300 overflow-y-auto overflow-x-hidden relative z-10",
            sidebarOpen ? "ml-64" : "ml-16"
          )}
        >
          <TopBar />
          <div className="p-6 max-w-[1800px] mx-auto animate-fade-in">{children}</div>
        </main>
      </div>
    </TooltipProvider>
  );
}
