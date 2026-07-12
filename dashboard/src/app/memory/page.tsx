'use client';
import AppLayout from '@/components/layout/app-layout';
import { GlassCard } from '@/components/shared/cards';
import { mockMemoryEntries } from '@/lib/mock-data';
import { useState } from 'react';

export default function MemoryPage() {
  const [searchQuery, setSearchQuery] = useState('');
  const [filter, setFilter] = useState('all');
  const filtered = mockMemoryEntries.filter(m => (filter === 'all' || m.type === filter) && m.content.toLowerCase().includes(searchQuery.toLowerCase()));

  const typeColors: Record<string, string> = {
    knowledge: 'bg-purple-500/20 text-purple-400',
    session: 'bg-cyan-500/20 text-cyan-400',
    vector: 'bg-emerald-500/20 text-emerald-400',
    condenser: 'bg-amber-500/20 text-amber-400',
    paging: 'bg-red-500/20 text-red-400',
  };

  return (
    <AppLayout title="Memory">
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
              <GlassCard key={entry.id}>
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
              </GlassCard>
            ))}
          </div>

          {/* Store Memory Panel */}
          <GlassCard title="Store Memory" className="sticky top-20">
            <div className="space-y-4">
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
          </GlassCard>
        </div>
      </div>
    </AppLayout>
  );
}
