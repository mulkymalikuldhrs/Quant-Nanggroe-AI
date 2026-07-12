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
import { MetricCard, RiskGauge, StatusBadge, SectionHeader, Skeleton, AnimatedNumber } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { cn } from "@/lib/utils";

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <ShieldAlert className="w-8 h-8 text-rose animate-pulse-glow" />
            Risk Defense
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Constitutional Enforcement Node
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button
            variant="outline"
            size="icon"
            onClick={() => {
              fetchPortfolioRisk();
              fetchKillSwitch();
            }}
            className="cursor-pointer scale-tap bg-background/50 backdrop-blur-sm border-border/50 hover:border-rose/50 hover:bg-rose/10 hover:text-rose transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
          {killSwitch?.is_active ? (
            <Button
              variant="outline"
              className="gap-2 font-bold tracking-wide text-emerald border-emerald/50 hover:bg-emerald/10 cursor-pointer shadow-[0_0_15px_rgba(16,185,129,0.2)] hover:shadow-[0_0_20px_rgba(16,185,129,0.4)] transition-all scale-tap"
              onClick={() => setResetDialogOpen(true)}
            >
              <PowerOff className="w-4 h-4" />
              RESTORE TRADING
            </Button>
          ) : (
            <Button
              variant="rose"
              className="gap-2 font-bold tracking-wide cursor-pointer shadow-[0_4px_20px_rgba(244,63,94,0.4)] hover:shadow-[0_4px_25px_rgba(244,63,94,0.6)] transition-all scale-tap"
              onClick={() => setKillDialogOpen(true)}
            >
              <Power className="w-4 h-4" />
              ENGAGE KILL SWITCH
            </Button>
          )}
        </div>
      </div>

      {/* Kill Switch Alert */}
      {killSwitch?.is_active && (
        <div className="p-5 rounded-xl border border-rose bg-rose/10 flex items-center gap-4 shadow-[0_0_30px_rgba(244,63,94,0.2)] animate-fade-in relative overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(244,63,94,0.1)_50%,transparent_75%)] bg-[length:250%_250%,100%_100%] animate-shimmer" />
          <div className="p-3 rounded-full bg-rose/20 pulse-ring relative z-10">
            <AlertTriangle className="w-8 h-8 text-rose" />
          </div>
          <div className="relative z-10">
            <p className="text-xl font-black text-rose uppercase tracking-tight">
              SYSTEM HALTED — PROTOCOL OVERRIDE
            </p>
            <p className="text-sm font-medium text-rose/80 mt-0.5">
              Reason: {killSwitch.activation_reason || "Manual Intervention"} | Timestamp:{" "}
              {killSwitch.activated_at
                ? new Date(killSwitch.activated_at).toLocaleString()
                : "Unknown"}
            </p>
          </div>
        </div>
      )}

      {/* Risk Status Banner */}
      <div
        className={cn(
          "p-4 rounded-xl border transition-colors animate-slide-up relative overflow-hidden group",
          riskStatus === "OK"
            ? "border-emerald/30 bg-emerald/5 shadow-[0_0_15px_rgba(16,185,129,0.1)]"
            : "border-rose/30 bg-rose/5 shadow-[0_0_15px_rgba(244,63,94,0.1)]"
        )}
        style={{ animationDelay: '100ms' }}
      >
        <div className={cn("absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity", 
          riskStatus === "OK" ? "bg-[radial-gradient(ellipse_at_center,rgba(16,185,129,0.1),transparent_50%)]" 
          : "bg-[radial-gradient(ellipse_at_center,rgba(244,63,94,0.1),transparent_50%)]"
        )} />
        <div className="flex items-center gap-3 relative z-10">
          {riskStatus === "OK" ? (
            <CheckCircle2 className="w-6 h-6 text-emerald drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" />
          ) : (
            <AlertTriangle className="w-6 h-6 text-rose drop-shadow-[0_0_5px_rgba(244,63,94,0.5)]" />
          )}
          <span
            className={cn("text-base font-bold uppercase tracking-widest",
              riskStatus === "OK" ? "text-emerald" : "text-rose"
            )}
          >
            Risk Posture: {riskStatus}
          </span>
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 animate-slide-up stagger-children" style={{ animationDelay: '200ms' }}>
        <MetricCard
          title="VaR (95%)"
          value={loadingPortfolioRisk ? 0 : (portfolioRisk?.var_95 ?? 0)}
          formatter={(v) => `${v.toFixed(2)}%`}
          subtitle="Value at Risk"
          icon={<TrendingDown className="w-5 h-5" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="CVaR (95%)"
          value={loadingPortfolioRisk ? 0 : (portfolioRisk?.cvar_95 ?? 0)}
          formatter={(v) => `${v.toFixed(2)}%`}
          subtitle="Conditional VaR"
          icon={<ShieldAlert className="w-5 h-5" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Max Drawdown"
          value={loadingPortfolioRisk ? 0 : ((portfolioRisk?.max_drawdown ?? 0) * 100)}
          formatter={(v) => `${v.toFixed(2)}%`}
          subtitle="Peak to trough"
          icon={<TrendingDown className="w-5 h-5" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Current Drawdown"
          value={loadingPortfolioRisk ? 0 : ((portfolioRisk?.current_drawdown ?? 0) * 100)}
          formatter={(v) => `${v.toFixed(2)}%`}
          subtitle="From peak"
          icon={<Activity className="w-5 h-5" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Daily P&L"
          value={loadingPortfolioRisk ? 0 : ((portfolioRisk?.daily_pnl_pct ?? 0) * 100)}
          formatter={(v) => `${v >= 0 ? '+' : ''}${v.toFixed(2)}%`}
          subtitle="Today"
          icon={<Zap className="w-5 h-5" />}
          color={(portfolioRisk?.daily_pnl_pct ?? 0) >= 0 ? "emerald" : "rose"}
          loading={loadingPortfolioRisk}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-up" style={{ animationDelay: '300ms' }}>
        {/* Risk Gauges */}
        <Card variant="flat" className="h-full">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-amber" />
              Risk Telemetry
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-6">
            {loadingPortfolioRisk ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="space-y-1">
                  <Skeleton className="h-3 w-24" />
                  <Skeleton className="h-2 w-full" />
                </div>
              ))
            ) : (
              <div className="stagger-children">
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
              </div>
            )}
          </CardContent>
        </Card>

        {/* Constitutional Limits */}
        <Card variant="gradient" className="h-full border border-rose/10 bg-gradient-to-br from-rose/5 to-transparent relative overflow-hidden group">
          <div className="absolute top-0 right-0 w-32 h-32 bg-rose/5 rounded-bl-full translate-x-16 -translate-y-16 group-hover:bg-rose/10 transition-colors pointer-events-none" />
          <CardHeader className="relative z-10">
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-rose" />
              Constitutional Directives
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4 relative z-10">
            <div className="stagger-children space-y-3">
              {CONSTITUTIONAL_LIMITS.map((limit) => (
                <div
                  key={limit.key}
                  className="p-3.5 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 hover:border-rose/30 transition-colors flex items-center justify-between group/item"
                >
                  <div>
                    <span className="text-sm font-bold text-foreground block mb-0.5">{limit.name}</span>
                    <span className="text-[10px] text-muted-foreground uppercase tracking-widest block group-hover/item:text-rose/80 transition-colors">Hard Limit</span>
                  </div>
                  <Badge variant="outline" className="text-sm font-mono font-bold bg-background shadow-sm px-2 py-0.5 border-rose/30 text-rose group-hover/item:shadow-[0_0_10px_rgba(244,63,94,0.2)] transition-shadow">
                    {limit.value}
                  </Badge>
                </div>
              ))}
            </div>

            {/* Sharpe & Sortino */}
            <div className="grid grid-cols-2 gap-4 pt-2">
              <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 text-center hover:bg-secondary/40 transition-colors">
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Sharpe Ratio</p>
                <p className="text-3xl font-black text-cyan tabular-nums drop-shadow-[0_0_10px_rgba(6,182,212,0.3)]">
                  <AnimatedNumber value={portfolioRisk?.sharpe_ratio ?? 0} formatter={(v) => v.toFixed(2)} />
                </p>
              </div>
              <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 text-center hover:bg-secondary/40 transition-colors">
                <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1">Sortino Ratio</p>
                <p className="text-3xl font-black text-purple tabular-nums drop-shadow-[0_0_10px_rgba(139,92,246,0.3)]">
                  <AnimatedNumber value={portfolioRisk?.sortino_ratio ?? 0} formatter={(v) => v.toFixed(2)} />
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Stress Test */}
      <Card variant="flat" className="animate-slide-up" style={{ animationDelay: '400ms' }}>
        <CardHeader>
          <CardTitle className="flex items-center justify-between">
            <span className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-amber" />
              Adverse Scenario Modeling
            </span>
            <Button
              variant="outline"
              size="sm"
              onClick={() => fetchStressTest()}
              disabled={loadingStressTest}
              className="cursor-pointer font-bold tracking-wide border-amber/30 text-amber hover:bg-amber/10 hover:text-amber"
            >
              {loadingStressTest ? (
                <RefreshCw className="w-4 h-4 animate-spin mr-2" />
              ) : (
                <RefreshCw className="w-4 h-4 mr-2" />
              )}
              EXECUTE SIMULATION
            </Button>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {stressTest ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5 stagger-children">
              {Object.entries(stressTest.scenarios).map(([name, data]) => (
                <div
                  key={name}
                  className="p-5 rounded-xl bg-secondary/10 border border-border/30 hover:bg-secondary/20 hover:border-amber/30 transition-all hover-lift relative overflow-hidden group"
                >
                  <div className="absolute top-0 right-0 w-16 h-16 bg-amber/5 rounded-bl-full translate-x-8 -translate-y-8 group-hover:bg-amber/10 transition-colors" />
                  <div className="flex items-start justify-between mb-3 relative z-10">
                    <span className="text-sm font-bold text-foreground">
                      {name.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                    </span>
                    <Badge
                      variant={Math.abs(data.loss_pct) > 0.08 ? "rose" : "amber"}
                      className="text-[10px] font-bold shadow-sm"
                    >
                      {(data.loss_pct * 100).toFixed(1)}%
                    </Badge>
                  </div>
                  <p className="text-xs text-muted-foreground mb-4 font-medium relative z-10">
                    {data.description}
                  </p>
                  <div className="space-y-2 text-xs font-mono relative z-10 bg-background/50 p-2.5 rounded-lg border border-border/50">
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">Est. Impact</span>
                      <span className="loss-text tabular-nums font-bold">
                        -${Math.abs(data.estimated_loss).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                    <div className="w-full h-px bg-border/50" />
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] text-muted-foreground uppercase tracking-widest font-bold">P95 Extremum</span>
                      <span className="text-amber tabular-nums font-bold">
                        -${Math.abs(data.p95_loss).toLocaleString(undefined, { maximumFractionDigits: 0 })}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="flex flex-col items-center justify-center py-16 text-muted-foreground font-medium">
              <Zap className="w-12 h-12 mb-4 text-border opacity-50" />
              <p className="text-sm">Initiate simulation to model portfolio resilience under systemic stress.</p>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Kill Switch Dialog */}
      <Dialog open={killDialogOpen} onOpenChange={setKillDialogOpen}>
        <DialogContent className="border-rose/50 shadow-[0_0_50px_rgba(244,63,94,0.2)]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-black text-rose flex items-center gap-3 uppercase tracking-tight">
              <Power className="w-6 h-6 animate-pulse" />
              ENGAGE KILL SWITCH
            </DialogTitle>
            <DialogDescription className="text-base text-rose/80 font-medium">
              This directive will immediately sever all market connections and halt all autonomous trading agents. Proceed only in critical emergencies.
            </DialogDescription>
          </DialogHeader>
          <div className="my-4 p-4 bg-rose/10 border border-rose/30 rounded-lg">
            <label className="text-[10px] font-bold uppercase tracking-widest text-rose mb-1.5 block">
              Authorization Reason
            </label>
            <Button
              variant="outline"
              className="w-full justify-start text-sm cursor-pointer border-rose/50 bg-background text-foreground"
              onClick={() => setKillDialogOpen(true)}
            >
              {killReason}
            </Button>
          </div>
          <DialogFooter className="gap-3">
            <Button variant="ghost" onClick={() => setKillDialogOpen(false)} className="cursor-pointer uppercase text-xs font-bold tracking-widest">
              Abort
            </Button>
            <Button
              variant="rose"
              className="font-bold tracking-widest shadow-[0_4px_20px_rgba(244,63,94,0.4)] cursor-pointer"
              onClick={handleActivateKillSwitch}
            >
              <Power className="w-4 h-4 mr-2" />
              AUTHORIZE HALT
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Reset Kill Switch Dialog */}
      <Dialog open={resetDialogOpen} onOpenChange={setResetDialogOpen}>
        <DialogContent className="border-emerald/50 shadow-[0_0_50px_rgba(16,185,129,0.2)]">
          <DialogHeader>
            <DialogTitle className="text-2xl font-black text-emerald flex items-center gap-3 uppercase tracking-tight">
              <PowerOff className="w-6 h-6" />
              RESTORE OPERATIONS
            </DialogTitle>
            <DialogDescription className="text-base font-medium">
              Acknowledge that risk conditions have normalized. This will permit autonomous agents to resume market interactions.
            </DialogDescription>
          </DialogHeader>
          <div className="my-4 p-4 bg-emerald/5 border border-emerald/20 rounded-lg">
            <label className="text-[10px] font-bold uppercase tracking-widest text-emerald mb-1.5 block">
              Security Authorization
            </label>
            <input
              type="text"
              value={resetConfirm}
              onChange={(e) => setResetConfirm(e.target.value)}
              className="w-full p-3 rounded-md bg-background border border-emerald/50 text-foreground text-sm font-mono focus:outline-none focus:ring-2 focus:ring-emerald/50 focus:border-transparent transition-all"
              placeholder="Type CONFIRM"
            />
          </div>
          <DialogFooter className="gap-3">
            <Button variant="ghost" onClick={() => setResetDialogOpen(false)} className="cursor-pointer uppercase text-xs font-bold tracking-widest">
              Abort
            </Button>
            <Button
              className="bg-emerald hover:bg-emerald/90 text-primary-foreground font-bold tracking-widest cursor-pointer shadow-[0_4px_20px_rgba(16,185,129,0.4)] disabled:opacity-50 disabled:shadow-none transition-all"
              onClick={handleResetKillSwitch}
              disabled={resetConfirm !== "CONFIRM"}
            >
              <PowerOff className="w-4 h-4 mr-2" />
              RESTORE SYSTEMS
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
