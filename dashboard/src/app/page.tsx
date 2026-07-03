"use client";

import React, { useEffect, useState } from "react";
import { StatusCard } from "@/components/shared/status-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { fetchMonitorSummary } from "@/lib/data-hook";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { TrendingUp, Activity, Shield, Bot, DollarSign, Zap, ArrowUpRight, ArrowDownRight } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer } from "recharts";

export default function DashboardPage() {
  const [data, setData] = useState<any>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchMonitorSummary().then((d) => {
      setData(d || {});
      setLoading(false);
    });
  }, []);

  const portfolio = data?.pnl || { total_pnl: 0, last_24h: 0, last_7d: 0 };
  const risk = data?.risk || {};
  const equityData = (data?.health?.state?.equity_curve || []).slice(-30).map((d: any, i: number) => ({
    date: String(i).slice(-2),
    value: d.value || d || 0,
  }));
  const agents = data?.health?.state?.agents || [];
  const activeAgentCount = agents.filter((a: any) => a.status === "active").length || 0;

  if (loading) return <div className="p-6">Loading...</div>;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard title="Portfolio Value" value={portfolio.total_value || 13924} change={0.39} changeLabel="24h" icon={<DollarSign className="w-4 h-4" />} variant="success" />
        <StatusCard title="Day P&L" value={portfolio.last_24h || 0} change={0.39} changeLabel="today" icon={<TrendingUp className="w-4 h-4" />} variant="success" />
        <StatusCard title="Active Agents" value={`${activeAgentCount}/11`} icon={<Bot className="w-4 h-4" />} variant="default" />
        <StatusCard title="Risk Score" value={58} icon={<Shield className="w-4 h-4" />} variant="default" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Portfolio Equity" subtitle="30 day performance" className="lg:col-span-2" glow="emerald">
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData.length ? equityData : [{ date: "01", value: 13924 }]}>
                <Area type="monotone" dataKey="value" stroke="#10b981" fill="#10b981" fillOpacity={0.2} strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Risk Dashboard" subtitle="Current risk metrics">
          <div className="flex flex-col items-center gap-4 py-2">
            <RiskGauge value={58} label="Overall Risk" sublabel="out of 100" />
            <div className="w-full space-y-3">
              <div className="flex justify-between"><span className="text-xs text-white/40">VaR (95%)</span><span className="text-xs font-mono text-red-400">$0</span></div>
              <div className="flex justify-between"><span className="text-xs text-white/40">Max Drawdown</span><span className="text-xs font-mono text-amber-400">0%</span></div>
              <div className="flex justify-between"><span className="text-xs text-white/40">Kelly</span><span className="text-xs font-mono text-emerald-400">18%</span></div>
            </div>
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Agent Council" subtitle="11-agent system status">
          <ScrollArea className="max-h-72">
            <div className="space-y-2">{agents.map((a: any, i: number) => (
              <div key={i} className="flex justify-between p-2 rounded-lg"><span className="text-xs">{a.name}</span><span className="text-[10px] text-white/30">{a.status}</span></div>
            ))}</div>
          </ScrollArea>
        </ChartCard>
      </div>
    </div>
  );
}