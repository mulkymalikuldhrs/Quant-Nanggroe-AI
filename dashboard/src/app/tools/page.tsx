'use client';
import { ChartCard } from '@/components/shared/chart-card';

export default function ToolsPage() {
  const tools = [
    { name: "qna-paper-daemon", desc: "Live paper trading daemon" },
    { name: "qna-watchdog", desc: "Auto-restart daemon" },
    { name: "qna-export", desc: "CSV/ZIP export" },
    { name: "paper_completion_gate", desc: "30-day validation" },
  ];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Tools</h1>
      <ChartCard title="Available Scripts" subtitle="QNA toolchain">
        <div className="space-y-2">
          {tools.map((t, i) => (
            <div key={i} className="p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm font-mono text-cyan-400">{t.name}</span>
              <p className="text-xs text-white/40 mt-1">{t.desc}</p>
            </div>
          ))}
        </div>
      </ChartCard>
    </div>
  );
}