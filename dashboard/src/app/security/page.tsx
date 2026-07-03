'use client';
import { useEffect, useState } from 'react';
import { ChartCard } from '@/components/shared/chart-card';
import { Shield } from 'lucide-react';

export default function SecurityPage() {
  const [events, setEvents] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/security/events").then(r => r.json()).then(d => setEvents(d.events || [])).catch(() => null);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Shield className="w-5 h-5 text-cyan-400" />
        Security
      </h1>
      <ChartCard title="Security Events" subtitle="Live from /api/security/events">
        <div className="space-y-2">
          {events.map((e: any) => (
            <div key={e.id} className="p-3 rounded-lg border border-white/[0.04] bg-white/[0.02]">
              <span className="text-xs text-cyan-400">{e.type}</span>
              <p className="text-xs text-white/50 mt-1">{e.detail}</p>
            </div>
          ))}
          {events.length === 0 && <p className="text-white/40 text-sm">No events or API not available</p>}
        </div>
      </ChartCard>
    </div>
  );
}