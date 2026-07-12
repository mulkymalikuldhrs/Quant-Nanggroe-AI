"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Badge } from "@/components/ui/badge";
import { PieChart, Wallet, TrendingUp, Activity } from "lucide-react";
import { portfolioApi, type PortfolioSummary, type PerformanceMetrics, type RiskData, type PortfolioPosition } from "@/lib/api-client";

export default function PortfolioPage() {
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [perf, setPerf] = useState<PerformanceMetrics | null>(null);
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [s, p, r] = await Promise.allSettled([
        portfolioApi.getSummary(),
        portfolioApi.getPerformance(),
        portfolioApi.getRisk(),
      ]);
      if (s.status === "fulfilled") setSummary(s.value);
      if (p.status === "fulfilled") setPerf(p.value);
      if (r.status === "fulfilled") setRisk(r.value);
      setLoading(false);
    })();
  }, []);

  return (
    <div className="space-y-4 animate-slide-up">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <Wallet className="w-5 h-5 text-emerald-400" /> Portfolio
      </h1>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard title="Total Value" value={summary?.totalValue ?? 0} icon={<Wallet className="w-4 h-4" />} variant="success" />
        <StatusCard title="Day P&L" value={summary?.dayPnl ?? 0} change={summary?.dayPnlPercent} icon={<TrendingUp className="w-4 h-4" />} variant={(summary?.dayPnl ?? 0) >= 0 ? "success" : "danger"} />
        <StatusCard title="Total P&L" value={summary?.totalPnl ?? 0} icon={<Activity className="w-4 h-4" />} variant={(summary?.totalPnl ?? 0) >= 0 ? "success" : "danger"} />
        <StatusCard title="Cash" value={summary?.cashBalance ?? 0} icon={<PieChart className="w-4 h-4" />} />
      </div>

      <ChartCard title="Positions" subtitle="Live from /api/portfolio/summary">
        <DataTable<PortfolioPosition>
          data={summary?.positions || []}
          emptyMessage={loading ? "Loading…" : "No open positions"}
          columns={[
            { key: "symbol", header: "Symbol", render: (r) => <span className="font-mono text-cyan-400">{r.symbol}</span> },
            { key: "side", header: "Side", render: (r) => <Badge variant={r.side === "long" ? "success" : "danger"} className="text-[10px]">{r.side}</Badge> },
            { key: "quantity", header: "Qty" },
            { key: "avgPrice", header: "Avg", render: (r) => <span className="font-mono">{r.avgPrice}</span> },
            { key: "currentPrice", header: "Price", render: (r) => <span className="font-mono">{r.currentPrice}</span> },
            { key: "pnlPercent", header: "P&L%", render: (r) => <span className={r.pnlPercent >= 0 ? "text-emerald-400" : "text-red-400"}>{r.pnlPercent}%</span> },
          ]}
        />
      </ChartCard>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard title="Sharpe" value={perf?.sharpe ?? "—"} icon={<Activity className="w-4 h-4" />} />
        <StatusCard title="Max DD" value={perf?.maxDrawdown ?? "—"} variant="warning" />
        <StatusCard title="Win Rate" value={perf?.winRate ?? "—"} variant="success" />
        <StatusCard title="VaR95" value={risk?.var95 ?? "—"} variant="warning" />
      </div>
    </div>
  );
}
