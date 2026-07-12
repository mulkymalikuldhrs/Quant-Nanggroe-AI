"use client";
export const dynamic = "force-dynamic";


import { securityApi } from '@/lib/api-client';
import type { SecurityEvent } from '@/lib/api-client';
import { useEffect, useState } from 'react';

export default function SecurityPage() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    securityApi.getEvents()
      .then(d => { setEvents(d); setLoading(false); })
      .catch(err => { setError(err.message); setLoading(false); });
  }, []);

  if (loading) return <div className="relative z-10"><p className="text-white/40">Loading security events...</p></div>;
  if (error) return <div className="relative z-10"><p className="text-red-400">Error: {error}</p></div>;

  const severityStyles: Record<string, string> = {
    info: 'border-cyan-500/20 bg-cyan-500/5',
    warning: 'border-amber-500/20 bg-amber-500/5',
    critical: 'border-red-500/20 bg-red-500/5',
  };
  const severityDots: Record<string, string> = {
    info: 'bg-cyan-500', warning: 'bg-amber-500', critical: 'bg-red-500',
  };

  return (
    <div className="relative z-10 space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <GlassCard>
            <div className="text-center">
              <div className="text-3xl font-bold text-cyan-400">{events.filter(e => e.severity === 'info').length}</div>
              <div className="text-white/30 text-xs mt-1">Info Events</div>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="text-center">
              <div className="text-3xl font-bold text-amber-400">{events.filter(e => e.severity === 'warning').length}</div>
              <div className="text-white/30 text-xs mt-1">Warnings</div>
            </div>
          </GlassCard>
          <GlassCard>
            <div className="text-center">
              <div className="text-3xl font-bold text-red-400">{events.filter(e => e.severity === 'critical').length}</div>
              <div className="text-white/30 text-xs mt-1">Critical</div>
            </div>
          </GlassCard>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Audit Log */}
          <GlassCard title="Audit Log" className="col-span-2">
            <div className="space-y-2">
              {events.map(event => (
                <div key={event.id} className={`p-3 rounded-lg border ${severityStyles[event.severity] || 'border-white/5'}`}>
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <div className={`w-2 h-2 rounded-full ${severityDots[event.severity]}`} />
                      <span className="text-white/70 text-xs font-medium">{event.type.replace(/_/g, ' ').toUpperCase()}</span>
                    </div>
                    <span className="text-white/20 text-[10px]">{new Date(event.timestamp).toLocaleString()}</span>
                  </div>
                  <p className="text-white/50 text-xs ml-4">{event.detail}</p>
                  <div className="text-white/20 text-[10px] ml-4 mt-1">Agent: {event.agent}</div>
                </div>
              ))}
            </div>
          </GlassCard>

          {/* Sandbox & Permissions */}
          <div className="space-y-4">
            <GlassCard title="Sandbox Status">
              <div className="space-y-3">
                {[
                  { name: 'Docker Sandbox', status: 'running', cpu: 34, memory: 52 },
                  { name: 'WASM Sandbox', status: 'idle', cpu: 0, memory: 8 },
                ].map(sb => (
                  <div key={sb.name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-white/70 text-xs font-medium">{sb.name}</span>
                      <span className={`text-[10px] px-2 py-0.5 rounded-full ${sb.status === 'running' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-white/5 text-white/30'}`}>{sb.status}</span>
                    </div>
                    <div className="grid grid-cols-2 gap-2">
                      <div>
                        <div className="text-[10px] text-white/30">CPU</div>
                        <div className="text-xs text-cyan-400">{sb.cpu}%</div>
                      </div>
                      <div>
                        <div className="text-[10px] text-white/30">Memory</div>
                        <div className="text-xs text-purple-400">{sb.memory}%</div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </GlassCard>

            <GlassCard title="Permission Rules">
              <div className="space-y-2">
                {[
                  { rule: 'shell_execution', scope: 'executor', action: 'grant' },
                  { rule: 'file_write_etc', scope: 'all', action: 'deny' },
                  { rule: 'docker_management', scope: 'colony', action: 'grant' },
                  { rule: 'network_access', scope: 'browser', action: 'grant' },
                ].map(p => (
                  <div key={p.rule} className="flex items-center justify-between p-2 rounded bg-white/[0.02]">
                    <span className="text-white/50 text-xs font-mono">{p.rule}</span>
                    <span className={`text-[10px] px-2 py-0.5 rounded ${p.action === 'grant' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'}`}>{p.action}</span>
                  </div>
                ))}
              </div>
            </GlassCard>
          </div>
        </div>
      </div>

  );
}
