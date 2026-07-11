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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { Progress } from "@/components/ui/progress";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, StatusBadge, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";

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
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <FlaskConical className="w-6 h-6 text-amber" />
            Backtest Engine
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Test strategies against historical data with full simulation
          </p>
        </div>
        <Button variant="ghost" size="icon" onClick={() => fetchBacktests()} className="cursor-pointer">
          <RefreshCw className="w-4 h-4" />
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Config Panel */}
        <div className="space-y-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <FlaskConical className="w-4 h-4 text-cyan" />
                Configuration
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Symbol</label>
                <Input
                  value={symbol}
                  onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                  className="font-mono"
                />
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Strategy</label>
                <Select value={strategy} onValueChange={setStrategy}>
                  <SelectTrigger>
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
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Start Date</label>
                  <Input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">End Date</label>
                  <Input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                  />
                </div>
              </div>
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">Initial Capital</label>
                <Input
                  type="number"
                  value={initialCapital}
                  onChange={(e) => setInitialCapital(e.target.value)}
                />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Commission</label>
                  <Input
                    type="number"
                    value={commission}
                    onChange={(e) => setCommission(e.target.value)}
                    step="0.0001"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">Slippage</label>
                  <Input
                    type="number"
                    value={slippage}
                    onChange={(e) => setSlippage(e.target.value)}
                    step="0.0001"
                  />
                </div>
              </div>
              <Button
                variant="cyan"
                className="w-full cursor-pointer"
                onClick={handleSubmit}
                disabled={isSubmitting}
              >
                {isSubmitting ? (
                  <>
                    <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                    Submitting...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4 mr-2" />
                    Run Backtest
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Previous Backtests */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                Previous Backtests
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-64">
                {backtests.length > 0 ? (
                  <div className="space-y-2">
                    {backtests.map((bt) => (
                      <button
                        key={bt.id}
                        onClick={() => fetchBacktestResult(bt.id)}
                        className="w-full p-2 rounded-lg bg-secondary/20 border border-border/30 hover:border-primary/30 transition-all text-left cursor-pointer"
                      >
                        <div className="flex items-center justify-between">
                          <span className="text-xs font-mono text-foreground">
                            {bt.symbol}
                          </span>
                          <StatusBadge
                            status={
                              bt.status === "COMPLETED"
                                ? "active"
                                : bt.status === "RUNNING"
                                ? "busy"
                                : bt.status === "FAILED"
                                ? "error"
                                : "idle"
                            }
                          />
                        </div>
                        <p className="text-[10px] text-muted-foreground mt-0.5">
                          {bt.strategy} • {bt.id.slice(0, 8)}
                        </p>
                      </button>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-6 text-muted-foreground text-xs">
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
            <Card className="glass-card p-4">
              <div className="flex items-center gap-3">
                <RefreshCw className="w-5 h-5 text-cyan animate-spin" />
                <div>
                  <p className="text-sm font-medium text-foreground">
                    Backtest Running...
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {symbol} — {strategy}
                  </p>
                </div>
                <Progress value={50} className="flex-1 ml-4" />
              </div>
            </Card>
          )}

          {/* Results Display */}
          {backtestResult && backtestResult.status === "COMPLETED" ? (
            <>
              {/* Metrics Grid */}
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 gap-4">
                <MetricCard
                  title="Total Return"
                  value={`${(backtestResult.total_return * 100).toFixed(2)}%`}
                  icon={<TrendingUp className="w-4 h-4" />}
                  color={backtestResult.total_return >= 0 ? "emerald" : "rose"}
                />
                <MetricCard
                  title="Sharpe Ratio"
                  value={backtestResult.sharpe_ratio.toFixed(2)}
                  icon={<BarChart3 className="w-4 h-4" />}
                  color={backtestResult.sharpe_ratio >= 1 ? "emerald" : "amber"}
                />
                <MetricCard
                  title="Max Drawdown"
                  value={`${(backtestResult.max_drawdown * 100).toFixed(2)}%`}
                  icon={<TrendingDown className="w-4 h-4" />}
                  color="rose"
                />
                <MetricCard
                  title="Win Rate"
                  value={`${(backtestResult.win_rate * 100).toFixed(1)}%`}
                  icon={<CheckCircle2 className="w-4 h-4" />}
                  color={backtestResult.win_rate >= 0.5 ? "emerald" : "amber"}
                />
                <MetricCard
                  title="Total Trades"
                  value={backtestResult.total_trades}
                  icon={<BarChart3 className="w-4 h-4" />}
                  color="cyan"
                />
                <MetricCard
                  title="Profit Factor"
                  value={backtestResult.profit_factor.toFixed(2)}
                  icon={<TrendingUp className="w-4 h-4" />}
                  color={backtestResult.profit_factor >= 1 ? "emerald" : "rose"}
                />
                <MetricCard
                  title="Avg Win"
                  value={`$${backtestResult.avg_win.toFixed(2)}`}
                  icon={<TrendingUp className="w-4 h-4" />}
                  color="emerald"
                />
                <MetricCard
                  title="Avg Loss"
                  value={`$${backtestResult.avg_loss.toFixed(2)}`}
                  icon={<TrendingDown className="w-4 h-4" />}
                  color="rose"
                />
              </div>

              {/* Equity Curve */}
              <Card className="glass-card">
                <CardHeader>
                  <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider">
                    Equity Curve
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="h-72">
                    {equityData.length > 0 ? (
                      <ResponsiveContainer width="100%" height="100%">
                        <AreaChart data={equityData}>
                          <defs>
                            <linearGradient id="backtestGrad" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#10b981" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                          <XAxis dataKey="day" stroke="#64748b" fontSize={10} />
                          <YAxis stroke="#64748b" fontSize={10} />
                          <Tooltip
                            contentStyle={{
                              background: "#0d1117",
                              border: "1px solid #1e293b",
                              borderRadius: "8px",
                              fontSize: "11px",
                            }}
                            formatter={(value: number) => [
                              `$${value.toLocaleString(undefined, { minimumFractionDigits: 2 })}`,
                              "Equity",
                            ]}
                          />
                          <Area
                            type="monotone"
                            dataKey="equity"
                            stroke="#10b981"
                            fill="url(#backtestGrad)"
                            strokeWidth={2}
                          />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                        No equity curve data
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            </>
          ) : backtestResult?.status === "FAILED" ? (
            <Card className="glass-card p-6">
              <div className="flex items-center gap-3">
                <AlertTriangle className="w-5 h-5 text-rose" />
                <div>
                  <p className="text-sm font-medium text-rose">Backtest Failed</p>
                  <p className="text-xs text-muted-foreground mt-0.5">
                    {backtestResult.error || "Unknown error"}
                  </p>
                </div>
              </div>
            </Card>
          ) : backtestResult?.status === "RUNNING" || backtestResult?.status === "QUEUED" ? (
            <Card className="glass-card p-6">
              <div className="flex items-center gap-3">
                <Clock className="w-5 h-5 text-amber animate-pulse" />
                <p className="text-sm text-foreground">
                  Backtest {backtestResult.status.toLowerCase()}...
                </p>
              </div>
            </Card>
          ) : (
            <Card className="glass-card p-12">
              <div className="text-center">
                <FlaskConical className="w-12 h-12 text-muted-foreground/30 mx-auto mb-4" />
                <p className="text-sm text-muted-foreground">
                  Configure and run a backtest to see results
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                  Select a symbol, strategy, and date range to get started
                </p>
              </div>
            </Card>
          )}
        </div>
      </div>
    </div>
  );
}
