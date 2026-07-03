"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Key, Shield, Bot, Settings as SettingsIcon, Save } from "lucide-react";

export default function SettingsPage() {
  const [exchanges, setExchanges] = useState<any[]>([]);

  useEffect(() => {
    fetch("/api/exchange/list").then(r => r.json()).then(setExchanges).catch(() => null);
  }, []);

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <SettingsIcon className="w-5 h-5 text-white/60" />
        Settings
      </h1>

      <ChartCard title="Exchange Credentials" subtitle="Live from /api/exchange/list">
        <div className="space-y-2">
          {exchanges.map((e: any) => (
            <div key={e.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70">{e.name}</span>
              <span className="text-xs text-white/30 ml-2">({e.type})</span>
            </div>
          ))}
          {exchanges.length === 0 && <p className="text-white/40 text-xs">Connect to /api/exchange/list</p>}
        </div>
      </ChartCard>
    </div>
  );
}