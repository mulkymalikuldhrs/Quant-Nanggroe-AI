'use client';
import AppLayout from '@/components/layout/app-layout';
import { GlassCard } from '@/components/shared/cards';
import { useState, useEffect } from 'react';
import apiRequest from '@/lib/api-client';
import { Loader2 } from 'lucide-react';

interface SecurityEvent {
  id: number; severity: string; type: string; detail: string;
  agent: string; timestamp: number;
}

interface SandboxItem {
  name: string; status: string; cpu: number; memory: number;
}

interface PermissionRule {
  rule: string; scope: string; action: string;
}

export default function SecurityPage() {
  const [events, setEvents] = useState<SecurityEvent[]>([]);
  const [sandboxes, setSandboxes] = useState<SandboxItem[]>([]);
  const [permissions, setPermissions] = useState<PermissionRule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [evts, sbs, perms] = await Promise.all([
          apiRequest<SecurityEvent[]>('/api/v1/security/events').catch(() => []),
          apiRequest<SandboxItem[]>('/api/v1/security/sandboxes').catch(() => []),
          apiRequest<PermissionRule[]>('/api/v1/security/permissions').catch(() => []),
        ]);
        setEvents(evts);
        setSandboxes(sbs);
        setPermissions(perms);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  const severityStyles: Record<string, string> = { info: 'border-cyan-500/20 bg-cyan-500/5', warning: 'border-amber-500/20 bg-amber-500/5', critical: 'border-red-500/20 bg-red-500/5' };
  const severityDots: Record<string, string> = { info: 'bg-cyan-500', warning: 'bg-amber-500', critical: 'bg-red-500' };

  if (loading) {
    return (
      <AppLayout title="Security">
        <div className="flex items-center justify-center h-64"><Loader2 className="w-8 h-8 text-cyan-400 animate-spin" /></div>
      </AppLayout>
    );
  }

  return (
    <AppLayout title="Security">
      <div className="relative z-10 space-y-6">
        <div className="grid grid-cols-3 gap-4">
          <GlassCard><div className="text-center"><div className="text-3xl font-bold text-cyan-400">{events.filter(e => e.severity === 'info').length}</div><div className="text-white/30 text-xs mt-1">Info Events</div></div></GlassCard>
          <GlassCard><div className="text-center"><div className="text-3xl font-bold text-amber-400">{events.filter(e => e.severity === 'warning').length}</div><div className="text-white/30 text-xs mt-1">Warnings</div></div></GlassCard>
          <GlassCard><div className="text-center"><div className="text-3xl font-bold text-red-400">{events.filter(e => e.severity === 'critical').length}</div><div className="text-white/30 text-xs mt-1">Critical</div></div></GlassCard>
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <GlassCard title="Audit Log" className="col-span-2">
            {events.length > 0 ? (
              <div className="space-y-2">{events.map(event => (
                <div key={event.id} className={`p-3 rounded-lg border ${severityStyles[event.severity] || 'border-white/5'}`}>
                  <div className="flex items-center justify-between mb-1"><div className="flex items-center gap-2"><div className={`w-2 h-2 rounded-full ${severityDots[event.severity]}`} /><span className="text-white/70 text-xs font-medium">{event.type.replace(/_/g,' ').toUpperCase()}</span></div><span className="text-white/20 text-[10px]">{new Date(event.timestamp).toLocaleString()}</span></div>
                  <p className="text-white/50 text-xs ml-4">{event.detail}</p>
                </div>
              ))}</div>
            ) : <p className="text-sm text-white/30 text-center py-8">No security events</p>}
          </GlassCard>
          <div className="space-y-4">
            <GlassCard title="Sandbox Status">
              {sandboxes.length > 0 ? (
                <div className="space-y-3">{sandboxes.map(sb => (
                  <div key={sb.name} className="p-3 rounded-lg bg-white/[0.02] border border-white/5"><div className="flex items-center justify-between mb-2"><span className="text-white/70 text-xs font-medium">{sb.name}</span><span className={`text-[10px] px-2 py-0.5 rounded-full ${sb.status==='running'?'bg-emerald-500/10 text-emerald-400':'bg-white/5 text-white/30'}`}>{sb.status}</span></div><div className="grid grid-cols-2 gap-2"><div><div className="text-[10px] text-white/30">CPU</div><div className="text-xs text-cyan-400">{sb.cpu}%</div></div><div><div className="text-[10px] text-white/30">Memory</div><div className="text-xs text-purple-400">{sb.memory}%</div></div></div></div>
                ))}</div>
              ) : <p className="text-sm text-white/30 text-center py-4">No sandbox data</p>}
            </GlassCard>
            <GlassCard title="Permission Rules">
              {permissions.length > 0 ? (
                <div className="space-y-2">{permissions.map(p => (
                  <div key={p.rule} className="flex items-center justify-between p-2 rounded bg-white/[0.02]"><span className="text-white/50 text-xs font-mono">{p.rule}</span><span className={`text-[10px] px-2 py-0.5 rounded ${p.action==='grant'?'bg-emerald-500/10 text-emerald-400':'bg-red-500/10 text-red-400'}`}>{p.action}</span></div>
                ))}</div>
              ) : <p className="text-sm text-white/30 text-center py-4">No permission rules</p>}
            </GlassCard>
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
