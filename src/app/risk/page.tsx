"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  ShieldAlert,
  AlertTriangle,
  CheckCircle2,
  RefreshCw,
  Zap,
  TrendingDown,
  Activity,
  Power,
  PowerOff,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { MetricCard, RiskGauge, StatusBadge, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";

const CONSTITUTIONAL_LIMITS = [
  { name: "Max Risk Per Trade", value: "0.5%", key: "risk_max_per_trade" },
  { name: "Max Daily Loss", value: "1.0%", key: "risk_max_daily_loss" },
  { name: "Max Weekly Loss", value: "3.0%", key: "risk_max_weekly_loss" },
  { name: "Max Drawdown", value: "10.0%", key: "risk_max_drawdown" },
];

export default function RiskPage() {
  const {
    portfolioRisk,
    killSwitch,
    stressTest,
    loadingPortfolioRisk,
    loadingKillSwitch,
    loadingStressTest,
    fetchPortfolioRisk,
    fetchKillSwitch,
    fetchStressTest,
    activateKillSwitch,
    resetKillSwitch,
  } = useAppStore();

  const [killDialogOpen, setKillDialogOpen] = useState(false);
  const [killReason, setKillReason] = useState("MANUAL");
  const [resetDialogOpen, setResetDialogOpen] = useState(false);
  const [resetConfirm, setResetConfirm] = useState("");

  useEffect(() => {
    fetchPortfolioRisk();
    fetchKillSwitch();
  }, [fetchPortfolioRisk, fetchKillSwitch]);

  const handleActivateKillSwitch = async () => {
    const ok = await activateKillSwitch(killReason);
    if (ok) setKillDialogOpen(false);
  };

  const handleResetKillSwitch = async () => {
    if (resetConfirm !== "CONFIRM") return;
    const ok = await resetKillSwitch();
    if (ok) {
      setResetDialogOpen(false);
      setResetConfirm("");
    }
  };

  const riskStatus = portfolioRisk?.risk_status ?? "OK";

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <ShieldAlert className="w-6 h-6 text-rose" />
            Risk Dashboard
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Portfolio risk management and constitutional limits
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              fetchPortfolioRisk();
              fetchKillSwitch();
            }}
            className="cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          {killSwitch?.is_active ? (
            <Button
              variant="outline"
              className="gap-2 text-emerald border-emerald/30 hover:bg-emerald/10 cursor-pointer"
              onClick={() => setResetDialogOpen(true)}
            >
              <PowerOff className="w-4 h-4" />
              Reset Kill Switch
            </Button>
          ) : (
            <Button
              variant="outline"
              className="gap-2 text-rose border-rose/30 hover:bg-rose/10 cursor-pointer"
              onClick={() => setKillDialogOpen(true)}
            >
              <Power className="w-4 h-4" />
              Kill Switch
            </Button>
          )}
        </div>
      </div>

      {/* Kill Switch Alert */}
      {killSwitch?.is_active && (
        <div className="p-4 rounded-lg border border-rose/40 bg-rose/5 animate-fade-in">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-full bg-rose/20 pulse-ring">
              <AlertTriangle className="w-5 h-5 text-rose" />
            </div>
            <div>
              <p className="text-sm font-bold text-rose">
                KILL SWITCH ACTIVE — ALL TRADING HALTED
              </p>
              <p className="text-xs text-muted-foreground mt-0.5">
                Reason: {killSwitch.activation_reason || "Unknown"} | Activated:{" "}
                {killSwitch.activated_at
                  ? new Date(killSwitch.activated_at).toLocaleString()
                  : "Unknown"}
              </p>
            </div>
          </div>
        </div>
      )}

      {/* Risk Status Banner */}
      <div
        className={`p-3 rounded-lg border ${
          riskStatus === "OK"
            ? "border-emerald/30 bg-emerald/5"
            : "border-rose/30 bg-rose/5"
        }`}
      >
        <div className="flex items-center gap-2">
          {riskStatus === "OK" ? (
            <CheckCircle2 className="w-4 h-4 text-emerald" />
          ) : (
            <AlertTriangle className="w-4 h-4 text-rose" />
          )}
          <span
            className={`text-sm font-medium ${
              riskStatus === "OK" ? "text-emerald" : "text-rose"
            }`}
          >
            Risk Status: {riskStatus}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="VaR (95%)"
          value={loadingPortfolioRisk ? "..." : `${(portfolioRisk?.var_95 ?? 0).toFixed(2)}%`}
          subtitle="Value at Risk"
          icon={<TrendingDown className="w-4 h-4" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="CVaR (95%)"
          value={loadingPortfolioRisk ? "..." : `${(portfolioRisk?.cvar_95 ?? 0).toFixed(2)}%`}
          subtitle="Conditional VaR"
          icon={<ShieldAlert className="w-4 h-4" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Max Drawdown"
          value={loadingPortfolioRisk ? "..." : `${((portfolioRisk?.max_drawdown ?? 0) * 100).toFixed(2)}%`}
          subtitle="Peak to trough"
          icon={<TrendingDown className="w-4 h-4" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Current Drawdown"
          value={loadingPortfolioRisk ? "..." : `${((portfolioRisk?.current_drawdown ?? 0) * 100).toFixed(2)}%`}
          subtitle="From peak"
          icon={<Activity className="w-4 h-4" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Daily P&L"
          value={loadingPortfolioRisk ? "..." : `${((portfolioRisk?.daily_pnl_pct ?? 0) * 100).toFixed(2)}%`}
          subtitle="Today"
          icon={<Zap className="w-4 h-4" />}
          color={(portfolioRisk?.daily_pnl_pct ?? 0) >= 0 ? "emerald" : "rose"}
          loading={loadingPortfolioRisk}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Risk Gauges */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber" />
              Risk Gauges
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {loadingPortfolioRisk ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-2 w-full" />
                </div>
              ))
            ) : (
              <>
                <RiskGauge
                  label="VaR (95%)"
                  value={(portfolioRisk?.var_95 ?? 0)}
                  max={5}
                />
                <RiskGauge
                  label="CVaR (95%)"
                  value={(portfolioRisk?.cvar_95 ?? 0)}
                  max={8}
                />
                <RiskGauge
                  label="Max Drawdown"
                  value={(portfolioRisk?.max_drawdown ?? 0) * 100}
                  max={15}
                />
                <RiskGauge
                  label="Current Drawdown"
                  value={(portfolioRisk?.current_drawdown ?? 0) * 100}
                  max={10}
                />
                <RiskGauge
                  label="Daily Loss"
                  value={Math.abs(portfolioRisk?.daily_pnl_pct ?? 0) * 100}
                  max={3}
                />
              </>
            )}
          </CardContent>
        </Card>

        {/* Constitutional Limits */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose" />
              Constitutional Limits
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {CONSTITUTIONAL_LIMITS.map((limit) => (
              <div
                key={limit.key}
                className="p-3 rounded-lg bg-secondary/20 border border-border/30"
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm text-foreground">{limit.name}</span>
                  <Badge variant="outline" className="text-[10px] font-mono">
                    {limit.value}
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground">
                  Cannot be overridden by agents. Enforced at execution level.
                </p>
              </div>
            ))}

            {/* Sharpe & Sortino */}
            <div className="grid grid-cols-2 gap-3 pt-2">
              <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                <p className="text-xs text-muted-foreground">Sharpe Ratio</p>
                <p className="text-lg font-bold text-cyan tabular-nums">
                  {(portfolioRisk?.sharpe_ratio ?? 0).toFixed(2)}
                </p>
              </div>
              <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                <p className="text-xs text-muted-foreground">Sortino Ratio</p>
                <p className="text-lg font-bold text-purple tabular-nums">
                  {(portfolioRisk?.sortino_ratio ?? 0).toFixed(2)}
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stress Test */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber" />
              Stress Test Scenarios
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchStressTest()}
              disabled={loadingStressTest}
              className="cursor-pointer"
            >
              {loadingStressTest ? (
                <RefreshCw className="w-4 h-4 animate-spin mr-1" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-1" />
              )}
              Run Stress Test
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stressTest ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {Object.entries(stressTest.scenarios).map(([name, data]) => (
                <div
                  key={name}
                  className="p-3 rounded-lg bg-secondary/20 border border-border/30"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs font-medium text-foreground">
                      {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <Badge
                      variant={Math.abs(data.loss_pct) > 0.08 ? "rose" : "amber"}
                      className="text-[9px]"
                    >
                      {(data.loss_pct * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <p className="text-[10px] text-muted-foreground mb-2">
                    {data.description}
                  </p>
                  <div className="space-y-1 text-xs">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Est. Loss</span>
                      <span className="loss-text tabular-nums">
                        -${Math.abs(data.estimated_loss).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">P95 Loss</span>
                      <span className="text-amber tabular-nums">
                        -${Math.abs(data.p95_loss).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-8 text-muted-foreground text-sm">
              Click &quot;Run Stress Test&quot; to simulate portfolio under adverse scenarios
            </div>
          )}
        </CardContent>
      </Card>

      {/* Kill Switch Dialog */}
      <Dialog open={killDialogOpen} onOpenChange={setKillDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-rose flex items-center gap-2">
              <Power className="w-5 h-5" />
              Activate Kill Switch
            </DialogTitle>
            <DialogDescription>
              This will immediately halt ALL trading activity. This action should
              only be used in emergency situations.
            </DialogDescription>
          </DialogHeader>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">
              Reason
            </label>
            <Button
              variant="outline"
              className="w-full justify-start text-sm cursor-pointer"
              onClick={() => setKillDialogOpen(true)}
            >
              {killReason}
            </Button>
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setKillDialogOpen(false)} className="cursor-pointer">
              Cancel
            </Button>
            <Button
              variant="outline"
              className="bg-rose hover:bg-rose/80 text-white cursor-pointer"
              onClick={handleActivateKillSwitch}
            >
              <Power className="w-4 h-4 mr-2" />
              ACTIVATE KILL SWITCH
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Kill Switch Dialog */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle className="text-emerald flex items-center gap-2">
              <PowerOff className="w-5 h-5" />
              Reset Kill Switch
            </DialogTitle>
            <DialogDescription>
              Type &quot;CONFIRM&quot; to resume trading. This will re-enable all
              trading operations.
            </DialogDescription>
          </DialogHeader>
          <div>
            <label className="text-sm font-medium text-foreground mb-1.5 block">
              Type CONFIRM to proceed
            </label>
            <input
              type="text"
              value={resetConfirm}
              onChange={(e) => setResetConfirm(e.target.value)}
              className="w-full p-2 rounded-md bg-secondary border border-border text-foreground text-sm"
              placeholder="CONFIRM"
            />
          </div>
          <DialogFooter>
            <Button variant="ghost" onClick={() => setResetDialogOpen(false)} className="cursor-pointer">
              Cancel
            </Button>
            <Button
              variant="outline"
              className="bg-emerald hover:bg-emerald/80 text-white cursor-pointer"
              onClick={handleResetKillSwitch}
              disabled={resetConfirm !== "CONFIRM"}
            >
              <PowerOff className="w-4 h-4 mr-2" />
              RESET KILL SWITCH
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
