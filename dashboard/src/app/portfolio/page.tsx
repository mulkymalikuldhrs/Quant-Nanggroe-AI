"use client";

import React, { useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { mockPortfolio, mockEquityCurve, mockPerformanceMetrics } from "@/lib/mock-data";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import {
  Briefcase,
  TrendingUp,
  Calculator,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  PieChart,
  Pie,
  Cell,
  CartesianGrid,
} from "recharts";

export default function PortfolioPage() {
  const [optimizer, setOptimizer] = useState("mean_variance");
  const equityData = mockEquityCurve.map((d) => ({ ...d, date: d.date.slice(5) }));

  const positionColumns = [
    {
      key: "symbol",
      header: "Symbol",
      render: (row: Record<string, unknown>) => (
        <div>
          <p className="font-medium text-white">{row.symbol as string}</p>
          <p className="text-xs text-white/30">{row.name as string}</p>
        </div>
      ),
    },
    {
      key: "side",
      header: "Side",
      render: (row: Record<string, unknown>) => (
        <Badge variant={row.side === "long" ? "success" : "danger"} className="text-[10px]">
          {(row.side as string).toUpperCase()}
        </Badge>
      ),
    },
    { key: "quantity", header: "Qty", render: (row: Record<string, unknown>) => (
      <span className="font-mono text-white/70">{(row.quantity as number).toLocaleString()}</span>
    )},
    { key: "avgPrice", header: "Avg Price", render: (row: Record<string, unknown>) => (
      <span className="font-mono text-white/70">{formatCurrency(row.avgPrice as number)}</span>
    )},
    { key: "currentPrice", header: "Current", render: (row: Record<string, unknown>) => (
      <span className="font-mono text-white">{formatCurrency(row.currentPrice as number)}</span>
    )},
    {
      key: "pnl",
      header: "P&L",
      render: (row: Record<string, unknown>) => (
        <span className={cn("font-mono font-medium", (row.pnl as number) >= 0 ? "text-emerald-400" : "text-red-400")}>
          {formatCurrency(row.pnl as number)}
        </span>
      ),
    },
    {
      key: "pnlPercent",
      header: "P&L %",
      render: (row: Record<string, unknown>) => (
        <span className={cn("font-mono font-medium", (row.pnlPercent as number) >= 0 ? "text-emerald-400" : "text-red-400")}>
          {formatPercent(row.pnlPercent as number)}
        </span>
      ),
    },
    {
      key: "weight",
      header: "Weight",
      render: (row: Record<string, unknown>) => (
        <span className="font-mono text-white/50">{(row.weight as number).toFixed(1)}%</span>
      ),
    },
  ];

  const optimizerOptions = [
    { value: "mean_variance", label: "Mean-Variance" },
    { value: "risk_parity", label: "Risk Parity" },
    { value: "equal_volatility", label: "Equal Volatility" },
  ];

  const metricsDisplay = [
    { label: "Sharpe Ratio", value: mockPerformanceMetrics.sharpe, color: "text-blue-400" },
    { label: "Sortino Ratio", value: mockPerformanceMetrics.sortino, color: "text-blue-400" },
    { label: "Calmar Ratio", value: mockPerformanceMetrics.calmar, color: "text-blue-400" },
    { label: "Max Drawdown", value: `${mockPerformanceMetrics.maxDrawdown}%`, color: "text-red-400" },
    { label: "Win Rate", value: `${mockPerformanceMetrics.winRate}%`, color: "text-emerald-400" },
    { label: "Profit Factor", value: mockPerformanceMetrics.profitFactor, color: "text-emerald-400" },
    { label: "Avg Win", value: formatCurrency(mockPerformanceMetrics.avgWin), color: "text-emerald-400" },
    { label: "Avg Loss", value: formatCurrency(mockPerformanceMetrics.avgLoss), color: "text-red-400" },
    { label: "Total Trades", value: mockPerformanceMetrics.totalTrades.toString(), color: "text-white/70" },
    { label: "Avg Holding", value: mockPerformanceMetrics.avgHoldingPeriod, color: "text-white/50" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-emerald-400" />
          Portfolio Management
        </h1>
        <p className="text-sm text-white/40 mt-0.5">Portfolio tracking, optimization & analysis</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusCard
          title="Portfolio Value"
          value={mockPortfolio.totalValue}
          change={mockPortfolio.totalPnlPercent}
          changeLabel="all time"
          variant="success"
        />
        <StatusCard
          title="Day P&L"
          value={mockPortfolio.dayPnl}
          change={mockPortfolio.dayPnlPercent}
          changeLabel="today"
          variant={mockPortfolio.dayPnl >= 0 ? "success" : "danger"}
        />
        <StatusCard
          title="Cash Balance"
          value={mockPortfolio.cashBalance}
          icon={<Briefcase className="w-4 h-4" />}
        />
        <StatusCard
          title="Invested"
          value={mockPortfolio.investedAmount}
          icon={<TrendingUp className="w-4 h-4" />}
        />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="holdings">Holdings</TabsTrigger>
          <TabsTrigger value="optimizer">Optimizer</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-3">
            <ChartCard title="Equity Curve" subtitle="All-time performance" className="lg:col-span-2" glow="emerald">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityData.filter((_, i) => i % 3 === 0)}>
                    <defs>
                      <linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                    <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
                    <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                    <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#portGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </ChartCard>

            <ChartCard title="Asset Allocation" subtitle="Portfolio breakdown">
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={mockPortfolio.allocation}
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      paddingAngle={3}
                      dataKey="value"
                    >
                      {mockPortfolio.allocation.map((entry, index) => (
                        <Cell key={index} fill={entry.color} stroke="transparent" />
                      ))}
                    </Pie>
                    <RechartsTooltip
                      contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }}
                      formatter={(value) => `${value}%`}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {mockPortfolio.allocation.map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} />
                      <span className="text-xs text-white/50">{item.name}</span>
                    </div>
                    <span className="text-xs font-mono text-white/70">{item.value}%</span>
                  </div>
                ))}
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="holdings">
          <ChartCard title="Holdings" subtitle="Current positions" className="mt-3">
            <DataTable columns={positionColumns} data={mockPortfolio.positions as unknown as Record<string, unknown>[]} />
          </ChartCard>
        </TabsContent>

        <TabsContent value="optimizer">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Portfolio Optimizer" subtitle="Optimize allocation">
              <div className="space-y-4">
                <div>
                  <label className="text-xs text-white/40 mb-1 block">Optimization Method</label>
                  <Select
                    value={optimizer}
                    onChange={(e) => setOptimizer(e.target.value)}
                    options={optimizerOptions}
                  />
                </div>
                <div className="space-y-3">
                  <h4 className="text-xs text-white/50 font-medium">Optimized Weights</h4>
                  {[
                    { name: "BTC", weight: 22.5 },
                    { name: "ETH", weight: 15.2 },
                    { name: "NVDA", weight: 12.8 },
                    { name: "SPY", weight: 18.5 },
                    { name: "AAPL", weight: 10.3 },
                    { name: "SOL", weight: 8.7 },
                    { name: "TSLA", weight: 5.2 },
                    { name: "EUR/USD", weight: 6.8 },
                  ].map((item) => (
                    <div key={item.name} className="flex items-center gap-3">
                      <span className="text-xs text-white/50 w-16">{item.name}</span>
                      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-emerald-500/60"
                          style={{ width: `${item.weight}%` }}
                        />
                      </div>
                      <span className="text-xs font-mono text-white/60 w-12 text-right">
                        {item.weight}%
                      </span>
                    </div>
                  ))}
                </div>
                <Button variant="glow" className="w-full">
                  <Calculator className="w-3.5 h-3.5 mr-1.5" />
                  Optimize Portfolio
                </Button>
              </div>
            </ChartCard>

            <ChartCard title="Position Sizing" subtitle="ATR-based calculator">
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-2">ATR Position Sizing</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] text-white/30">ATR (14)</p>
                      <p className="text-sm font-mono text-white">$2.45</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Risk per trade</p>
                      <p className="text-sm font-mono text-white">1.0%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Stop distance</p>
                      <p className="text-sm font-mono text-white">2x ATR</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Position size</p>
                      <p className="text-sm font-mono text-emerald-400">116 shares</p>
                    </div>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-2">Kelly Criterion</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div>
                      <p className="text-[10px] text-white/30">Win rate</p>
                      <p className="text-sm font-mono text-white">58.2%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Win/Loss ratio</p>
                      <p className="text-sm font-mono text-white">1.72</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Kelly fraction</p>
                      <p className="text-sm font-mono text-amber-400">18.0%</p>
                    </div>
                    <div>
                      <p className="text-[10px] text-white/30">Half-Kelly</p>
                      <p className="text-sm font-mono text-emerald-400">9.0%</p>
                    </div>
                  </div>
                </div>
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="metrics">
          <ChartCard title="Performance Metrics" subtitle="Comprehensive portfolio analytics" className="mt-3">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              {metricsDisplay.map((metric, i) => (
                <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
                  <p className="text-xs text-white/40 mb-1">{metric.label}</p>
                  <p className={`text-lg font-mono font-bold ${metric.color}`}>{metric.value}</p>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
