'use client';
import { useState, useEffect } from 'react';
import { ChartCard } from '@/components/shared/chart-card';

export default function MemoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [entries, setEntries] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/memory/search?q=" + searchQuery).then(r => r.json()).then(d => setEntries(d.entries || []));
  }, [searchQuery]);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white">Memory</h1>
      <input
        type="text"
        placeholder="Search memory..."
        value={searchQuery}
        onChange={e => setSearchQuery(e.target.value)}
        className="w-full max-w-md bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white"
      />
      <ChartCard title="Memory Entries" subtitle="Live from /api/memory/search">
        <div className="space-y-2">
          {entries.map((e: any) => (
            <div key={e.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-[10px] bg-cyan-500/20 text-cyan-400 px-2 py-0.5 rounded-full">{e.type}</span>
              <p className="text-xs text-white/70 mt-1 font-mono">{e.key}</p>
              <p className="text-xs text-white/40 mt-1 line-clamp-2">{e.content}</p>
            </div>
          ))}
          {entries.length === 0 && <p className="text-white/40 text-sm">No entries or API not available</p>}
        </div>
      </ChartCard>
    </div>
  );
}