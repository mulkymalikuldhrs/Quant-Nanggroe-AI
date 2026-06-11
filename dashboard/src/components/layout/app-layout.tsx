"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { sidebarOpen } = useAppStore();

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[800px] h-[800px] bg-emerald-500/[0.02] rounded-full blur-[150px]" />
        <div className="absolute -bottom-1/2 -right-1/4 w-[600px] h-[600px] bg-blue-500/[0.02] rounded-full blur-[150px]" />
      </div>

      <Sidebar />
      <Header />

      <main
        className={cn(
          "pt-14 min-h-screen transition-all duration-300",
          sidebarOpen ? "pl-60" : "pl-16",
        )}
      >
        <div className="p-4 lg:p-6">{children}</div>
      </main>
    </div>
  );
}
