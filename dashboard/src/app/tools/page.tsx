'use client';
import AppLayout from '@/components/layout/app-layout';
import { GlassCard } from '@/components/shared/cards';
import { useState, useEffect } from 'react';
import apiRequest from '@/lib/api-client';
import { Loader2 } from 'lucide-react';

interface Tool {
  id: string; name: string; category: string; description: string;
  executions: number; lastUsed: string;
}

export default function ToolsPage() {
  const [tools, setTools] = useState<Tool[]>([]);
  const [selectedTool, setSelectedTool] = useState<string | null>(null);
  const [params, setParams] = useState('{}');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const data = await apiRequest<Tool[]>('/api/v1/tools');
        setTools(data);
      } catch {
        setTools([]);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const categories = [...new Set(tools.map(t => t.category))];
  const categoryIcons: Record<string, string> = { web: '🌐', dev: '💻', infra: '🏗️', system: '📁', protocol: '🔗', cognitive: '🧠', media: '🎙️', comms: '📡' };

  if (loading) {
    return (
      <AppLayout title="Tools">
        <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 text-cyan-400 animate-spin" /></div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Tools">
      <div className="relative z-10 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="col-span-2 space-y-4">
            {categories.length > 0 ? categories.map(cat => (
              <GlassCard key={cat} title={`${categoryIcons[cat] || '🔧'} ${cat.toUpperCase()}`}>
                <div className="grid grid-cols-2 gap-3">
                  {tools.filter(t => t.category === cat).map(tool => (
                    <div key={tool.id} onClick={() => setSelectedTool(tool.id)}
                      className={`p-3 rounded-lg border cursor-pointer transition-all hover:scale-[1.02] ${selectedTool === tool.id ? 'bg-cyan-500/10 border-cyan-500/30' : 'bg-white/[0.02] border-white/5'}`}>
                      <div className="flex items-center justify-between mb-1"><span className="text-white text-sm font-medium">{tool.name}</span><span className="text-white/30 text-[10px]">{tool.executions} runs</span></div>
                      <p className="text-white/40 text-xs">{tool.description}</p>
                      <div className="text-white/20 text-[10px] mt-1">Last: {tool.lastUsed}</div>
                    </div>
                  ))}
                </div>
              </GlassCard>
            )) : <GlassCard><p className="text-sm text-white/30 text-center py-8">No tools available</p></GlassCard>}
          </div>
          <GlassCard title="Execute Tool" className="sticky top-20">
            <div className="space-y-4">
              <div><label className="text-white/40 text-xs block mb-1">Selected Tool</label><div className="p-2 rounded bg-white/5 text-white/70 text-sm">{selectedTool || 'None'}</div></div>
              <div><label className="text-white/40 text-xs block mb-1">Parameters (JSON)</label><textarea value={params} onChange={e => setParams(e.target.value)} className="w-full h-32 bg-white/5 border border-white/10 rounded-lg p-2 text-white/70 text-xs font-mono focus:outline-none focus:border-cyan-500/50" /></div>
              <button className="w-full py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium hover:opacity-90 transition">Execute</button>
              <div><label className="text-white/40 text-xs block mb-1">Result</label><div className="p-3 rounded-lg bg-white/[0.02] border border-white/5 min-h-[100px]"><p className="text-white/20 text-xs italic">No result yet.</p></div></div>
            </div>
          </GlassCard>
        </div>
      </div>
    </AppLayout>
  );
}
