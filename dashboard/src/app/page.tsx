"use client";

import { useEffect, useState, useCallback } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { useAppStore } from "@/lib/store";
import { apiRequest, agentsApi, portfolioApi, marketApi, brokersApi, schedulerApi } from "@/lib/api-client";
import type { MarketSentiment, BrokerAccount, MT5AccountInfo, SchedulerStatus } from "@/lib/api-client";
import { useRealtimeData } from "@/lib/websocket";
import { ErrorBoundary, ErrorDisplay } from "@/components/shared/error-boundary";
import {
  Activity, Wallet, TrendingUp, Bot, Radio, Shield, RefreshCw,
  Wifi, WifiOff, GitBranch, Building2, Play, Square, Clock,
  ArrowUp, ArrowDown, ArrowLeftRight, ArrowRight, BarChart3, Briefcase, Globe, Cpu, Zap,
} from "lucide-react";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";

function DashboardContent() {
  const {
    killSwitch, agents, portfolio, realtimePrices, realtimeRegime,
    realtimePortfolio, wsConnected, loadingStates, sidebarOpen,
    fetchAgents, fetchPortfolio, refreshAll,
  } = useAppStore();

  const { connectionError } = useRealtimeData();
  const [mkt, setMkt] = useState<MarketSentiment | null>(null);
  const [mktError, setMktError] = useState<string | null>(null);
  const [initialLoading, setInitialLoading] = useState(true);
  const [brokers, setBrokers] = useState<BrokerAccount[]>([]);
  const [scheduler, setScheduler] = useState<SchedulerStatus | null>(null);
  const [time, setTime] = useState(new Date());

  // Clock tick
  useEffect(() => {
    const id = setInterval(() => setTime(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  // Initial data load
  useEffect(() => {
    (async () => {
      await Promise.allSettled([
        fetchAgents(),
        fetchPortfolio(),
        marketApi.getSentiment().then(setMkt).catch(e => setMktError(e.message)),
        brokersApi.list().then(r => setBrokers(r.accounts)).catch(() => {}),
        schedulerApi.getStatus().then(setScheduler).catch(() => {}),
      ]);
      setInitialLoading(false);
    })();
  }, [fetchAgents, fetchPortfolio]);

  // Auto-refresh
  useEffect(() => {
    const interval = setInterval(() => refreshAll(), 30000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const handleRetry = useCallback(() => {
    refreshAll();
    marketApi.getSentiment().then(setMkt).catch(e => setMktError(e.message));
    brokersApi.list().then(r => setBrokers(r.accounts)).catch(() => {});
  }, [refreshAll]);

  // Derived data
  const activeAgents = agents.filter((a: any) => a.status === "active").length;
  const portfolioValue = realtimePortfolio?.total_value ?? portfolio?.total_value ?? 0;
  const dailyPnl = realtimePortfolio?.daily_pnl ?? portfolio?.unrealized_pnl ?? 0;
  const brokerCount = brokers.length;
  const connectedBrokers = brokers.filter(b => b.connected).length;

  // Market regime
  const regimeStr = realtimeRegime?.market
    ? realtimeRegime.market.charAt(0).toUpperCase() + realtimeRegime.market.slice(1)
    : mkt?.fear_greed != null
      ? mkt.fear_greed >= 60 ? "Bullish" : mkt.fear_greed >= 40 ? "Neutral" : "Bearish"
      : "—";
  const regimeVariant = regimeStr === "Bullish" ? "success" as const
    : regimeStr === "Bearish" ? "danger" as const
    : "warning" as const;

  // Price ticker data
  const tickerSymbols = Object.keys(realtimePrices).length > 0
    ? Object.entries(realtimePrices).slice(0, 12)
    : [];

  // Pipeline overview stats
  const pipelineStages = loadingStates.health.lastUpdated ? "15/15" : "—";

  if (initialLoading) {
    return (
      <div className="space-y-4 animate-pulse">
        <div className="space-y-2">
          <div className="h-8 w-64 rounded-xl bg-white/5" />
          <div className="h-4 w-48 rounded-lg bg-white/3" />
        </div>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {[1,2,3,4].map(i => (
            <div key={i} className="h-28 rounded-xl bg-white/3 skeleton-pulse" />
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* ── Header Row ──────────────────────────────────────────── */}
      <div className="flex items-center justify-between flex-wrap gap-3 stagger-1">
        <div>
          <span className="eyebrow">Command Center</span>
          <h1 className="text-2xl font-bold text-white">
            Quant Nanggroe
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            Autonomous hedge-fund pipeline • {time.toLocaleTimeString()}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full bg-white/[0.04] border border-white/[0.06]">
            <div className={cn("w-1.5 h-1.5 rounded-full", wsConnected ? "bg-emerald-500 shadow-[0_0_6px_rgba(16,185,129,0.5)] animate-pulse" : "bg-amber-500")} />
            <span className="text-[10px] font-mono font-medium text-white/50">
              {wsConnected ? "LIVE" : connectionError ? "RECONNECT" : "OFFLINE"}
            </span>
          </div>
          <Badge variant={killSwitch ? "danger" : "success"} className="text-[10px] flex items-center gap-1">
            <Shield className="w-3 h-3" />
            {killSwitch ? "HALTED" : "OPERATIONAL"}
          </Badge>
          <Button variant="ghost" size="icon" className="h-7 w-7" onClick={handleRetry}>
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* ── Live Price Ticker ───────────────────────────────────── */}
      {tickerSymbols.length > 0 && (
        <div className="stagger-2">
          <div className="double-bezel p-2">
            <div className="ticker-tape">
              <div className="ticker-tape-inner">
                {[...tickerSymbols, ...tickerSymbols].map(([symbol, data], i) => (
                  <div key={i} className="flex items-center gap-3 shrink-0">
                    <span className="text-xs font-medium text-white/70">{symbol}</span>
                    <span className="text-xs font-mono text-white">
                      ${(data as any).price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                    </span>
                    <span className={cn(
                      "text-[10px] font-mono flex items-center gap-0.5",
                      (data as any).change_24h >= 0 ? "text-profit" : "text-loss"
                    )}>
                      {(data as any).change_24h >= 0 ? <ArrowUp className="w-2.5 h-2.5" /> : <ArrowDown className="w-2.5 h-2.5" />}
                      {Math.abs((data as any).change_24h).toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Connection error banner */}
      {connectionError && (
        <div className="stagger-2 flex items-center gap-2 px-3 py-2 rounded-xl bg-amber-500/10 border border-amber-500/20">
          <WifiOff className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
          <p className="text-xs text-amber-200/80">{connectionError}</p>
          <Button variant="ghost" size="icon" className="h-6 w-6 ml-auto" onClick={handleRetry}>
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      )}

      {/* ── Premium Metric Cards (Staggered Entry) ──────────────── */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {([
          { title: "Portfolio", value: portfolioValue, change: dailyPnl, icon: Wallet, variant: portfolioValue > 0 ? "success" as const : "default" as const, format: "currency" as const },
          { title: "Day P&L", value: dailyPnl, change: portfolio?.total_value ? (dailyPnl / portfolio.total_value) * 100 : undefined, icon: TrendingUp, variant: dailyPnl >= 0 ? "success" as const : "danger" as const, format: "currency" as const },
          { title: "Active Agents", value: `${activeAgents}/${agents.length || 0}`, icon: Bot, variant: activeAgents > 0 ? "success" as const : "default" as const, format: "text" as const },
          { title: "Market Regime", value: regimeStr, icon: Radio, variant: regimeVariant, format: "text" as const },
        ]).map((card: any, i) => (
          <div key={card.title} className={`stagger-${i + 3}`}>
            <Card className="relative overflow-hidden group p-4 transition-all duration-300 hover:-translate-y-0.5">
              <div className="absolute inset-0 bg-gradient-to-br from-white/[0.02] to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none" />
              <div className="relative z-10">
                <div className="flex items-start justify-between mb-2">
                  <p className="text-[10px] font-medium uppercase tracking-[0.1em] text-white/30">{card.title}</p>
                  <div className="p-1.5 rounded-lg bg-white/[0.04] text-white/30 group-hover:text-white/50 transition-colors">
                    <card.icon className="w-4 h-4" />
                  </div>
                </div>
                <p className="text-xl font-mono font-bold tracking-tight text-white">
                  {typeof card.value === "number" && card.format === "currency"
                    ? formatCurrency(card.value)
                    : card.value}
                </p>
                {card.change !== undefined && (
                  <div className="flex items-center gap-1 mt-1">
                    {card.change > 0
                      ? <ArrowUp className="w-3 h-3 text-profit" />
                      : card.change < 0
                        ? <ArrowDown className="w-3 h-3 text-loss" />
                        : null}
                    <span className={cn("text-xs font-mono font-medium", card.change >= 0 ? "text-profit" : "text-loss")}>
                      {card.change > 0 ? "+" : ""}{card.change.toFixed(2)}%
                    </span>
                  </div>
                )}
              </div>
            </Card>
          </div>
        ))}
      </div>

      {/* ── Bento Grid: Pipeline + Brokers + System ─────────────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Pipeline Overview */}
        <div className="lg:col-span-2 stagger-5">
          <Card className="p-5">
            <CardHeader>
              <div>
                <CardTitle>Pipeline Overview</CardTitle>
                <CardDescription>15-stage autonomous trading pipeline</CardDescription>
              </div>
              <Badge variant="success" size="sm" pulse={scheduler?.running}>
                <Activity className="w-3 h-3 mr-1" />
                {scheduler?.running ? "RUNNING" : "STANDBY"}
              </Badge>
            </CardHeader>
            <CardContent>
              {/* Pipeline flow visualization */}
              <div className="flex flex-wrap items-center gap-2 mb-4">
                {["Data", "Regime", "AIHF", "HF", "Strat", "Filter", "Vote", "Council", "Risk", "Decide", "Exec", "Log", "Eval", "Evolve"].map((stage, i, arr) => (
                  <div key={stage} className="flex items-center gap-2">
                    <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-emerald-500/8 border border-emerald-500/15">
                      <span className="text-[9px] font-mono text-emerald-400/80">{String(i + 1).padStart(2, "0")}</span>
                      <span className="text-[10px] font-medium text-white/70">{stage}</span>
                    </div>
                    {i < arr.length - 1 && (
                      <ArrowRight className="w-3 h-3 text-white/15" />
                    )}
                  </div>
                ))}
              </div>

              {/* Pipeline controls */}
              <div className="flex items-center gap-3">
                <Button
                  variant="glass"
                  size="sm"
                  className="h-8 text-[11px]"
                  onClick={async () => {
                    try {
                      if (scheduler?.running) {
                        await schedulerApi.stop();
                      } else {
                        await schedulerApi.start(30, ["BTC-USD", "ETH-USD"]);
                      }
                      const s = await schedulerApi.getStatus();
                      setScheduler(s);
                    } catch {}
                  }}
                >
                  {scheduler?.running ? (
                    <><Square className="w-3 h-3 mr-1.5" /> Stop Pipeline</>
                  ) : (
                    <><Play className="w-3 h-3 mr-1.5" /> Run Pipeline</>
                  )}
                </Button>
                {scheduler?.interval_minutes && (
                  <span className="text-[10px] text-white/30 font-mono flex items-center gap-1">
                    <Clock className="w-3 h-3" />
                    Every {scheduler.interval_minutes}m
                  </span>
                )}
                <span className="text-[10px] text-white/20 font-mono ml-auto">
                  Stages: {pipelineStages}
                </span>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Broker Status */}
        <div className="stagger-6">
          <Card className="p-5">
            <CardHeader>
              <div>
                <CardTitle>Broker Status</CardTitle>
                <CardDescription>
                  {brokerCount} account{brokerCount !== 1 ? "s" : ""} • {connectedBrokers} connected
                </CardDescription>
              </div>
              <Building2 className="w-4 h-4 text-white/30" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {brokers.length === 0 ? (
                  <p className="text-xs text-white/20 py-4 text-center">No brokers configured</p>
                ) : (
                  brokers.slice(0, 5).map((b, i) => (
                    <div key={b.name} className={`flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04] stagger-${Math.min(i + 1, 5)}`}>
                      <div className="flex items-center gap-2.5">
                        <div className={cn("w-2 h-2 rounded-full", b.connected ? "bg-profit shadow-[0_0_6px_rgba(52,211,153,0.4)]" : "bg-white/20")} />
                        <div>
                          <p className="text-xs font-medium text-white/70">{b.name}</p>
                          <p className="text-[10px] text-white/30">{b.role}</p>
                        </div>
                      </div>
                      <Badge variant={b.connected ? "success" : "warning"} size="sm" className="text-[9px]">
                        {b.connected ? "ONLINE" : "OFFLINE"}
                      </Badge>
                    </div>
                  ))
                )}
                {brokers.length > 5 && (
                  <p className="text-[10px] text-white/20 text-center pt-1">+{brokers.length - 5} more</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>

      {/* ── Second Bento Row: System Health + Quick Actions ─────── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* System Health */}
        <div className="stagger-7">
          <Card className="p-5">
            <CardHeader>
              <div>
                <CardTitle>System Health</CardTitle>
                <CardDescription>Service status overview</CardDescription>
              </div>
              <Cpu className="w-4 h-4 text-white/30" />
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {[
                  { label: "Engine", icon: Activity, color: "text-emerald-400", status: "ONLINE" as const },
                  { label: "Agents", icon: Bot, color: "text-cyan-400", status: activeAgents > 0 ? "success" as const : "warning" as const, detail: `${activeAgents} active` },
                  { label: "WebSocket", icon: Wifi, color: wsConnected ? "text-emerald-400" : "text-amber-400", status: wsConnected ? "success" as const : "warning" as const, detail: wsConnected ? "CONNECTED" : "RECONNECT" },
                  { label: "Pipeline", icon: GitBranch, color: "text-violet-400", status: scheduler?.running ? "success" as const : "warning" as const, detail: scheduler?.running ? "ACTIVE" : "STANDBY" },
                  { label: "Regime", icon: Radio, color: "text-purple-400", status: regimeVariant, detail: `${regimeStr}${realtimeRegime?.confidence ? ` (${Math.round(realtimeRegime.confidence * 100)}%)` : ""}` },
                ].map((svc) => (
                  <div key={svc.label} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                    <span className="text-xs text-white/60 flex items-center gap-2">
                      <svc.icon className={cn("w-3.5 h-3.5", svc.color)} />
                      {svc.label}
                    </span>
                    <div className="flex items-center gap-2">
                      {svc.detail && <span className="text-[10px] text-white/30 font-mono">{svc.detail}</span>}
                      <Badge variant={
                        svc.status === "ONLINE" || svc.status === "success" ? "success"
                        : "warning"
                      } size="sm" className="text-[9px]">
                        {svc.status === "ONLINE" ? "ONLINE" : svc.detail?.split(" ")[0] || svc.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Error Displays */}
        <div className="lg:col-span-2 stagger-8 space-y-2">
          {loadingStates.agents.error && (
            <ErrorDisplay error={loadingStates.agents.error} onRetry={fetchAgents} title="Agents unavailable" />
          )}
          {loadingStates.portfolio.error && (
            <ErrorDisplay error={loadingStates.portfolio.error} onRetry={fetchPortfolio} title="Portfolio unavailable" />
          )}
          {mktError && (
            <ErrorDisplay error={mktError} onRetry={handleRetry} title="Market data unavailable" />
          )}

          {/* If no errors, show quick nav grid */}
          {!loadingStates.agents.error && !loadingStates.portfolio.error && !mktError && (
            <Card className="p-5">
              <CardHeader>
                <div>
                  <CardTitle>Quick Actions</CardTitle>
                  <CardDescription>Navigate modules</CardDescription>
                </div>
                <Zap className="w-4 h-4 text-white/30" />
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
                  {[
                    { name: "Trading", href: "/trading", icon: ArrowLeftRight, desc: "Live orders & positions" },
                    { name: "Portfolio", href: "/portfolio", icon: Briefcase, desc: "Cross-broker view" },
                    { name: "Risk", href: "/risk", icon: Shield, desc: "VaR, Kelly, drawdown" },
                    { name: "Agents", href: "/agents", icon: Bot, desc: "Council & pipeline" },
                    { name: "Backtest", href: "/backtest", icon: BarChart3, desc: "Strategy testing" },
                    { name: "Pipeline", href: "/pipeline", icon: GitBranch, desc: "15-stage flow" },
                    { name: "Brokers", href: "/brokers", icon: Building2, desc: "MT5 accounts" },
                    { name: "Settings", href: "/settings", icon: Activity, desc: "Config & keys" },
                  ].map((item) => (
                    <a
                      key={item.href}
                      href={item.href}
                      className="group flex flex-col items-center gap-1 p-3 rounded-xl bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200 text-center"
                    >
                      <item.icon className="w-4 h-4 text-white/40 group-hover:text-emerald-400 transition-colors" />
                      <span className="text-xs font-medium text-white/70 group-hover:text-white transition-colors">{item.name}</span>
                      <span className="text-[9px] text-white/20">{item.desc}</span>
                    </a>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>
      </div>

      {/* ── Live Prices Panel ───────────────────────────────────── */}
      {tickerSymbols.length > 0 && (
        <div className="stagger-9">
          <Card className="p-5">
            <CardHeader>
              <div>
                <CardTitle>Live Prices</CardTitle>
                <CardDescription>Real-time market data</CardDescription>
              </div>
              <Badge variant="success" size="sm" pulse>
                <Wifi className="w-3 h-3 mr-1" />
                WS LIVE
              </Badge>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-2">
                {tickerSymbols.map(([symbol, data]: [string, any]) => (
                  <div key={symbol} className="bbg-cell flex items-center justify-between">
                    <div>
                      <p className="text-[11px] font-medium text-white/70">{symbol}</p>
                      <p className="text-[10px] text-white/30">Vol: {(data as any).change_24h ? `${(Math.abs(data as any).toFixed(0))}` : "—"}</p>
                    </div>
                    <div className="text-right">
                      <p className="text-xs font-mono text-white font-medium">
                        ${Number(data.price).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                      </p>
                      <p className={cn("text-[10px] font-mono", data.change_24h >= 0 ? "text-profit" : "text-loss")}>
                        {data.change_24h >= 0 ? "+" : ""}{data.change_24h.toFixed(2)}%
                      </p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      )}

      {/* Footer refresh indicator */}
      {loadingStates.agents.loading && (
        <p className="text-[10px] text-white/20 animate-pulse text-center">Refreshing data...</p>
      )}
    </div>
  );
}

export default function HomePage() {
  return (
    <ErrorBoundary>
      <DashboardContent />
    </ErrorBoundary>
  );
}
