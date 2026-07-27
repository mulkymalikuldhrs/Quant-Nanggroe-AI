"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { backtestApi } from "@/lib/api-client";
import type { WalkForwardResult, WalkForwardStatus, BatchWalkForwardResult } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import {
  FlaskConical,
  Play,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  AlertCircle,
  CheckCircle,
} from "lucide-react";
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid,
  Legend,
} from "recharts";

export default function WalkForwardPage() {
  const [strategies, setStrategies] = useState<Array<{ id: string; name: string }>>([]);
  const [selectedStrategy, setSelectedStrategy] = useState("");
  const [mode, setMode] = useState<"rolling" | "anchored" | "cpcv">("rolling");
  const [isRunning, setIsRunning] = useState(false);
  const [result, setResult] = useState<WalkForwardResult | null>(null);
  const [batchResult, setBatchResult] = useState<BatchWalkForwardResult | null>(null);
  const [wfStatus, setWfStatus] = useState<WalkForwardStatus | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [strats, status] = await Promise.allSettled([
          backtestApi.getStrategies(),
          backtestApi.walkForwardStatus(),
        ]);
        if (strats.status === "fulfilled") {
          setStrategies(strats.value.map((s) => ({ id: s.id, name: s.name })));
          if (strats.value.length > 0 && !selectedStrategy) {
            setSelectedStrategy(strats.value[0].id);
          }
        }
        if (status.status === "fulfilled") {
          setWfStatus(status.value);
        }
      } catch (err) {
        // Strategies load failed - continue with empty list
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  const handleRunWF = async () => {
    if (!selectedStrategy) return;
    setIsRunning(true);
    setResult(null);
    try {
      const res = await backtestApi.runWalkForward({
        strategy: selectedStrategy,
        mode,
        train_window: 252,
        test_window: 63,
      });
      setResult(res);
    } catch (err) {
      // Walk-forward validation failed - result stays null
    } finally {
      setIsRunning(false);
    }
  };

  const handleBatchWF = async () => {
    setIsRunning(true);
    setBatchResult(null);
    try {
      const res = await backtestApi.batchWalkForward({ symbol: "BTC-USD", period: "2y" });
      setBatchResult(res);
    } catch (err) {
      // Batch validation failed - result stays null
    } finally {
      setIsRunning(false);
    }
  };

  if (loading) {
    return (
      <div className="space-y-4 animate-slide-up">
        <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  const strategyOptions = strategies.map((s) => ({ value: s.id, label: s.name }));
  const modeOptions = [
    { value: "rolling", label: "Rolling" },
    { value: "anchored", label: "Anchored" },
    { value: "cpcv", label: "CPCV" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <FlaskConical className="w-5 h-5 text-blue-400" />
            Walk-Forward Validation
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            Rolling window validation • Out-of-sample testing • Decay detection
          </p>
        </div>
        <Button variant="ghost" size="sm" onClick={() => backtestApi.walkForwardStatus().then(setWfStatus)} disabled={isRunning}>
          <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
          Refresh
        </Button>
      </div>

      {/* Status Summary */}
      {wfStatus && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatusCard title="Total Strategies" value={String(wfStatus.total_strategies)} variant="info" />
          <StatusCard title="Validated" value={String(wfStatus.validated_count)} variant="success" />
          <StatusCard title="Decayed" value={String(wfStatus.decayed_count)} variant={wfStatus.decayed_count > 0 ? "danger" : "success"} />
          <StatusCard
            title="Avg OOS Sharpe"
            value={wfStatus.strategies.length > 0
              ? (wfStatus.strategies.reduce((s, st) => s + st.avg_oos_sharpe, 0) / wfStatus.strategies.length).toFixed(2)
              : "—"
            }
          />
        </div>
      )}

      {/* Single Strategy WF */}
      <Tabs defaultValue="single">
        <TabsList>
          <TabsTrigger value="single">Single Strategy</TabsTrigger>
          <TabsTrigger value="batch">Batch Validation</TabsTrigger>
          <TabsTrigger value="status">Registry Status</TabsTrigger>
        </TabsList>

        <TabsContent value="single">
          <ChartCard title="Single Strategy Walk-Forward" subtitle="Validate strategy across rolling windows">
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
              <div>
                <label className="text-xs text-white/40 mb-1 block">Strategy</label>
                <Select value={selectedStrategy} onChange={(e) => setSelectedStrategy(e.target.value)} options={strategyOptions} />
              </div>
              <div>
                <label className="text-xs text-white/40 mb-1 block">Mode</label>
                <Select value={mode} onChange={(e) => setMode(e.target.value as any)} options={modeOptions} />
              </div>
              <div className="flex items-end">
                <Button variant="glow" onClick={handleRunWF} disabled={isRunning || !selectedStrategy} className="w-full">
                  {isRunning ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1.5" />}
                  {isRunning ? "Validating..." : "Run Walk-Forward"}
                </Button>
              </div>
            </div>

            {result && (
              <div className="space-y-4 mt-4">
                {/* Aggregate Stats */}
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
                  <StatusCard title="Folds" value={String(result.n_folds)} />
                  <StatusCard title="Mean IS Sharpe" value={result.aggregate.mean_is_sharpe.toFixed(2)} variant="info" />
                  <StatusCard title="Mean OOS Sharpe" value={result.aggregate.mean_oos_sharpe.toFixed(2)} variant={result.aggregate.mean_oos_sharpe > 0 ? "success" : "danger"} />
                  <StatusCard title="Degradation" value={`${(result.aggregate.degradation_ratio * 100).toFixed(0)}%`} variant={result.aggregate.degradation_ratio < 0.3 ? "success" : "warning"} />
                  <StatusCard title="Stability" value={`${(result.stability.overall_stability * 100).toFixed(0)}%`} variant={result.stability.overall_stability > 0.6 ? "success" : "warning"} />
                </div>

                {/* Fold-by-Fold Chart */}
                <ChartCard title="Fold Performance" subtitle="IS vs OOS Sharpe per fold">
                  <div className="h-64">
                    <ResponsiveContainer width="100%" height="100%">
                      <BarChart data={result.folds}>
                        <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                        <XAxis dataKey="fold" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                        <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                        <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                        <Legend />
                        <Bar dataKey="is_sharpe" fill="#10b981" name="IS Sharpe" radius={[4, 4, 0, 0]} />
                        <Bar dataKey="oos_sharpe" fill="#3b82f6" name="OOS Sharpe" radius={[4, 4, 0, 0]} />
                      </BarChart>
                    </ResponsiveContainer>
                  </div>
                </ChartCard>

                {/* Fold Details Table */}
                <ChartCard title="Fold Details" subtitle="Per-fold metrics">
                  <div className="overflow-x-auto">
                    <table className="w-full text-xs">
                      <thead>
                        <tr className="border-b border-white/10">
                          <th className="p-2 text-left text-white/40">Fold</th>
                          <th className="p-2 text-right text-white/40">IS Sharpe</th>
                          <th className="p-2 text-right text-white/40">OOS Sharpe</th>
                          <th className="p-2 text-right text-white/40">IS Return</th>
                          <th className="p-2 text-right text-white/40">OOS Return</th>
                          <th className="p-2 text-right text-white/40">Degradation</th>
                        </tr>
                      </thead>
                      <tbody>
                        {result.folds.map((fold) => {
                          const deg = fold.is_sharpe !== 0 ? (fold.oos_sharpe / fold.is_sharpe) : 0;
                          return (
                            <tr key={fold.fold} className="border-b border-white/5">
                              <td className="p-2 text-white/70">#{fold.fold}</td>
                              <td className="p-2 text-right font-mono text-emerald-400">{fold.is_sharpe.toFixed(2)}</td>
                              <td className="p-2 text-right font-mono text-blue-400">{fold.oos_sharpe.toFixed(2)}</td>
                              <td className="p-2 text-right font-mono text-emerald-400">{(fold.is_return * 100).toFixed(1)}%</td>
                              <td className="p-2 text-right font-mono text-blue-400">{(fold.oos_return * 100).toFixed(1)}%</td>
                              <td className="p-2 text-right font-mono">
                                <span className={cn(deg > 0.7 ? "text-emerald-400" : deg > 0.4 ? "text-amber-400" : "text-red-400")}>
                                  {(deg * 100).toFixed(0)}%
                                </span>
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </ChartCard>
              </div>
            )}
          </ChartCard>
        </TabsContent>

        <TabsContent value="batch">
          <ChartCard title="Batch Walk-Forward Validation" subtitle="Validate all strategies">
            <div className="mb-4">
              <Button variant="glow" onClick={handleBatchWF} disabled={isRunning}>
                {isRunning ? <RefreshCw className="w-3.5 h-3.5 mr-1.5 animate-spin" /> : <Play className="w-3.5 h-3.5 mr-1.5" />}
                {isRunning ? "Validating All..." : "Validate All Strategies"}
              </Button>
            </div>

            {batchResult && (
              <div className="space-y-4">
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  <StatusCard title="Total" value={String(batchResult.total)} />
                  <StatusCard title="Validated" value={String(batchResult.validated)} variant="success" />
                  <StatusCard title="Decayed" value={String(batchResult.results.filter((r) => r.decayed).length)} variant="danger" />
                  <StatusCard
                    title="Avg OOS Sharpe"
                    value={batchResult.results.length > 0
                      ? (batchResult.results.reduce((s, r) => s + r.mean_oos_sharpe, 0) / batchResult.results.length).toFixed(2)
                      : "—"
                    }
                  />
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-white/10">
                        <th className="p-2 text-left text-white/40">Strategy</th>
                        <th className="p-2 text-right text-white/40">Folds</th>
                        <th className="p-2 text-right text-white/40">OOS Sharpe</th>
                        <th className="p-2 text-right text-white/40">OOS Return</th>
                        <th className="p-2 text-center text-white/40">Status</th>
                      </tr>
                    </thead>
                    <tbody>
                      {batchResult.results
                        .sort((a, b) => b.mean_oos_sharpe - a.mean_oos_sharpe)
                        .map((r) => (
                          <tr key={r.strategy} className="border-b border-white/5">
                            <td className="p-2 text-white/70 font-medium">{r.strategy}</td>
                            <td className="p-2 text-right font-mono text-white/50">{r.n_folds}</td>
                            <td className="p-2 text-right font-mono">
                              <span className={r.mean_oos_sharpe > 0 ? "text-emerald-400" : "text-red-400"}>
                                {r.mean_oos_sharpe.toFixed(2)}
                              </span>
                            </td>
                            <td className="p-2 text-right font-mono">
                              <span className={r.mean_oos_return > 0 ? "text-emerald-400" : "text-red-400"}>
                                {(r.mean_oos_return * 100).toFixed(1)}%
                              </span>
                            </td>
                            <td className="p-2 text-center">
                              {r.decayed ? (
                                <Badge variant="danger" className="text-[10px]">DECAYED</Badge>
                              ) : (
                                <Badge variant="success" className="text-[10px]">VALID</Badge>
                              )}
                            </td>
                          </tr>
                        ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}
          </ChartCard>
        </TabsContent>

        <TabsContent value="status">
          <ChartCard title="Walk-Forward Registry" subtitle="Historical validation results">
            {wfStatus && wfStatus.strategies.length > 0 ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/10">
                      <th className="p-2 text-left text-white/40">Strategy</th>
                      <th className="p-2 text-right text-white/40">Validations</th>
                      <th className="p-2 text-right text-white/40">Best OOS</th>
                      <th className="p-2 text-right text-white/40">Avg OOS</th>
                      <th className="p-2 text-right text-white/40">Decays</th>
                    </tr>
                  </thead>
                  <tbody>
                    {wfStatus.strategies
                      .sort((a, b) => b.best_oos_sharpe - a.best_oos_sharpe)
                      .map((s) => (
                        <tr key={s.name} className="border-b border-white/5">
                          <td className="p-2 text-white/70 font-medium">{s.name}</td>
                          <td className="p-2 text-right font-mono text-white/50">{s.n_validations}</td>
                          <td className="p-2 text-right font-mono text-emerald-400">{s.best_oos_sharpe.toFixed(2)}</td>
                          <td className="p-2 text-right font-mono text-blue-400">{s.avg_oos_sharpe.toFixed(2)}</td>
                          <td className="p-2 text-right font-mono">
                            <span className={s.decay_count > 0 ? "text-red-400" : "text-white/30"}>{s.decay_count}</span>
                          </td>
                        </tr>
                      ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <div className="text-center py-8 text-white/30">
                <AlertCircle className="w-8 h-8 mx-auto mb-2 opacity-50" />
                <p>No walk-forward validations yet</p>
                <p className="text-xs mt-1">Run batch validation to populate registry</p>
              </div>
            )}
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
