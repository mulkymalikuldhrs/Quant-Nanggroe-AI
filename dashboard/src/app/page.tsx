"use client";

import React, { useEffect } from "react";
import { StatusCard } from "@/components/shared/status-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { useAppStore } from "@/lib/store";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import {
  TrendingUp,
  Activity,
  Shield,
  Bot,
  DollarSign,
  Zap,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from "recharts";



export default function DashboardPage() {
  const { agentsData, portfolioData, fetchAgents, fetchPortfolio } = useAppStore();

  useEffect(() => {
    fetchAgents();
    fetchPortfolio();
  }, []);

  const equityData = portfolioData
    ? [{ date: new Date(portfolioData.timestamp).toISOString().split("T")[0].slice(5), value: portfolioData.total_value }]
    : [];

  const displayAgents = agentsData?.agents?.map((a, i) => ({
    id: a.name,
    name: a.name.charAt(0).toUpperCase() + a.name.slice(1),
    status: a.status,
    action: a.description,
    icon: ["🔍", "📊", "💼", "🛡️", "🎯", "⚡", "₿", "💱", "🌍", "🔮", "📈"][i] || "🤖",
  })) || [];

  const activeAgentCount = displayAgents.filter((a) => a.status === "active").length;

  const portfolioValue = portfolioData?.total_value || 0;
  const dayPnl = portfolioData?.daily_pnl || 0;
  const dayPnlPercent = portfolioData?.total_value ? (portfolioData.daily_pnl / portfolioData.total_value) * 100 : 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard
          title="Portfolio Value"
          value={portfolioValue}
          change={dayPnlPercent}
          changeLabel="24h"
          icon={<DollarSign className="w-4 h-4" />}
          variant="success"
        />
        <StatusCard
          title="Day P&L"
          value={dayPnl}
          change={dayPnlPercent}
          changeLabel="today"
          icon={<TrendingUp className="w-4 h-4" />}
          variant={dayPnl >= 0 ? "success" : "danger"}
        />
        <StatusCard
          title="Active Agents"
          value={`${activeAgentCount}/${displayAgents.length}`}
          icon={<Bot className="w-4 h-4" />}
          variant="default"
        />
        <StatusCard
          title="Risk Score"
          value={portfolioData?.risk_budget_used ? Math.round(portfolioData.risk_budget_used) : "—"}
          icon={<Shield className="w-4 h-4" />}
          variant="default"
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard
          title="Portfolio Equity"
          subtitle="30 day performance"
          className="lg:col-span-2"
          glow="emerald"
        >
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={equityData}>
                <defs>
                  <linearGradient id="equityGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
                <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#equityGradient)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        <ChartCard title="Risk Dashboard" subtitle="Current risk metrics">
          <div className="flex flex-col items-center gap-4 py-2">
            <RiskGauge value={portfolioData?.risk_budget_used || 0} label="Overall Risk" sublabel="budget used" />
            <div className="w-full space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Cash Balance</span>
                <span className="text-xs font-mono text-white">{formatCurrency(portfolioData?.cash || 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Unrealized P&L</span>
                <span className={`text-xs font-mono ${(portfolioData?.unrealized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{formatCurrency(portfolioData?.unrealized_pnl || 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Realized P&L</span>
                <span className={`text-xs font-mono ${(portfolioData?.realized_pnl || 0) >= 0 ? 'text-emerald-400' : 'text-red-400'}`}>{formatCurrency(portfolioData?.realized_pnl || 0)}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Positions</span>
                <span className="text-xs font-mono text-white">{portfolioData?.positions?.length || 0}</span>
              </div>
            </div>
          </div>
        </ChartCard>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <ChartCard title="Market Overview" subtitle="Key instruments">
          <div className="space-y-3">
            {(portfolioData?.positions || []).slice(0, 6).map((pos) => (
              <div key={pos.symbol} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors border border-white/[0.04]">
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-xs font-bold text-white/60">{pos.symbol.slice(0, 2)}</div>
                  <div><p className="text-sm font-medium text-white">{pos.symbol}</p><p className="text-xs text-white/30">{pos.direction} • {pos.quantity} units</p></div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono font-medium text-white">{formatCurrency(pos.current_price)}</p>
                  <span className={cn("text-xs font-mono", pos.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400")}>{formatCurrency(pos.unrealized_pnl)}</span>
                </div>
              </div>
            ))}
            {(!portfolioData?.positions || portfolioData.positions.length === 0) && (
              <p className="text-xs text-white/30 text-center py-4">No positions. Start trading to see market data.</p>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Active Signals" subtitle="Agent-generated signals" action={<Badge variant="info"><Activity className="w-3 h-3 mr-1" />Live</Badge>}>
          <ScrollArea className="max-h-72">
            <div className="space-y-2">
              <p className="text-xs text-white/30 text-center py-4">Connect backend to see real-time agent signals.</p>
            </div>
          </ScrollArea>
        </ChartCard>

        <ChartCard title="Agent Council" subtitle={`${activeAgentCount}-agent system status`}>
          <ScrollArea className="max-h-72">
            <div className="space-y-2">
              {displayAgents.map((agent) => (
                <div key={agent.id} className="flex items-center justify-between p-2 rounded-lg hover:bg-white/[0.03] transition-colors">
                  <div className="flex items-center gap-2.5">
                    <span className="text-base">{agent.icon}</span>
                    <div><p className="text-xs font-medium text-white/80">{agent.name}</p><p className="text-[10px] text-white/30 truncate max-w-[140px]">{agent.action}</p></div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div className={cn("w-1.5 h-1.5 rounded-full", agent.status === "active" ? "bg-emerald-400 shadow-[0_0_4px_rgba(16,185,129,0.5)]" : agent.status === "warning" ? "bg-amber-400" : "bg-white/20")} />
                    <span className="text-[10px] text-white/30">{agent.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>
      </div>

      <ChartCard title="Recent Decisions" subtitle="Latest agent decisions" action={<Badge variant="default"><Zap className="w-3 h-3 mr-1" />Live Feed</Badge>}>
        <ScrollArea className="max-h-48">
          <div className="space-y-2">
            <p className="text-xs text-white/30 text-center py-4">No recent decisions. Pipeline not running.</p>
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}
