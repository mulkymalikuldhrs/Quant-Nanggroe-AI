"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { apiRequest } from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import { cn, formatCurrency, formatPercent, formatTimestamp, pnlColor } from "@/lib/utils";
import {
  GitBranch,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Clock,
  Settings,
  Save,
  Check,
} from "lucide-react";

// ── Types ──────────────────────────────────────────────────────────────

interface EvolutionStats {
  total_trades: number;
  active_strategies: number;
  disabled_count: number;
  last_run: string | null;
  total_pnl: number;
}

interface StrategySnapshot {
  id: number;
  run_id: number;
  strategy_name: string;
  timeframe: string | null;
  sharpe: number | null;
  sortino: number | null;
  win_rate: number | null;
  profit_factor: number | null;
  max_drawdown: number | null;
  avg_return: number | null;
  trade_count: number;
  action: string | null;
  action_reason: string | null;
  run_timestamp: string | null;
  run_trigger: string | null;
}

interface ClosedTrade {
  id: number;
  timestamp: string;
  symbol: string;
  strategy: string;
  timeframe: string | null;
  direction: string;
  entry_price: number | null;
  exit_price: number | null;
  pnl: number | null;
  pnl_pct: number | null;
  hold_hours: number | null;
}

interface ConfigData {
  drawdown_trigger?: number;
  interval_trades?: number;
  consecutive_loss?: number;
  consecutive_loss_trigger?: number;
  threshold_trades?: number;
  schedule_days?: number;
  min_sharpe?: number;
  min_win_rate?: number;
  max_drawdown_allowed?: number;
  evolve_on_schedule?: boolean;
  evolve_on_drawdown?: boolean;
  evolve_on_loss_streak?: boolean;
  auto_disable?: boolean;
  update_weights?: boolean;
  [key: string]: unknown;
}

// ── Helpers ────────────────────────────────────────────────────────────

const actionBadge = (action: string | null) => {
  switch (action) {
    case "keep":
      return <Badge variant="info" className="bg-emerald-500/15 text-emerald-400 border-emerald-500/20">Keep</Badge>;
    case "disable":
      return <Badge variant="info" className="bg-red-500/15 text-red-400 border-red-500/20">Disable</Badge>;
    case "evolve":
      return <Badge variant="info" className="bg-amber-500/15 text-amber-400 border-amber-500/20">Evolve</Badge>;
    default:
      return <Badge variant="default" className="text-white/30">—</Badge>;
  }
};

const pnlCell = (pnl: number | null) => {
  if (pnl === null) return <span className="text-white/30">—</span>;
  const color = pnl >= 0 ? "text-emerald-400" : "text-red-400";
  const icon = pnl >= 0 ? <TrendingUp className="w-3 h-3 inline mr-1" /> : <TrendingDown className="w-3 h-3 inline mr-1" />;
  return <span className={color}>{icon}{formatCurrency(pnl)}</span>;
};

// ── Page Component ─────────────────────────────────────────────────────

