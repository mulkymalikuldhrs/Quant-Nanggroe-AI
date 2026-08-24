"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn } from "@/lib/utils";
import { Activity, RefreshCw, Zap, Clock, TrendingUp, AlertTriangle, Flame, Filter } from "lucide-react";

interface CandleEvent {
  symbol: string;
  timeframe: string;
  timestamp: string;
  signal: string;
  confidence: number;
  traded: boolean;
  notified: boolean;
  error: string | null;
  duration_ms: number;
}

interface SchedulerStatus {
  running: boolean;
  symbols: string[];
  timeframes: string[];
  total_events: number;
  last_event: string | null;
  uptime_seconds: number;
}

interface TfPerf {
  total: number;
  traded: number;
  avg_confidence: number;
  signals: { buy: number; sell: number; hold: number };
}

const TF_COLORS: Record<string, string> = {
  M15: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  H1: "bg-purple-500/20 text-purple-400 border-purple-500/30",
  H4: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  D1: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
};

const SIGNAL_COLORS: Record<string, string> = {
  buy: "bg-emerald-500/20 text-emerald-400",
  sell: "bg-red-500/20 text-red-400",
  hold: "bg-slate-500/20 text-slate-400",
};

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)}ms`;
  return `${(ms / 1000).toFixed(1)}s`;
}

function formatUptime(seconds: number): string {
  if (seconds < 60) return `${seconds}s`;
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ${seconds % 60}s`;
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

interface SymbolPerf {
  total: number;
  traded: number;
  signals: { buy: number; sell: number; hold: number };
  avg_confidence: number;
}

interface Pagination {
  page: number;
  limit: number;
  total: number;
  pages: number;
}

