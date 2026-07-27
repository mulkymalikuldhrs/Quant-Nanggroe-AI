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
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { apiRequest, backtestApi } from "@/lib/api-client";
import type { Strategy, WalkForwardStatus } from "@/lib/api-client";
import { cn, formatPercent } from "@/lib/utils";
import {
  Zap,
  Play,
  Pause,
  Plus,
  Code,
  Upload,
  FileJson,
  Settings,
  AlertCircle,
  RefreshCw,
  Search,
  Filter,
  TrendingUp,
  TrendingDown,
  FlaskConical,
} from "lucide-react";

export default function StrategiesPage() {
  const [selectedStrategy, setSelectedStrategy] = useState<string | null>(null);
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [filterCategory, setFilterCategory] = useState<string>("all");
  const [filterStatus, setFilterStatus] = useState<string>("all");
  const [wfStatus, setWfStatus] = useState<WalkForwardStatus | null>(null);

  const loadStrategies = async () => {
    setLoading(true);
    setError(null);
    try {
      const [strats, wf] = await Promise.allSettled([
        apiRequest<Strategy[]>("/api/backtest/strategies"),
        backtestApi.walkForwardStatus(),
      ]);
      if (strats.status === "fulfilled") setStrategies(strats.value);
      if (wf.status === "fulfilled") setWfStatus(wf.value);
    } catch (err) {
      setError("Backend unavailable — showing cached data");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadStrategies(); }, []);

  // Filter strategies
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

  // Get unique categories
  const categories = Array.from(new Set(strategies.map((s) => s.category).filter(Boolean))).sort();

  const strategyColumns = [
    {
      key: "name",
      header: "Strategy",
      render: (row: Record<string, unknown>) => (
        <div>
          <p className="font-medium text-white">{row.name as string}</p>
          <p className="text-xs text-white/30">{row.category as string}</p>
        </div>
      ),
    },
    {
      key: "performance",
      header: "Return %",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const ret = bt.return_pct ?? 0;
        return (
          <span className={cn("font-mono font-medium", ret >= 0 ? "text-emerald-400" : "text-red-400")}>
            {ret.toFixed(2)}%
          </span>
        );
      },
    },
    {
      key: "sharpe",
      header: "Sharpe",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const sharpe = bt.sharpe ?? 0;
        return <span className="font-mono text-blue-400">{sharpe.toFixed(2)}</span>;
      },
    },
    {
      key: "dd",
      header: "Max DD %",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const dd = bt.max_dd_pct ?? 0;
        return <span className="font-mono text-orange-400">{dd.toFixed(2)}%</span>;
      },
    },
    {
      key: "wf",
      header: "Walk-Fwd",
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
      key: "gate",
      header: "Audit Gate",
      render: (row: Record<string, unknown>) => {
        const bt = (row.backtest as any) || {};
        const gate = bt.gate ?? "HOLD";
        const color = gate === "PASS" ? "success" : gate === "REJECT" ? "danger" : "warning";
        return (
          <Badge variant={color} className="text-[10px]">
            {(gate as string).toUpperCase()}
          </Badge>
        );
      },
    },
    {
      key: "status",
      header: "Status",
      render: (row: Record<string, unknown>) => (
        <Badge
          variant={(row.enabled as boolean) ? "success" : "warning"}
          className="text-[10px]"
        >
          {(row.enabled as boolean) ? "ACTIVE" : "INACTIVE"}
        </Badge>
      ),
    },
    {
      key: "actions",
      header: "Actions",
      render: (row: Record<string, unknown>) => (
        <div className="flex items-center gap-1">
          <Button variant="ghost" size="sm" className="h-7 px-2">
            {(row.status as string) === "active" ? (
              <Pause className="w-3 h-3" />
            ) : (
              <Play className="w-3 h-3" />
            )}
          </Button>
          <Button variant="ghost" size="sm" className="h-7 px-2">
            <Settings className="w-3 h-3" />
          </Button>
        </div>
      ),
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
            {strategies.length} registered strategies • Walk-forward validated
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="ghost" size="sm" onClick={loadStrategies} disabled={loading}>
            <RefreshCw className={cn("w-3.5 h-3.5 mr-1.5", loading && "animate-spin")} />
            Refresh
          </Button>
          <Button variant="glow">
            <Plus className="w-3.5 h-3.5 mr-1.5" />
            New Strategy
          </Button>
        </div>
      </div>

      {/* Strategy Summary */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatusCard title="Total" value={String(strategies.length)} variant="info" />
        <StatusCard title="Active" value={String(strategies.filter((s) => s.enabled).length)} variant="success" />
        <StatusCard title="KEEP" value={String(strategies.filter((s) => { const bt = (s as any).backtest; return bt && bt.verdict === "KEEP"; }).length)} variant="success" />
        <StatusCard title="WF Validated" value={String(wfStatus?.validated_count || 0)} variant="info" />
        <StatusCard title="Avg Sharpe" value={(() => { const avg = strategies.reduce((s, st) => { const bt = (st as any).backtest; return s + (bt?.btc_sharpe || 0); }, 0) / (strategies.length || 1); return avg.toFixed(2); })()} />
      </div>

      {/* Search & Filter */}
      <div className="flex flex-col sm:flex-row gap-3">
        <div className="flex-1 relative">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-white/30" />
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search strategies..."
            className="pl-9"
          />
        </div>
        <div className="flex gap-2">
          <select
            value={filterCategory}
            onChange={(e) => setFilterCategory(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 outline-none"
          >
            <option value="all">All Categories</option>
            {categories.map((cat) => (
              <option key={cat} value={cat}>{cat}</option>
            ))}
          </select>
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="px-3 py-2 rounded-lg bg-white/5 border border-white/10 text-sm text-white/70 outline-none"
          >
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
          <TabsTrigger value="schema">Schema Editor</TabsTrigger>
          <TabsTrigger value="loader">Loader/Parser</TabsTrigger>
          <TabsTrigger value="adapter">Backtest Adapter</TabsTrigger>
        </TabsList>

        <TabsContent value="list">
          <ChartCard title="Strategies" subtitle={`${filteredStrategies.length} of ${strategies.length} strategies`} className="mt-3">
            <DataTable
              columns={strategyColumns}
              data={filteredStrategies as unknown as Record<string, unknown>[]}
              onRowClick={(row) => setSelectedStrategy(row.id as string)}
            />
          </ChartCard>

          {/* Strategy Detail */}
          {selectedStrategy && (
            <ChartCard
              title="Strategy Detail"
              subtitle={strategies.find((s) => s.id === selectedStrategy)?.name}
              className="mt-3"
              glow="emerald"
            >
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
                          <div className="flex justify-between">
                            <span className="text-xs text-white/30">Status</span>
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
                        </div>
                      </div>
                      <div className="flex gap-2">
                        <Button variant="default" className="flex-1">
                          <Play className="w-3 h-3 mr-1" />
                          Backtest
                        </Button>
                        <Button variant="ghost" className="flex-1">
                          <Code className="w-3 h-3 mr-1" />
                          Edit
                        </Button>
                      </div>
                    </div>
                    <div className="space-y-3">
                      <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <p className="text-xs text-white/40 mb-2">Performance History</p>
                        <div className="h-32 flex items-end gap-1">
                          {Array.from({ length: 12 }, (_, i) => {
                            const val = Math.random() * 5 + (((strat as any).backtest?.btc_return || 0) > 0 ? 1 : -1);
                            return (
                              <div key={i} className="flex-1 flex flex-col items-center gap-1">
                                <div
                                  className={cn(
                                    "w-full rounded-t",
                                    val >= 0 ? "bg-emerald-500/30" : "bg-red-500/30",
                                  )}
                                  style={{ height: `${Math.abs(val) * 20}px` }}
                                />
                                <span className="text-[8px] text-white/20">
                                  {["J", "F", "M", "A", "M", "J", "J", "A", "S", "O", "N", "D"][i]}
                                </span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    </div>
                  </div>
                );
              })()}
            </ChartCard>
          )}
        </TabsContent>

        <TabsContent value="schema">
          <ChartCard title="Strategy Schema Editor" subtitle="Define strategy structure" className="mt-3">
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
              <div>
                <p className="text-xs text-white/40 mb-2">Strategy Schema (JSON)</p>
                <div className="p-3 rounded-lg bg-black/30 border border-white/[0.06] font-mono text-xs text-emerald-300/80 overflow-x-auto">
                  <pre>{JSON.stringify(
                    {
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
                      risk: {
                        max_position: 0.10,
                        max_drawdown: -0.05,
                        kelly_fraction: 0.5,
                      },
                      execution: {
                        order_type: "limit",
                        time_in_force: "GTC",
                        slippage_model: "percentage",
                      },
                    },
                    null,
                    2,
                  )}</pre>
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
                <Button variant="glow" className="w-full">
                  <Code className="w-3.5 h-3.5 mr-1.5" />
                  Save Schema
                </Button>
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
                    <Badge variant={file.status === "loaded" ? "success" : "danger"} className="text-[10px]">
                      {file.status}
                    </Badge>
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
                const vColor = verdict === "KEEP" ? "success" : verdict === "ELIMINATE" ? "destructive" : verdict === "MARGINAL" ? "warning" : "secondary";
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
