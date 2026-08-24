"use client";

import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { AssistantWidget } from "@/components/assistant/assistant-widget";

export function AppLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050510] text-white overflow-hidden">
      {/* Ambient background orbs */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden">
        <div className="orb orb-1" />
        <div className="orb orb-2" />
        <div className="orb orb-3" />
      </div>

      {/* Noise overlay */}
      <div className="noise-overlay" />

      {/* Fluid Island Navigation */}
      <Sidebar />

      {/* Header */}
      <Header />

      {/* Main Content */}
      <main className="relative z-10 pt-[68px]">
        <div className="p-4 lg:p-6 max-w-[1600px] mx-auto animate-fade-in">
          <ErrorBoundary>
            {children}
          </ErrorBoundary>
        </div>
      </main>

      {/* QNA Assistant — draggable/resizable floating copilot */}
      <AssistantWidget />
    </div>
  );
}
