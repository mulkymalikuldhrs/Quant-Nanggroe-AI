'use client';
import { GlassCard } from '@/components/shared/cards';
import { mockChannels } from '@/lib/mock-data';
import { useState } from 'react';

export default function ChannelsPage() {
  const [selectedChannel, setSelectedChannel] = useState('discord');

  const channelIcons: Record<string, string> = { discord: '🎮', slack: '💼', telegram: '✈️', whatsapp: '📱' };
  const channel = mockChannels.find(c => c.id === selectedChannel) || mockChannels[0];

  return (
    <div className="relative z-10 space-y-6">
        {/* Channel Selector */}
        <div className="flex gap-3">
          {mockChannels.map(ch => (
            <button key={ch.id} onClick={() => setSelectedChannel(ch.id)}
              className={`flex items-center gap-2 px-4 py-2 rounded-lg border transition-all ${
                selectedChannel === ch.id ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-400' : 'bg-white/[0.02] border-white/5 text-white/40 hover:bg-white/5'
              }`}>
              <span>{channelIcons[ch.id]}</span>
              <span className="text-sm">{ch.name}</span>
              <div className={`w-2 h-2 rounded-full ${
                ch.status === 'connected' ? 'bg-emerald-500' : ch.status === 'error' ? 'bg-red-500' : 'bg-gray-500'
              }`} />
            </button>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Message Feed */}
          <GlassCard title={`${channel.name} Messages`} className="col-span-2">
            <div className="space-y-3 min-h-[400px]">
              {['System deployed to production', 'New agent added to Alpha Colony', 'Risk threshold adjusted to 2%', 'Market analysis completed for BTC/USDT', 'Memory condenser executed successfully'].map((msg, i) => (
                <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-white/[0.02]">
                  <div className="w-8 h-8 rounded-full bg-gradient-to-br from-cyan-500/20 to-purple-500/20 flex items-center justify-center text-xs text-white/50 flex-shrink-0">
                    {channel.name[0]}
                  </div>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="text-white/70 text-xs font-medium">MultiColony Bot</span>
                      <span className="text-white/20 text-[10px]">{8 + i}:{15 + i * 5}</span>
                    </div>
                    <p className="text-white/50 text-xs mt-0.5">{msg}</p>
                  </div>
                </div>
              ))}
            </div>
            <div className="mt-4 flex gap-2">
              <input type="text" placeholder="Type a message..."
                className="flex-1 bg-white/5 border border-white/10 rounded-lg px-4 py-2 text-white text-sm focus:outline-none focus:border-cyan-500/50" />
              <button className="px-4 py-2 rounded-lg bg-cyan-500/20 text-cyan-400 text-sm hover:bg-cyan-500/30 transition">Send</button>
            </div>
          </GlassCard>

          {/* Channel Config */}
          <GlassCard title="Configuration">
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <span className="text-white/60 text-sm">Status</span>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  channel.status === 'connected' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-red-500/10 text-red-400'
                }`}>{channel.status}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-white/60 text-sm">Messages</span>
                <span className="text-white/40 text-sm">{channel.messages}</span>
              </div>
              {Object.entries(channel.config).map(([key, value]) => (
                <div key={key}>
                  <label className="text-white/40 text-xs block mb-1">{key}</label>
                  <input type="text" defaultValue={value as string}
                    className="w-full bg-white/5 border border-white/10 rounded-lg px-3 py-2 text-white text-xs font-mono focus:outline-none focus:border-cyan-500/50" />
                </div>
              ))}
              <button className="w-full py-2 rounded-lg bg-gradient-to-r from-cyan-500 to-purple-500 text-white text-sm font-medium hover:opacity-90 transition mt-4">
                Save Configuration
              </button>
            </div>
          </GlassCard>
        </div>
      </div>

  );
}
