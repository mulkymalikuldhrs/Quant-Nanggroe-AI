"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn } from "@/lib/utils";
import { Bell, RefreshCw, TrendingUp, AlertTriangle, Zap, Clock, Filter } from "lucide-react";

interface Notification {
  id: string;
  type: "trade" | "signal" | "alert" | "system";
  symbol?: string;
  timeframe?: string;
  message: string;
  signal?: string;
  confidence?: number;
  traded?: boolean;
  timestamp: string;
}

interface NotificationStats {
  total: number;
  trades: number;
  signals: number;
  alerts: number;
  system: number;
  last_hour: number;
  last_24h: number;
}

const TYPE_COLORS: Record<string, string> = {
  trade: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
  signal: "bg-blue-500/20 text-blue-400 border-blue-500/30",
  alert: "bg-amber-500/20 text-amber-400 border-amber-500/30",
  system: "bg-slate-500/20 text-slate-400 border-slate-500/30",
};

const TYPE_ICONS: Record<string, string> = {
  trade: "💰",
  signal: "📡",
  alert: "⚠️",
  system: "🔧",
};

function NotificationsContent() {
  const [data, setData] = useState<{ notifications: Notification[]; stats: NotificationStats } | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>("all");

  const load = async () => {
    try {
      const res = await fetch("/api/notifications", { cache: "no-store" });
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

  // WS + polling fallback: keep polling but back off to 15s; WS pushes via useRealtimeData will also trigger reload when connected.
  useEffect(() => {
    load();
    const iv = setInterval(load, 15000);
    return () => clearInterval(iv);
  }, []);

  if (loading && !data) {
    return (
      <div className="space-y-4">
        <div className="flex items-center gap-3 mb-6">
          <div className="h-8 w-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Bell className="h-4 w-4 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
            <p className="text-sm text-muted-foreground">Trade signals and system alerts</p>
          </div>
        </div>
        {[1, 2, 3].map((i) => (
          <div key={i} className="h-32 rounded-xl bg-muted/30 animate-pulse" />
        ))}
      </div>
    );
  }

  const notifications = data?.notifications ?? [];
  const stats = data?.stats;
  const filtered = filterType === "all" ? notifications : notifications.filter((n) => n.type === filterType);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="h-8 w-8 rounded-lg bg-blue-500/20 flex items-center justify-center">
            <Bell className="h-4 w-4 text-blue-400" />
          </div>
          <div>
            <h1 className="text-2xl font-bold tracking-tight">Notifications</h1>
            <p className="text-sm text-muted-foreground">Trade signals, alerts, and system notifications</p>
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
              <Bell className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Total</span>
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
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Signals</span>
            </div>
            <div className="text-2xl font-bold text-blue-400">{stats?.signals ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <AlertTriangle className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Alerts</span>
            </div>
            <div className="text-2xl font-bold text-amber-400">{stats?.alerts ?? 0}</div>
          </CardContent>
        </Card>
        <Card className="border-border/50 bg-card/50">
          <CardContent className="p-4">
            <div className="flex items-center gap-2 mb-2">
              <Clock className="h-4 w-4 text-muted-foreground" />
              <span className="text-xs text-muted-foreground">Last Hour</span>
            </div>
            <div className="text-2xl font-bold">{stats?.last_hour ?? 0}</div>
          </CardContent>
        </Card>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-2">
        <Filter className="h-4 w-4 text-muted-foreground" />
        {["all", "trade", "signal", "alert", "system"].map((type) => (
          <Button
            key={type}
            variant={filterType === type ? "default" : "outline"}
            size="sm"
            onClick={() => setFilterType(type)}
            className="text-xs"
          >
            {type.charAt(0).toUpperCase() + type.slice(1)}
          </Button>
        ))}
      </div>

      {/* Notifications List */}
      <Card className="border-border/50 bg-card/50">
        <CardContent>
          {filtered.length === 0 ? (
            <div className="text-center py-12 text-muted-foreground">
              <Bell className="h-8 w-8 mx-auto mb-3 opacity-30" />
              <p className="text-sm">No notifications yet</p>
              <p className="text-xs mt-1">Start the daemon to begin receiving notifications</p>
            </div>
          ) : (
            <div className="space-y-2 max-h-[600px] overflow-y-auto">
              {filtered.slice().reverse().map((n) => (
                <div
                  key={n.id}
                  className="flex items-start gap-3 rounded-lg border border-border/30 p-3 hover:bg-muted/30 transition-colors"
                >
                  <span className="text-lg mt-0.5">{TYPE_ICONS[n.type]}</span>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <Badge variant="info" className={cn("text-xs", TYPE_COLORS[n.type])}>
                        {n.type.toUpperCase()}
                      </Badge>
                      {n.symbol && (
                        <span className="font-mono text-sm font-medium">{n.symbol}</span>
                      )}
                      {n.timeframe && (
                        <Badge variant="info" className="text-xs">{n.timeframe}</Badge>
                      )}
                      {n.signal && (
                        <Badge className={cn("text-xs", n.signal === "buy" ? "bg-emerald-600" : n.signal === "sell" ? "bg-red-600" : "bg-slate-600")}>
                          {n.signal.toUpperCase()}
                        </Badge>
                      )}
                      {n.confidence !== undefined && (
                        <span className="text-xs text-muted-foreground">
                          {(n.confidence * 100).toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <p className="text-sm text-muted-foreground whitespace-pre-wrap">{n.message}</p>
                  </div>
                  <span className="text-xs text-muted-foreground whitespace-nowrap">
                    {new Date(n.timestamp).toLocaleTimeString()}
                  </span>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

export default function NotificationsPage() {
  return (
    <ErrorBoundary>
      <NotificationsContent />
    </ErrorBoundary>
  );
}
