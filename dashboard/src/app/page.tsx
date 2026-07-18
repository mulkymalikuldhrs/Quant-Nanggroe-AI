"use client";

import { useEffect, useState, useCallback } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useAppStore } from "@/lib/store";
import { agentsApi, portfolioApi, marketApi, type Agent, type MarketSentiment } from "@/lib/api-client";
import { SchedulerControls } from "@/components/scheduler-controls";
import { useRealtimeData } from "@/lib/websocket";
import { ErrorBoundary, ErrorDisplay } from "@/components/shared/error-boundary";
import { PageSkeleton, StatusCardSkeleton } from "@/components/shared/loading-skeleton";
import { Activity, Wallet, TrendingUp, Bot, Radio, Shield, RefreshCw, Wifi, WifiOff } from "lucide-react";

function DashboardContent() {
  const {
    killSwitch,
    agents,
    portfolio,
    realtimePrices,
    realtimeRegime,
    realtimePortfolio,
    wsConnected,
    loadingStates,
    fetchAgents,
    fetchPortfolio,
    refreshAll,
  } = useAppStore();

  const { connectionError } = useRealtimeData();
  const [mkt, setMkt] = useState<MarketSentiment | null>(null);
  const [mktError, setMktError] = useState<string | null>(null);
  const [mktLoading, setMktLoading] = useState(true);
  const [initialLoading, setInitialLoading] = useState(true);

  // Initial data load
  useEffect(() => {
    (async () => {
      await Promise.allSettled([
        fetchAgents(),
        fetchPortfolio(),
        (async () => {
          try {
            const data = await marketApi.getSentiment();
            setMkt(data);
            setMktError(null);
          } catch (err) {
            setMktError(err instanceof Error ? err.message : "Failed to load market data");
          }
        })(),
      ]);
      setInitialLoading(false);
      setMktLoading(false);
    })();
  }, [fetchAgents, fetchPortfolio]);

  // Auto-refresh every 30 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      refreshAll();
    }, 30000);
    return () => clearInterval(interval);
  }, [refreshAll]);

  const handleRetry = useCallback(() => {
    refreshAll();
    setMktLoading(true);
    marketApi.getSentiment()
      .then((data) => { setMkt(data); setMktError(null); })
      .catch((err) => { setMktError(err.message); })
      .finally(() => setMktLoading(false));
  }, [refreshAll]);

  // Derived data
  const activeAgents = agents.filter((a) => a.status === "active").length;

  // Real-time data (falls back to REST data)
  const portfolioValue = realtimePortfolio?.total_value ?? portfolio?.total_value ?? 0;
  const dailyPnl = realtimePortfolio?.daily_pnl ?? portfolio?.unrealized_pnl ?? 0;
  const dailyPnlPercent = portfolio?.total_value
    ? (dailyPnl / portfolio.total_value) * 100
    : undefined;
  const marketRegime = realtimeRegime?.market ?? mkt?.fear_greed ?? null;
  const regimeLabel =
    marketRegime !== null
      ? typeof marketRegime === "string"
        ? marketRegime.charAt(0).toUpperCase() + marketRegime.slice(1)
        : marketRegime >= 60
          ? "Bullish"
          : marketRegime >= 40
            ? "Neutral"
            : "Bearish"
      : "—";
  const regimeVariant =
    regimeLabel === "Bullish"
      ? "success"
      : regimeLabel === "Bearish"
        ? "danger"
        : "warning";

  // Loading state
  const agentsLoading = loadingStates.agents.loading;
  const portfolioLoading = loadingStates.portfolio.loading;

  // Error states
  const agentsError = loadingStates.agents.error;
  const portfolioError = loadingStates.portfolio.error;

  if (initialLoading) {
    return <PageSkeleton />;
  }

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-white">Quant Nanggroe</h1>
          <p className="text-sm text-white/40">Autonomous hedge-fund command center</p>
        </div>
        <div className="flex items-center gap-2">
          {/* Connection status */}
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            {wsConnected ? (
              <>
                <Wifi className="w-3 h-3 text-emerald-400" />
                <span className="text-[10px] text-emerald-400 font-medium">LIVE</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3 h-3 text-white/30" />
                <span className="text-[10px] text-white/30 font-medium">
                  {connectionError ? "RECONNECTING" : "OFFLINE"}
                </span>
              </>
            )}
          </div>

          {/* Kill switch badge */}
          <Badge
            variant={killSwitch ? "danger" : "success"}
            className="text-[11px] flex items-center gap-1"
          >
            <Shield className="w-3 h-3" />
            {killSwitch ? "HALTED" : "LIVE"}
          </Badge>

          {/* Refresh button */}
          <Button
            variant="ghost"
            size="icon"
            className="h-7 w-7"
            onClick={handleRetry}
            title="Refresh all data"
          >
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Connection error banner */}
      {connectionError && (
        <div className="flex items-center gap-2 px-3 py-2 rounded-lg bg-amber-500/10 border border-amber-500/20">
          <WifiOff className="w-3.5 h-3.5 text-amber-400 flex-shrink-0" />
          <p className="text-xs text-amber-200/80">{connectionError}</p>
          <Button
            variant="ghost"
            size="icon"
            className="h-6 w-6 ml-auto"
            onClick={handleRetry}
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        </div>
      )}

      {/* Metric Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        {portfolioLoading && !portfolio ? (
          <>
            <StatusCardSkeleton />
            <StatusCardSkeleton />
            <StatusCardSkeleton />
            <StatusCardSkeleton />
          </>
        ) : (
          <>
            <StatusCard
              title="Portfolio Value"
              value={portfolioValue}
              icon={<Wallet className="w-4 h-4" />}
              variant={portfolioValue > 0 ? "success" : "default"}
            />
            <StatusCard
              title="Day P&L"
              value={dailyPnl}
              change={dailyPnlPercent}
              icon={<TrendingUp className="w-4 h-4" />}
              variant={dailyPnl >= 0 ? "success" : "danger"}
            />
            <StatusCard
              title="Active Agents"
              value={agentsLoading && !agents.length ? "..." : `${activeAgents}/${agents.length}`}
              icon={<Bot className="w-4 h-4" />}
            />
            <StatusCard
              title="Market Regime"
              value={regimeLabel}
              icon={<Radio className="w-4 h-4" />}
              variant={regimeVariant as "success" | "danger" | "warning"}
            />
          </>
        )}
      </div>

      {/* Error displays */}
      <div className="space-y-2">
        {agentsError && (
          <ErrorDisplay
            error={agentsError}
            onRetry={fetchAgents}
            title="Agents unavailable"
          />
        )}
        {portfolioError && (
          <ErrorDisplay
            error={portfolioError}
            onRetry={fetchPortfolio}
            title="Portfolio data unavailable"
          />
        )}
        {mktError && (
          <ErrorDisplay
            error={mktError}
            onRetry={handleRetry}
            title="Market data unavailable"
          />
        )}
      </div>

      {/* Scheduler Controls */}
      <SchedulerControls />

      {/* System Health & Quick Nav */}
      <div className="grid md:grid-cols-2 gap-4">
        <ChartCard title="System Health" subtitle="Live overview">
          <div className="space-y-2">
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald-400" /> Engine
              </span>
              <Badge variant="success" className="text-[10px]">ONLINE</Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2">
                <Bot className="w-4 h-4 text-cyan-400" /> Agents
              </span>
              <Badge
                variant={activeAgents > 0 ? "success" : "warning"}
                className="text-[10px]"
              >
                {agentsLoading ? "..." : `${activeAgents} active`}
              </Badge>
            </div>
            <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
              <span className="text-sm text-white/70 flex items-center gap-2">
                <Wifi className={`w-4 h-4 ${wsConnected ? "text-emerald-400" : "text-white/30"}`} />{" "}
                WebSocket
              </span>
              <Badge
                variant={wsConnected ? "success" : "warning"}
                className="text-[10px]"
              >
                {wsConnected ? "CONNECTED" : "RECONNECTING"}
              </Badge>
            </div>
            {realtimeRegime && (
              <div className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]">
                <span className="text-sm text-white/70 flex items-center gap-2">
                  <Radio className="w-4 h-4 text-purple-400" /> Regime
                </span>
                <Badge variant={regimeVariant as "success" | "danger" | "warning"} className="text-[10px]">
                  {realtimeRegime.market.toUpperCase()} ({Math.round(realtimeRegime.confidence * 100)}%)
                </Badge>
              </div>
            )}
          </div>
        </ChartCard>

        <ChartCard title="Quick Nav" subtitle="Modules">
          <div className="grid grid-cols-2 gap-2">
            {[
              ["Trading", "/trading"], ["Portfolio", "/portfolio"], ["Risk", "/risk"],
              ["Backtest", "/backtest"], ["Agents", "/agents"], ["Memory", "/memory"],
              ["Market", "/market"], ["Colony", "/colony"],
            ].map(([name, href]) => (
              <a
                key={href}
                href={href}
                className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] text-sm text-white/80 hover:bg-white/[0.05] hover:border-white/[0.08] transition-all duration-200"
              >
                {name}
              </a>
            ))}
          </div>
        </ChartCard>
      </div>

      {/* Real-time data indicators */}
      {Object.keys(realtimePrices).length > 0 && (
        <ChartCard title="Live Prices" subtitle="Real-time WebSocket">
          <div className="space-y-1">
            {Object.entries(realtimePrices).map(([symbol, data]) => (
              <div
                key={symbol}
                className="flex items-center justify-between p-2 rounded bg-white/[0.02] border border-white/[0.04]"
              >
                <span className="text-sm font-mono text-white/80">{symbol}</span>
                <div className="flex items-center gap-3">
                  <span className="text-sm font-mono text-white font-medium">
                    ${data.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}
                  </span>
                  <span
                    className={`text-xs font-mono ${
                      data.change_24h >= 0 ? "text-emerald-400" : "text-red-400"
                    }`}
                  >
                    {data.change_24h >= 0 ? "+" : ""}
                    {data.change_24h.toFixed(2)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </ChartCard>
      )}

      {/* Subtle loading indicator for background refreshes */}
      {loadingStates.agents.loading && (
        <p className="text-[10px] text-white/20 animate-pulse text-center">
          Refreshing data...
        </p>
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
