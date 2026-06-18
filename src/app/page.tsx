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
  BarChart,
  Bar,
} from "recharts";
import {
  Zap,
  TrendingUp,
  TrendingDown,
  Bot,
  Activity,
  ShieldAlert,
  Clock,
  ArrowUpRight,
  AlertTriangle,
  CheckCircle2,
  Play,
  FlaskConical,
  LineChart,
  Server,
  RefreshCw,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, StatusBadge, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import Link from "next/link";

const severityIcon: Record<string, React.ReactNode> = {
  success: <CheckCircle2 className="w-3.5 h-3.5 text-emerald" />,
  info: <Activity className="w-3.5 h-3.5 text-cyan" />,
  warning: <AlertTriangle className="w-3.5 h-3.5 text-amber" />,
  error: <AlertTriangle className="w-3.5 h-3.5 text-rose" />,
};

const severityColor: Record<string, string> = {
  success: "border-l-emerald",
  info: "border-l-cyan",
  warning: "border-l-amber",
  error: "border-l-rose",
};

export default function DashboardPage() {
  const {
    portfolio,
    portfolioRisk,
    agents,
    positions,
    eventFeed,
    systemHealth,
    killSwitch,
    loadingPortfolio,
    loadingPortfolioRisk,
    loadingAgents,
    loadingHealth,
    fetchPortfolio,
    fetchPortfolioRisk,
    fetchAgents,
    fetchPositions,
    fetchHealth,
    fetchKillSwitch,
  } = useAppStore();

  const [equityHistory, setEquityHistory] = useState<Array<{ time: string; value: number }>>([]);

  useEffect(() => {
    fetchPortfolio();
    fetchPortfolioRisk();
    fetchAgents();
    fetchPositions();
    fetchHealth();
    fetchKillSwitch();
  }, [fetchPortfolio, fetchPortfolioRisk, fetchAgents, fetchPositions, fetchHealth, fetchKillSwitch]);

  // Build equity history from portfolio changes
  useEffect(() => {
    if (portfolio?.total_value) {
      setEquityHistory((prev) => {
        const newEntry = {
          time: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
          value: portfolio.total_value,
        };
        const updated = [...prev, newEntry];
        return updated.length > 30 ? updated.slice(-30) : updated;
      });
    }
  }, [portfolio?.total_value]);

  // Auto-refresh every 30s
  useEffect(() => {
    const interval = setInterval(() => {
      fetchPortfolio();
      fetchPortfolioRisk();
      fetchPositions();
      fetchHealth();
    }, 30000);
    return () => clearInterval(interval);
  }, [fetchPortfolio, fetchPortfolioRisk, fetchPositions, fetchHealth]);

  const activeAgents = agents.filter((a) => a.status === "active").length;
  const totalPnl = portfolio?.unrealized_pnl ?? 0;
  const isProfit = totalPnl >= 0;
  const riskStatus = portfolioRisk?.risk_status ?? "OK";

  const handleRefresh = useCallback(() => {
    fetchPortfolio();
    fetchPortfolioRisk();
    fetchAgents();
    fetchPositions();
    fetchHealth();
    fetchKillSwitch();
  }, [fetchPortfolio, fetchPortfolioRisk, fetchAgents, fetchPositions, fetchHealth, fetchKillSwitch]);

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Zap className="w-6 h-6 text-cyan" />
            Mission Control
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Quant Nanggroe AI — Trading Intelligence Dashboard
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="icon" onClick={handleRefresh} className="cursor-pointer">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Badge
            variant={riskStatus === "OK" ? "emerald" : "rose"}
            className="gap-1"
          >
            <span
              className={`status-dot ${
                riskStatus === "OK" ? "status-dot-active" : "status-dot-error"
              } ${riskStatus === "OK" ? "pulse-ring" : ""}`}
            />
            {riskStatus === "OK" ? "System OK" : "Risk HALT"}
          </Badge>
          <Badge variant="outline" className="text-muted-foreground">
            <Clock className="w-3 h-3 mr-1" />
            {new Date().toLocaleTimeString()}
          </Badge>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
        <MetricCard
          title="Portfolio Value"
          value={loadingPortfolio ? "..." : `$${(portfolio?.total_value ?? 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`}
          subtitle={isProfit ? "Unrealized profit" : "Unrealized loss"}
          icon={<TrendingUp className="w-4 h-4" />}
          color={isProfit ? "emerald" : "rose"}
          trend={
            portfolio?.unrealized_pnl
              ? {
                  value: Math.abs(portfolio.unrealized_pnl / (portfolio.total_value || 1) * 100),
                  positive: isProfit,
                }
              : undefined
          }
          loading={loadingPortfolio}
        />
        <MetricCard
          title="Active Positions"
          value={loadingPortfolio ? "..." : portfolio?.position_count ?? 0}
          subtitle={`of ${positions.length} total`}
          icon={<Activity className="w-4 h-4" />}
          color="cyan"
          loading={loadingPortfolio}
        />
        <MetricCard
          title="Active Agents"
          value={loadingAgents ? "..." : activeAgents}
          subtitle={`of ${agents.length} total`}
          icon={<Bot className="w-4 h-4" />}
          color="purple"
          loading={loadingAgents}
        />
        <MetricCard
          title="VaR (95%)"
          value={loadingPortfolioRisk ? "..." : `${(portfolioRisk?.var_95 ?? 0).toFixed(2)}%`}
          subtitle="Value at Risk"
          icon={<ShieldAlert className="w-4 h-4" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Max Drawdown"
          value={loadingPortfolioRisk ? "..." : `${((portfolioRisk?.max_drawdown ?? 0) * 100).toFixed(2)}%`}
          subtitle="Historical peak-to-trough"
          icon={<TrendingDown className="w-4 h-4" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
      </div>

      {/* Kill Switch Alert */}
      {killSwitch?.is_active && (
        <div className="p-4 rounded-lg border border-rose/40 bg-rose/5 flex items-center gap-3 animate-fade-in">
          <AlertTriangle className="w-5 h-5 text-rose shrink-0" />
          <div>
            <p className="text-sm font-bold text-rose">
              KILL SWITCH ACTIVE — All Trading Halted
            </p>
            <p className="text-xs text-muted-foreground mt-0.5">
              {killSwitch.activation_reason || "Manual activation"} at{" "}
              {killSwitch.activated_at
                ? new Date(killSwitch.activated_at).toLocaleString()
                : "unknown time"}
            </p>
          </div>
          <Link href="/risk" className="ml-auto">
            <Button variant="outline" size="sm" className="text-rose border-rose/30 hover:bg-rose/10">
              View Risk Panel
            </Button>
          </Link>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Equity Curve */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <LineChart className="w-4 h-4 text-cyan" />
              Equity Curve
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {equityHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityHistory}>
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={11} />
                    <YAxis stroke="#64748b" fontSize={11} />
                    <Tooltip
                      contentStyle={{
                        background: "#0d1117",
                        border: "1px solid #1e293b",
                        borderRadius: "8px",
                        fontSize: "12px",
                      }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#06b6d4"
                      fill="url(#equityGrad)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  <Activity className="w-4 h-4 mr-2" />
                  Waiting for portfolio data...
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Risk Metrics */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber" />
              Risk Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {loadingPortfolioRisk ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="space-y-1">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                ))
              ) : (
                <>
                  <RiskBar label="VaR (95%)" value={portfolioRisk?.var_95 ?? 0} max={10} />
                  <RiskBar label="CVaR (95%)" value={portfolioRisk?.cvar_95 ?? 0} max={15} />
                  <RiskBar label="Max Drawdown" value={(portfolioRisk?.max_drawdown ?? 0) * 100} max={20} />
                  <RiskBar label="Current Drawdown" value={(portfolioRisk?.current_drawdown ?? 0) * 100} max={20} />
                  <RiskBar label="Daily P&L" value={Math.abs(portfolioRisk?.daily_pnl_pct ?? 0) * 100} max={5} invert />
                  <div className="grid grid-cols-2 gap-3 pt-2">
                    <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                      <p className="text-xs text-muted-foreground">Sharpe Ratio</p>
                      <p className="text-lg font-bold text-cyan">{(portfolioRisk?.sharpe_ratio ?? 0).toFixed(2)}</p>
                    </div>
                    <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                      <p className="text-xs text-muted-foreground">Sortino Ratio</p>
                      <p className="text-lg font-bold text-purple">{(portfolioRisk?.sortino_ratio ?? 0).toFixed(2)}</p>
                    </div>
                  </div>
                </>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions + Positions + Event Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Quick Actions */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Link href="/trading" className="block">
              <button className="w-full flex items-center gap-3 p-3 rounded-lg bg-gradient-to-r from-emerald/10 to-cyan/10 border border-emerald/20 hover:border-emerald/40 transition-all cursor-pointer">
                <div className="p-2 rounded-lg bg-emerald/20">
                  <LineChart className="w-4 h-4 text-emerald" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Place Trade</p>
                  <p className="text-xs text-muted-foreground">Execute a new order</p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-muted-foreground ml-auto" />
              </button>
            </Link>
            <Link href="/agents" className="block">
              <button className="w-full flex items-center gap-3 p-3 rounded-lg bg-gradient-to-r from-purple/10 to-cyan/10 border border-purple/20 hover:border-purple/40 transition-all cursor-pointer">
                <div className="p-2 rounded-lg bg-purple/20">
                  <Play className="w-4 h-4 text-purple" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Run Agent</p>
                  <p className="text-xs text-muted-foreground">Execute AI analysis</p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-muted-foreground ml-auto" />
              </button>
            </Link>
            <Link href="/backtest" className="block">
              <button className="w-full flex items-center gap-3 p-3 rounded-lg bg-gradient-to-r from-amber/10 to-cyan/10 border border-amber/20 hover:border-amber/40 transition-all cursor-pointer">
                <div className="p-2 rounded-lg bg-amber/20">
                  <FlaskConical className="w-4 h-4 text-amber" />
                </div>
                <div className="text-left">
                  <p className="text-sm font-medium text-foreground">Run Backtest</p>
                  <p className="text-xs text-muted-foreground">Test a strategy</p>
                </div>
                <ArrowUpRight className="w-4 h-4 text-muted-foreground ml-auto" />
              </button>
            </Link>
          </CardContent>
        </Card>

        {/* Positions Summary */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald" />
              Open Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="max-h-72">
              {positions.length > 0 ? (
                <div className="space-y-2">
                  {positions.map((pos, idx) => (
                    <div
                      key={idx}
                      className="p-3 rounded-lg bg-secondary/20 border border-border/30 hover:border-primary/20 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-foreground font-mono">
                          {pos.ticker}
                        </span>
                        <span
                          className={`text-sm font-bold tabular-nums ${
                            pos.pnl >= 0 ? "profit-text" : "loss-text"
                          }`}
                        >
                          {pos.pnl >= 0 ? "+" : ""}
                          {pos.pnl.toFixed(2)}
                        </span>
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground">
                        <span>{pos.amount} @ {pos.avg_price.toFixed(2)}</span>
                        <span>Now: {pos.current_price.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                  No open positions
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Live Event Feed */}
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan" />
              Live Event Feed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-72">
              <div className="space-y-1">
                {eventFeed.length > 0 ? (
                  eventFeed.map((event) => (
                    <div
                      key={event.id}
                      className={`flex items-start gap-2 p-2 rounded-md hover:bg-secondary/30 transition-colors border-l-2 ${
                        severityColor[event.severity] || "border-l-cyan"
                      }`}
                    >
                      <span className="mt-0.5 shrink-0">
                        {severityIcon[event.severity] || severityIcon.info}
                      </span>
                      <div className="min-w-0 flex-1">
                        <p className="text-xs text-foreground leading-relaxed">
                          {event.message}
                        </p>
                        <div className="flex items-center gap-2 mt-0.5">
                          <Badge
                            variant="outline"
                            className="text-[10px] px-1.5 py-0"
                          >
                            {event.type}
                          </Badge>
                          <span className="text-[10px] text-muted-foreground">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center h-32 text-muted-foreground text-sm">
                    <Server className="w-4 h-4 mr-2" />
                    Waiting for events...
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Agent Overview Row */}
      <div>
        <SectionHeader
          title="Agent Overview"
          description="Current status of all deployed agents"
          action={
            <Link
              href="/agents"
              className="text-xs text-primary hover:text-primary/80 flex items-center gap-1"
            >
              View All <ArrowUpRight className="w-3 h-3" />
            </Link>
          }
        />
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 mt-4">
          {loadingAgents
            ? Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="glass-card p-4 space-y-3">
                  <Skeleton className="h-4 w-24" />
                  <Skeleton className="h-3 w-32" />
                  <Skeleton className="h-3 w-20" />
                </div>
              ))
            : agents.slice(0, 9).map((agent) => (
                <div
                  key={agent.name}
                  className="glass-card p-3 hover:border-primary/30 transition-all"
                >
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-medium text-foreground">
                      {agent.name}
                    </span>
                    <StatusBadge status={agent.status} />
                  </div>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div className="flex justify-between">
                      <span>Role</span>
                      <span className="text-foreground">{agent.role || "—"}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Registered</span>
                      <span className="text-foreground">
                        {agent.registered ? "Yes" : "No"}
                      </span>
                    </div>
                  </div>
                </div>
              ))}
        </div>
      </div>

      {/* System Health */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
            <Server className="w-4 h-4 text-emerald" />
            System Health
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">API Server</span>
                <StatusBadge
                  status={systemHealth?.status === "healthy" ? "active" : "error"}
                  size="sm"
                />
              </div>
              <p className="text-sm font-medium text-foreground">
                {systemHealth?.service || "—"}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Kill Switch</span>
                <StatusBadge
                  status={killSwitch?.is_active ? "HALT" : "OK"}
                  size="sm"
                />
              </div>
              <p className="text-sm font-medium text-foreground">
                {killSwitch?.is_active ? "TRADING HALTED" : "Trading Active"}
              </p>
            </div>
            <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
              <div className="flex items-center justify-between mb-1">
                <span className="text-xs text-muted-foreground">Risk Status</span>
                <StatusBadge status={riskStatus} size="sm" />
              </div>
              <p className="text-sm font-medium text-foreground">
                {portfolioRisk?.risk_status === "OK"
                  ? "All checks passing"
                  : "Risk limits exceeded"}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function RiskBar({
  label,
  value,
  max,
  invert = false,
}: {
  label: string;
  value: number;
  max: number;
  invert?: boolean;
}) {
  const pct = Math.min((Math.abs(value) / max) * 100, 100);
  const isGood = invert ? value < 0 : pct < 50;
  const color = isGood ? "bg-emerald" : pct < 80 ? "bg-amber" : "bg-rose";
  const textColor = isGood ? "text-emerald" : pct < 80 ? "text-amber" : "text-rose";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-medium tabular-nums", textColor)}>
          {value.toFixed(2)}%
        </span>
      </div>
      <div className="h-1.5 rounded-full bg-secondary/50">
        <div
          className={cn("h-full rounded-full transition-all duration-500", color)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

function cn(...classes: (string | undefined | false)[]) {
  return classes.filter(Boolean).join(" ");
}
