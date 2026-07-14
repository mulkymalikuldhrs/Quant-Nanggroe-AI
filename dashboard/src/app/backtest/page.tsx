"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { backtestApi } from "@/lib/api-client";
import type { BacktestResult, Strategy } from "@/lib/api-client";
import { formatCurrency, formatPercent } from "@/lib/utils";
import {
  FlaskConical,
  Play,
  RefreshCw,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

// ── Fallback data ──────────────────────────────────────────────────

const FALLBACK_RESULT: BacktestResult = {
  id: "bt-1", strategy: "momentum_alpha", symbol: "AAPL",
  startDate: "2023-01-01", endDate: "2024-01-01",
  initialCapital: 100000, finalValue: 124500,
  totalReturn: 24.5, sharpe: 1.82, maxDrawdown: 8.5, winRate: 62,
  totalTrades: 184,
  equityCurve: Array.from({ length: 24 }, (_, i) => ({
    date: `2023-${String(i + 1).padStart(2, "0")}-01`,
    value: 100000 + i * 1020 + (i % 5) * 200,
  })),
  drawdownCurve: Array.from({ length: 24 }, (_, i) => ({
    date: `2023-${String(i + 1).padStart(2, "0")}-01`,
    value: -Math.abs(Math.sin(i * 0.5) * 8),
  })),
  monteCarlo: {
    simulations: 1000, meanReturn: 18.5, p5Return: -5.2, p95Return: 42.1,
    worstCase: -18.3, bestCase: 68.4,
  },
};

export default function BacktestPage() {
  const [symbol, setSymbol] = useState("AAPL");
  const [strategy, setStrategy] = useState("momentum_alpha");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState<BacktestResult>(FALLBACK_RESULT);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [engines, setEngines] = useState<string[]>([]);

  useEffect(() => {
    Promise.allSettled([
      backtestApi.getStrategies(),
      backtestApi.getEngines(),
    ]).then(([s, e]) => {
      if (s.status === "fulfilled") setStrategies(s.value);
      if (e.status === "fulfilled") setEngines(e.value);
      setLoading(false);
    });
  }, []);

  const strategyOptions = strategies.length > 0
    ? strategies.map((s) => ({ value: s.id, label: s.name }))
    : [
        { value: "momentum_alpha", label: "Momentum Alpha" },
        { value: "value_quality", label: "Value + Quality" },
        { value: "mean_reversion", label: "Mean Reversion" },
      ];

  const engineOptions = engines.length > 0
    ? engines.map((e) => ({ value: e.toLowerCase().replace(/\s+/g, "_"), label: e }))
    : [{ value: "equity_engine", label: "Equity Engine" }];

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => {
        if (prev >= 100) { clearInterval(interval); return 100; }
        return prev + 2;
      });
    }, 60);

    try {
      const data = await backtestApi.run({
        strategy, symbol, startDate, endDate, initialCapital: 100000,
      });
      const res = await backtestApi.getResult(data.id);
      setResult(res);
    } catch (err) {
      console.error("Backtest run failed:", err);
    } finally {
      clearInterval(interval);
      setProgress(100);
      setTimeout(() => { setIsRunning(false); setProgress(0); }, 500);
    }
  };

  if (loading) return (
    <div className="space-y-4 animate-slide-up">
      <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
      <LoadingSkeleton variant="page" />
    </div>
  );

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <FlaskConical className="w-5 h-5 text-blue-400" />
          Backtesting Engine
        </h1>
        <p className="text-sm text-white/40 mt-0.5">
          {engines.length || 3} engines &bull; Monte Carlo &amp; Walk-Forward
        </p>
      </div>

      {/* Configuration */}
      <ChartCard title="Backtest Configuration" subtitle="Configure and run backtests">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <div>
            <label className="text-xs text-white/40 mb-1 block">Symbol</label>
            <Input value={symbol} onChange={(e) => setSymbol(e.target.value)} placeholder="e.g. AAPL" />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Strategy</label>
            <Select value={strategy} onChange={(e) => setStrategy(e.target.value)} options={strategyOptions} />
          </div>
          <div>
            <label className="text-xs text-white/40 mb-1 block">Engine</label>
            <Select value="equity_engine" onChange={() => {}} options={engineOptions} />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs text-white/40 mb-1 block">Start</label>
              <Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label className="text-xs text-white/40 mb-1 block">End</label>
              <Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>
        </div>

        {/* Run Button + Progress */}
        <div className="flex items-center gap-4">
          <Button variant="glow" onClick={handleRunBacktest} disabled={isRunning}>
            {isRunning ? (
              <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" />
            ) : (
              <Play className="w-3.5 h-3.5 mr-1.5" />
            )}
            {isRunning ? "Running..." : "Run Backtest"}
          </Button>
          {isRunning && (
            <div className="flex-1">
              <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                <div className="h-full bg-blue-500/60 rounded-full transition-all duration-300" style={{ width: `${progress}%` }} />
              </div>
              <p className="text-xs text-white/30 mt-1">{progress}% complete</p>
            </div>
          )}
        </div>
      </ChartCard>

      {/* Results */}
      <Tabs defaultValue="equity">
        <TabsList>
          <TabsTrigger value="equity">Equity Curve</TabsTrigger>
          <TabsTrigger value="drawdown">Drawdown</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
          <TabsTrigger value="montecarlo">Monte Carlo</TabsTrigger>
        </TabsList>

        <TabsContent value="equity">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
            <StatusCard title="Total Return" value={formatPercent(result.totalReturn)} variant="success" />
            <StatusCard title="Sharpe Ratio" value={result.sharpe.toFixed(2)} />
            <StatusCard title="Max Drawdown" value={`${result.maxDrawdown}%`} variant="danger" />
            <StatusCard title="Win Rate" value={`${result.winRate}%`} />
          </div>
          <ChartCard title="Equity Curve" className="mt-3" glow="emerald">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={result.equityCurve}>
                  <defs>
                    <linearGradient id="btEquityGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(0)}K`} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                  <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#btEquityGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="drawdown">
          <ChartCard title="Drawdown" subtitle="Peak-to-trough declines">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={result.drawdownCurve}>
                  <defs>
                    <linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} />
                      <stop offset="95%" stopColor="#ef4444" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                  <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={(v) => `${v.toFixed(1)}%`} />
                  <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                  <Area type="monotone" dataKey="value" stroke="#ef4444" fill="url(#ddGrad)" strokeWidth={2} />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="metrics">
          <ChartCard title="Performance Metrics" subtitle="Detailed backtest statistics">
            <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
              {[
                { label: "Total Return", value: formatPercent(result.totalReturn), color: "text-emerald-400" },
                { label: "Sharpe Ratio", value: result.sharpe.toFixed(2), color: "text-blue-400" },
                { label: "Max Drawdown", value: `${result.maxDrawdown}%`, color: "text-red-400" },
                { label: "Win Rate", value: `${result.winRate}%`, color: "text-emerald-400" },
                { label: "Total Trades", value: result.totalTrades.toString(), color: "text-white/70" },
                { label: "Initial Capital", value: formatCurrency(result.initialCapital), color: "text-white/70" },
                { label: "Final Value", value: formatCurrency(result.finalValue), color: "text-emerald-400" },
              ].map((metric, i) => (
                <div key={i} className="bbg-cell">
                  <p className="text-[10px] text-white/30 mb-0.5">{metric.label}</p>
                  <p className={`text-base font-mono font-bold ${metric.color}`}>{metric.value}</p>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="montecarlo">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
            <StatusCard title="Simulations" value={result.monteCarlo.simulations.toLocaleString()} />
            <StatusCard title="Mean Return" value={formatPercent(result.monteCarlo.meanReturn)} variant="success" />
            <StatusCard title="5th Percentile" value={formatPercent(result.monteCarlo.p5Return)} variant="warning" />
            <StatusCard title="Worst Case" value={formatPercent(result.monteCarlo.worstCase)} variant="danger" />
          </div>
          <ChartCard title="Monte Carlo Distribution" className="mt-3" subtitle={`${result.monteCarlo.simulations.toLocaleString()} simulations`}>
            <div className="space-y-3">
              {[
                { label: "Best Case", value: result.monteCarlo.bestCase, color: "#10b981" },
                { label: "95th Percentile", value: result.monteCarlo.p95Return, color: "#34d399" },
                { label: "Mean", value: result.monteCarlo.meanReturn, color: "#3b82f6" },
                { label: "5th Percentile", value: result.monteCarlo.p5Return, color: "#f59e0b" },
                { label: "Worst Case", value: result.monteCarlo.worstCase, color: "#ef4444" },
              ].map((item, i) => (
                <div key={i} className="flex items-center gap-3">
                  <span className="text-xs text-white/40 w-28">{item.label}</span>
                  <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                    <div className="h-full rounded-full transition-all duration-1000" style={{ width: `${Math.max(5, ((item.value + 10) / 70) * 100)}%`, backgroundColor: item.color }} />
                  </div>
                  <span className="text-xs font-mono text-white/60 w-16 text-right">{formatPercent(item.value)}</span>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
