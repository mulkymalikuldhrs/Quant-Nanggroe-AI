"use client";

import React, { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Badge } from "@/components/ui/badge";
import { useAppStore } from "@/lib/store";
import { formatCurrency, formatPercent, cn } from "@/lib/utils";
import { Briefcase, TrendingUp, Calculator } from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, PieChart, Pie, Cell, CartesianGrid,
} from "recharts";



export default function PortfolioPage() {
  const { portfolioData, fetchPortfolio } = useAppStore();
  const [optimizer, setOptimizer] = useState("mean_variance");

  useEffect(() => { fetchPortfolio(); }, []);

  const positions = portfolioData?.positions?.map((p) => ({
    symbol: p.symbol,
    name: p.symbol,
    quantity: p.quantity,
    avgPrice: p.entry_price,
    currentPrice: p.current_price,
    pnl: p.unrealized_pnl,
    pnlPercent: p.entry_price ? (p.unrealized_pnl / (p.quantity * p.entry_price)) * 100 : 0,
    weight: 0,
    side: p.direction.toLowerCase(),
  })) || [];

  const allocation = portfolioData?.allocation
    ? Object.entries(portfolioData.allocation).map(([name, value], i) => ({
        name,
        value: Math.round(value),
        color: ["#f59e0b", "#10b981", "#3b82f6", "#8b5cf6", "#6b7280"][i] || "#6b7280",
      }))
    : [];

  const positionColumns = [
    { key: "symbol", header: "Symbol", render: (row: Record<string, unknown>) => (<div><p className="font-medium text-white">{row.symbol as string}</p><p className="text-xs text-white/30">{row.name as string}</p></div>) },
    { key: "side", header: "Side", render: (row: Record<string, unknown>) => (<Badge variant={row.side === "long" ? "success" : "danger"} className="text-[10px]">{(row.side as string).toUpperCase()}</Badge>) },
    { key: "quantity", header: "Qty", render: (row: Record<string, unknown>) => (<span className="font-mono text-white/70">{(row.quantity as number).toLocaleString()}</span>) },
    { key: "avgPrice", header: "Avg Price", render: (row: Record<string, unknown>) => (<span className="font-mono text-white/70">{formatCurrency(row.avgPrice as number)}</span>) },
    { key: "currentPrice", header: "Current", render: (row: Record<string, unknown>) => (<span className="font-mono text-white">{formatCurrency(row.currentPrice as number)}</span>) },
    { key: "pnl", header: "P&L", render: (row: Record<string, unknown>) => (<span className={cn("font-mono font-medium", (row.pnl as number) >= 0 ? "text-emerald-400" : "text-red-400")}>{formatCurrency(row.pnl as number)}</span>) },
    { key: "pnlPercent", header: "P&L %", render: (row: Record<string, unknown>) => (<span className={cn("font-mono font-medium", (row.pnlPercent as number) >= 0 ? "text-emerald-400" : "text-red-400")}>{formatPercent(row.pnlPercent as number)}</span>) },
    { key: "weight", header: "Weight", render: (row: Record<string, unknown>) => (<span className="font-mono text-white/50">{(row.weight as number).toFixed(1)}%</span>) },
  ];

  const optimizerOptions = [
    { value: "mean_variance", label: "Mean-Variance" },
    { value: "risk_parity", label: "Risk Parity" },
    { value: "equal_volatility", label: "Equal Volatility" },
  ];

  const totalValue = portfolioData?.total_value || 0;
  const dayPnl = portfolioData?.daily_pnl || 0;
  const cash = portfolioData?.cash || 0;
  const invested = portfolioData?.total_value ? portfolioData.total_value - portfolioData.cash : 0;

  return (
    <div className="space-y-4 animate-slide-up">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2"><Briefcase className="w-5 h-5 text-emerald-400" />Portfolio Management</h1>
        <p className="text-sm text-white/40 mt-0.5">Portfolio tracking, optimization & analysis</p>
      </div>

      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusCard title="Portfolio Value" value={totalValue} variant="success" />
        <StatusCard title="Day P&L" value={dayPnl} variant={dayPnl >= 0 ? "success" : "danger"} />
        <StatusCard title="Cash Balance" value={cash} icon={<Briefcase className="w-4 h-4" />} />
        <StatusCard title="Invested" value={invested} icon={<TrendingUp className="w-4 h-4" />} />
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
            <ChartCard title="Equity Curve" subtitle="Portfolio value" className="lg:col-span-2" glow="emerald">
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={[{ date: "current", value: totalValue }]}>
                    <defs><linearGradient id="portGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
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
                    <Pie data={allocation} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                      {allocation.map((_entry, index) => (<Cell key={index} fill={allocation[index].color} stroke="transparent" />))}
                    </Pie>
                    <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} formatter={(value) => `${value}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {allocation.map((item) => (
                  <div key={item.name} className="flex items-center justify-between">
                    <div className="flex items-center gap-2"><div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: item.color }} /><span className="text-xs text-white/50">{item.name}</span></div>
                    <span className="text-xs font-mono text-white/70">{item.value}%</span>
                  </div>
                ))}
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="holdings">
          <ChartCard title="Holdings" subtitle="Current positions" className="mt-3">
            <DataTable columns={positionColumns} data={positions as unknown as Record<string, unknown>[]} />
          </ChartCard>
        </TabsContent>

        <TabsContent value="optimizer">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Portfolio Optimizer" subtitle="Optimize allocation">
              <div className="space-y-4">
                <div><label className="text-xs text-white/40 mb-1 block">Optimization Method</label><Select value={optimizer} onChange={(e) => setOptimizer(e.target.value)} options={optimizerOptions} /></div>
                <Button variant="glow" className="w-full"><Calculator className="w-3.5 h-3.5 mr-1.5" />Optimize Portfolio</Button>
              </div>
            </ChartCard>
            <ChartCard title="Position Sizing" subtitle="ATR-based calculator">
              <div className="space-y-4">
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-2">ATR Position Sizing</p>
                  <div className="grid grid-cols-2 gap-3">
                    <div><p className="text-[10px] text-white/30">ATR (14)</p><p className="text-sm font-mono text-white">—</p></div>
                    <div><p className="text-[10px] text-white/30">Risk per trade</p><p className="text-sm font-mono text-white">1.0%</p></div>
                    <div><p className="text-[10px] text-white/30">Stop distance</p><p className="text-sm font-mono text-white">2x ATR</p></div>
                    <div><p className="text-[10px] text-white/30">Position size</p><p className="text-sm font-mono text-white">—</p></div>
                  </div>
                </div>
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="metrics">
          <ChartCard title="Performance Metrics" subtitle="Comprehensive portfolio analytics" className="mt-3">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { label: "Sharpe Ratio", value: portfolioData?.risk_budget_used ? "—" : "—", color: "text-white/50" },
                { label: "Sortino Ratio", value: "—", color: "text-white/50" },
                { label: "Max Drawdown", value: portfolioData ? "—" : "—", color: "text-white/50" },
                { label: "Win Rate", value: "—", color: "text-white/50" },
                { label: "Profit Factor", value: "—", color: "text-white/50" },
                { label: "Total Trades", value: portfolioData?.positions?.length?.toString() || "0", color: "text-white/70" },
                { label: "Daily P&L", value: formatCurrency(portfolioData?.daily_pnl || 0), color: (portfolioData?.daily_pnl || 0) >= 0 ? "text-emerald-400" : "text-red-400" },
                { label: "Realized P&L", value: formatCurrency(portfolioData?.realized_pnl || 0), color: "text-white/70" },
              ].map((metric, i) => (
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