export default function EvolutionPage() {
  const [stats, setStats] = useState<EvolutionStats | null>(null);
  const [strategies, setStrategies] = useState<StrategySnapshot[]>([]);
  const [trades, setTrades] = useState<ClosedTrade[]>([]);
  const [config, setConfig] = useState<ConfigData>({});
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  const loadAll = async () => {
    setLoading(true);
    setError(null);
    try {
      const [statusRes, stratRes, tradesRes, configRes] = await Promise.all([
        apiRequest<{ success: boolean; data: EvolutionStats }>("/api/evolution/status"),
        apiRequest<{ success: boolean; data: StrategySnapshot[] }>("/api/evolution/strategies?limit=50"),
        apiRequest<{ success: boolean; data: ClosedTrade[] }>("/api/evolution/trades?limit=20"),
        apiRequest<{ success: boolean; data: ConfigData }>("/api/evolution/config"),
      ]);
      setStats(statusRes.data);
      setStrategies(stratRes.data);
      setTrades(tradesRes.data);
      setConfig(configRes.data);
    } catch {
      setError("Evolution API unavailable — backend /api/evolution/* unreachable");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadAll(); }, []);

  const updateConfig = async (key: string, value: string) => {
    setSaving(true);
    setSaved(false);
    try {
      await apiRequest<{ success: boolean }>(`/api/evolution/config?key=${encodeURIComponent(key)}&value=${encodeURIComponent(value)}`, {
        method: "POST",
      });
      setConfig((prev) => ({ ...prev, [key]: value }));
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch {
      // silent
    } finally {
      setSaving(false);
    }
  };

  if (loading && !stats) {
    return (
      <div className="space-y-4 animate-slide-up">
        <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center min-h-[60vh] gap-4">
        <div className="p-4 rounded-full bg-red-500/10">
          <Activity className="w-8 h-8 text-red-400" />
        </div>
        <p className="text-sm text-red-400/80">{error}</p>
        <Button onClick={loadAll} variant="outline" size="sm">
          <RefreshCw className="w-4 h-4 mr-2" /> Retry
        </Button>
      </div>
    );
  }

  const strategyColumns = [
    {
      key: "strategy_name",
      header: "Strategy",
      render: (row: StrategySnapshot) => (
        <span className="font-medium text-white/90">{row.strategy_name}</span>
      ),
    },
    {
      key: "timeframe",
      header: "TF",
      width: "80px",
      render: (row: StrategySnapshot) => (
        <span className="text-white/50 text-xs">{row.timeframe || "—"}</span>
      ),
    },
    {
      key: "sharpe",
      header: "Sharpe",
      width: "100px",
      render: (row: StrategySnapshot) => (
        <span className={cn("font-mono text-sm", (row.sharpe ?? 0) >= 0.5 ? "text-emerald-400" : "text-red-400")}>
          {row.sharpe?.toFixed(2) ?? "—"}
        </span>
      ),
    },
    {
      key: "win_rate",
      header: "Win Rate",
      width: "100px",
      render: (row: StrategySnapshot) => (
        <span className="font-mono text-sm">{row.win_rate != null ? formatPercent(row.win_rate) : "—"}</span>
      ),
    },
    {
      key: "profit_factor",
      header: "Profit Factor",
      width: "110px",
      render: (row: StrategySnapshot) => (
        <span className="font-mono text-sm">{row.profit_factor?.toFixed(2) ?? "—"}</span>
      ),
    },
    {
      key: "trade_count",
      header: "Trades",
      width: "80px",
      render: (row: StrategySnapshot) => (
        <span className="font-mono text-sm text-white/60">{row.trade_count}</span>
      ),
    },
    {
      key: "action",
      header: "Action",
      width: "100px",
      render: (row: StrategySnapshot) => actionBadge(row.action),
    },
  ];

  const tradeColumns = [
    {
      key: "timestamp",
      header: "Time",
      width: "160px",
      render: (row: ClosedTrade) => (
        <span className="text-xs text-white/60">{formatTimestamp(row.timestamp)}</span>
      ),
    },
    {
      key: "symbol",
      header: "Symbol",
      width: "100px",
      render: (row: ClosedTrade) => (
        <span className="font-medium text-white/80">{row.symbol}</span>
      ),
    },
    {
      key: "strategy",
      header: "Strategy",
      width: "120px",
      render: (row: ClosedTrade) => (
        <span className="text-xs text-white/50">{row.strategy}</span>
      ),
    },
    {
      key: "direction",
      header: "Dir",
      width: "60px",
      render: (row: ClosedTrade) => (
        <Badge variant="default" className={cn(
          "text-[10px] font-mono",
          row.direction.toLowerCase() === "buy" ? "text-emerald-400 border-emerald-500/20" : "text-red-400 border-red-500/20",
        )}>
          {row.direction.toUpperCase()}
        </Badge>
      ),
    },
    {
      key: "pnl",
      header: "PnL",
      width: "120px",
      render: (row: ClosedTrade) => pnlCell(row.pnl),
    },
    {
      key: "hold_hours",
      header: "Hold (h)",
      width: "90px",
      render: (row: ClosedTrade) => (
        <span className="font-mono text-xs text-white/50">{row.hold_hours?.toFixed(1) ?? "—"}</span>
      ),
    },
  ];

  return (
    <div className="space-y-6 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2.5 rounded-xl bg-gradient-to-br from-amber-500/20 to-orange-600/10 border border-amber-500/15">
            <GitBranch className="w-5 h-5 text-amber-400" />
          </div>
          <div>
            <h1 className="text-lg font-bold text-white">Evolution</h1>
            <p className="text-xs text-white/30">Strategy evolution loop — mutation, selection, scoring</p>
          </div>
        </div>
        <Button onClick={loadAll} variant="outline" size="sm" disabled={loading}>
          <RefreshCw className={cn("w-4 h-4 mr-2", loading && "animate-spin")} />
          Refresh
        </Button>
      </div>

      {/* Summary Cards */}
      {stats && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
          <StatusCard
            title="Total Trades"
            value={stats.total_trades}
            format="number"
            icon={<BarChart3 className="w-4 h-4" />}
          />
          <StatusCard
            title="Active Strategies"
            value={stats.active_strategies}
            format="number"
            variant="success"
            icon={<Activity className="w-4 h-4" />}
          />
          <StatusCard
            title="Disabled"
            value={stats.disabled_count}
            format="number"
            variant={stats.disabled_count > 0 ? "warning" : "default"}
            icon={<TrendingDown className="w-4 h-4" />}
          />
          <StatusCard
            title="Total P&L"
            value={stats.total_pnl}
            format="currency"
            variant={stats.total_pnl >= 0 ? "success" : "danger"}
            trend={stats.total_pnl >= 0 ? "up" : "down"}
            icon={<TrendingUp className="w-4 h-4" />}
          />
          <StatusCard
            title="Last Evolution"
            value={stats.last_run ? formatTimestamp(stats.last_run) : "Never"}
            format="text"
            icon={<Clock className="w-4 h-4" />}
            subtitle={stats.last_run ? "Run timestamp" : "No runs recorded"}
          />
        </div>
      )}

      {/* Main Content */}
      <Tabs defaultValue="strategies" className="space-y-4">
        <TabsList>
          <TabsTrigger value="strategies">Strategies</TabsTrigger>
          <TabsTrigger value="trades">Closed Trades</TabsTrigger>
          <TabsTrigger value="config">Configuration</TabsTrigger>
        </TabsList>

        {/* Strategies Tab */}
        <TabsContent value="strategies" className="space-y-4">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm text-white/70">Strategy Snapshots</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <DataTable
                columns={strategyColumns}
                data={strategies}
                keyExtractor={(r) => String(r.id)}
                emptyMessage="No strategy snapshots recorded yet"
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Trades Tab */}
        <TabsContent value="trades" className="space-y-4">
          <Card>
            <CardHeader className="py-3 px-4">
              <CardTitle className="text-sm text-white/70">Recent Closed Trades</CardTitle>
            </CardHeader>
            <CardContent className="p-0">
              <DataTable
                columns={tradeColumns}
                data={trades}
                keyExtractor={(r) => String(r.id)}
                emptyMessage="No closed trades recorded yet"
              />
            </CardContent>
          </Card>
        </TabsContent>

        {/* Config Tab */}
        <TabsContent value="config" className="space-y-4">
          <Card>
            <CardHeader className="py-3 px-4 flex flex-row items-center justify-between">
              <div className="flex items-center gap-2">
                <Settings className="w-4 h-4 text-white/40" />
                <CardTitle className="text-sm text-white/70">Evolution Configuration</CardTitle>
              </div>
              {saved && (
                <span className="text-xs text-emerald-400 flex items-center gap-1">
                  <Check className="w-3 h-3" /> Saved
                </span>
              )}
            </CardHeader>
            <CardContent className="p-4 space-y-4">
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
                <ConfigField
                  label="Drawdown Trigger (%)"
                  value={String(config.drawdown_trigger ?? config.max_drawdown_allowed ?? "")}
                  placeholder="5.0"
                  onSave={(v) => updateConfig("drawdown_trigger", v)}
                  saving={saving}
                />
                <ConfigField
                  label="Interval Trades"
                  value={String(config.interval_trades ?? config.threshold_trades ?? "")}
                  placeholder="20"
                  onSave={(v) => updateConfig("threshold_trades", v)}
                  saving={saving}
                />
                <ConfigField
                  label="Consecutive Loss Trigger"
                  value={String(config.consecutive_loss_trigger ?? config.consecutive_loss ?? "")}
                  placeholder="3"
                  onSave={(v) => updateConfig("consecutive_loss", v)}
                  saving={saving}
                />
                <ConfigField
                  label="Min Sharpe"
                  value={String(config.min_sharpe ?? "")}
                  placeholder="0.5"
                  onSave={(v) => updateConfig("min_sharpe", v)}
                  saving={saving}
                />
                <ConfigField
                  label="Min Win Rate"
                  value={String(config.min_win_rate ?? "")}
                  placeholder="0.40"
                  onSave={(v) => updateConfig("min_win_rate", v)}
                  saving={saving}
                />
                <ConfigField
                  label="Max Drawdown Allowed (%)"
                  value={String(config.max_drawdown_allowed ?? "")}
                  placeholder="15.0"
                  onSave={(v) => updateConfig("max_drawdown_allowed", v)}
                  saving={saving}
                />
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  );
}

// ── Config Field Sub-component ────────────────────────────────────────

function ConfigField({
  label,
  value,
  placeholder,
  onSave,
  saving,
}: {
  label: string;
  value: string;
  placeholder: string;
  onSave: (value: string) => void;
  saving: boolean;
}) {
  const [val, setVal] = useState(value);

  useEffect(() => { setVal(value); }, [value]);

  return (
    <div className="space-y-1.5">
      <label className="text-[11px] text-white/40 uppercase tracking-wider">{label}</label>
      <div className="flex gap-2">
        <Input
          value={val}
          onChange={(e) => setVal(e.target.value)}
          placeholder={placeholder}
          className="h-8 text-sm font-mono"
        />
        <Button
          onClick={() => onSave(val)}
          disabled={saving || val === value}
          size="sm"
          variant="outline"
          className="h-8 px-3"
        >
          {saving ? <RefreshCw className="w-3 h-3 animate-spin" /> : <Save className="w-3 h-3" />}
        </Button>
      </div>
    </div>
  );
}