"use client";
export const dynamic = "force-dynamic";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { channelsApi } from "@/lib/api-client";
import type { Channel } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  MessageSquare,
  Send,
  Settings,
  Wifi,
  WifiOff,
  RefreshCw,
  AlertCircle,
} from "lucide-react";

const CHANNEL_ICONS: Record<string, string> = {
  discord: "🎮", slack: "💼", telegram: "✈️", whatsapp: "📱", email: "📧",
};

function ChannelsContent() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedChannelId, setSelectedChannelId] = useState("");

  const loadChannels = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await channelsApi.list();
      setChannels(data);
      if (data.length > 0 && !selectedChannelId) setSelectedChannelId(data[0].id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Channels unavailable");
      setChannels([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadChannels(); }, []);

  if (loading) return (
    <div className="space-y-4 animate-slide-up">
      <div className="h-8 w-48 rounded-lg bg-white/5 animate-pulse" />
      <div className="h-24 rounded-xl bg-white/5 animate-pulse" />
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 h-64 rounded-xl bg-white/5 animate-pulse" />
        <div className="h-64 rounded-xl bg-white/5 animate-pulse" />
      </div>
    </div>
  );

  const channel = channels.find((c) => c.id === selectedChannelId) || channels[0];
  const activeCount = channels.filter((c) => c.status === "connected").length;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <MessageSquare className="w-5 h-5 text-cyan-400" />
          Notification Channels
        </h1>
        <p className="text-sm text-white/40 mt-0.5">{activeCount} of {channels.length} channels connected</p>
      </div>

      {/* Notification Channels */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={loadChannels}>
            <RefreshCw className="w-3 h-3 mr-1" /> Retry
          </Button>
        </div>
      )}

      {/* Channel Selector */}
      <div className="flex flex-wrap gap-2">
        {channels.map((ch) => (
          <button key={ch.id} onClick={() => setSelectedChannelId(ch.id)}
            className={cn(
              "flex items-center gap-2 px-4 py-2 rounded-lg border transition-all text-sm",
              selectedChannelId === ch.id
                ? "bg-cyan-500/10 border-cyan-500/30 text-cyan-400"
                : "bg-white/[0.02] border-white/5 text-white/40 hover:bg-white/[0.04]",
            )}
          >
            <span>{CHANNEL_ICONS[ch.id] || "📡"}</span>
            <span>{ch.name}</span>
            <div className={cn("w-2 h-2 rounded-full", ch.status === "connected" ? "bg-emerald-500" : ch.status === "error" ? "bg-red-500" : "bg-gray-500")} />
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Message Feed */}
        <ChartCard title={`${channel?.name || "Channel"} Messages`} subtitle="Recent activity" className="lg:col-span-2">
          <div className="space-y-3 min-h-[300px]">
            {channels.length === 0 ? (
              <div className="flex items-center justify-center h-full text-white/30 text-sm">
                No notification channels configured. Set QNAI_TELEGRAM_BOT_TOKEN or QNAI_WHATSAPP_TOKEN env vars.
              </div>
            ) : (
              <div className="flex items-center justify-center h-full text-white/30 text-sm">
                Message history available via audit log. Use Send to deliver notifications.
              </div>
            )}
          </div>
          <div className="mt-4 flex gap-2">
            <Input placeholder="Type a message..." className="flex-1" />
            <Button variant="glow" size="sm">
              <Send className="w-3.5 h-3.5 mr-1" /> Send
            </Button>
          </div>
        </ChartCard>

        {/* Channel Configuration */}
        <ChartCard title="Configuration" subtitle={`${channel?.name || ""} settings`}>
          <div className="space-y-4">
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/60">Status</span>
              <div className="flex items-center gap-2">
                {channel?.status === "connected" ? (
                  <><Wifi className="w-3.5 h-3.5 text-emerald-400" /><span className="text-xs text-emerald-400">Connected</span></>
                ) : (
                  <><WifiOff className="w-3.5 h-3.5 text-white/30" /><span className="text-xs text-white/30">Disconnected</span></>
                )}
              </div>
            </div>
            <div className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/60">Messages</span>
              <span className="text-sm font-mono text-white/40">{channel?.messages || 0}</span>
            </div>
            {channel?.config && Object.entries(channel.config).map(([key, value]) => (
              <div key={key}>
                <label className="text-xs text-white/40 mb-1 block capitalize">{key.replace(/_/g, " ")}</label>
                <Input defaultValue={value as string} className="font-mono text-xs" />
              </div>
            ))}
            <Button variant="glow" className="w-full" size="sm">
              <Settings className="w-3.5 h-3.5 mr-1" /> Save Configuration
            </Button>
          </div>
        </ChartCard>
      </div>
    </div>
  );
}

export default function ChannelsPage() {
  return (
    <ErrorBoundary>
      <ChannelsContent />
    </ErrorBoundary>
  );
}
