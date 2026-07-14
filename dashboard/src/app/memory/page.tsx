"use client";
export const dynamic = "force-dynamic";

import React from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { memoryApi } from '@/lib/api-client';
import type { MemoryEntry } from '@/lib/api-client';
import { useEffect, useState } from 'react';

export default function MemoryPage() {
  const [entries, setEntries] = useState<MemoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    memoryApi.search('')
      .then(res => { setEntries(res.entries); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  const filtered = entries.filter(m => (filter === 'all' || m.type === filter) && m.content.toLowerCase().includes(searchQuery.toLowerCase()));

  if (loading) return <div className="relative z-10"><p className="text-white/40">Loading memory entries...</p></div>;
  if (error) return <div className="relative z-10"><p className="text-red-400">Error: {error}</p></div>;

  const typeColors: Record<string, string> = {
    knowledge: 'bg-purple-500/20 text-purple-400',
    session: 'bg-cyan-500/20 text-cyan-400',
    vector: 'bg-emerald-500/20 text-emerald-400',
    condenser: 'bg-amber-500/20 text-amber-400',
    paging: 'bg-red-500/20 text-red-400',
  };

  return (
    <div className="relative z-10 space-y-6">
        <div className="flex items-center gap-4">
          <input type="text" placeholder="Search memory..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm flex-1 max-w-md focus:outline-none focus:border-cyan-500/50" />
          <div className="flex gap-2">
            {['all', 'knowledge', 'session', 'vector', 'condenser'].map(t => (
              <button key={t} onClick={() => setFilter(t)}
                className={`px-3 py-1 rounded-lg text-xs ${filter === t ? 'bg-cyan-500/20 text-cyan-400 border border-cyan-500/30' : 'bg-white/5 text-white/40 border border-white/10'}`}>
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="col-span-2 space-y-3">
            {filtered.map(entry => (
              <Card key={entry.id}>
                <div className="space-y-2">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${typeColors[entry.type] || 'bg-white/10 text-white/40'}`}>{entry.type}</span>
                      <span className="text-white/60 text-sm font-mono">{entry.key}</span>
                    </div>
                    <span className="text-white/30 text-[10px]">Relevance: {entry.relevance}</span>
                  </div>
                  <p className="text-white/50 text-xs leading-relaxed">{entry.content}</p>
                  <div className="text-white/20 text-[10px]">{new Date(entry.timestamp).toLocaleString()}</div>
                </div>
              </Card>
            ))}
          </div>

          {/* Store Memory Panel */}
          <Card className="sticky top-20">
            <div className="px-4 pt-4 pb-2">
              <h3 className="text-sm font-medium text-white/70">Store Memory</h3>
            </div>
            <div className="px-4 pb-4 space-y-4">
              <div>
                <label className="text-white/40 text-xs block mb-1">Key</label>
                <input type="text" className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm focus:outline-none focus:border-cyan-500/50" />
              </div>
              <div>
                <label className="text-white/40 text-xs block mb-1">Type</label>
                <select className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-sm">
                  <option value="knowledge">Knowledge</option>
                  <option value="session">Session</option>
                  <option value="vector">Vector</option>
                  <option value="condenser">Condenser</option>
                </select>
              </div>
              <div>
                <label className="text-white/40 text-xs block mb-1">Content</label>
                <textarea className="w-full h-24 bg-white/5 border border-white/10 rounded-lg p-2 text-white text-xs focus:outline-none focus:border-cyan-500/50" />
              </div>
              <button className="w-full py-2 rounded-lg bg-gradient-to-r from-purple-500 to-cyan-500 text-white text-sm font-medium hover:opacity-90 transition">
                Store
              </button>
            </div>
          </Card>
        </div>
      </div>

  );
}
