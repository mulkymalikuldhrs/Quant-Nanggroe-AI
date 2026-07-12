"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import {
  FlaskConical,
  Play,
  RefreshCw,
  CheckCircle2,
  Clock,
  AlertTriangle,
  TrendingUp,
  TrendingDown,
  BarChart3,
  Settings2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, StatusBadge, SectionHeader, Skeleton, AnimatedNumber } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

const STRATEGIES = [
  "sma_crossover",
  "mean_reversion",
  "momentum",
  "breakout",
  "pairs_trading",
  "statistical_arb",
];

export default function BacktestPage() {
  const {
    backtests,
    backtestResult,
    loadingBacktests,
    loadingBacktestResult,
    fetchBacktests,
    fetchBacktestResult,
    submitBacktest,
  } = useAppStore();

  const [symbol, setSymbol] = useState("AAPL");
  const [strategy, setStrategy] = useState("sma_crossover");
  const [startDate, setStartDate] = useState("2024-01-01");
  const [endDate, setEndDate] = useState("2024-12-31");
  const [initialCapital, setInitialCapital] = useState("100000");
  const [commission, setCommission] = useState("0.001");
  const [slippage, setSlippage] = useState("0.0005");
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [pollingId, setPollingId] = useState<string | null>(null);

  useEffect(() => {
    fetchBacktests();
  }, [fetchBacktests]);

  // Poll for backtest result
  useEffect(() => {
    if (!pollingId) return;
    const interval = setInterval(async () => {
      await fetchBacktestResult(pollingId);
    }, 2000);
    return () => clearInterval(interval);
  }, [pollingId, fetchBacktestResult]);

  // Stop polling when result is complete
  useEffect(() => {
    if (backtestResult && (backtestResult.status === "COMPLETED" || backtestResult.status === "FAILED")) {
      setPollingId(null);
    }
  }, [backtestResult]);

  const handleSubmit = async () => {
    setIsSubmitting(true);
    try {
      const id = await submitBacktest({
        symbol,
        strategy,
        start_date: startDate,
        end_date: endDate,
        initial_capital: parseFloat(initialCapital),
        commission: parseFloat(commission),
        slippage: parseFloat(slippage),
      });
      if (id) {
        setPollingId(id);
      }
    } finally {
      setIsSubmitting(false);
    }
  };

  // Equity curve chart data
  const equityData =
    backtestResult?.equity_curve?.map((val, i) => ({
      day: i,
      equity: val,
    })) || [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <FlaskConical className="w-8 h-8 text-amber animate-pulse-glow" />
            Simulation Engine
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Backtest & Validate Trading Strategies
          </p>
        </div>
        <Button variant="outline" size="icon" onClick={() => fetchBacktests()} className="cursor-pointer scale-tap bg-background/50 backdrop-blur-sm border-border/50 hover:border-amber/50 hover:bg-amber/10 hover:text-amber transition-colors">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        {/* Config Panel */}
        <div className="space-y-6">
          <Card variant="flat" className="border-t-4 border-t-amber relative overflow-hidden group">
            <div className="absolute right-0 top-0 w-32 h-32 bg-amber/5 rounded-bl-full translate-x-16 -translate-y-16 group-hover:bg-amber/10 transition-colors pointer-events-none" />
            <CardHeader className="relative z-10">
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Settings2 className="w-4 h-4 text-amber" />
                Parameters
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4 relative z-10">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Symbol</label>
                <Input
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="font-mono bg-secondary/20 focus-visible:ring-amber/50"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Strategy</label>
                <Select value={strategy} onValueChange={setStrategy}>
                  <SelectTrigger className="bg-secondary/20 focus:ring-amber/50">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {STRATEGIES.map((s) => (
                      <SelectItem key={s} value={s}>
                        {s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Start Date</label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="bg-secondary/20 focus-visible:ring-amber/50 font-mono text-xs"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">End Date</label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="bg-secondary/20 focus-visible:ring-amber/50 font-mono text-xs"
                  />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Initial Capital</label>
                <div className="relative">
                  <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">$</span>
                  <Input
                    type="number"
                    value={initialCapital}
                    onChange={(e) => setInitialCapital(e.target.value)}
                    className="tabular-nums font-mono pl-6 bg-secondary/20 focus-visible:ring-amber/50"
                  />
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Commission</label>
                  <Input
                    type="number"
                    value={commission}
                    onChange={(e) => setCommission(e.target.value)}
                    step="0.0001"
                    className="tabular-nums font-mono bg-secondary/20 focus-visible:ring-amber/50"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">Slippage</label>
                  <Input
                    type="number"
                    value={slippage}
                    onChange={(e) => setSlippage(e.target.value)}
                    step="0.0001"
                    className="tabular-nums font-mono bg-secondary/20 focus-visible:ring-amber/50"
                  />
                </div>
              </div>
              <Button
                className="w-full cursor-pointer h-12 font-bold text-base tracking-wide bg-amber hover:bg-amber/90 text-primary-foreground shadow-[0_4px_20px_rgba(245,158,11,0.3)] hover-lift mt-2"
                onClick={handleSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                    SIMULATING...
                  </>
                ) : (
                  <>
                    <Play className="w-5 h-5 mr-2" />
                    RUN BACKTEST
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Previous Backtests */}
          <Card variant="flat">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Clock className="w-4 h-4 text-cyan" />
                History
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-64 pr-3">
                {backtests.length > 0 ? (
                  <div className="space-y-3 stagger-children">
                    {backtests.map((bt) => (
                      <button
                        key={bt.id}
                        onClick={() => fetchBacktestResult(bt.id)}
                        className="w-full p-3 rounded-xl bg-secondary/20 border border-border/40 hover:border-cyan/40 hover:bg-cyan/5 transition-all text-left cursor-pointer group"
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <span className="text-sm font-bold font-mono text-foreground tracking-tight">
                            {bt.symbol}
                          </span>
                          <StatusBadge
                            status={
                              bt.status === "COMPLETED"
                                ? "active"
                                : bt.status === "RUNNING"
                                ? "processing"
                                : bt.status === "FAILED"
                                ? "error"
                                : "idle"
                            }
                          />
                        </div>
                        <p className="text-[10px] text-muted-foreground font-medium uppercase tracking-widest flex items-center justify-between">
                          <span>{bt.strategy.replace(/_/g, " ")}</span>
                          <span className="font-mono opacity-50">#{bt.id.slice(0, 8)}</span>
                        </p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground text-xs font-medium">
                    No backtests yet
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>

        {/* Results */}
        <div className="lg:col-span-2 space-y-6">
          {/* Progress indicator when running */}
          {pollingId && backtestResult?.status === "RUNNING" && (
            <Card className="glass-card p-6 border-amber/30 bg-amber/5 animate-pulse relative overflow-hidden">
              <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(245,158,11,0.05)_50%,transparent_75%)] bg-[length:250%_250%,100%_100%] animate-shimmer" />
              <div className="flex items-center gap-4 relative z-10">
                <RefreshCw className="w-8 h-8 text-amber animate-spin drop-shadow-[0_0_10px_rgba(245,158,11,0.5)]" />
                <div className="flex-1">
                  <p className="text-sm font-bold text-foreground uppercase tracking-widest mb-1">
                    Simulation Running
                  </p>
                  <p className="text-xs text-muted-foreground font-mono">
                    {symbol} — {strategy}
                  </p>
                </div>
                <div className="w-1/2">
                  <Progress value={75} className="h-2" indicatorClassName="bg-gradient-to-r from-amber to-cyan animate-pulse" />
                </div>
              </div>
            </Card>
          )}

          {/* Results Display */}
          {backtestResult && backtestResult.status === "COMPLETED" ? (
            <div className="space-y-6 animate-slide-up">
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4 stagger-children">
                <MetricCard
                  title="Total Return"
                  value={backtestResult.total_return * 100}
                  formatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`}
                  icon={<TrendingUp className="w-5 h-5" />}
                  color={backtestResult.total_return >= 0 ? "emerald" : "rose"}
                />
                <MetricCard
                  title="Sharpe Ratio"
                  value={backtestResult.sharpe_ratio}
                  formatter={(v) => v.toFixed(2)}
                  icon={<BarChart3 className="w-5 h-5" />}
                  color={backtestResult.sharpe_ratio >= 1 ? "emerald" : "amber"}
                />
                <MetricCard
                  title="Max Drawdown"
                  value={backtestResult.max_drawdown * 100}
                  formatter={(v) => `${v.toFixed(2)}%`}
                  icon={<TrendingDown className="w-5 h-5" />}
                  color="rose"
                />
                <MetricCard
                  title="Win Rate"
                  value={backtestResult.win_rate * 100}
                  formatter={(v) => `${v.toFixed(1)}%`}
                  icon={<CheckCircle2 className="w-5 h-5" />}
                  color={backtestResult.win_rate >= 0.5 ? "emerald" : "amber"}
                />
                <MetricCard
                  title="Total Trades"
                  value={backtestResult.total_trades}
                  icon={<BarChart3 className="w-5 h-5" />}
                  color="cyan"
                />
                <MetricCard
                  title="Profit Factor"
                  value={backtestResult.profit_factor}
                  formatter={(v) => v.toFixed(2)}
                  icon={<TrendingUp className="w-5 h-5" />}
                  color={backtestResult.profit_factor >= 1 ? "emerald" : "rose"}
                />
                <MetricCard
                  title="Avg Win"
                  value={backtestResult.avg_win}
                  formatter={(v) => `$${v.toFixed(2)}`}
                  icon={<TrendingUp className="w-5 h-5" />}
                  color="emerald"
                />
                <MetricCard
                  title="Avg Loss"
                  value={backtestResult.avg_loss}
                  formatter={(v) => `$${v.toFixed(2)}`}
                  icon={<TrendingDown className="w-5 h-5" />}
                  color="rose"
                />
              </div>

              {/* Equity Curve */}
              <Card variant="gradient">
                <CardHeader>
                  <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                    <LineChart className="w-4 h-4 text-emerald" />
                    Equity Curve
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-[360px] w-full">
                    {equityData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={equityData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                          <defs>
                            <linearGradient id="backtestGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.4} />
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                            </linearGradient>
                            <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
                              <feGaussianBlur stdDeviation="4" result="blur" />
                              <feComposite in="SourceGraphic" in2="blur" operator="over" />
                            </filter>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                          <XAxis dataKey="day" stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                          <YAxis stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} tickFormatter={(v) => `$${(v/1000).toFixed(0)}k`} />
                          <Tooltip
                            contentStyle={{
                              background: "rgba(10, 15, 26, 0.95)",
                              backdropFilter: "blur(10px)",
                              border: "1px solid rgba(16, 185, 129, 0.3)",
                              borderRadius: "8px",
                              boxShadow: "0 4px 20px rgba(0,0,0,0.4), 0 0 10px rgba(16,185,129,0.1)",
                              fontSize: "12px",
                              fontWeight: 600,
                            }}
                            itemStyle={{ color: "#10b981" }}
                            formatter={(value: number) => [
                              `$${value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`,
                              "Equity",
                            ]}
                            cursor={{ stroke: 'rgba(16, 185, 129, 0.5)', strokeWidth: 1, strokeDasharray: '4 4' }}
                          />
                          <Area
                            type="monotone"
                            dataKey="equity"
                            stroke="#10b981"
                            strokeWidth={3}
                            fill="url(#backtestGrad)"
                            activeDot={{ r: 6, fill: "#10b981", stroke: "#030712", strokeWidth: 2, filter: "url(#glowGreen)" }}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-medium">
                        No equity curve data
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </div>
          ) : backtestResult?.status === "FAILED" ? (
            <Card className="glass-card p-8 border-rose/30 bg-rose/5">
              <div className="flex items-center gap-4">
                <div className="p-3 bg-rose/20 rounded-full">
                  <AlertTriangle className="w-8 h-8 text-rose drop-shadow-[0_0_10px_rgba(244,63,94,0.5)]" />
                </div>
                <div>
                  <p className="text-lg font-black tracking-tight text-rose uppercase mb-1">Simulation Failed</p>
                  <p className="text-sm font-medium text-rose/80">
                    {backtestResult.error || "An unknown error occurred during execution."}
                  </p>
                </div>
              </div>
            </Card>
          ) : backtestResult?.status === "RUNNING" || backtestResult?.status === "QUEUED" ? (
            null
          ) : (
            <Card className="glass-card p-16 flex flex-col items-center justify-center h-[500px]">
              <div className="w-24 h-24 rounded-full bg-secondary/30 flex items-center justify-center mb-6 shadow-[inset_0_0_20px_rgba(255,255,255,0.05)]">
                <FlaskConical className="w-10 h-10 text-muted-foreground/50" />
              </div>
              <h3 className="text-xl font-bold text-foreground mb-2">Awaiting Parameters</h3>
              <p className="text-sm text-muted-foreground text-center max-w-sm">
                Configure a simulation in the left panel to validate your trading strategies against historical market data.
              </p>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
