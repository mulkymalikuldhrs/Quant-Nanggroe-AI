'use client';
import AppLayout from '@/components/layout/app-layout';
import { GlassCard } from '@/components/shared/cards';
import { mockColonies, mockAgents } from '@/lib/mock-data';

export default function ColonyPage() {
  return (
    <AppLayout title="Colony">
      <div className="relative z-10 space-y-6">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Colony Network Topology */}
          <GlassCard title="Network Topology" className="col-span-2">
            <div className="grid grid-cols-4 gap-3">
              {mockAgents.map((agent, i) => (
                <div key={agent.id} className={`p-3 rounded-lg border text-center transition-all hover:scale-105 ${
                  agent.status === 'active' ? 'bg-cyan-500/5 border-cyan-500/20' :
                  agent.status === 'error' ? 'bg-red-500/5 border-red-500/20' :
                  'bg-white/[0.02] border-white/5'
                }`}>
                  <div className={`w-8 h-8 rounded-full mx-auto mb-2 flex items-center justify-center text-xs font-bold ${
                    agent.status === 'active' ? 'bg-cyan-500/20 text-cyan-400' :
                    agent.status === 'error' ? 'bg-red-500/20 text-red-400' :
                    'bg-white/5 text-white/30'
                  }`}>{agent.type[0].toUpperCase()}</div>
                  <div className="text-white/70 text-[10px] truncate">{agent.name}</div>
                  <div className="text-white/30 text-[9px]">{agent.status}</div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Colony Details */}
          <div className="space-y-4">
            {mockColonies.map(colony => (
              <GlassCard key={colony.id}>
                <div className="space-y-3">
                  <div className="flex items-center justify-between">
                    <h3 className="text-white font-medium text-sm">{colony.name}</h3>
                    <span className={`text-[10px] px-2 py-0.5 rounded-full ${
                      colony.status === 'active' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'
                    }`}>{colony.status}</span>
                  </div>
                  <div className="space-y-2">
                    <div className="flex justify-between text-[10px]"><span className="text-white/30">Health</span><span className="text-white/60">{colony.health}%</span></div>
                    <div className="h-2 rounded-full bg-white/5"><div className="h-full rounded-full bg-gradient-to-r from-cyan-500 to-emerald-500" style={{ width: `${colony.health}%` }} /></div>
                    <div className="flex justify-between text-[10px]"><span className="text-white/30">Capacity</span><span className="text-white/60">{colony.agents}/{colony.capacity}</span></div>
                    <div className="h-2 rounded-full bg-white/5"><div className="h-full rounded-full bg-purple-500/60" style={{ width: `${(colony.agents/colony.capacity)*100}%` }} /></div>
                  </div>
                  <div className="text-white/30 text-[10px]">Schedule: {colony.schedule}</div>
                </div>
              </GlassCard>
            ))}
            <button className="w-full py-3 rounded-lg bg-cyan-500/10 border border-cyan-500/20 text-cyan-400 text-sm hover:bg-cyan-500/20 transition">
              + Create Colony
            </button>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
