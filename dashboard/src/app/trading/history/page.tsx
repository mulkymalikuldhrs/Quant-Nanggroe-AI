"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect, useCallback, useMemo } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { DataTable } from "@/components/shared/data-table";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn, formatCurrency, formatPercent, formatPrice, formatTimestamp } from "@/lib/utils";
import { apiRequest } from "@/lib/api-client";
import { Clock, Filter, RefreshCw, Search, TrendingDown, TrendingUp, ArrowLeft } from "lucide-react";
import Link from "next/link";

interface TradeDetail {
  id: string;
  ticket: number | null;
  symbol: string;
  side: "buy" | "sell";
  volume: number;
  entry_price: number;
  exit_price: number;
  entry_time: string;
  exit_time: string;
  pnl: number;
  pnl_pct: number | null;
  commission: number;
  swap: number;
  strategy: string | null;
  broker: string | null;
  comment: string | null;
}

interface TradeHistoryResponse {
  trades: TradeDetail[];
  total_count: number;
  limit: number;
  filters: Record<string, unknown>;
}

function TradeHistoryContent() {
  const [trades, setTrades] = useState<TradeDetail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [filterSymbol, setFilterSymbol] = useState("");
  const [filterDateFrom, setFilterDateFrom] = useState("");
  const [filterDateTo, setFilterDateTo] = useState("");
  const [filterStrategy, setFilterStrategy] = useState("");
  const [filterLimit, setFilterLimit] = useState(50);

  const fetchHistory = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const params = new URLSearchParams();
      if (filterSymbol) params.set("symbol", filterSymbol);
      if (filterDateFrom) params.set("date_from", filterDateFrom);
      if (filterDateTo) params.set("date_to", filterDateTo);
      if (filterStrategy) params.set("strategy", filterStrategy);
      params.set("limit", String(filterLimit));

      const data = await apiRequest<TradeHistoryResponse>(`/api/trading/history?${params.toString()}`);
      setTrades(data.trades || []);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load trade history");
      setTrades([]);
    } finally {
      setLoading(false);
    }
  }, [filterSymbol, filterDateFrom, filterDateTo, filterStrategy, filterLimit]);

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  const totals = useMemo(() => {
    let grossPnl = 0;
    let wins = 0;
    let losses = 0;
    for (const t of trades) {
      grossPnl += t.pnl;
      if (t.pnl > 0) wins++;
      else if (t.pnl < 0) losses++;
    }
    const totalTrades = trades.length;
    const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
    const avgWin = wins > 0 ? grossPnl / totalTrades : 0;
    return { grossPnl, totalTrades, wins, losses, winRate, avgWin };
  }, [trades]);

  const columns = [
    {
      key: "exit_time",
      label: "Date",
      width: "140px",
      render: (r: TradeDetail) => (
        <span className="text-[11px] text-white/60">{formatTimestamp(r.exit_time)}</span>
      ),
    },
    {
      key: "symbol",
      label: "Symbol",
      width: "90px",
      render: (r: TradeDetail) => <span className="font-medium text-white">{r.symbol}</span>,
    },
    {
      key: "side",
      label: "Side",
      width: "60px",
      render: (r: TradeDetail) => (
        <Badge variant={r.side === "buy" ? "success" : "danger"} size="sm">
          {r.side === "buy" ? "BUY" : "SELL"}
        </Badge>
      ),
    },
    {
      key: "volume",
      label: "Qty",
      align: "right" as const,
      width: "70px",
      render: (r: TradeDetail) => <span className="font-mono">{r.volume}</span>,
    },
    {
      key: "entry_price",
      label: "Entry",
      align: "right" as const,
      width: "90px",
      render: (r: TradeDetail) => (
        <span className="font-mono text-white/60">{formatPrice(r.entry_price, "$")}</span>
      ),
    },
    {
      key: "exit_price",
      label: "Exit",
      align: "right" as const,
      width: "90px",
      render: (r: TradeDetail) => (
        <span className="font-mono text-white/60">{formatPrice(r.exit_price, "$")}</span>
      ),
    },
    {
      key: "pnl",
      label: "P&L",
      align: "right" as const,
      sortable: true,
      width: "120px",
      render: (r: TradeDetail) => (
        <span className={cn("font-mono font-medium", r.pnl >= 0 ? "text-profit" : "text-loss")}>
          {formatCurrency(r.pnl)}
        </span>
      ),
    },
    {
      key: "pnl_pct",
      label: "P&L %",
      align: "right" as const,
      width: "80px",
      render: (r: TradeDetail) => (
        <span className={cn("font-mono", r.pnl_pct != null && r.pnl_pct >= 0 ? "text-profit" : "text-loss")}>
          {r.pnl_pct != null ? `${r.pnl_pct >= 0 ? "+" : ""}${r.pnl_pct.toFixed(2)}%` : "—"}
        </span>
      ),
    },
    {
      key: "strategy",
      label: "Strategy",
      width: "100px",
      render: (r: TradeDetail) => (
        <span className="text-xs text-white/40">{r.strategy || "—"}</span>
      ),
    },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Link
            href="/trading"
            className="flex items-center gap-1.5 text-xs text-white/40 hover:text-white/60 transition-colors"
          >
            <ArrowLeft className="w-3.5 h-3.5" />
            Back to Trading
          </Link>
          <div>
            <h1 className="text-xl font-bold text-white flex items-center gap-2">
              <Clock className="w-5 h-5 text-emerald-400" />
              Trade History
            </h1>
            <p className="text-sm text-white/40">Closed trades • MT5 & journal sources</p>
          </div>
        </div>
        <Button variant="primary" size="sm" onClick={fetchHistory} loading={loading}>
          <RefreshCw className="w-3.5 h-3.5" />
        </Button>
      </div>

      {/* Filters */}
      <Card className="p-3">
        <div className="flex items-center gap-3 flex-wrap">
          <div className="flex items-center gap-2">
            <Filter className="w-3.5 h-3.5 text-white/20" />
            <span className="text-[10px] text-white/30 uppercase tracking-wider">Filters</span>
          </div>
          <Input
            placeholder="Symbol"
            value={filterSymbol}
            onChange={(e) => setFilterSymbol(e.target.value)}
            className="w-28 h-8 text-xs"
          />
          <Input
            type="date"
            value={filterDateFrom}
            onChange={(e) => setFilterDateFrom(e.target.value)}
            className="w-36 h-8 text-xs"
          />
          <Input
            type="date"
            value={filterDateTo}
            onChange={(e) => setFilterDateTo(e.target.value)}
            className="w-36 h-8 text-xs"
          />
          <Input
            placeholder="Strategy"
            value={filterStrategy}
            onChange={(e) => setFilterStrategy(e.target.value)}
            className="w-28 h-8 text-xs"
          />
          <Button variant="secondary" size="sm" onClick={fetchHistory}>
            <Search className="w-3 h-3" />
            Search
          </Button>
          {(filterSymbol || filterDateFrom || filterDateTo || filterStrategy) && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setFilterSymbol("");
                setFilterDateFrom("");
                setFilterDateTo("");
                setFilterStrategy("");
              }}
            >
              Clear
            </Button>
          )}
        </div>
      </Card>

      {/* Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Card>
          <CardContent className="p-3">
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Total Trades</p>
            <p className="text-lg font-bold font-mono text-white">{totals.totalTrades}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Gross P&L</p>
            <p className={cn("text-lg font-bold font-mono", totals.grossPnl >= 0 ? "text-profit" : "text-loss")}>
              {formatCurrency(totals.grossPnl)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Win Rate</p>
            <p className="text-lg font-bold font-mono text-white">{totals.winRate.toFixed(1)}%</p>
            <p className="text-[10px] text-white/20 mt-0.5">
              {totals.wins}W / {totals.losses}L
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="p-3">
            <p className="text-[10px] text-white/30 uppercase tracking-wider mb-1">Avg Trade</p>
            <p className={cn("text-lg font-bold font-mono", totals.avgWin >= 0 ? "text-profit" : "text-loss")}>
              {formatCurrency(totals.avgWin)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Error */}
      {error && (
        <Card className="border-red-500/20 bg-red-500/5">
          <CardContent className="p-3 text-xs text-red-400">{error}</CardContent>
        </Card>
      )}

      {/* Trade Table */}
      <Card>
        <CardHeader>
          <CardTitle>Closed Trades</CardTitle>
          <Badge variant="info" size="sm">
            {trades.length} trades
          </Badge>
        </CardHeader>
        <CardContent>
          <DataTable
            columns={columns}
            data={trades}
            keyExtractor={(r) => r.id}
            loading={loading}
            emptyMessage="No closed trades found"
          />
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
