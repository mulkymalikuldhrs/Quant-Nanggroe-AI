"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/lib/store";
import { agentsApi, portfolioApi, marketApi, type Agent, type PortfolioSummary, type MarketSentiment } from "@/lib/api-client";
import { Activity, Wallet, TrendingUp, Bot, Radio, Shield } from "lucide-react";

export default function HomePage() {
  const { killSwitch } = useAppStore();
  const [agents, setAgents] = useState<Agent[]>([]);
  const [pf, setPf] = useState<PortfolioSummary | null>(null);
  const [mkt, setMkt] = useState<MarketSentiment | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      const [a, p, m] = await Promise.allSettled([
        agentsApi.getStatus().catch(() => null),
        portfolioApi.getSummary().catch(() => null),
        marketApi.getSentiment().catch(() => null),
      ]);
      if (a.status === "fulfilled" && a.value) setAgents(a.value.agents || []);
      if (p.status === "fulfilled") setPf(p.value);
      if (m.status === "fulfilled") setMkt(m.value);
      setLoading(false);
    })();
  }, []);

  const activeAgents = agents.filter((a) => a.status === "active").length;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-white">Quant Nanggroe</h1>
          <p className="text-sm text-white/40">Autonomous hedge-fund command center</p>
        </div>
        <Badge variant={killSwitch ? "danger" : "success"} className="text-[11px] flex items-center gap-1">
          <Shield className="w-3 h-3" /> {killSwitch ? "HALTED" : "LIVE"}
        </Badge>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard title="Portfolio" value={pf?.totalValue ?? 0} icon={<Wallet className="w-4 h-4" />} variant="success" />
        <StatusCard title="Day P&L" value={pf?.dayPnl ?? 0} change={pf?.dayPnlPercent} icon={<TrendingUp className="w-4 h-4" />} variant={(pf?.dayPnl ?? 0) >= 0 ? "success" : "danger"} />
        <StatusCard title="Active Agents" value={`${activeAgents}/${agents.length}`} icon={<Bot className="w-4 h-4" />} />
        <StatusCard title="Sentiment" value={mkt?.fear_greed ?? "—"} icon={<Radio className="w-4 h-4" />} variant={(mkt?.fear_greed ?? 50) >= 50 ? "success" : "danger"} />
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="System Health" subtitle="Live overview">
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2"><Activity className="w-4 h-4 text-emerald-400" /> Engine</span>
              <Badge variant="success" className="text-[10px]">ONLINE</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2"><Bot className="w-4 h-4 text-cyan-400" /> Agents</span>
              <Badge variant={activeAgents > 0 ? "success" : "warning"} className="text-[10px]">{activeAgents} active</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2"><Shield className="w-4 h-4 text-amber-400" /> Kill Switch</span>
              <Badge variant={killSwitch ? "danger" : "success"} className="text-[10px]">{killSwitch ? "ACTIVE" : "ARMED"}</Badge>
            </div>
          </div>
        </ChartCard>

        <ChartCard title="Quick Nav" subtitle="Modules">
          <div className="grid grid-cols-2 gap-2">
            {[
              ["Trading", "/trading"], ["Portfolio", "/portfolio"], ["Risk", "/risk"],
              ["Backtest", "/backtest"], ["Agents", "/agents"], ["Memory", "/memory"],
            ].map(([name, href]) => (
              <a key={href} href={href} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-sm text-white/80 hover:bg-white/[0.05] transition-colors">
                {name}
              </a>
            ))}
          </div>
        </ChartCard>
      </div>

      {loading && <p className="text-xs text-white/30">Syncing live data…</p>}
    </div>
  );
}
