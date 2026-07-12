"use client";
export const dynamic = "force-dynamic";


import { toolsApi } from '@/lib/api-client';
import type { Tool } from '@/lib/api-client';
import { useEffect, useState } from 'react';

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [params, setParams] = useState('{}');

  useEffect(() => {
    toolsApi.list()
      .then(d => { setTools(d); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="relative z-10"><p className="text-white/40">Loading tools...</p></div>;
  if (error) return <div className="relative z-10"><p className="text-red-400">Error: {error}</p></div>;

  const categories = [...new Set(tools.map(t => t.category))];
  const categoryIcons: Record<string, string> = { web: '🌐', dev: '💻', infra: '🏗️', system: '📁', protocol: '🔗', cognitive: '🧠', media: '🎙️', comms: '📡' };

  return (
    <div className="relative z-10 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="col-span-2 space-y-4">
            {categories.map(cat => (
              <GlassCard key={cat} title={`${categoryIcons[cat] || '🔧'} ${cat.toUpperCase()}`}>
                <div className="grid grid-cols-2 gap-3">
                  {tools.filter(t => t.category === cat).map(tool => (
                    <div key={tool.id} onClick={() => setSelectedTool(tool.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02] ${
                        selectedTool === tool.id ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-white/[0.02] border-white/5'
                      }`}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-white text-sm font-medium">{tool.name}</span>
                        <span className="text-white/30 text-[10px]">{tool.executions} runs</span>
                      </div>
                      <p className="text-white/40 text-xs">{tool.description}</p>
                      <div className="text-white/20 text-[10px] mt-1">Last: {tool.lastUsed}</div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            ))}
          </div>

          {/* Tool Execution Panel */}
          <GlassCard title="Execute Tool" className="sticky top-20">
            <div className="space-y-4">
              <div>
                <label className="text-white/40 text-xs block mb-1">Selected Tool</label>
                <div className="p-2 rounded bg-white/5 text-white/70 text-sm">{selectedTool || 'None'}</div>
              </div>
              <div>
                <label className="text-white/40 text-xs block mb-1">Parameters (JSON)</label>
                <textarea value={params} onChange={e => setParams(e.target.value)}
                  className="w-full h-32 bg-white/5 border border-white/10 rounded-lg p-2 text-white/70 text-xs font-mono focus:outline-none focus:border-cyan-500/50" />
              </div>
              <button className="w-full py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium hover:opacity-90 transition">
                Execute
              </button>
              <div>
                <label className="text-white/40 text-xs block mb-1">Result</label>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 min-h-[100px]">
                  <p className="text-white/20 text-xs italic">No result yet. Execute a tool to see output.</p>
                </div>
              </div>
            </div>
          </GlassCard>
        </div>
      </div>

  );
}
