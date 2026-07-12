"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { LineChart, TrendingUp, Radio } from "lucide-react";
import { marketApi, type MarketSentiment, type TradingSignal } from "@/lib/api-client";

export default function MarketPage() {
  const [sentiment, setSentiment] = useState<MarketSentiment | null>(null);
  const [signals, setSignals] = useState<TradingSignal[]>([]);
  const [loading, setLoading] = useState(true);

  async function refresh() {
    try {
      const [s, sig] = await Promise.all([
        marketApi.getSentiment().catch(() => null),
        marketApi.getSignals().catch(() => []),
      ]);
      setSentiment(s);
      setSignals(Array.isArray(sig) ? sig : []);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <LineChart className="w-5 h-5 text-blue-400" /> Market
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
        <StatusCard title="Fear & Greed" value={sentiment?.fear_greed ?? "—"} icon={<TrendingUp className="w-4 h-4" />} variant={(sentiment?.fear_greed ?? 50) >= 50 ? "success" : "danger"} />
        <StatusCard title="Overall Sentiment" value={sentiment?.overall ?? "—"} icon={<Radio className="w-4 h-4" />} />
        <StatusCard title="Active Signals" value={signals.length} icon={<Radio className="w-4 h-4" />} />
      </div>

      <ChartCard title="Sector Sentiment" subtitle="From /api/market/sentiment">
        <div className="space-y-2">
          {(sentiment?.sectors || []).map((s, i) => (
            <div key={i} className="flex items-center gap-2">
              <span className="text-xs text-white/60 w-24 truncate">{s.name}</span>
              <div className="flex-1 h-2 rounded bg-white/[0.05] overflow-hidden">
                <div className={`h-full ${s.sentiment >= 0 ? "bg-emerald-500" : "bg-red-500"}`} style={{ width: `${Math.min(100, Math.abs(s.sentiment) * 100)}%` }} />
              </div>
              <span className="text-xs font-mono text-white/50">{s.sentiment}</span>
            </div>
          ))}
          {(!sentiment?.sectors || sentiment.sectors.length === 0) && <p className="text-white/40 text-sm p-2">{loading ? "Loading…" : "No data"}</p>}
        </div>
      </ChartCard>

      <ChartCard title="Trading Signals" subtitle="From /api/market/signals">
        <DataTable<TradingSignal>
          data={signals}
          emptyMessage={loading ? "Loading…" : "No signals"}
          columns={[
            { key: "time", header: "Time", render: (r) => <span className="font-mono text-xs">{String(r.time).slice(0, 19)}</span> },
            { key: "agent", header: "Agent", render: (r) => <span className="text-cyan-400">{r.agent}</span> },
            { key: "symbol", header: "Symbol", render: (r) => <span className="font-mono">{r.symbol}</span> },
            { key: "signal", header: "Signal", render: (r) => <Badge variant={r.signal === "BUY" ? "success" : r.signal === "SELL" ? "danger" : "default"} className="text-[10px]">{r.signal}</Badge> },
            { key: "confidence", header: "Conf%", render: (r) => <span className="font-mono">{Math.round(r.confidence * 100)}</span> },
            { key: "reason", header: "Reason", render: (r) => <span className="text-white/50 text-xs">{r.reason}</span> },
          ]}
        />
      </ChartCard>
    </div>
  );
}
