'use client';
import { useEffect, useState } from 'react';
import { ChartCard } from '@/components/shared/chart-card';

export default function ColonyPage() {
  const [data, setData] = useState<any>(null);

  useEffect(() => {
    fetch("/api/colony/list").then(r => r.json()).then(setData).catch(() => null);
  }, []);

  const colonies = data || [];

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Colony</h1>
      <ChartCard title="Colonies" subtitle="Live from /api/colony/list">
        <div className="space-y-3">
          {colonies.map((c: any) => (
            <div key={c.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div className="flex justify-between">
                <span className="text-sm font-medium text-white">{c.name}</span>
                <span className="text-[10px] bg-emerald-500/10 text-emerald-400 px-2 py-0.5 rounded-full">{c.status}</span>
              </div>
              <div className="mt-2 space-y-1">
                <p className="text-xs text-white/40">Health: {c.health}%</p>
                <p className="text-xs text-white/40">Agents: {c.agents}/{c.capacity}</p>
              </div>
            </div>
          ))}
          {colonies.length === 0 && <p className="text-white/40 text-sm">Connect to /api/colony/list</p>}
        </div>
      </ChartCard>
    </div>
  );
}