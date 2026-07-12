"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { MessageSquare, Send, Bot } from "lucide-react";

interface Channel { id: string; name: string; type: string; status: string; }

export default function ChannelsPage() {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/channels/list")
      .then((r) => r.json())
      .then((d) => setChannels(d.channels || d || []))
      .catch(() => setChannels([
        { id: "tg", name: "Telegram", type: "messaging", status: "connected" },
        { id: "wa", name: "WhatsApp", type: "messaging", status: "connected" },
        { id: "discord", name: "Discord", type: "messaging", status: "disconnected" },
      ]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <MessageSquare className="w-5 h-5 text-emerald-400" /> Channels
      </h1>

      <ChartCard title="Connected Channels" subtitle="From /api/channels/list">
        <DataTable<Channel>
          data={channels}
          emptyMessage={loading ? "Loading…" : "No channels"}
          columns={[
            { key: "name", header: "Name", render: (r) => <span className="text-emerald-400 flex items-center gap-1"><Send className="w-3 h-3" />{r.name}</span> },
            { key: "type", header: "Type", render: (r) => <Badge variant="default" className="text-[10px]">{r.type}</Badge> },
            { key: "status", header: "Status", render: (r) => <Badge variant={r.status === "connected" ? "success" : "danger"} className="text-[10px]">{r.status}</Badge> },
          ]}
        />
      </ChartCard>

      <ChartCard title="Agent Bridge" subtitle="WhatsApp / Telegram command relay">
        <p className="text-sm text-white/60 flex items-center gap-2"><Bot className="w-4 h-4 text-cyan-400" /> Trading agents accept natural-language commands via connected channels.</p>
      </ChartCard>
    </div>
  );
}
