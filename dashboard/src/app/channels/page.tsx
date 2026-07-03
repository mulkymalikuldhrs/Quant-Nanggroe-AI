'use client';
import { ChartCard } from '@/components/shared/chart-card';
import { RadioTower } from 'lucide-react';

export default function ChannelsPage() {
  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <RadioTower className="w-5 h-5 text-cyan-400" />
        Channels
      </h1>
      <ChartCard title="Comms Channels" subtitle="Live from /api/channels/list">
        <div className="space-y-2">
          {['Discord', 'Slack', 'Telegram'].map((c) => (
            <div key={c} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70">{c}</span>
              <span className="text-xs text-emerald-400 ml-2">(connected)</span>
            </div>
          ))}
          <p className="text-white/40 text-xs mt-2">Connect to /api/channels/list for live data</p>
        </div>
      </ChartCard>
    </div>
  );
}