function CandleMonitorContent() {
  const [data, setData] = useState<{ status: SchedulerStatus; events: CandleEvent[]; tf_performance: Record<string, TfPerf>; symbol_performance: Record<string, SymbolPerf>; pagination: Pagination } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filterSymbol, setFilterSymbol] = useState<string>("");
  const [filterTf, setFilterTf] = useState<string>("");

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), limit: "50" });
      if (filterSymbol) params.set("symbol", filterSymbol);
      if (filterTf) params.set("timeframe", filterTf);
      const res = await fetch(`/api/candle-monitor?${params}`, { cache: "no-store" });
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    load();
    const iv = setInterval(load, 5000);
    return () => clearInterval(iv);
  }, [page, filterSymbol, filterTf]);

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-8 w-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
            <Flame className="h-4 w-4 text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Candle Monitor</h1>
            <p className="text-sm text-muted-foreground">Real-time candle close events</p>
          </div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 rounded-xl bg-muted/30 animate-pulse" />
        ))}
      </div>
    );
  }

  const status = data?.status;
  const events = data?.events ?? [];
  const tfPerf = data?.tf_performance ?? {};

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-amber-500/20 flex items-center justify-center">
            <Flame className="h-4 w-4 text-amber-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Candle Monitor</h1>
            <p className="text-sm text-muted-foreground">Real-time candle close events across all timeframes</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={status?.running ? "default" : "danger"} className="gap-1">
            <span className={cn("h-2 w-2 rounded-full", status?.running ? "bg-emerald-400 animate-pulse" : "bg-red-400")} />
            {status?.running ? "RUNNING" : "STOPPED"}
          </Badge>
          <Button variant="outline" size="sm" onClick={load}>
            <RefreshCw className="h-4 w-4" />
          </Button>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Status Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Activity className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Events</span>
            </div>
            <div className="text-2xl font-bold">{status?.total_events ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Symbols</span>
            </div>
            <div className="text-2xl font-bold">{status?.symbols?.length ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Uptime</span>
            </div>
            <div className="text-2xl font-bold">{formatUptime(status?.uptime_seconds ?? 0)}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Timeframes</span>
            </div>
            <div className="flex gap-1 mt-1">
              {(status?.timeframes ?? []).map((tf) => (
                <Badge key={tf} variant="info" className={cn("text-xs", TF_COLORS[tf])}>
                  {tf}
                </Badge>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* TF Performance */}
      {Object.keys(tfPerf).length > 0 && (
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Timeframe Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {Object.entries(tfPerf).map(([tf, perf]) => (
                <div key={tf} className={cn("rounded-lg border p-3", TF_COLORS[tf])}>
                  <div className="font-bold text-lg">{tf}</div>
                  <div className="text-xs opacity-70 mt-1">
                    {perf.total} events | {perf.traded} trades
                  </div>
                  <div className="text-xs opacity-70">
                    Avg conf: {(perf.avg_confidence * 100).toFixed(0)}%
                  </div>
                  <div className="flex gap-2 mt-2 text-xs">
                    <span className="text-emerald-400">↑{perf.signals.buy}</span>
                    <span className="text-red-400">↓{perf.signals.sell}</span>
                    <span className="text-slate-400">—{perf.signals.hold}</span>
                  </div>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Symbol Performance */}
      {data?.symbol_performance && Object.keys(data.symbol_performance).length > 0 && (
        <Card className="border-border/50 bg-card/50">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm font-medium">Per-Symbol Performance</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
              {Object.entries(data.symbol_performance).map(([sym, perf]) => (
                <button
                  key={sym}
                  onClick={() => setFilterSymbol(filterSymbol === sym ? "" : sym)}
                  className={cn(
                    "rounded-lg border p-3 text-left transition-colors",
                    filterSymbol === sym ? "border-blue-500 bg-blue-500/10" : "border-border/30 hover:bg-muted/30"
                  )}
                >
                  <div className="font-mono text-sm font-medium">{sym}</div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {perf.total} events | {perf.traded} trades
                  </div>
                  <div className="text-xs text-muted-foreground">
                    Avg: {(perf.avg_confidence * 100).toFixed(0)}%
                  </div>
                </button>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Filters */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {["", "M15", "H1", "H4", "D1"].map((tf) => (
          <Button
            key={tf}
            variant={filterTf === tf ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterTf(tf)}
            className="text-xs"
          >
            {tf || "All TFs"}
          </Button>
        ))}
        {filterSymbol && (
          <Badge variant="info" className="gap-1">
            {filterSymbol}
            <button onClick={() => setFilterSymbol("")} className="ml-1 hover:text-white">×</button>
          </Badge>
        )}
      </div>

      {/* Recent Events */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Candle Close Events</CardTitle>
          <CardDescription className="text-xs">
            {data?.pagination?.total ?? 0} total events | Page {data?.pagination?.page ?? 1}/{data?.pagination?.pages ?? 1} | Auto-refreshing every 5s
          </CardDescription>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Flame className="h-8 w-8 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No candle close events yet</p>
              <p className="text-xs mt-1">Start the daemon to begin monitoring</p>
            </div>
          ) : (
            <div className="space-y-2">
              {events.map((ev, i) => (
                <div
                  key={`${ev.timestamp}-${i}`}
                  className="flex items-center gap-3 rounded-lg border border-border/30 p-3 hover:bg-muted/30 transition-colors"
                >
                  <Badge variant="info" className={cn("text-xs font-mono", TF_COLORS[ev.timeframe])}>
                    {ev.timeframe}
                  </Badge>
                  <span className="font-mono text-sm font-medium min-w-[80px]">{ev.symbol}</span>
                  <Badge className={cn("text-xs", SIGNAL_COLORS[ev.signal])}>
                    {ev.signal.toUpperCase()}
                  </Badge>
                  <span className="text-xs text-muted-foreground min-w-[40px]">
                    {(ev.confidence * 100).toFixed(0)}%
                  </span>
                  {ev.traded && (
                    <Badge variant="default" className="text-xs bg-emerald-600">
                      TRADE
                    </Badge>
                  )}
                  {ev.error && (
                    <Badge variant="danger" className="text-xs">ERR</Badge>
                  )}
                  <span className="text-xs text-muted-foreground ml-auto">
                    {formatDuration(ev.duration_ms)}
                  </span>
                  <span className="text-xs text-muted-foreground">
                    {new Date(ev.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {(data?.pagination?.pages ?? 0) > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/30">
              <span className="text-xs text-muted-foreground">
                Page {data?.pagination?.page ?? 1} of {data?.pagination?.pages ?? 1}
              </span>
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page <= 1}
                  onClick={() => setPage(page - 1)}
                >
                  Previous
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  disabled={page >= (data?.pagination?.pages ?? 1)}
                  onClick={() => setPage(page + 1)}
                >
                  Next
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function CandleMonitorPage() {
  return (
    <ErrorBoundary>
      <CandleMonitorContent />
    </ErrorBoundary>
  );
}
