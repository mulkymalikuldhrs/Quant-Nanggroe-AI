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
  Zap,
  TrendingUp,
  TrendingDown,
  Bot,
  Activity,
  ShieldAlert,
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
import { MetricCard, StatusBadge, SectionHeader, Skeleton, AnimatedNumber, RiskGauge } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import Link from "next/link";
import { cn } from "@/lib/utils";

const severityIcon: Record<string, React.ReactNode> = {
  success: <CheckCircle2 className="w-3.5 h-3.5 text-emerald" />,
  info: <Activity className="w-3.5 h-3.5 text-cyan" />,
  warning: <AlertTriangle className="w-3.5 h-3.5 text-amber" />,
  error: <AlertTriangle className="w-3.5 h-3.5 text-rose" />,
};

const severityColor: Record<string, string> = {
  success: "border-l-emerald shadow-[inset_2px_0_10px_rgba(16,185,129,0.1)]",
  info: "border-l-cyan shadow-[inset_2px_0_10px_rgba(6,182,212,0.1)]",
  warning: "border-l-amber shadow-[inset_2px_0_10px_rgba(245,158,11,0.1)]",
  error: "border-l-rose shadow-[inset_2px_0_10px_rgba(244,63,94,0.1)]",
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
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <Zap className="w-8 h-8 text-cyan animate-pulse-glow" />
            Mission Control
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Quant Nanggroe AI Overview
          </p>
        </div>
        <div className="flex items-center gap-3">
          <Button variant="outline" size="icon" onClick={handleRefresh} className="cursor-pointer scale-tap bg-background/50 backdrop-blur-sm border-border/50 hover:border-cyan/50 hover:bg-cyan/10 hover:text-cyan transition-colors">
            <RefreshCw className="w-4 h-4" />
          </Button>
          <Badge
            variant={riskStatus === "OK" ? "emerald" : "rose"}
            className="gap-2 px-3 py-1 shadow-[0_0_15px_rgba(0,0,0,0.1)]"
          >
            <span
              className={`status-dot ${
                riskStatus === "OK" ? "status-dot-active pulse-ring" : "status-dot-error"
              }`}
            />
            {riskStatus === "OK" ? "SYSTEM OK" : "RISK HALT"}
          </Badge>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4 stagger-children">
        <MetricCard
          title="Portfolio Value"
          value={loadingPortfolio ? 0 : (portfolio?.total_value ?? 0)}
          subtitle={isProfit ? "Unrealized profit" : "Unrealized loss"}
          icon={<TrendingUp className="w-5 h-5" />}
          color={isProfit ? "emerald" : "rose"}
          trend={
            portfolio?.unrealized_pnl
              ? {
                  value: Math.abs((portfolio.unrealized_pnl / (portfolio.total_value || 1)) * 100),
                  positive: isProfit,
                }
              : undefined
          }
          loading={loadingPortfolio}
        />
        <MetricCard
          title="Active Positions"
          value={loadingPortfolio ? 0 : (portfolio?.position_count ?? 0)}
          subtitle={`of ${positions.length} total`}
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          loading={loadingPortfolio}
        />
        <MetricCard
          title="Active Agents"
          value={loadingAgents ? 0 : activeAgents}
          subtitle={`of ${agents.length} total`}
          icon={<Bot className="w-5 h-5" />}
          color="purple"
          loading={loadingAgents}
        />
        <MetricCard
          title="VaR (95%)"
          value={loadingPortfolioRisk ? 0 : (portfolioRisk?.var_95 ?? 0)}
          subtitle="Value at Risk"
          icon={<ShieldAlert className="w-5 h-5" />}
          color="amber"
          loading={loadingPortfolioRisk}
        />
        <MetricCard
          title="Max Drawdown"
          value={loadingPortfolioRisk ? 0 : ((portfolioRisk?.max_drawdown ?? 0) * 100)}
          subtitle="Historical peak-to-trough"
          icon={<TrendingDown className="w-5 h-5" />}
          color="rose"
          loading={loadingPortfolioRisk}
        />
      </div>

      {/* Kill Switch Alert */}
      {killSwitch?.is_active && (
        <div className="p-4 rounded-xl border border-rose bg-rose/10 flex items-center gap-4 shadow-[0_0_30px_rgba(244,63,94,0.15)] animate-fade-in relative overflow-hidden">
          <div className="absolute inset-0 bg-[linear-gradient(45deg,transparent_25%,rgba(244,63,94,0.1)_50%,transparent_75%)] bg-[length:250%_250%,100%_100%] animate-shimmer" />
          <AlertTriangle className="w-8 h-8 text-rose shrink-0 animate-pulse-glow relative z-10" />
          <div className="relative z-10">
            <p className="text-lg font-black tracking-tight text-rose uppercase">
              KILL SWITCH ACTIVE — All Trading Halted
            </p>
            <p className="text-sm font-medium text-rose/80 mt-0.5">
              {killSwitch.activation_reason || "Manual activation"} at{" "}
              {killSwitch.activated_at
                ? new Date(killSwitch.activated_at).toLocaleString()
                : "unknown time"}
            </p>
          </div>
          <Link href="/risk" className="ml-auto relative z-10">
            <Button variant="rose" className="font-bold shadow-[0_0_15px_rgba(244,63,94,0.4)]">
              View Risk Panel
            </Button>
          </Link>
        </div>
      )}

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 animate-slide-up" style={{ animationDelay: '100ms' }}>
        {/* Equity Curve */}
        <Card variant="gradient" className="h-full">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <LineChart className="w-4 h-4 text-cyan" />
              Equity Curve
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-[280px] w-full relative">
              {equityHistory.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={equityHistory} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                    <defs>
                      <linearGradient id="equityGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.5} />
                        <stop offset="95%" stopColor="#06b6d4" stopOpacity={0.0} />
                      </linearGradient>
                      <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
                        <feGaussianBlur stdDeviation="4" result="blur" />
                        <feComposite in="SourceGraphic" in2="blur" operator="over" />
                      </filter>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                    <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                    <YAxis stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} tickFormatter={(val) => `$${val / 1000}k`} />
                    <Tooltip
                      contentStyle={{
                        background: "rgba(10, 15, 26, 0.9)",
                        backdropFilter: "blur(10px)",
                        border: "1px solid rgba(6, 182, 212, 0.3)",
                        borderRadius: "8px",
                        boxShadow: "0 4px 20px rgba(0,0,0,0.4), 0 0 10px rgba(6,182,212,0.1)",
                        fontSize: "12px",
                        fontWeight: 600,
                      }}
                      itemStyle={{ color: "#06b6d4" }}
                      cursor={{ stroke: 'rgba(6, 182, 212, 0.5)', strokeWidth: 1, strokeDasharray: '4 4' }}
                    />
                    <Area
                      type="monotone"
                      dataKey="value"
                      stroke="#06b6d4"
                      strokeWidth={3}
                      fill="url(#equityGrad)"
                      activeDot={{ r: 6, fill: "#06b6d4", stroke: "#030712", strokeWidth: 2, filter: "url(#glow)" }}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                  <Activity className="w-5 h-5 mr-3 animate-pulse" />
                  Waiting for portfolio data...
                </div>
              )}
            </div>
          </CardContent>
        </Card>

        {/* Risk Metrics */}
        <Card variant="flat" className="h-full border border-amber/10 bg-gradient-to-br from-amber/5 to-transparent">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <ShieldAlert className="w-4 h-4 text-amber" />
              Risk Metrics
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-5">
              {loadingPortfolioRisk ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <div key={i} className="space-y-1">
                    <Skeleton className="h-3 w-24" />
                    <Skeleton className="h-2 w-full" />
                  </div>
                ))
              ) : (
                <div className="stagger-children">
                  <RiskGauge label="VaR (95%)" value={portfolioRisk?.var_95 ?? 0} max={10} />
                  <RiskGauge label="CVaR (95%)" value={portfolioRisk?.cvar_95 ?? 0} max={15} />
                  <RiskGauge label="Max Drawdown" value={(portfolioRisk?.max_drawdown ?? 0) * 100} max={20} />
                  
                  <div className="grid grid-cols-2 gap-4 pt-4">
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Sharpe Ratio</p>
                      <p className="text-2xl font-black text-cyan drop-shadow-[0_0_10px_rgba(6,182,212,0.3)]">
                        <AnimatedNumber value={portfolioRisk?.sharpe_ratio ?? 0} formatter={(v) => v.toFixed(2)} />
                      </p>
                    </div>
                    <div className="p-4 rounded-xl bg-secondary/30 border border-border/50 hover:bg-secondary/50 transition-colors">
                      <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-widest mb-1">Sortino Ratio</p>
                      <p className="text-2xl font-black text-purple drop-shadow-[0_0_10px_rgba(139,92,246,0.3)]">
                        <AnimatedNumber value={portfolioRisk?.sortino_ratio ?? 0} formatter={(v) => v.toFixed(2)} />
                      </p>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Quick Actions + Positions + Event Feed */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
        {/* Quick Actions */}
        <Card variant="flat">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <Zap className="w-4 h-4 text-cyan" />
              Quick Actions
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-3 stagger-children">
            <Link href="/trading" className="block group">
              <div className="w-full flex items-center gap-4 p-4 rounded-xl bg-secondary/20 border border-border/50 group-hover:border-emerald/40 group-hover:bg-emerald/5 transition-all cursor-pointer hover-lift">
                <div className="p-2.5 rounded-lg bg-emerald/20 shadow-[0_0_15px_rgba(16,185,129,0.2)] group-hover:scale-110 transition-transform">
                  <LineChart className="w-5 h-5 text-emerald" />
                </div>
                <div className="text-left flex-1">
                  <p className="text-sm font-bold text-foreground">Place Trade</p>
                  <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Execute a manual order</p>
                </div>
                <ArrowUpRight className="w-5 h-5 text-muted-foreground group-hover:text-emerald transition-colors" />
              </div>
            </Link>
            <Link href="/agents" className="block group">
              <div className="w-full flex items-center gap-4 p-4 rounded-xl bg-secondary/20 border border-border/50 group-hover:border-purple/40 group-hover:bg-purple/5 transition-all cursor-pointer hover-lift">
                <div className="p-2.5 rounded-lg bg-purple/20 shadow-[0_0_15px_rgba(139,92,246,0.2)] group-hover:scale-110 transition-transform">
                  <Play className="w-5 h-5 text-purple" />
                </div>
                <div className="text-left flex-1">
                  <p className="text-sm font-bold text-foreground">Run Agent</p>
                  <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Trigger AI analysis</p>
                </div>
                <ArrowUpRight className="w-5 h-5 text-muted-foreground group-hover:text-purple transition-colors" />
              </div>
            </Link>
            <Link href="/backtest" className="block group">
              <div className="w-full flex items-center gap-4 p-4 rounded-xl bg-secondary/20 border border-border/50 group-hover:border-amber/40 group-hover:bg-amber/5 transition-all cursor-pointer hover-lift">
                <div className="p-2.5 rounded-lg bg-amber/20 shadow-[0_0_15px_rgba(245,158,11,0.2)] group-hover:scale-110 transition-transform">
                  <FlaskConical className="w-5 h-5 text-amber" />
                </div>
                <div className="text-left flex-1">
                  <p className="text-sm font-bold text-foreground">Run Backtest</p>
                  <p className="text-[11px] text-muted-foreground font-medium mt-0.5">Test strategy logic</p>
                </div>
                <ArrowUpRight className="w-5 h-5 text-muted-foreground group-hover:text-amber transition-colors" />
              </div>
            </Link>
          </CardContent>
        </Card>

        {/* Positions Summary */}
        <Card variant="flat">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-emerald" />
              Open Positions
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[260px] pr-3">
              {positions.length > 0 ? (
                <div className="space-y-3 stagger-children">
                  {positions.map((pos, idx) => (
                    <div
                      key={idx}
                      className="p-3.5 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 hover:border-emerald/30 transition-colors group relative overflow-hidden"
                    >
                      <div className="absolute left-0 top-0 bottom-0 w-1 bg-gradient-to-b from-emerald/40 to-cyan/40 opacity-0 group-hover:opacity-100 transition-opacity" />
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-base font-bold text-foreground font-mono tracking-tight">
                          {pos.ticker}
                        </span>
                        <Badge
                          variant={pos.pnl >= 0 ? "emerald" : "rose"}
                          className="font-mono text-xs shadow-[0_0_10px_rgba(0,0,0,0.1)]"
                        >
                          {pos.pnl >= 0 ? "+" : ""}
                          <AnimatedNumber value={pos.pnl} formatter={(v) => v.toFixed(2)} />
                        </Badge>
                      </div>
                      <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                        <span className="tabular-nums bg-background/50 px-2 py-0.5 rounded border border-border/50">Qty: {pos.amount} @ ${pos.avg_price.toFixed(2)}</span>
                        <span className="tabular-nums">Now: ${pos.current_price.toFixed(2)}</span>
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-medium">
                  <div className="text-center">
                    <Activity className="w-8 h-8 mx-auto mb-3 text-border" />
                    No open positions
                  </div>
                </div>
              )}
            </ScrollArea>
          </CardContent>
        </Card>

        {/* Live Event Feed */}
        <Card variant="flat">
          <CardHeader>
            <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
              <Activity className="w-4 h-4 text-cyan" />
              Live Event Feed
            </CardTitle>
          </CardHeader>
          <CardContent>
            <ScrollArea className="h-[260px] pr-3">
              <div className="relative border-l border-border/40 ml-3 space-y-4 pb-4 stagger-children">
                {eventFeed.length > 0 ? (
                  eventFeed.map((event) => (
                    <div
                      key={event.id}
                      className="relative pl-6 group"
                    >
                      <div className={cn("absolute -left-2 top-0.5 w-4 h-4 rounded-full border-2 border-card flex items-center justify-center bg-card shadow-[0_0_10px_rgba(0,0,0,0.5)]", 
                        event.severity === 'success' ? 'text-emerald' :
                        event.severity === 'warning' ? 'text-amber' :
                        event.severity === 'error' ? 'text-rose' : 'text-cyan'
                      )}>
                        {severityIcon[event.severity] || severityIcon.info}
                      </div>
                      <div className={cn("p-3 rounded-lg bg-secondary/10 border border-border/30 transition-colors group-hover:bg-secondary/20", severityColor[event.severity] || "border-l-cyan")}>
                        <p className="text-xs font-medium text-foreground leading-relaxed">
                          {event.message}
                        </p>
                        <div className="flex items-center gap-2 mt-2">
                          <span className={cn(
                            "text-[9px] uppercase tracking-widest font-bold px-1.5 py-0.5 rounded-sm bg-background border border-border/50",
                            event.severity === 'success' ? 'text-emerald' :
                            event.severity === 'warning' ? 'text-amber' :
                            event.severity === 'error' ? 'text-rose' : 'text-cyan'
                          )}>
                            {event.type}
                          </span>
                          <span className="text-[10px] font-mono text-muted-foreground">
                            {new Date(event.timestamp).toLocaleTimeString()}
                          </span>
                        </div>
                      </div>
                    </div>
                  ))
                ) : (
                  <div className="flex items-center justify-center h-48 text-muted-foreground text-sm font-medium">
                    <div className="text-center">
                      <Server className="w-8 h-8 mx-auto mb-3 text-border" />
                      Waiting for events...
                    </div>
                  </div>
                )}
              </div>
            </ScrollArea>
          </CardContent>
        </Card>
      </div>

      {/* Agent Overview Row */}
      <div className="animate-slide-up" style={{ animationDelay: '300ms' }}>
        <SectionHeader
          title="Agent Swarm"
          description="Live status of all deployed autonomous agents"
          action={
            <Link href="/agents">
              <Button variant="outline" size="sm" className="text-xs group border-border/50 hover:border-cyan/50 hover:text-cyan transition-colors">
                View All <ArrowUpRight className="w-3 h-3 ml-1 group-hover:translate-x-0.5 group-hover:-translate-y-0.5 transition-transform" />
              </Button>
            </Link>
          }
        />
        <div className="mt-5 w-full">
          <div className="flex overflow-x-auto snap-x snap-mandatory gap-4 pb-6 custom-scroll stagger-children">
            {loadingAgents
              ? Array.from({ length: 6 }).map((_, i) => (
                  <div key={i} className="glass-card p-5 min-w-[280px] space-y-4 snap-start shrink-0">
                    <Skeleton className="h-5 w-24" />
                    <Skeleton className="h-4 w-32" />
                    <Skeleton className="h-4 w-20" />
                  </div>
                ))
              : agents.map((agent) => (
                  <div
                    key={agent.name}
                    className="glass-card p-5 min-w-[280px] snap-start shrink-0 hover:border-cyan/40 hover:shadow-[0_0_20px_rgba(6,182,212,0.1)] transition-all hover-lift relative overflow-hidden group"
                  >
                    <div className="absolute top-0 right-0 w-16 h-16 bg-cyan/5 rounded-bl-full translate-x-8 -translate-y-8 group-hover:bg-cyan/10 transition-colors" />
                    <div className="flex items-center justify-between mb-4 relative z-10">
                      <div className="flex items-center gap-3">
                        <div className={cn("w-8 h-8 rounded-full flex items-center justify-center shadow-[inset_0_0_10px_rgba(255,255,255,0.1)]", 
                          agent.status === "active" ? "bg-emerald/20 border border-emerald/30 shadow-[0_0_10px_rgba(16,185,129,0.3)]" :
                          agent.status === "error" ? "bg-rose/20 border border-rose/30 shadow-[0_0_10px_rgba(244,63,94,0.3)]" :
                          "bg-secondary/40 border border-border/50"
                        )}>
                          <Bot className={cn("w-4 h-4", 
                            agent.status === "active" ? "text-emerald" :
                            agent.status === "error" ? "text-rose" :
                            "text-muted-foreground"
                          )} />
                        </div>
                        <span className="text-sm font-bold text-foreground">
                          {agent.name}
                        </span>
                      </div>
                      <StatusBadge status={agent.status} />
                    </div>
                    <div className="text-xs text-muted-foreground space-y-2.5 font-medium relative z-10">
                      <div className="flex justify-between items-center bg-secondary/10 px-2 py-1.5 rounded border border-border/30">
                        <span>Role</span>
                        <span className="text-foreground">{agent.role || "—"}</span>
                      </div>
                      <div className="flex justify-between items-center bg-secondary/10 px-2 py-1.5 rounded border border-border/30">
                        <span>Registered</span>
                        <span className={agent.registered ? "text-emerald" : "text-muted-foreground"}>
                          {agent.registered ? "Verified" : "Pending"}
                        </span>
                      </div>
                    </div>
                  </div>
                ))}
          </div>
        </div>
      </div>

      {/* System Health */}
      <div className="animate-slide-up" style={{ animationDelay: '400ms' }}>
        <SectionHeader
          title="System Core"
          description="Infrastructure health and connection status"
        />
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mt-5 stagger-children">
          <div className="glass-card p-5 border-l-4 border-l-cyan relative overflow-hidden group hover:border-cyan/50 transition-colors">
            <div className="absolute right-0 bottom-0 w-24 h-24 bg-cyan/5 rounded-tl-full translate-x-10 translate-y-10 group-hover:bg-cyan/10 transition-colors" />
            <div className="flex items-center justify-between mb-3 relative z-10">
              <div className="flex items-center gap-2">
                <Server className="w-4 h-4 text-cyan" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">API Server</span>
              </div>
              <StatusBadge
                status={systemHealth?.status === "healthy" ? "active" : "error"}
                size="sm"
              />
            </div>
            <p className="text-lg font-black text-foreground relative z-10 font-mono tracking-tight">
              {systemHealth?.service || "—"}
            </p>
          </div>
          
          <div className="glass-card p-5 border-l-4 border-l-purple relative overflow-hidden group hover:border-purple/50 transition-colors">
            <div className="absolute right-0 bottom-0 w-24 h-24 bg-purple/5 rounded-tl-full translate-x-10 translate-y-10 group-hover:bg-purple/10 transition-colors" />
            <div className="flex items-center justify-between mb-3 relative z-10">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-purple" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Kill Switch</span>
              </div>
              <StatusBadge
                status={killSwitch?.is_active ? "HALT" : "OK"}
                size="sm"
              />
            </div>
            <p className={cn("text-lg font-black relative z-10 tracking-tight", killSwitch?.is_active ? "text-rose drop-shadow-[0_0_10px_rgba(244,63,94,0.5)]" : "text-foreground")}>
              {killSwitch?.is_active ? "TRADING HALTED" : "Trading Active"}
            </p>
          </div>
          
          <div className="glass-card p-5 border-l-4 border-l-emerald relative overflow-hidden group hover:border-emerald/50 transition-colors">
            <div className="absolute right-0 bottom-0 w-24 h-24 bg-emerald/5 rounded-tl-full translate-x-10 translate-y-10 group-hover:bg-emerald/10 transition-colors" />
            <div className="flex items-center justify-between mb-3 relative z-10">
              <div className="flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald" />
                <span className="text-xs font-bold uppercase tracking-widest text-muted-foreground">Risk Status</span>
              </div>
              <StatusBadge status={riskStatus} size="sm" />
            </div>
            <p className="text-lg font-black text-foreground relative z-10 tracking-tight">
              {portfolioRisk?.risk_status === "OK"
                ? "All checks passing"
                : "Limits exceeded"}
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
