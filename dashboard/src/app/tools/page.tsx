"use client";

import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Wrench, Terminal } from "lucide-react";

interface Tool { name: string; desc: string; group: string; }

const TOOLS: Tool[] = [
  { name: "qna-paper-daemon", desc: "Live paper trading daemon", group: "trading" },
  { name: "qna-watchdog", desc: "Auto-restart & health monitor", group: "ops" },
  { name: "qna-export", desc: "CSV / ZIP export", group: "data" },
  { name: "paper_completion_gate", desc: "30-day paper validation gate", group: "risk" },
  { name: "graphify", desc: "Codebase knowledge graph builder", group: "dev" },
  { name: "agent-ctx", desc: "Agent context inspector", group: "dev" },
];

export default function ToolsPage() {
  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Wrench className="w-5 h-5 text-cyan-400" /> Tools
      </h1>

      <ChartCard title="Available Scripts" subtitle="QNA toolchain">
        <div className="grid md:grid-cols-2 gap-2">
          {TOOLS.map((t, i) => (
            <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] flex items-start gap-2">
              <Terminal className="w-4 h-4 text-cyan-400 mt-0.5" />
              <div>
                <span className="text-sm font-mono text-cyan-400">{t.name}</span>
                <Badge variant="default" className="text-[9px] ml-2">{t.group}</Badge>
                <p className="text-xs text-white/40 mt-1">{t.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </ChartCard>
    </div>
  );
}
