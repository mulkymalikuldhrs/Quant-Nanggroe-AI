"use client";

import React, { useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { useAppStore } from "@/lib/store";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { FlaskConical, Play } from "lucide-react";
import { AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid } from "recharts";

const engineOptions = [
  { value: "equity_engine", label: "Equity Engine" }, { value: "crypto_engine", label: "Crypto Engine" },
  { value: "forex_engine", label: "Forex Engine" }, { value: "futures_engine", label: "Futures Engine" },
  { value: "walk_forward", label: "Walk Forward" }, { value: "monte_carlo", label: "Monte Carlo" },
];

const factorZooList = [
  { name: "Alpha101", count: 101, description: "WorldQuant 101 Alpha factors" },
  { name: "GTJA191", count: 191, description: "Guotai Junan 191 factors" },
  { name: "Qlib158", count: 158, description: "Microsoft Qlib 158 factors" },
  { name: "Barra", count: 10, description: "Barra risk model factors" },
  { name: "Technical", count: 5, description: "Technical analysis factors" },
  { name: "Fundamental", count: 3, description: "Fundamental analysis factors" },
  { name: "Academic", count: 1, description: "Academic research factors" },
];

export default function BacktestPage() {
  const { backtestResult, runBacktest } = useAppStore();
  const [symbol, setSymbol] = useState("AAPL");
  const [engine, setEngine] = useState("equity_engine");
  const [strategy, setStrategy] = useState("momentum_alpha");
  const [startDate, setStartDate] = useState("2023-01-01");
  const [endDate, setEndDate] = useState("2024-01-01");
  const [selectedFactors, setSelectedFactors] = useState<string[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const [progress, setProgress] = useState(0);

  const strategyOptions = [
    { value: "momentum_alpha", label: "Momentum Alpha" }, { value: "value_quality", label: "Value + Quality" },
    { value: "mean_reversion", label: "Mean Reversion" }, { value: "breakout_scanner", label: "Breakout Scanner" },
    { value: "crypto_momentum", label: "Crypto Momentum" }, { value: "forex_carry", label: "Forex Carry" },
  ];

  const handleRunBacktest = async () => {
    setIsRunning(true);
    setProgress(0);
    const interval = setInterval(() => {
      setProgress((prev) => { if (prev >= 100) { clearInterval(interval); return 100; } return prev + 2; });
    }, 60);
    await runBacktest({ strategy, symbols: [symbol], period: "1Y" });
    setIsRunning(false);
  };

  const toggleFactor = (zooName: string) => {
    setSelectedFactors((prev) => prev.includes(zooName) ? prev.filter((f) => f !== zooName) : [...prev, zooName]);
  };

  const result = backtestResult || {
    id: "bt_001", strategy: "Momentum Alpha", symbol: "AAPL", startDate: "2023-01-01", endDate: "2024-01-01",
    initialCapital: 100000, finalValue: 128450, totalReturn: 28.45, sharpe: 1.92, maxDrawdown: -8.7,
    winRate: 61.5, totalTrades: 156,
    equityCurve: Array.from({ length: 252 }, (_, i) => {
      const date = new Date(2023, 0, 1); date.setDate(date.getDate() + i);
      const value = 100000 + Math.sin(i / 20) * 5000 + i * 110 + Math.random() * 2000;
      return { date: date.toISOString().split("T")[0], value: Math.round(value * 100) / 100 };
    }),
    drawdownCurve: Array.from({ length: 252 }, (_, i) => {
      const date = new Date(2023, 0, 1); date.setDate(date.getDate() + i);
      return { date: date.toISOString().split("T")[0], value: -Math.abs(Math.sin(i / 30) * 5 + Math.random() * 3) };
    }),
    monteCarlo: { simulations: 1000, meanReturn: 26.8, p5Return: 12.3, p95Return: 42.1, worstCase: -5.2, bestCase: 58.4 },
  };

  return (
    <div className="space-y-4 animate-slide-up">
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2"><FlaskConical className="w-5 h-5 text-blue-400" />Backtesting Engine</h1>
        <p className="text-sm text-white/40 mt-0.5">{engineOptions.length} engines • 469 alpha factors</p>
      </div>

      <ChartCard title="Backtest Configuration" subtitle="Configure and run backtests">
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 mb-4">
          <div><label className="text-xs text-white/40 mb-1 block">Symbol</label><Input value={symbol} onChange={(e) => setSymbol(e.target.value)} /></div>
          <div><label className="text-xs text-white/40 mb-1 block">Strategy</label><Select value={strategy} onChange={(e) => setStrategy(e.target.value)} options={strategyOptions} /></div>
          <div><label className="text-xs text-white/40 mb-1 block">Engine</label><Select value={engine} onChange={(e) => setEngine(e.target.value)} options={engineOptions} /></div>
          <div className="grid grid-cols-2 gap-2">
            <div><label className="text-xs text-white/40 mb-1 block">Start</label><Input type="date" value={startDate} onChange={(e) => setStartDate(e.target.value)} /></div>
            <div><label className="text-xs text-white/40 mb-1 block">End</label><Input type="date" value={endDate} onChange={(e) => setEndDate(e.target.value)} /></div>
          </div>
        </div>

        <div className="mb-4">
          <label className="text-xs text-white/40 mb-2 block">Factor Zoos</label>
          <div className="flex flex-wrap gap-2">
            {factorZooList.map((zoo) => (
              <button key={zoo.name} onClick={() => toggleFactor(zoo.name)}
                className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all border ${selectedFactors.includes(zoo.name) ? "bg-blue-500/15 text-blue-400 border-blue-500/30" : "bg-white/[0.03] text-white/40 border-white/[0.06] hover:bg-white/[0.06]"}`}>
                {zoo.name}<span className="ml-1 text-white/30">({zoo.count})</span>
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-4">
          <Button variant="glow" onClick={handleRunBacktest} disabled={isRunning}>
            {isRunning ? <div className="w-3.5 h-3.5 mr-1.5 border-2 border-white/30 border-t-white rounded-full animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1.5" />}
            {isRunning ? "Running..." : "Run Backtest"}
          </Button>
          {isRunning && <div className="flex-1"><Progress value={progress} /><p className="text-xs text-white/30 mt-1">{progress}% complete</p></div>}
        </div>
      </ChartCard>

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
                <AreaChart data={result.equityCurve.filter((_: unknown, i: number) => i % 2 === 0)}>
                  <defs><linearGradient id="btEquityGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
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
          <ChartCard title="Drawdown" subtitle="Peak-to-trough declines" glow="red">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={result.drawdownCurve.filter((_: unknown, i: number) => i % 2 === 0)}>
                  <defs><linearGradient id="ddGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#ef4444" stopOpacity={0.3} /><stop offset="95%" stopColor="#ef4444" stopOpacity={0} /></linearGradient></defs>
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
                <div key={i} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-1">{metric.label}</p>
                  <p className={`text-lg font-mono font-bold ${metric.color}`}>{metric.value}</p>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="montecarlo">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-3">
            <StatusCard title="Simulations" value="1,000" />
            <StatusCard title="Mean Return" value={formatPercent(result.monteCarlo.meanReturn)} variant="success" />
            <StatusCard title="5th Percentile" value={formatPercent(result.monteCarlo.p5Return)} variant="warning" />
            <StatusCard title="Worst Case" value={formatPercent(result.monteCarlo.worstCase)} variant="danger" />
          </div>
          <ChartCard title="Monte Carlo Distribution" className="mt-3" subtitle="1000 simulations">
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
