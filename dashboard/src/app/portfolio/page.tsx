"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { ChartCard } from "@/components/shared/chart-card";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { useAppStore } from "@/lib/store";
import { cn, formatCurrency, formatPercent, formatPrice } from "@/lib/utils";
import { portfolioApi, brokersApi } from "@/lib/api-client";
import type { PortfolioSummary, PerformanceMetrics, EquityCurveResponse, EquityCurvePoint, RiskData, AllocationBucket } from "@/lib/api-client";
import {
  Briefcase, TrendingUp, Calculator, RefreshCw, Activity, Shield,
  PieChart as PieChartIcon, BarChart3, Split, ArrowUpDown,
} from "lucide-react";
import {
  AreaChart, Area, XAxis, YAxis, Tooltip as RechartsTooltip,
  ResponsiveContainer, CartesianGrid, LineChart, Line, PieChart, Pie, Cell,
} from "recharts";

// ── API state ──────────────────────────────────────────────────────

type PositionRow = PortfolioSummary["positions"][number];

function PortfolioDashboardContent() {
  const { realtimePortfolio } = useAppStore();
  const [view, setView] = useState<"value" | "drawdown">("value");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [summary, setSummary] = useState<PortfolioSummary | null>(null);
  const [perf, setPerf] = useState<PerformanceMetrics | null>(null);
  const [equityCurve, setEquityCurve] = useState<EquityCurvePoint[]>([]);
  const [risk, setRisk] = useState<RiskData | null>(null);
  const [brokerCount, setBrokerCount] = useState(0);

  useEffect(() => {
    let cancelled = false;
    async function fetchAll() {
      setLoading(true);
      setError(null);
      try {
        const [summaryRes, perfRes, equityRes, riskRes, brokers] = await Promise.all([
          portfolioApi.getSummary(),
          portfolioApi.getPerformance(),
          portfolioApi.getEquityCurve(),
          portfolioApi.getRisk(),
          brokersApi.list().catch(() => null),
        ]);
        if (cancelled) return;
        setSummary(summaryRes);
        setPerf(perfRes);
        setEquityCurve(equityRes.points);
        setRisk(riskRes);
        setBrokerCount(brokers?.accounts?.length ?? 1);
      } catch (e) {
        if (!cancelled) setError((e as Error).message);
      } finally {
        if (!cancelled) setLoading(false);
      }
    }
    fetchAll();
    return () => { cancelled = true; };
  }, []);

  // Real-time portfolio value (from WebSocket if available, else API)
  const portfolioValue = summary?.totalValue ?? 0;
  const dailyPnl = summary?.dayPnl ?? 0;
  const dailyPnlPct = summary?.dayPnlPercent ?? 0;
  const totalPnl = summary?.totalPnl ?? 0;
  const totalPnlPct = summary?.totalPnlPercent ?? 0;
  const allocations = summary?.allocation ?? [];
  const positions = summary?.positions ?? [];

  const positionColumns = [
    { key: "symbol", label: "Symbol", render: (r: PositionRow) => (
      <div><p className="font-medium text-white">{r.symbol}</p><p className="text-[10px] text-white/30">{r.name}</p></div>
    )},
    { key: "side", label: "Side", render: (r: PositionRow) => (
      <Badge variant={r.side === "long" ? "success" : "danger"} size="sm">{r.side.toUpperCase()}</Badge>
    )},
    { key: "qty", label: "Qty", align: "right" as const, render: (r: PositionRow) => <span className="font-mono">{r.quantity}</span> },
    { key: "avg", label: "Avg Price", align: "right" as const, render: (r: PositionRow) => <span className="font-mono text-white/60">{formatCurrency(r.avgPrice)}</span> },
    { key: "curr", label: "Current", align: "right" as const, render: (r: PositionRow) => <span className="font-mono">{formatCurrency(r.currentPrice)}</span> },
    { key: "pnl", label: "P&L", align: "right" as const, sortable: true, render: (r: PositionRow) => (
      <span className={cn("font-mono font-medium", r.pnl >= 0 ? "text-profit" : "text-loss")}>{formatCurrency(r.pnl)}</span>
    )},
    { key: "pnl%", label: "P&L %", align: "right" as const, render: (r: PositionRow) => (
      <span className={cn("font-mono", r.pnlPercent >= 0 ? "text-profit" : "text-loss")}>{formatPercent(r.pnlPercent)}</span>
    )},
    { key: "weight", label: "Weight", align: "right" as const, render: (r: PositionRow) => (
      <div className="flex items-center gap-2 justify-end">
        <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div className="h-full bg-emerald-500/60 rounded-full" style={{ width: `${r.weight * 4}%` }} />
        </div>
        <span className="font-mono text-white/50 text-[10px] w-8 text-right">{r.weight}%</span>
      </div>
    )},
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <Briefcase className="w-5 h-5 text-emerald-400" />
          Portfolio Management
        </h1>
        <p className="text-sm text-white/40">Cross-broker aggregation • Real-time risk analytics • Multi-asset allocation</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        <StatusCard title="Portfolio Value" value={portfolioValue} change={totalPnlPct} changeLabel="all time" variant="success" format="currency" loading={loading}
          icon={<Briefcase className="w-4 h-4" />} />
        <StatusCard title="Day P&L" value={dailyPnl} change={dailyPnlPct} changeLabel="today" variant={dailyPnl >= 0 ? "success" : "danger"} format="currency" loading={loading}
          icon={<TrendingUp className="w-4 h-4" />} />
        <StatusCard title="Total Positions" value={positions.length} format="number" subtitle={`cross ${brokerCount} brokers`} loading={loading}
          icon={<Activity className="w-4 h-4" />} />
        <StatusCard title="Risk Score" value={risk?.riskScore ?? 0} subtitle={risk ? `${risk.riskScore <= 30 ? "Low" : risk.riskScore <= 60 ? "Moderate" : "High"} · ${risk.riskScore <= 30 ? "Conservative" : risk.riskScore <= 60 ? "Balanced" : "Aggressive"}` : "--"} format="number" variant={risk?.riskScore != null && risk.riskScore <= 30 ? "success" : risk?.riskScore != null && risk.riskScore <= 60 ? "warning" : "danger"} loading={loading}
          icon={<Shield className="w-4 h-4" />} />
      </div>

      <Tabs defaultValue="overview">
        <TabsList>
          <TabsTrigger value="overview">Overview</TabsTrigger>
          <TabsTrigger value="holdings">Holdings</TabsTrigger>
          <TabsTrigger value="sizing">Position Sizing</TabsTrigger>
          <TabsTrigger value="metrics">Metrics</TabsTrigger>
        </TabsList>

        <TabsContent value="overview">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-3">
            {/* Equity Curve */}
            <ChartCard title="Equity Curve" subtitle="Cross-broker aggregated" className="lg:col-span-2" fullscreen>
              <div className="flex items-center gap-1 mb-3">
                <button className={cn("px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors", view === "value" ? "bg-white/[0.08] text-white" : "text-white/30 hover:text-white/50")} onClick={() => setView("value")}>Value</button>
                <button className={cn("px-2.5 py-1 rounded-lg text-[10px] font-medium transition-colors", view === "drawdown" ? "bg-white/[0.08] text-white" : "text-white/30 hover:text-white/50")} onClick={() => setView("drawdown")}>Drawdown</button>
              </div>
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  {view === "value" ? (
                    <AreaChart data={equityCurve}>
                      <defs><linearGradient id="eqGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#10b981" stopOpacity={0.3} /><stop offset="95%" stopColor="#10b981" stopOpacity={0} /></linearGradient></defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={v => `$${(v / 1000).toFixed(0)}K`} />
                      <RechartsTooltip contentStyle={{ background: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                      <Area type="monotone" dataKey="value" stroke="#10b981" fill="url(#eqGrad)" strokeWidth={2} />
                    </AreaChart>
                  ) : (
                    <LineChart data={equityCurve.map((d, i, arr) => {
                      const peak = Math.max(...arr.slice(0, i + 1).map(x => x.value));
                      return { ...d, dd: ((d.value - peak) / peak) * 100 };
                    })}>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={v => `${v.toFixed(1)}%`} domain={["auto", 0]} />
                      <RechartsTooltip contentStyle={{ background: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px" }} formatter={v => `${Number(v).toFixed(2)}%`} />
                      <Line type="monotone" dataKey="dd" stroke="#ef4444" strokeWidth={1.5} dot={false} />
                    </LineChart>
                  )}
                </ResponsiveContainer>
              </div>
            </ChartCard>

            {/* Allocation */}
            <ChartCard title="Asset Allocation" subtitle="Cross-broker breakdown">
              <div className="h-52">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={allocations} cx="50%" cy="50%" innerRadius={50} outerRadius={80} paddingAngle={3} dataKey="value">
                      {allocations.map((e, i) => <Cell key={i} fill={e.color} stroke="transparent" />)}
                    </Pie>
                    <RechartsTooltip contentStyle={{ background: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} formatter={v => `${v}%`} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
              <div className="space-y-1.5 mt-2">
                {allocations.map(item => (
                  <div key={item.name} className="flex items-center justify-between p-1.5">
                    <div className="flex items-center gap-2">
                      <div className="w-2.5 h-2.5 rounded-full" style={{ background: item.color }} />
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
          <ChartCard title="Holdings" subtitle="All positions across brokers" className="mt-3">
            <DataTable columns={positionColumns} data={positions} keyExtractor={p => p.symbol} loading={loading} emptyMessage="No positions" />
          </ChartCard>
        </TabsContent>

        <TabsContent value="sizing">
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-4 mt-3">
            {/* Kelly Criterion */}
            <ChartCard title="Kelly Criterion" subtitle="Optimal position sizing">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-3">
                  {[
                    { label: "Win Rate", value: perf ? `${perf.winRate}%` : "--", color: "text-profit" },
                    { label: "Win/Loss Ratio", value: perf ? perf.profitFactor.toFixed(2) : "--", color: "text-white" },
                    { label: "Kelly %", value: risk ? `${(risk.kellyFraction * 100).toFixed(1)}%` : "--", color: "text-warning" },
                    { label: "Half-Kelly %", value: risk ? `${(risk.kellyFraction * 50).toFixed(1)}%` : "--", color: "text-profit" },
                    { label: "Optimal f", value: risk ? risk.kellyFraction.toFixed(2) : "--", color: "text-info" },
                    { label: "Edge", value: perf ? `${((perf.winRate / 100) * (perf.profitFactor - 1)).toFixed(1)}%` : "--", color: "text-profit" },
                  ].map(m => (
                    <div key={m.label} className="bbg-cell">
                      <p className="text-[9px] text-white/30 mb-0.5">{m.label}</p>
                      <p className={`text-sm font-mono font-bold ${m.color}`}>{m.value}</p>
                    </div>
                  ))}
                </div>
                <div className="p-3 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-[10px] text-white/30 mb-2">Kelly Growth Curve</p>
                  <div className="flex items-end gap-1 h-16">
                    {[0, 0.05, 0.1, 0.15, 0.18, 0.2, 0.25, 0.3].map((f, i) => (
                      <div key={i} className="flex-1 flex flex-col items-center">
                        <div className={cn("w-full rounded-t-sm transition-all", f <= 0.18 ? "bg-profit" : "bg-loss")}
                          style={{ height: `${f * 200}px` }} />
                        <span className="text-[8px] text-white/20 mt-1">{(f * 100).toFixed(0)}%</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </ChartCard>

            {/* Risk Gauges */}
            <ChartCard title="Risk Metrics" subtitle="Portfolio risk assessment">
              <div className="grid grid-cols-3 gap-2">
                <RiskGauge value={risk?.var95 ?? 0} label="Var (95%)" size="sm" />
                <RiskGauge value={risk?.riskScore != null ? risk.riskScore / 100 : 0} label="Risk Score" size="sm" />
                <RiskGauge value={risk?.currentDrawdown != null ? Math.abs(risk.currentDrawdown) / 100 : 0} label="Drawdown" size="sm" />
              </div>
              <div className="mt-4 space-y-2">
                {(risk?.checks ?? [
                  { id: 1, name: "VaR (95%)", value: risk ? `${(risk.var95 * 100).toFixed(1)}%` : "--", limit: "", status: "pass" as const },
                  { id: 2, name: "VaR (99%)", value: risk ? `${(risk.var99 * 100).toFixed(1)}%` : "--", limit: "", status: "pass" as const },
                  { id: 3, name: "CVaR (95%)", value: risk ? `${(risk.cvar95 * 100).toFixed(1)}%` : "--", limit: "", status: "pass" as const },
                  { id: 4, name: "Max Drawdown", value: risk ? `${risk.maxDrawdown.toFixed(1)}%` : "--", limit: "", status: "warning" as const },
                  { id: 5, name: "Current DD", value: risk ? `${risk.currentDrawdown.toFixed(1)}%` : "--", limit: "", status: "pass" as const },
                  { id: 6, name: "Kelly Fraction", value: risk ? `${(risk.kellyFraction * 100).toFixed(1)}%` : "--", limit: "", status: "success" as const },
                ]).map(m => (
                  <div key={(m as any).name || (m as any).label} className="flex items-center justify-between px-2 py-1.5">
                    <span className="text-[11px] text-white/40">{(m as any).name || (m as any).label}</span>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-white/70">{m.value}</span>
                      <Badge variant={m.status === "pass" ? "success" : m.status === "warning" ? "warning" : "danger"} size="sm" className="text-[8px]">{m.status === "pass" ? "OK" : "WARN"}</Badge>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>

            {/* Position Sizing Calculator */}
            <ChartCard title="Position Calculator" subtitle="ATR-based sizing">
              <div className="space-y-3">
                <Select label="Symbol" value="BTC/USDT" onChange={() => {}}
                  options={positions.map(p => ({ value: p.symbol, label: p.symbol }))} />
                  <div className="grid grid-cols-2 gap-2">
                  <div className="bbg-cell"><p className="text-[9px] text-white/30 mb-0.5">Account Risk</p><p className="text-sm font-mono text-white">0.5%</p></div>
                  <div className="bbg-cell"><p className="text-[9px] text-white/30 mb-0.5">ATR (14)</p><p className="text-sm font-mono text-white/40">--</p></div>
                  <div className="bbg-cell"><p className="text-[9px] text-white/30 mb-0.5">Stop Distance</p><p className="text-sm font-mono text-white/40">--</p></div>
                  <div className="bbg-cell"><p className="text-[9px] text-white/30 mb-0.5">Position Size</p><p className="text-sm font-mono text-white/40">--</p></div>
                </div>
                <Button variant="primary" className="w-full" size="sm">
                  <Calculator className="w-3.5 h-3.5 mr-1.5" />
                  Calculate
                </Button>
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="metrics">
          <ChartCard title="Performance Metrics" subtitle="Comprehensive portfolio analytics" className="mt-3">
            <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
              {[
                { label: "Sharpe Ratio", value: perf ? perf.sharpe.toFixed(2) : "--", color: "text-profit" },
                { label: "Sortino Ratio", value: perf ? perf.sortino.toFixed(2) : "--", color: "text-profit" },
                { label: "Calmar Ratio", value: perf ? perf.calmar.toFixed(2) : "--", color: "text-info" },
                { label: "Max Drawdown", value: perf ? `${perf.maxDrawdown}%` : "--", color: "text-loss" },
                { label: "Win Rate", value: perf ? `${perf.winRate}%` : "--", color: "text-profit" },
                { label: "Profit Factor", value: perf ? perf.profitFactor.toFixed(2) : "--", color: "text-profit" },
                { label: "Avg Win", value: perf ? formatCurrency(perf.avgWin) : "--", color: "text-profit" },
                { label: "Avg Loss", value: perf ? formatCurrency(perf.avgLoss) : "--", color: "text-loss" },
                { label: "Total Trades", value: perf ? perf.totalTrades.toString() : "--", color: "text-white/70" },
                { label: "Avg Holding", value: perf ? perf.avgHoldingPeriod : "--", color: "text-white/50" },
              ].map(m => (
                <div key={m.label} className="bbg-cell text-center">
                  <p className="text-[10px] text-white/30 mb-1">{m.label}</p>
                  <p className={`text-lg font-mono font-bold ${m.color}`}>{m.value}</p>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}

export default function PortfolioPage() {
  return (
    <ErrorBoundary>
      <PortfolioDashboardContent />
    </ErrorBoundary>
  );
}
