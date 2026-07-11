"use client";

import React from "react";
import { Sidebar } from "@/components/dashboard/sidebar";
import { useWebSocket } from "@/lib/use-websocket";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { TooltipProvider } from "@/components/ui/tooltip";

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
    <TooltipProvider>
      <div className="flex min-h-screen grid-bg">
        <Sidebar />
        <main
          className={cn(
            "flex-1 transition-all duration-300 overflow-auto",
            sidebarOpen ? "ml-64" : "ml-16"
          )}
        >
          <div className="p-6 max-w-[1800px] mx-auto">{children}</div>
        </main>
      </div>
    </TooltipProvider>
  );
}
