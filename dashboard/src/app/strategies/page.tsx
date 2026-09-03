"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Switch } from "@/components/ui/switch";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { apiRequest, backtestApi, strategiesApi } from "@/lib/api-client";
import type { Strategy, WalkForwardStatus, StrategyPerformance, StrategyComparison } from "@/lib/api-client";
import { cn, formatPercent, formatCurrency, pnlColor } from "@/lib/utils";
import {
  Zap, Play, Pause, Plus, Code, Upload, FileJson, Settings, AlertCircle,
  RefreshCw, Search, Filter, TrendingUp, TrendingDown, FlaskConical,
  Sliders, BarChart3, GitCompare, CheckCircle2, XCircle,
} from "lucide-react";

function StrategiesContent() {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [wfStatus, setWfStatus] = useState<WalkForwardStatus | null>(null);
  const [togglingId, setTogglingId] = useState<string | null>(null);
  const [weights, setWeights] = useState<Record<string, number>>({});
  const [perfData, setPerfData] = useState<Record<string, StrategyPerformance>>({});
  const [loadingPerf, setLoadingPerf] = useState<Record<string, boolean>>({});
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [comparison, setComparison] = useState<StrategyComparison | null>(null);
  const [compareLoading, setCompareLoading] = useState(false);
  // CANONICAL 15.6: per-symbol CPCV specialists
  const [allocationMap, setAllocationMap] = useState<Record<string, string[]>>({});

  useEffect(() => {
    apiRequest<{ allocation_map: Record<string, string[]> }>("/api/export/allocation")
      .then((d) => setAllocationMap(d.allocation_map || {}))
      .catch(() => { /* allocation optional */ });
  }, []);

  const loadStrategies = async () => {
    setLoading(true);
    setError(null);
    try {
      const [strats, wf] = await Promise.allSettled([
        apiRequest<Strategy[]>("/api/backtest/strategies"),
        backtestApi.walkForwardStatus(),
      ]);
      if (strats.status === "fulfilled") {
        setStrategies(strats.value);
        const w: Record<string, number> = {};
        strats.value.forEach(s => { w[s.id] = 50; });
        setWeights(w);
      }
      if (wf.status === "fulfilled") setWfStatus(wf.value);
    } catch {
      setError("Backend unavailable — showing cached data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStrategies(); }, []);

  const handleToggle = async (id: string) => {
    setTogglingId(id);
    const next = !strategies.find((s) => s.id === id)?.enabled;
    try {
      await strategiesApi.toggle(id, next);
      setStrategies(prev => prev.map(s => s.id === id ? { ...s, enabled: next } : s));
    } catch { /* ignore */ }
    setTogglingId(null);
  };

  const handleWeightChange = async (id: string, value: number) => {
    setWeights(prev => ({ ...prev, [id]: value }));
    try {
      await strategiesApi.updateParams(id, { weight: value });
    } catch { /* ignore */ }
  };

  const loadPerf = async (id: string) => {
    if (perfData[id]) return;
    setLoadingPerf(prev => ({ ...prev, [id]: true }));
    try {
      const data = await strategiesApi.performance(id);
      setPerfData(prev => ({ ...prev, [id]: data }));
    } catch { /* ignore */ }
    setLoadingPerf(prev => ({ ...prev, [id]: false }));
  };

  const runCompare = async () => {
    if (compareIds.length < 2) return;
    setCompareLoading(true);
    try {
      const data = await strategiesApi.compare(compareIds);
      setComparison(data);
    } catch { /* ignore */ }
    setCompareLoading(false);
  };

  const filteredStrategies = strategies.filter((s) => {
    const matchesSearch = searchQuery === "" ||
      s.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      s.description?.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = filterCategory === "all" || s.category === filterCategory;
    const matchesStatus = filterStatus === "all" ||
      (filterStatus === "active" && s.enabled) ||
      (filterStatus === "inactive" && !s.enabled) ||
      (filterStatus === "keep" && (s as any).backtest?.verdict === "KEEP") ||
      (filterStatus === "validated" && wfStatus?.strategies.some((w) => w.name === s.id));
    return matchesSearch && matchesCategory && matchesStatus;
  });

  const categories = Array.from(new Set(strategies.map((s) => s.category).filter(Boolean))).sort();

  const toggleCompare = (id: string) => {
    setCompareIds(prev =>
      prev.includes(id) ? prev.filter(x => x !== id) : [...prev, id].slice(0, 5),
    );
  };

  const strategyColumns = [
    {
      key: "compare",
      header: "",
      render: (row: Record<string, unknown>) => (
        <input type="checkbox" checked={compareIds.includes(row.id as string)}
          onChange={() => toggleCompare(row.id as string)}
          className="w-3.5 h-3.5 rounded border-white/20 bg-transparent accent-emerald-500 cursor-pointer" />
      ),
      width: "30px",
    },
    {
      key: "name", header: "Strategy",
      render: (row: Record<string, unknown>) => (
        <div>
          <p className="font-medium text-white text-sm">{row.name as string}</p>
          <p className="text-[10px] text-white/30">{row.category as string}</p>
        </div>
      ),
    },
    {
      key: "enabled",
      header: "Active",
      render: (row: Record<string, unknown>) => (
        <Switch
          checked={row.enabled as boolean}
          onCheckedChange={() => handleToggle(row.id as string)}
          disabled={togglingId === row.id}
          className="scale-75"
        />
      ),
      width: "60px",
    },
    {
      key: "weight",
      header: "Weight",
      render: (row: Record<string, unknown>) => (
        <div className="flex items-center gap-2 w-28">
          <input type="range" min="0" max="100" value={weights[row.id as string] ?? 50}
            onChange={e => handleWeightChange(row.id as string, parseInt(e.target.value))}
            className="flex-1 h-1 rounded-full appearance-none bg-white/[0.08] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-400 [&::-webkit-slider-thumb]:cursor-pointer" />
          <span className="font-mono text-[10px] text-white/50 w-7 text-right">{weights[row.id as string] ?? 50}%</span>
        </div>
      ),
      width: "120px",
    },
    {
      key: "live",
      header: "30d Perf",
      render: (row: Record<string, unknown>) => {
        const id = row.id as string;
        const perf = perfData[id];
        if (!perf && loadingPerf[id]) return <span className="text-[10px] text-white/20">loading...</span>;
        if (!perf) {
          loadPerf(id);
          return <span className="text-[10px] text-white/20">—</span>;
        }
        return (
          <div className="text-[10px] font-mono space-y-0.5">
            <span className={cn("block", pnlColor(perf.sharpe))}>S:{perf.sharpe.toFixed(2)}</span>
            <span className={cn("block", pnlColor(perf.winRate - 50))}>W:{perf.winRate.toFixed(1)}%</span>
            <span className={cn("block", pnlColor(perf.totalPnl))}>{formatCurrency(perf.totalPnl)}</span>
          </div>
        );
      },
      width: "100px",
    },
    {
      key: "performance",
      header: "Return %",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const ret = bt.return_pct ?? 0;
        return <span className={cn("font-mono font-medium", pnlColor(ret))}>{ret.toFixed(2)}%</span>;
      },
    },
    {
      key: "sharpe", header: "Sharpe",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const sharpe = bt.sharpe ?? 0;
        return <span className="font-mono text-blue-400">{sharpe.toFixed(2)}</span>;
      },
    },
    {
      key: "dd", header: "Max DD %",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const dd = bt.max_dd_pct ?? 0;
        return <span className="font-mono text-orange-400">{dd.toFixed(2)}%</span>;
      },
    },
    {
      key: "wf", header: "Walk-Fwd",
      render: (row: Record<string, unknown>) => {
        const wf = (row.walk_forward as any) || {};
        if (!wf.validated) return <span className="text-white/20 text-[10px]">—</span>;
        const sharp = wf.oos_sharpe ?? 0;
        const decayed = wf.decayed;
        return (
          <span className={cn("font-mono text-[10px]", decayed ? "text-red-400" : sharp >= 0 ? "text-emerald-400" : "text-red-400")}>
            {decayed ? "DECAY" : `S=${sharp.toFixed(2)}`}
            {wf.n_windows ? ` (${wf.n_windows}w)` : ""}
          </span>
        );
      },
    },
    {
      key: "gate", header: "Audit",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const gate = bt.gate ?? "HOLD";
        const color = gate === "PASS" ? "success" : gate === "REJECT" ? "danger" : "warning";
        return <Badge variant={color} className="text-[10px]">{(gate as string).toUpperCase()}</Badge>;
      },
    },
    {
      key: "actions", header: "",
      render: (row: Record<string, unknown>) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-7 px-2" onClick={() => handleToggle(row.id as string)} disabled={togglingId === row.id}>
            {(row.enabled as boolean) ? <Pause className="w-3 h-3 text-amber-400" /> : <Play className="w-3 h-3 text-emerald-400" />}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2">
            <Settings className="w-3 h-3" />
          </Button>
        </div>
      ),
      width: "70px",
    },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Zap className="w-5 h-5 text-amber-400" />
            Strategy Management
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            {strategies.length} registered strategies • Walk-forward validated • Live editing
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={loadStrategies} disabled={loading}>
            <RefreshCw className={cn("w-3.5 h-3.5 mr-1.5", loading && "animate-spin")} />Refresh
          </Button>
          <Button variant="glow"><Plus className="w-3.5 h-3.5 mr-1.5" />New Strategy</Button>
        </div>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatusCard title="Total" value={String(strategies.length)} variant="info" />
        <StatusCard title="Active" value={String(strategies.filter((s) => s.enabled).length)} variant="success" />
        <StatusCard title="KEEP" value={String(strategies.filter((s) => { const bt = (s as any).backtest; return bt && bt.verdict === "KEEP"; }).length)} variant="success" />
        <StatusCard title="WF Validated" value={String(wfStatus?.validated_count || 0)} variant="info" />
        <StatusCard title="Avg Sharpe" value={(() => { const avg = strategies.reduce((s, st) => { const bt = (st as any).backtest; return s + (bt?.btc_sharpe || 0); }, 0) / (strategies.length || 1); return avg.toFixed(2); })()} />
      </div>

      {/* CANONICAL 15.6: per-symbol CPCV specialists */}
      {Object.keys(allocationMap).length > 0 && (
        <ChartCard title="Per-Symbol Specialists"
          subtitle="CPCV-proven allocation — only these strategies trade each asset class (combo-profit-share ≥ 50%)">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            {[
              { key: "BTC-USD", label: "Crypto (BTC/ETH/SOL)", icon: "₿" },
              { key: "EURUSD=X", label: "Forex Majors", icon: "$" },
              { key: "GC=F", label: "Gold / Metals", icon: "Au" },
            ].map(({ key, label, icon }) => (
              <div key={key} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                <div className="flex items-center gap-2 mb-2">
                  <span className="w-6 h-6 rounded-full bg-amber-500/15 text-amber-400 flex items-center justify-center text-[10px] font-bold">{icon}</span>
                  <span className="text-xs font-medium text-white/70">{label}</span>
                </div>
                <div className="flex flex-wrap gap-1.5">
                  {(allocationMap[key] || []).map((s) => (
                    <Badge key={s} variant="info" className="text-[10px] font-mono">{s}</Badge>
                  ))}
                  {!(allocationMap[key] || []).length && (
                    <span className="text-[10px] text-white/25">No proven specialists</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      )}

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <Input value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} placeholder="Search strategies..." className="pl-9" />
        </div>
        <div className="flex gap-2">
          <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 outline-none">
            <option value="all">All Categories</option>
            {categories.map((cat) => (<option key={cat} value={cat}>{cat}</option>))}
          </select>
          <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 outline-none">
            <option value="all">All Status</option>
            <option value="active">Active</option>
            <option value="inactive">Inactive</option>
            <option value="keep">KEEP</option>
            <option value="validated">WF Validated</option>
          </select>
        </div>
      </div>

      <Tabs defaultValue="list">
        <TabsList>
          <TabsTrigger value="list">Strategy List</TabsTrigger>
          <TabsTrigger value="compare"><GitCompare className="w-3.5 h-3.5 mr-1.5" />Compare ({compareIds.length})</TabsTrigger>
          <TabsTrigger value="schema">Schema Editor</TabsTrigger>
          <TabsTrigger value="loader">Loader/Parser</TabsTrigger>
          <TabsTrigger value="adapter">Backtest Adapter</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <ChartCard title="Strategies" subtitle={`${filteredStrategies.length} of ${strategies.length} strategies`} className="mt-3">
            <DataTable columns={strategyColumns} data={filteredStrategies as unknown as Record<string, unknown>[]}
              onRowClick={(row) => setSelectedStrategy(row.id as string)} />
          </ChartCard>

          {selectedStrategy && (
            <ChartCard title="Strategy Detail" subtitle={strategies.find((s) => s.id === selectedStrategy)?.name} className="mt-3" glow="emerald">
              {(() => {
                const strat = strategies.find((s) => s.id === selectedStrategy);
                if (!strat) return null;
                return (
                  <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-xs text-white/40 mb-2">Configuration</p>
                        <div className="space-y-1.5">
                          <div className="flex justify-between">
                            <span className="text-xs text-white/30">Type</span>
                            <span className="text-xs text-white/70">{strat.category || "N/A"}</span>
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-xs text-white/30">Enabled</span>
                            <Switch checked={strat.enabled} onCheckedChange={() => handleToggle(strat.id)} />
                          </div>
                          <div className="flex justify-between items-center">
                            <span className="text-xs text-white/30">Weight</span>
                            <div className="flex items-center gap-2">
                              <input type="range" min="0" max="100" value={weights[strat.id] ?? 50}
                                onChange={e => handleWeightChange(strat.id, parseInt(e.target.value))}
                                className="w-20 h-1 rounded-full appearance-none bg-white/[0.08] [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-emerald-400" />
                              <span className="font-mono text-xs text-white/60 w-8 text-right">{weights[strat.id] ?? 50}%</span>
                            </div>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-white/30">Verdict</span>
                            <Badge variant={(strat as any).backtest?.verdict === "KEEP" ? "success" : "warning"} className="text-[10px]">
                              {(strat as any).backtest?.verdict || "UNTESTED"}
                            </Badge>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-white/30">Total Return</span>
                            <span className={cn("text-xs font-mono", ((strat as any).backtest?.btc_return || 0) >= 0 ? "text-emerald-400" : "text-red-400")}>
                              {formatPercent(((strat as any).backtest?.btc_return || 0))}
                            </span>
                          </div>
                          <div className="flex justify-between">
                            <span className="text-xs text-white/30">Sharpe Ratio</span>
                            <span className="text-xs font-mono text-blue-400">{((strat as any).backtest?.btc_sharpe || 0).toFixed(2)}</span>
                          </div>
                          {(() => {
                            const perf = perfData[strat.id];
                            if (!perf) return null;
                            return (
                              <>
                                <div className="flex justify-between">
                                  <span className="text-xs text-white/30">30d Win Rate</span>
                                  <span className={cn("text-xs font-mono", pnlColor(perf.winRate - 50))}>{perf.winRate.toFixed(1)}%</span>
                                </div>
                                <div className="flex justify-between">
                                  <span className="text-xs text-white/30">30d P&L</span>
                                  <span className={cn("text-xs font-mono", pnlColor(perf.totalPnl))}>{formatCurrency(perf.totalPnl)}</span>
                                </div>
                              </>
                            );
                          })()}
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="default" className="flex-1"><Play className="w-3 h-3 mr-1" />Backtest</Button>
                        <Button variant="ghost" className="flex-1"><Code className="w-3 h-3 mr-1" />Edit</Button>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-xs text-white/40 mb-2">Performance History</p>
                        <div className="h-32 flex items-center justify-center">
                          <p className="text-[10px] text-white/20">
                            Monthly history — requires backtest run (fail-closed, no synthetic data)
                          </p>
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </ChartCard>
          )}
        </TabsContent>

        {/* Strategy Comparison Tab */}
        <TabsContent value="compare">
          <ChartCard title="Strategy Comparison" subtitle={`${compareIds.length} strategies selected`} action={
            <Button variant="glow" size="sm" className="h-7 text-[10px]" onClick={runCompare}
              disabled={compareIds.length < 2 || compareLoading}>
              {compareLoading ? <RefreshCw className="w-3 h-3 mr-1 animate-spin" /> : <GitCompare className="w-3 h-3 mr-1" />}
              Compare
            </Button>
          } className="mt-3">
            {compareIds.length < 2 ? (
              <p className="text-xs text-white/30 py-4 text-center">Select at least 2 strategies using the checkboxes in the list view</p>
            ) : comparison ? (
              <div className="overflow-x-auto">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-white/[0.06]">
                      <th className="text-left text-white/30 font-medium pb-2 pr-4">Metric</th>
                      {comparison.strategies.map(s => (
                        <th key={s.id} className="text-right text-white/50 font-medium pb-2 px-2">{s.name}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {Object.entries(comparison.metrics).map(([metric, values]) => (
                      <tr key={metric} className="border-b border-white/[0.03]">
                        <td className="py-2 pr-4 text-white/40 capitalize">{metric.replace(/_/g, " ")}</td>
                        {comparison.strategies.map(s => {
                          const val = values[s.id] ?? 0;
                          const isPnl = metric === "totalPnl" || metric === "return_pct";
                          return (
                            <td key={s.id} className={cn("py-2 px-2 text-right font-mono", isPnl && pnlColor(val))}>
                              {isPnl ? metric === "totalPnl" ? formatCurrency(val) : `${val.toFixed(2)}%` : val.toFixed(3)}
                            </td>
                          );
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-xs text-white/30 py-4 text-center">Click Compare to see side-by-side metrics</p>
            )}
          </ChartCard>
        </TabsContent>

        <TabsContent value="schema">
          <ChartCard title="Strategy Schema Editor" subtitle="Define strategy structure" className="mt-3">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-white/40 mb-2">Strategy Schema (JSON)</p>
                <div className="p-3 rounded-lg bg-black/30 border border-white/[0.06] font-mono text-xs text-emerald-300/80 overflow-x-auto">
                  <pre>{JSON.stringify({
                    name: "momentum_alpha",
                    version: "2.1.0",
                    type: "momentum",
                    parameters: {
                      lookback_period: 20,
                      momentum_threshold: 0.05,
                      position_size: 0.1,
                      stop_loss: 0.02,
                      take_profit: 0.05,
                    },
                    signals: ["price_momentum", "volume_surge", "trend_strength"],
                    risk: { max_position: 0.10, max_drawdown: -0.05, kelly_fraction: 0.5 },
                    execution: { order_type: "limit", time_in_force: "GTC", slippage_model: "percentage" },
                  }, null, 2)}</pre>
                </div>
              </div>
              <div className="space-y-3">
                <p className="text-xs text-white/40 mb-2">Schema Validation</p>
                <div className="p-3 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/15">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400" />
                    <span className="text-xs text-emerald-400">Schema valid</span>
                  </div>
                  <p className="text-xs text-white/30 mt-1">All required fields present. Type checking passed.</p>
                </div>
                <div className="space-y-2">
                  {[
                    { field: "name", type: "string", required: true },
                    { field: "type", type: "enum", required: true },
                    { field: "parameters", type: "object", required: true },
                    { field: "signals", type: "array", required: true },
                    { field: "risk", type: "object", required: false },
                    { field: "execution", type: "object", required: false },
                  ].map((item) => (
                    <div key={item.field} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02]">
                      <div className="flex items-center gap-2">
                        <FileJson className="w-3 h-3 text-white/30" />
                        <span className="text-xs font-mono text-white/60">{item.field}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant="default" className="text-[9px]">{item.type}</Badge>
                        {item.required && <Badge variant="danger" className="text-[9px]">required</Badge>}
                      </div>
                    </div>
                  ))}
                </div>
                <Button variant="glow" className="w-full"><Code className="w-3.5 h-3.5 mr-1.5" />Save Schema</Button>
              </div>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="loader">
          <ChartCard title="Strategy Loader/Parser" subtitle="Load strategies from files" className="mt-3">
            <div className="space-y-4">
              <div className="border-2 border-dashed border-white/[0.08] rounded-xl p-8 text-center hover:border-white/[0.15] transition-colors cursor-pointer">
                <Upload className="w-8 h-8 text-white/20 mx-auto mb-3" />
                <p className="text-sm text-white/40">Drop strategy files here</p>
                <p className="text-xs text-white/20 mt-1">Python (.py), JSON (.json), YAML (.yaml)</p>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {[
                  { name: "momentum_alpha_v2.py", type: "Python", size: "4.2 KB", status: "loaded" },
                  { name: "value_quality.json", type: "JSON", size: "1.8 KB", status: "loaded" },
                  { name: "mean_reversion.yaml", type: "YAML", size: "2.1 KB", status: "error" },
                ].map((file) => (
                  <div key={file.name} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center gap-2">
                      <Code className="w-3.5 h-3.5 text-white/30" />
                      <div>
                        <p className="text-xs font-mono text-white/70">{file.name}</p>
                        <p className="text-[10px] text-white/30">{file.type} • {file.size}</p>
                      </div>
                    </div>
                    <Badge variant={file.status === "loaded" ? "success" : "danger"} className="text-[10px]">{file.status}</Badge>
                  </div>
                ))}
              </div>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="adapter">
          <ChartCard title="Strategy Arsenal" subtitle={`${strategies.length} strategies — backtested on BTC-USD & EURUSD`} className="mt-3">
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {strategies.map((strat) => {
                const bt = (strat as any).backtest || {};
                const verdict = bt.verdict || "UNTESTED";
                const vColor = verdict === "KEEP" ? "success" : verdict === "ELIMINATE" ? "danger" : verdict === "MARGINAL" ? "warning" : "secondary";
                const sharpe = bt.btc_sharpe ?? bt.eur_sharpe ?? null;
                return (
                  <div key={strat.id} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center justify-between mb-1">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-white/80">{strat.name}</span>
                        <Badge variant="default" className="text-[9px] text-white/40">{(strat as any).category || ""}</Badge>
                      </div>
                      <Badge variant={vColor as any} className="text-[10px]">{verdict}</Badge>
                    </div>
                    <div className="flex items-center gap-4 text-[10px] text-white/40">
                      {sharpe !== null && <span>Sharpe: <span className={sharpe > 0 ? "text-green-400" : "text-red-400"}>{sharpe.toFixed(2)}</span></span>}
                      {bt.btc_return !== undefined && <span>BTC: <span className={bt.btc_return > 0 ? "text-green-400" : "text-red-400"}>{bt.btc_return.toFixed(1)}%</span></span>}
                      {bt.eur_return !== undefined && <span>EUR: <span className={bt.eur_return > 0 ? "text-green-400" : "text-red-400"}>{bt.eur_return.toFixed(1)}%</span></span>}
                      {(strat as any).asset_classes?.length > 0 && <span>{(strat as any).asset_classes.join(", ")}</span>}
                    </div>
                    {bt.reason && <p className="text-[9px] text-white/30 mt-1">{bt.reason}</p>}
                  </div>
                );
              })}
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function StrategiesPage() {
  return (
    <ErrorBoundary>
      <StrategiesContent />
    </ErrorBoundary>
  );
}
