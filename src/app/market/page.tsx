"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  Globe,
  RefreshCw,
  TrendingUp,
  TrendingDown,
  Activity,
  BarChart3,
  Gauge,
  Newspaper,
  Calendar,
} from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { MetricCard, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";

const WATCHLIST_SYMBOLS = [
  "AAPL",
  "MSFT",
  "GOOGL",
  "AMZN",
  "NVDA",
  "TSLA",
  "BTC-USD",
  "ETH-USD",
  "EURUSD",
  "GBPUSD",
];

interface PriceInfo {
  symbol: string;
  price: number | null;
  timestamp: string;
}

export default function MarketPage() {
  const {
    ohlcvData,
    pressureData,
    loadingOHLCV,
    loadingPressure,
    fetchOHLCV,
    fetchPressure,
  } = useAppStore();

  const [selectedSymbol, setSelectedSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1d");
  const [prices, setPrices] = useState<Record<string, PriceInfo>>({});
  const [loadingPrices, setLoadingPrices] = useState<Record<string, boolean>>({});
  const [regimeResult, setRegimeResult] = useState<{
    regime: string;
    base_regime: string;
    volatility: string;
    liquidity: string;
    trade_allowed: boolean;
    no_trade_reasons: string[];
  } | null>(null);

  useEffect(() => {
    fetchOHLCV(selectedSymbol, timeframe, 100);
    fetchPressure(selectedSymbol);
  }, [selectedSymbol, timeframe, fetchOHLCV, fetchPressure]);

  // Fetch prices for watchlist
  useEffect(() => {
    const fetchPrices = async () => {
      for (const symbol of WATCHLIST_SYMBOLS) {
        setLoadingPrices((p) => ({ ...p, [symbol]: true }));
        try {
          const data = await apiClient.getPrice(symbol);
          setPrices((p) => ({ ...p, [symbol]: data }));
        } catch {
          // ignore
        }
        setLoadingPrices((p) => ({ ...p, [symbol]: false }));
      }
    };
    fetchPrices();
    const interval = setInterval(fetchPrices, 60000);
    return () => clearInterval(interval);
  }, []);

  const handleDetectRegime = async () => {
    try {
      const result = await apiClient.detectRegime({
        symbol: selectedSymbol,
      });
      setRegimeResult(result);
    } catch {
      // ignore
    }
  };

  // Chart data
  const chartData = ohlcvData.map((candle) => ({
    time: new Date(candle.timestamp).toLocaleDateString([], {
      month: "short",
      day: "numeric",
    }),
    close: candle.close,
    volume: candle.volume,
  }));

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <Globe className="w-6 h-6 text-sky" />
            Market Overview
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time prices, market data, and regime analysis
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Input
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value.toUpperCase())}
            className="w-28 font-mono"
            placeholder="Symbol"
          />
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-24">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="1h">1H</SelectItem>
              <SelectItem value="4h">4H</SelectItem>
              <SelectItem value="1d">1D</SelectItem>
              <SelectItem value="1w">1W</SelectItem>
            </SelectContent>
          </Select>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              fetchOHLCV(selectedSymbol, timeframe, 100);
              fetchPressure(selectedSymbol);
            }}
            className="cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Watchlist */}
      <div>
        <SectionHeader title="Watchlist" description="Real-time price quotes" />
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mt-4">
          {WATCHLIST_SYMBOLS.map((symbol) => {
            const priceInfo = prices[symbol];
            const isLoading = loadingPrices[symbol];
            const isCrypto = symbol.includes("USD") && !symbol.includes("EUR") && !symbol.includes("GBP");
            const isForex = symbol.includes("EUR") || symbol.includes("GBP");

            return (
              <button
                key={symbol}
                onClick={() => setSelectedSymbol(symbol)}
                className={`glass-card p-3 text-left transition-all cursor-pointer ${
                  selectedSymbol === symbol
                    ? "border-primary/40 bg-primary/5"
                    : "hover:border-primary/20"
                }`}
              >
                <div className="flex items-center justify-between mb-1">
                  <span className="text-sm font-mono font-medium text-foreground">
                    {symbol}
                  </span>
                  <Badge
                    variant={isCrypto ? "amber" : isForex ? "emerald" : "cyan"}
                    className="text-[8px] px-1 py-0"
                  >
                    {isCrypto ? "Crypto" : isForex ? "FX" : "Stock"}
                  </Badge>
                </div>
                {isLoading ? (
                  <Skeleton className="h-5 w-16 mt-1" />
                ) : priceInfo?.price != null ? (
                  <p className="text-lg font-bold text-foreground tabular-nums">
                    ${priceInfo.price.toLocaleString(undefined, {
                      minimumFractionDigits: 2,
                      maximumFractionDigits: priceInfo.price < 1 ? 6 : 2,
                    })}
                  </p>
                ) : (
                  <p className="text-sm text-muted-foreground mt-1">—</p>
                )}
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart */}
        <div className="lg:col-span-2 space-y-6">
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-cyan" />
                {selectedSymbol} — Price Chart
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-72">
                {chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData}>
                      <defs>
                        <linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.2} />
                          <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} />
                      <Tooltip
                        contentStyle={{
                          background: "#0d1117",
                          border: "1px solid #1e293b",
                          borderRadius: "8px",
                          fontSize: "11px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="#0ea5e9"
                        fill="url(#marketGrad)"
                        strokeWidth={2}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                    {loadingOHLCV ? "Loading..." : "No data available"}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Market Regime */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-purple" />
                  Market Regime Detection
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDetectRegime}
                  className="cursor-pointer"
                >
                  Detect
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent>
              {regimeResult ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                    <p className="text-xs text-muted-foreground">Regime</p>
                    <Badge
                      variant={
                        regimeResult.regime.includes("bull") ? "emerald" : "rose"
                      }
                      className="mt-1"
                    >
                      {regimeResult.regime}
                    </Badge>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                    <p className="text-xs text-muted-foreground">Volatility</p>
                    <p className="text-sm font-medium text-foreground mt-1">
                      {regimeResult.volatility}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                    <p className="text-xs text-muted-foreground">Liquidity</p>
                    <p className="text-sm font-medium text-foreground mt-1">
                      {regimeResult.liquidity}
                    </p>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30">
                    <p className="text-xs text-muted-foreground">Trade Allowed</p>
                    <p
                      className={`text-sm font-medium mt-1 ${
                        regimeResult.trade_allowed ? "text-emerald" : "text-rose"
                      }`}
                    >
                      {regimeResult.trade_allowed ? "Yes" : "No"}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  Click &quot;Detect&quot; to analyze the market regime
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel */}
        <div className="space-y-6">
          {/* Pressure Analysis */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber" />
                Pressure Analysis
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pressureData ? (
                <div className="space-y-4">
                  {/* Pressure bars */}
                  <div className="space-y-2">
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-emerald">Buy Pressure</span>
                        <span className="text-emerald tabular-nums">
                          {(pressureData.buy_pressure * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-secondary/50">
                        <div
                          className="h-full rounded-full bg-emerald transition-all"
                          style={{ width: `${pressureData.buy_pressure * 100}%` }}
                        />
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between text-xs mb-1">
                        <span className="text-rose">Sell Pressure</span>
                        <span className="text-rose tabular-nums">
                          {(pressureData.sell_pressure * 100).toFixed(1)}%
                        </span>
                      </div>
                      <div className="h-2 rounded-full bg-secondary/50">
                        <div
                          className="h-full rounded-full bg-rose transition-all"
                          style={{ width: `${pressureData.sell_pressure * 100}%` }}
                        />
                      </div>
                    </div>
                  </div>
                  <div className="p-3 rounded-lg bg-secondary/20 border border-border/30 text-xs space-y-1">
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Spread</span>
                      <span className="text-foreground tabular-nums">
                        {pressureData.spread?.toFixed(4) ?? "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Mid Price</span>
                      <span className="text-foreground tabular-nums">
                        {pressureData.mid_price?.toFixed(2) ?? "—"}
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-muted-foreground">Verdict</span>
                      <Badge
                        variant={
                          pressureData.verdict.includes("BUY")
                            ? "emerald"
                            : pressureData.verdict.includes("SELL")
                            ? "rose"
                            : "outline"
                        }
                        className="text-[9px]"
                      >
                        {pressureData.verdict}
                      </Badge>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground text-sm">
                  {loadingPressure ? "Loading..." : "No pressure data"}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Market Sentiment */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Newspaper className="w-4 h-4 text-cyan" />
                Market Sentiment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                <div className="p-3 rounded-lg bg-gradient-to-r from-emerald/10 to-rose/10 border border-border/30">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-xs text-muted-foreground">Fear & Greed</span>
                    <span className="text-sm font-bold text-amber">Neutral</span>
                  </div>
                  <div className="h-2 rounded-full bg-secondary/50 overflow-hidden">
                    <div
                      className="h-full rounded-full"
                      style={{
                        width: "50%",
                        background: "linear-gradient(to right, #ef4444, #f59e0b, #10b981)",
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] text-muted-foreground mt-1">
                    <span>Extreme Fear</span>
                    <span>Extreme Greed</span>
                  </div>
                </div>

                <div className="space-y-2">
                  {[
                    { label: "S&P 500", trend: "bullish", confidence: 68 },
                    { label: "NASDAQ", trend: "bullish", confidence: 72 },
                    { label: "BTC", trend: "neutral", confidence: 50 },
                    { label: "EUR/USD", trend: "bearish", confidence: 55 },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between p-2 rounded bg-secondary/20 text-xs"
                    >
                      <span className="text-foreground font-medium">{item.label}</span>
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            item.trend === "bullish"
                              ? "emerald"
                              : item.trend === "bearish"
                              ? "rose"
                              : "outline"
                          }
                          className="text-[9px]"
                        >
                          {item.trend}
                        </Badge>
                        <span className="text-muted-foreground tabular-nums">
                          {item.confidence}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
