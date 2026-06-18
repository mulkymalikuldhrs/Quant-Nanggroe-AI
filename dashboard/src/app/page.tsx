"use client";

import React from "react";
import { StatusCard } from "@/components/shared/status-card";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { RiskGauge } from "@/components/shared/risk-gauge";
import {
  mockPortfolio,
  mockMarketData,
  mockSignals,
  mockRecentDecisions,
  mockAgents,
  mockEquityCurve,
  mockRiskData,
} from "@/lib/mock-data";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import {
  TrendingUp,
  Activity,
  Shield,
  Bot,
  DollarSign,
  Zap,
  ArrowUpRight,
  ArrowDownRight,
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
  const equityData = mockEquityCurve.slice(-30).map((d) => ({
    ...d,
    date: d.date.slice(5),
  }));

  const activeAgentCount = mockAgents.filter((a) => a.status === "active").length;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Top Status Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatusCard
          title="Portfolio Value"
          value={mockPortfolio.totalValue}
          change={mockPortfolio.dayPnlPercent}
          changeLabel="24h"
          icon={<DollarSign className="w-4 h-4" />}
          variant="success"
        />
        <StatusCard
          title="Day P&L"
          value={mockPortfolio.dayPnl}
          change={mockPortfolio.dayPnlPercent}
          changeLabel="today"
          icon={<TrendingUp className="w-4 h-4" />}
          variant={mockPortfolio.dayPnl >= 0 ? "success" : "danger"}
        />
        <StatusCard
          title="Active Agents"
          value={`${activeAgentCount}/11`}
          icon={<Bot className="w-4 h-4" />}
          variant="default"
        />
        <StatusCard
          title="Risk Score"
          value={mockRiskData.riskScore}
          icon={<Shield className="w-4 h-4" />}
          variant={mockRiskData.riskScore > 60 ? "warning" : "default"}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Portfolio Equity Curve */}
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
                <XAxis
                  dataKey="date"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                />
                <YAxis
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }}
                  tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`}
                />
                <RechartsTooltip
                  contentStyle={{
                    backgroundColor: "rgba(10,10,26,0.95)",
                    border: "1px solid rgba(255,255,255,0.1)",
                    borderRadius: "8px",
                    fontSize: "12px",
                  }}
                  labelStyle={{ color: "rgba(255,255,255,0.5)" }}
                  itemStyle={{ color: "#10b981" }}
                />
                <Area
                  type="monotone"
                  dataKey="value"
                  stroke="#10b981"
                  fill="url(#equityGradient)"
                  strokeWidth={2}
                />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </ChartCard>

        {/* Risk Gauge */}
        <ChartCard title="Risk Dashboard" subtitle="Current risk metrics">
          <div className="flex flex-col items-center gap-4 py-2">
            <RiskGauge value={mockRiskData.riskScore} label="Overall Risk" sublabel="out of 100" />
            <div className="w-full space-y-3">
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">VaR (95%)</span>
                <span className="text-xs font-mono text-red-400">{formatCurrency(Math.abs(mockRiskData.var95))}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">CVaR (95%)</span>
                <span className="text-xs font-mono text-red-400">{formatCurrency(Math.abs(mockRiskData.cvar95))}</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Max Drawdown</span>
                <span className="text-xs font-mono text-amber-400">{mockRiskData.maxDrawdown}%</span>
              </div>
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Kelly Fraction</span>
                <span className="text-xs font-mono text-emerald-400">{(mockRiskData.kellyFraction * 100).toFixed(1)}%</span>
              </div>
            </div>
          </div>
        </ChartCard>
      </div>

      {/* Market Overview + Signals */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Market Overview */}
        <ChartCard title="Market Overview" subtitle="Key instruments">
          <div className="space-y-3">
            {mockMarketData.symbols.map((item) => (
              <div
                key={item.symbol}
                className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] hover:bg-white/[0.04] transition-colors border border-white/[0.04]"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center text-xs font-bold text-white/60">
                    {item.symbol.slice(0, 2)}
                  </div>
                  <div>
                    <p className="text-sm font-medium text-white">{item.symbol}</p>
                    <p className="text-xs text-white/30">Vol: {item.volume}</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-mono font-medium text-white">
                    {item.symbol.includes("/") ? item.price.toFixed(4) : formatCurrency(item.price)}
                  </p>
                  <div className="flex items-center justify-end gap-1">
                    {item.change >= 0 ? (
                      <ArrowUpRight className="w-3 h-3 text-emerald-400" />
                    ) : (
                      <ArrowDownRight className="w-3 h-3 text-red-400" />
                    )}
                    <span
                      className={cn(
                        "text-xs font-mono",
                        item.change >= 0 ? "text-emerald-400" : "text-red-400",
                      )}
                    >
                      {formatPercent(item.change)}
                    </span>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </ChartCard>

        {/* Active Signals */}
        <ChartCard
          title="Active Signals"
          subtitle="Agent-generated signals"
          action={
            <Badge variant="info">
              <Activity className="w-3 h-3 mr-1" />
              Live
            </Badge>
          }
        >
          <ScrollArea className="max-h-72">
            <div className="space-y-2">
              {mockSignals.map((signal) => (
                <div
                  key={signal.id}
                  className="p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:border-white/[0.08] transition-colors"
                >
                  <div className="flex items-center justify-between mb-1">
                    <div className="flex items-center gap-2">
                      <Badge
                        variant={
                          signal.signal === "BUY"
                            ? "success"
                            : signal.signal === "SELL"
                              ? "danger"
                              : "warning"
                        }
                        className="text-[10px]"
                      >
                        {signal.signal}
                      </Badge>
                      <span className="text-xs font-medium text-white">{signal.symbol}</span>
                    </div>
                    <span className="text-[10px] text-white/30">{signal.time}</span>
                  </div>
                  <p className="text-xs text-white/40">{signal.reason}</p>
                  <div className="flex items-center justify-between mt-1.5">
                    <span className="text-[10px] text-white/30">by {signal.agent}</span>
                    <span className="text-[10px] text-white/40 font-mono">
                      {(signal.confidence * 100).toFixed(0)}% conf
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>

        {/* Agent Council Status */}
        <ChartCard title="Agent Council" subtitle="11-agent system status">
          <ScrollArea className="max-h-72">
            <div className="space-y-2">
              {mockAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center justify-between p-2 rounded-lg hover:bg-white/[0.03] transition-colors"
                >
                  <div className="flex items-center gap-2.5">
                    <span className="text-base">{agent.icon}</span>
                    <div>
                      <p className="text-xs font-medium text-white/80">{agent.name}</p>
                      <p className="text-[10px] text-white/30 truncate max-w-[140px]">{agent.action}</p>
                    </div>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <div
                      className={cn(
                        "w-1.5 h-1.5 rounded-full",
                        agent.status === "active"
                          ? "bg-emerald-400 shadow-[0_0_4px_rgba(16,185,129,0.5)]"
                          : agent.status === "warning"
                            ? "bg-amber-400"
                            : "bg-white/20",
                      )}
                    />
                    <span className="text-[10px] text-white/30">{agent.status}</span>
                  </div>
                </div>
              ))}
            </div>
          </ScrollArea>
        </ChartCard>
      </div>

      {/* Recent Decisions */}
      <ChartCard
        title="Recent Decisions"
        subtitle="Latest agent decisions"
        action={
          <Badge variant="default">
            <Zap className="w-3 h-3 mr-1" />
            Live Feed
          </Badge>
        }
      >
        <ScrollArea className="max-h-48">
          <div className="space-y-2">
            {mockRecentDecisions.map((decision) => (
              <div
                key={decision.id}
                className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]"
              >
                <div
                  className={cn(
                    "w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0",
                    decision.impact === "high"
                      ? "bg-emerald-400"
                      : decision.impact === "medium"
                        ? "bg-amber-400"
                        : "bg-white/30",
                  )}
                />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-0.5">
                    <span className="text-xs font-medium text-white/70">{decision.agent}</span>
                    <span className="text-[10px] text-white/30">{decision.time}</span>
                  </div>
                  <p className="text-xs text-white/50">{decision.decision}</p>
                </div>
              </div>
            ))}
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}
