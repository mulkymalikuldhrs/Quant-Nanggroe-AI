"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import { ErrorBoundary } from "@/components/shared/error-boundary";

export function AppLayout({ children }: { children: React.ReactNode }) {
  const { sidebarOpen } = useAppStore();

  return (
    <div className="min-h-screen bg-[#0a0a1a] text-white overflow-hidden">
      {/* Ambient background glow */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="absolute -top-1/2 -left-1/4 w-[1000px] h-[1000px] bg-emerald-500/[0.015] rounded-full blur-[200px]" />
        <div className="absolute -bottom-1/2 -right-1/4 w-[800px] h-[800px] bg-blue-500/[0.015] rounded-full blur-[200px]" />
        <div className="absolute top-1/3 left-1/2 -translate-x-1/2 w-[600px] h-[600px] bg-purple-500/[0.008] rounded-full blur-[200px]" />
      </div>

      {/* Noise overlay */}
      <div className="noise-overlay" />

      {/* Sidebar */}
      <Sidebar />

      {/* Header */}
      <Header />

      {/* Main Content */}
      <main
        className={cn(
          "pt-14 min-h-screen transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] relative z-10",
          sidebarOpen ? "pl-64" : "pl-[68px]",
        )}
      >
        <div className="p-4 lg:p-6 animate-fade-in">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </div>
      </main>
    </div>
  );
}
