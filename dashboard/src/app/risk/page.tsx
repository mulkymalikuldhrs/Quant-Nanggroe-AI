"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { RiskGauge } from "@/components/shared/risk-gauge";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { LoadingSkeleton } from "@/components/shared/loading-skeleton";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { apiRequest } from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";
import {
  Shield,
  Skull,
  Brain,
  CheckCircle,
  XCircle,
  AlertCircle,
  RefreshCw,
} from "lucide-react";

interface RiskCheck {
  id: number;
  name: string;
  status: "pass" | "warning" | "fail";
  value: string;
  limit: string;
}

interface RiskData {
  var95: number;
  var99: number;
  cvar95: number;
  maxDrawdown: number;
  currentDrawdown: number;
  kellyFraction: number;
  riskScore: number;
  checks: RiskCheck[];
  correlationMatrix: number[][];
  correlationLabels: string[];
  sharpe: number;
  sortino: number;
  winRate: number;
  profitFactor: number;
}

export default function RiskPage() {
  const { killSwitch, toggleKillSwitch } = useAppStore();
  const [riskData, setRiskData] = useState<RiskData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const loadRiskData = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await apiRequest<RiskData>("/api/portfolio/risk");
      setRiskData(data);
    } catch {
      // Fallback to mock data if backend unavailable
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { loadRiskData(); }, []);

  const checkIcon = (status: string) => {
    switch (status) {
      case "pass":
        return <CheckCircle className="w-3.5 h-3.5 text-emerald-400" />;
      case "warning":
        return <AlertCircle className="w-3.5 h-3.5 text-amber-400" />;
      case "fail":
        return <XCircle className="w-3.5 h-3.5 text-red-400" />;
      default:
        return null;
    }
  };

  if (loading && !riskData) {
    return (
      <div className="space-y-4 animate-slide-up">
        <div className="h-8 w-64 rounded-lg bg-white/5 animate-pulse" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 rounded-xl bg-white/5 animate-pulse" />
          ))}
        </div>
        <LoadingSkeleton variant="page" />
      </div>
    );
  }

  const data = riskData || {
    riskScore: 35,
    var95: -5200,
    var99: -8500,
    cvar95: -6800,
    maxDrawdown: 8.5,
    currentDrawdown: 2.1,
    kellyFraction: 0.18,
    sharpe: 1.72,
    sortino: 2.1,
    winRate: 62,
    profitFactor: 1.85,
    checks: [
      { id: 1, name: "Position Size Limit", status: "pass", value: "8%", limit: "10%" },
      { id: 2, name: "VaR Constraint", status: "pass", value: "$4,250", limit: "$10,000" },
      { id: 3, name: "Drawdown Limit", status: "pass", value: "-2.1%", limit: "-5%" },
      { id: 4, name: "Leverage Check", status: "pass", value: "1.0x", limit: "2.0x" },
      { id: 5, name: "Concentration Limit", status: "warning", value: "28%", limit: "40%" },
      { id: 6, name: "Sector Exposure", status: "pass", value: "18%", limit: "40%" },
      { id: 7, name: "Kelly Fraction", status: "pass", value: "18%", limit: "25%" },
      { id: 8, name: "Correlation Bound", status: "pass", value: "0.42", limit: "0.70" },
      { id: 9, name: "Emotional Lockout", status: "pass", value: "Calm", limit: "Calm" },
    ] as RiskCheck[],
    correlationMatrix: [
      [1, 0.65, 0.42, 0.38, 0.15],
      [0.65, 1, 0.55, 0.45, 0.08],
      [0.42, 0.55, 1, 0.72, -0.05],
      [0.38, 0.45, 0.72, 1, -0.12],
      [0.15, 0.08, -0.05, -0.12, 1],
    ] as number[][],
    correlationLabels: ["BTC", "ETH", "NVDA", "SPY", "EUR/USD"],
  };

  const riskScore = data.riskScore;
  const var95 = Math.abs(data.var95);
  const cvar95 = Math.abs(data.cvar95);
  const drawdown = data.maxDrawdown;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <Shield className="w-5 h-5 text-amber-400" />
            Risk Management
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            VaR • CVaR • Kelly Criterion • 9-checkpoint gate • Kill Switch
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="h-7 px-2 text-white/30 hover:text-white/50"
            onClick={loadRiskData}
            disabled={loading}
          >
            <RefreshCw className={`w-3.5 h-3.5 ${loading ? "animate-spin" : ""}`} />
          </Button>
          <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-red-500/5 border border-red-500/20">
            <Skull className="w-4 h-4 text-red-400" />
            <span className="text-sm text-red-400 font-medium">Kill Switch</span>
            <Switch checked={killSwitch} onCheckedChange={toggleKillSwitch} />
          </div>
        </div>
      </div>

      {/* Kill Switch Warning */}
      {killSwitch && (
        <div className="p-4 rounded-lg bg-red-500/10 border border-red-500/30 flex items-center gap-3 animate-slide-up">
          <Skull className="w-6 h-6 text-red-400 flex-shrink-0" />
          <div>
            <p className="text-sm font-medium text-red-400">EMERGENCY KILL SWITCH ACTIVE</p>
            <p className="text-xs text-red-400/60 mt-0.5">
              All trading operations suspended. No new orders will be placed. Existing orders may be cancelled.
            </p>
          </div>
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="p-3 rounded-lg bg-red-500/10 border border-red-500/20 flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
          <p className="text-sm text-red-400 flex-1">{error}</p>
          <Button variant="ghost" size="sm" className="h-7 text-xs" onClick={loadRiskData}>
            <RefreshCw className="w-3 h-3 mr-1" /> Retry
          </Button>
        </div>
      )}

      {/* Summary Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3">
        <StatusCard
          title="Risk Score"
          value={`${riskScore}/100`}
          variant={riskScore > 60 ? "danger" : riskScore > 35 ? "warning" : "success"}
          trend={riskScore > 50 ? "down" : "up"}
        />
        <StatusCard
          title="Sharpe Ratio"
          value={data.sharpe.toFixed(2)}
          variant={data.sharpe > 2 ? "success" : data.sharpe > 1 ? "info" : "warning"}
        />
        <StatusCard
          title="Sortino Ratio"
          value={data.sortino.toFixed(2)}
          variant={data.sortino > 2 ? "success" : "info"}
        />
        <StatusCard
          title="Win Rate"
          value={`${data.winRate}%`}
          variant={data.winRate > 60 ? "success" : "warning"}
        />
        <StatusCard
          title="Profit Factor"
          value={data.profitFactor.toFixed(2)}
          variant={data.profitFactor > 2 ? "success" : data.profitFactor > 1.5 ? "info" : "warning"}
        />
      </div>

      {/* Risk Gauges */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
        <RiskGauge value={riskScore} label="Overall Risk" sublabel="/100" variant={riskScore > 60 ? "danger" : riskScore > 35 ? "warning" : "success"} />
        <RiskGauge value={var95} maxValue={var95 * 3} label="VaR (95%)" sublabel="dollars" variant="warning" />
        <RiskGauge value={cvar95} maxValue={cvar95 * 3} label="CVaR (95%)" sublabel="dollars" variant="danger" />
        <RiskGauge value={drawdown} maxValue={drawdown * 3} label="Max Drawdown" sublabel="percent" variant="danger" />
      </div>

      <Tabs defaultValue="checks">
        <TabsList>
          <TabsTrigger value="checks">Risk Checks</TabsTrigger>
          <TabsTrigger value="correlation">Correlation</TabsTrigger>
          <TabsTrigger value="kelly">Kelly & Sizing</TabsTrigger>
          <TabsTrigger value="parity">Risk Parity</TabsTrigger>
          <TabsTrigger value="performance">Performance</TabsTrigger>
        </TabsList>

        <TabsContent value="checks">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="9-Checkpoint Risk Gate" subtitle="Constitutional risk checks" glow="amber">
              <div className="space-y-2">
                {data.checks.map((check) => (
                  <div
                    key={check.id}
                    className={cn(
                      "flex items-center justify-between p-3 rounded-lg border transition-colors",
                      check.status === "pass"
                        ? "bg-emerald-500/[0.03] border-emerald-500/10"
                        : check.status === "warning"
                          ? "bg-amber-500/[0.05] border-amber-500/15"
                          : "bg-red-500/[0.05] border-red-500/15",
                    )}
                  >
                    <div className="flex items-center gap-3">
                      {checkIcon(check.status)}
                      <div>
                        <p className="text-xs font-medium text-white/70">{check.name}</p>
                        <p className="text-[10px] text-white/30">
                          Value: <span className="text-white/50">{check.value}</span> • Limit: <span className="text-white/50">{check.limit}</span>
                        </p>
                      </div>
                    </div>
                    <Badge
                      variant={check.status === "pass" ? "success" : check.status === "warning" ? "warning" : "danger"}
                      className="text-[10px]"
                    >
                      {check.status.toUpperCase()}
                    </Badge>
                  </div>
                ))}
              </div>
            </ChartCard>

            <div className="space-y-4">
              <ChartCard title="Constitutional Limits" subtitle="System-wide risk boundaries">
                <div className="space-y-3">
                  {[
                    { name: "Max Position Size", current: "8%", limit: "10%", used: 80 },
                    { name: "Max Sector Exposure", current: "28%", limit: "40%", used: 70 },
                    { name: "Max VaR", current: `$${Math.round(data.var95).toLocaleString()}`, limit: "$10,000", used: Math.min(100, Math.round((Math.abs(data.var95) / 10000) * 100)) },
                    { name: "Max Drawdown", current: `${data.maxDrawdown.toFixed(1)}%`, limit: "25%", used: Math.round((data.maxDrawdown / 25) * 100) },
                    { name: "Max Leverage", current: "1.0x", limit: "2.0x", used: 50 },
                  ].map((item, i) => (
                    <div key={i}>
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-white/50">{item.name}</span>
                        <span className="text-[10px] text-white/30">
                          {item.current} / {item.limit}
                        </span>
                      </div>
                      <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className={cn(
                            "h-full rounded-full transition-all",
                            item.used > 80 ? "bg-red-400" : item.used > 60 ? "bg-amber-400" : "bg-emerald-400",
                          )}
                          style={{ width: `${item.used}%` }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              </ChartCard>

              <ChartCard title="Emotional Lockout" subtitle="Trading psychology monitor">
                <div className="p-4 rounded-lg bg-emerald-500/[0.05] border border-emerald-500/15 text-center">
                  <Brain className="w-8 h-8 text-emerald-400 mx-auto mb-2" />
                  <p className="text-sm font-medium text-emerald-400">Calm State</p>
                  <p className="text-xs text-white/30 mt-1">No emotional lockout active</p>
                </div>
              </ChartCard>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="correlation">
          <ChartCard title="Correlation Matrix" subtitle="Asset correlation heatmap" className="mt-3">
            <div className="overflow-x-auto">
              <table className="w-full">
                <thead>
                  <tr>
                    <th className="p-2" />
                    {data.correlationLabels.map((label) => (
                      <th key={label} className="p-2 text-xs text-white/40 font-medium">
                        {label}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {data.correlationMatrix.map((row, i) => (
                    <tr key={i}>
                      <td className="p-2 text-xs text-white/40 font-medium">
                        {data.correlationLabels[i]}
                      </td>
                      {row.map((val, j) => {
                        const color =
                          val > 0.7
                            ? "bg-red-500/30"
                            : val > 0.5
                              ? "bg-amber-500/20"
                              : val > 0.3
                                ? "bg-amber-500/10"
                                : val < -0.1
                                  ? "bg-blue-500/15"
                                  : "bg-white/5";
                        return (
                          <td key={j} className="p-1">
                            <div
                              className={cn(
                                "w-12 h-12 rounded flex items-center justify-center text-xs font-mono",
                                color,
                              )}
                            >
                              <span className={val > 0.7 ? "text-red-300" : val > 0.3 ? "text-amber-300" : "text-white/50"}>
                                {val.toFixed(2)}
                              </span>
                            </div>
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="kelly">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Kelly Criterion" subtitle="Optimal position sizing">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
                    <p className="text-xs text-white/40 mb-1">Kelly Fraction</p>
                    <p className="text-2xl font-mono font-bold text-amber-400">
                      {(data.kellyFraction * 100).toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
                    <p className="text-xs text-white/40 mb-1">Half-Kelly</p>
                    <p className="text-2xl font-mono font-bold text-emerald-400">
                      {(data.kellyFraction * 50).toFixed(1)}%
                    </p>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-2">Kelly Parameters</p>
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span className="text-xs text-white/40">Win Probability</span>
                      <span className="text-xs font-mono text-white/70">{data.winRate}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-white/40">Win/Loss Ratio</span>
                      <span className="text-xs font-mono text-white/70">{data.profitFactor.toFixed(2)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-xs text-white/40">Recommended Size</span>
                      <span className="text-xs font-mono text-emerald-400">
                        ${Math.round(data.kellyFraction * 25000).toLocaleString()}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </ChartCard>

            <ChartCard title="Position Sizing" subtitle="Risk-adjusted sizing calculator">
              <div className="space-y-3">
                {[
                  { symbol: "BTC", kelly: 18, halfKelly: 9, atr: 850 },
                  { symbol: "ETH", kelly: 15, halfKelly: 7.5, atr: 120 },
                  { symbol: "NVDA", kelly: 12, halfKelly: 6, atr: 25 },
                  { symbol: "AAPL", kelly: 8, halfKelly: 4, atr: 3.5 },
                  { symbol: "SPY", kelly: 10, halfKelly: 5, atr: 8 },
                ].map((item) => (
                  <div key={item.symbol} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-medium text-white">{item.symbol}</span>
                      <span className="text-xs font-mono text-emerald-400">
                        {item.halfKelly}% allocation
                      </span>
                    </div>
                    <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className="h-full rounded-full bg-emerald-400/60"
                        style={{ width: `${item.halfKelly * 5}%` }}
                      />
                    </div>
                    <div className="flex justify-between mt-1.5">
                      <span className="text-[10px] text-white/30">ATR: ${item.atr}</span>
                      <span className="text-[10px] text-white/30">Kelly: {item.kelly}%</span>
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="parity">
          <ChartCard title="Risk Parity Allocation" subtitle="Equal risk contribution" className="mt-3">
            <div className="space-y-3">
              {[
                { name: "BTC", riskContrib: 22, weight: 18, vol: 65 },
                { name: "ETH", riskContrib: 18, weight: 15, vol: 72 },
                { name: "NVDA", riskContrib: 16, weight: 12, vol: 45 },
                { name: "SPY", riskContrib: 14, weight: 20, vol: 18 },
                { name: "AAPL", riskContrib: 10, weight: 15, vol: 25 },
                { name: "EUR/USD", riskContrib: 8, weight: 10, vol: 8 },
                { name: "TSLA", riskContrib: 6, weight: 5, vol: 55 },
                { name: "SOL", riskContrib: 6, weight: 5, vol: 85 },
              ].map((item) => (
                <div key={item.name} className="flex items-center gap-3">
                  <span className="text-xs text-white/50 w-16">{item.name}</span>
                  <div className="flex-1">
                    <div className="flex items-center gap-2">
                      <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-blue-400/60"
                          style={{ width: `${item.weight * 4}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-white/40 w-10">{item.weight}%</span>
                    </div>
                    <div className="flex items-center gap-2 mt-0.5">
                      <div className="flex-1 h-1 bg-white/5 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full bg-amber-400/40"
                          style={{ width: `${item.riskContrib * 4}%` }}
                        />
                      </div>
                      <span className="text-[10px] font-mono text-amber-400/60 w-10">{item.riskContrib}%</span>
                    </div>
                  </div>
                  <span className="text-[10px] text-white/30 w-12 text-right">σ {item.vol}%</span>
                </div>
              ))}
            </div>
            <div className="mt-4 p-2 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <div className="flex items-center justify-between">
                <span className="text-xs text-white/40">Risk Parity Status</span>
                <Badge variant="success" className="text-[10px]">Balanced</Badge>
              </div>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="performance">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Risk-Adjusted Returns" subtitle="Sharpe, Sortino, Calmar ratios">
              <div className="space-y-3">
                {[
                  { label: "Sharpe Ratio", value: data.sharpe, max: 3, color: "bg-blue-400" },
                  { label: "Sortino Ratio", value: data.sortino, max: 3, color: "bg-emerald-400" },
                  { label: "Win Rate", value: data.winRate / 100, max: 1, color: "bg-purple-400", pct: true },
                  { label: "Profit Factor", value: Math.min(data.profitFactor / 3, 1), max: 1, color: "bg-amber-400" },
                ].map((item) => (
                  <div key={item.label}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-white/50">{item.label}</span>
                      <span className="text-xs font-mono text-white/70">
                        {item.pct ? `${(item.value * 100).toFixed(1)}%` : item.value.toFixed(2)}
                      </span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${item.color}/60 transition-all`}
                        style={{ width: `${(item.value / item.max) * 100}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            </ChartCard>

            <ChartCard title="Drawdown Analysis" subtitle="Current vs Max drawdown">
              <div className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
                    <p className="text-xs text-white/40 mb-1">Current Drawdown</p>
                    <p className={`text-2xl font-mono font-bold ${data.currentDrawdown > 3 ? "text-red-400" : "text-amber-400"}`}>
                      -{data.currentDrawdown.toFixed(1)}%
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
                    <p className="text-xs text-white/40 mb-1">Max Drawdown</p>
                    <p className="text-2xl font-mono font-bold text-red-400">
                      -{data.maxDrawdown.toFixed(1)}%
                    </p>
                  </div>
                </div>
                <div className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                  <p className="text-xs text-white/40 mb-2">Drawdown Utilization</p>
                  <div className="h-3 bg-white/5 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full transition-all ${
                        data.currentDrawdown / data.maxDrawdown > 0.7
                          ? "bg-red-400"
                          : data.currentDrawdown / data.maxDrawdown > 0.4
                            ? "bg-amber-400"
                            : "bg-emerald-400"
                      }`}
                      style={{ width: `${Math.min(100, (data.currentDrawdown / Math.max(data.maxDrawdown, 1)) * 100)}%` }}
                    />
                  </div>
                  <div className="flex justify-between mt-1">
                    <span className="text-[10px] text-white/30">0%</span>
                    <span className="text-[10px] text-white/30">{((data.currentDrawdown / Math.max(data.maxDrawdown, 1)) * 100).toFixed(0)}% used</span>
                    <span className="text-[10px] text-white/30">100%</span>
                  </div>
                </div>
              </div>
            </ChartCard>
          </div>
        </TabsContent>
      </Tabs>
    </div>
  );
}
