"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn } from "@/lib/utils";
import { History, RefreshCw, Filter, TrendingUp, BarChart3, AlertTriangle } from "lucide-react";

interface TradeEvent {
  id: number;
  symbol: string;
  timeframe: string;
  signal: string;
  confidence: number;
  traded: boolean;
  regime: string;
  strategy: string;
  entry_price: number;
  pnl: number;
  duration_ms: number;
  error: string;
  timestamp: string;
}

interface TradeStats {
  total: number;
  trades: number;
  signals: number;
  errors: number;
  last_24h: number;
  by_symbol: Array<{ symbol: string; total: number; trades: number; avg_confidence: number }>;
  by_timeframe: Array<{ timeframe: string; total: number; trades: number; avg_confidence: number }>;
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

function TradeHistoryContent() {
  const [data, setData] = useState<{ events: TradeEvent[]; pagination: { page: number; limit: number; total: number; pages: number }; stats: TradeStats } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [page, setPage] = useState(1);
  const [filterSymbol, setFilterSymbol] = useState("");
  const [filterTf, setFilterTf] = useState("");
  const [tradedOnly, setTradedOnly] = useState(false);

  const load = async () => {
    try {
      const params = new URLSearchParams({ page: String(page), limit: "50" });
      if (filterSymbol) params.set("symbol", filterSymbol);
      if (filterTf) params.set("timeframe", filterTf);
      if (tradedOnly) params.set("traded", "1");
      const res = await fetch(`/api/trade-history?${params}`, { cache: "no-store" });
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
  }, [page, filterSymbol, filterTf, tradedOnly]);

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-8 w-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <History className="h-4 w-4 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Trade History</h1>
            <p className="text-sm text-muted-foreground">Complete trade and signal log</p>
          </div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 rounded-xl bg-muted/30 animate-pulse" />
        ))}
      </div>
    );
  }

  const events = data?.events ?? [];
  const stats = data?.stats;
  const pagination = data?.pagination;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-purple-500/20 flex items-center justify-center">
            <History className="h-4 w-4 text-purple-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Trade History</h1>
            <p className="text-sm text-muted-foreground">Complete trade and signal log (unlimited SQLite storage)</p>
          </div>
        </div>
        <Button variant="outline" size="sm" onClick={load}>
          <RefreshCw className="h-4 w-4" />
        </Button>
      </div>

      {error && (
        <div className="rounded-lg border border-red-500/30 bg-red-500/10 p-4 flex items-center gap-2">
          <AlertTriangle className="h-4 w-4 text-red-400" />
          <span className="text-sm text-red-400">{error}</span>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <History className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total Events</span>
            </div>
            <div className="text-2xl font-bold">{stats?.total ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <span className="text-sm">💰</span>
              <span className="text-xs text-muted-foreground">Trades</span>
            </div>
            <div className="text-2xl font-bold text-emerald-400">{stats?.trades ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <BarChart3 className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Signals</span>
            </div>
            <div className="text-2xl font-bold text-blue-400">{stats?.signals ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Errors</span>
            </div>
            <div className="text-2xl font-bold text-amber-400">{stats?.errors ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <TrendingUp className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Last 24h</span>
            </div>
            <div className="text-2xl font-bold">{stats?.last_24h ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 flex-wrap">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {["", "M15", "H1", "H4", "D1"].map((tf) => (
          <Button
            key={tf}
            variant={filterTf === tf ? "default" : "outline"}
            size="sm"
            onClick={() => { setFilterTf(tf); setPage(1); }}
            className="text-xs"
          >
            {tf || "All TFs"}
          </Button>
        ))}
        <Button
          variant={tradedOnly ? "default" : "outline"}
          size="sm"
          onClick={() => { setTradedOnly(!tradedOnly); setPage(1); }}
          className="text-xs"
        >
          Trades Only
        </Button>
        {filterSymbol && (
          <Badge variant="info" className="gap-1">
            {filterSymbol}
            <button onClick={() => { setFilterSymbol(""); setPage(1); }} className="ml-1 hover:text-white">×</button>
          </Badge>
        )}
      </div>

      {/* Events */}
      <Card className="border-border/50 bg-card/50">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm font-medium">Trade Events</CardTitle>
          <CardDescription className="text-xs">
            {pagination?.total ?? 0} total | Page {pagination?.page ?? 1}/{pagination?.pages ?? 1}
          </CardDescription>
        </CardHeader>
        <CardContent>
          {events.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <History className="h-8 w-8 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No trade events yet</p>
              <p className="text-xs mt-1">Start the daemon to begin recording</p>
            </div>
          ) : (
            <div className="space-y-2">
              {events.map((ev) => (
                <div
                  key={ev.id}
                  className="flex items-center gap-3 rounded-lg border border-border/30 p-3 hover:bg-muted/30 transition-colors"
                >
                  <Badge variant="info" className={cn("text-xs font-mono", TF_COLORS[ev.timeframe])}>
                    {ev.timeframe}
                  </Badge>
                  <button
                    onClick={() => setFilterSymbol(ev.symbol)}
                    className="font-mono text-sm font-medium min-w-[80px] hover:text-blue-400 transition-colors"
                  >
                    {ev.symbol}
                  </button>
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
                  {ev.entry_price > 0 && (
                    <span className="text-xs text-muted-foreground">
                      @ {ev.entry_price.toFixed(5)}
                    </span>
                  )}
                  {ev.pnl !== 0 && (
                    <span className={cn("text-xs font-medium", ev.pnl > 0 ? "text-emerald-400" : "text-red-400")}>
                      {ev.pnl > 0 ? "+" : ""}{ev.pnl.toFixed(2)}
                    </span>
                  )}
                  {ev.error && (
                    <Badge variant="danger" className="text-xs">ERR</Badge>
                  )}
                  <span className="text-xs text-muted-foreground ml-auto">
                    {new Date(ev.timestamp).toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          )}

          {/* Pagination */}
          {(pagination?.pages ?? 0) > 1 && (
            <div className="flex items-center justify-between mt-4 pt-4 border-t border-border/30">
              <span className="text-xs text-muted-foreground">
                Page {pagination?.page ?? 1} of {pagination?.pages ?? 1}
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
                  disabled={page >= (pagination?.pages ?? 1)}
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

export default function TradeHistoryPage() {
  return (
    <ErrorBoundary>
      <TradeHistoryContent />
    </ErrorBoundary>
  );
}
