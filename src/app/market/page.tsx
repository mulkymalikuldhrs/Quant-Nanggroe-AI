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
import { MetricCard, SectionHeader, Skeleton, AnimatedNumber } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <Globe className="w-8 h-8 text-sky animate-spin-slow" />
            Market Intelligence
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Global Quotes & Regime Analysis
          </p>
        </div>
        <div className="flex items-center gap-2 bg-secondary/20 p-1.5 rounded-xl border border-border/50 backdrop-blur-sm shadow-[0_0_15px_rgba(0,0,0,0.1)]">
          <Input
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value.toUpperCase())}
            className="w-28 font-mono h-9 border-none bg-secondary/30 focus-visible:ring-1 focus-visible:ring-sky/50"
            placeholder="Symbol"
          />
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-24 h-9 border-none bg-secondary/30 focus:ring-1 focus:ring-sky/50">
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
            className="cursor-pointer h-9 w-9 scale-tap hover:bg-sky/10 hover:text-sky transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Watchlist */}
      <div className="animate-slide-up" style={{ animationDelay: '100ms' }}>
        <SectionHeader title="Live Quotes" description="Continuous monitoring of tracked assets" />
        <div className="flex overflow-x-auto pb-4 pt-2 -mx-2 px-2 custom-scroll gap-4 stagger-children">
          {WATCHLIST_SYMBOLS.map((symbol) => {
            const priceInfo = prices[symbol];
            const isLoading = loadingPrices[symbol];
            const isCrypto = symbol.includes("USD") && !symbol.includes("EUR") && !symbol.includes("GBP");
            const isForex = symbol.includes("EUR") || symbol.includes("GBP");
            const colorClass = isCrypto ? "amber" : isForex ? "emerald" : "sky";

            return (
              <button
                key={symbol}
                onClick={() => setSelectedSymbol(symbol)}
                className={cn(
                  "glass-card p-4 text-left transition-all cursor-pointer min-w-[160px] snap-start shrink-0 hover-lift group relative overflow-hidden",
                  selectedSymbol === symbol
                    ? `border-${colorClass}/50 bg-${colorClass}/10 shadow-[0_0_15px_rgba(var(--${colorClass}-rgb),0.2)]`
                    : `border-border/40 hover:border-${colorClass}/30 hover:bg-${colorClass}/5`
                )}
              >
                <div className={cn(`absolute right-0 top-0 w-16 h-16 bg-${colorClass}/5 rounded-bl-full translate-x-8 -translate-y-8 group-hover:bg-${colorClass}/10 transition-colors`)} />
                <div className="flex items-center justify-between mb-2 relative z-10">
                  <span className={cn("text-base font-black font-mono tracking-tight", 
                    selectedSymbol === symbol ? `text-${colorClass}` : "text-foreground"
                  )}>
                    {symbol}
                  </span>
                  <Badge
                    variant={isCrypto ? "amber" : isForex ? "emerald" : "sky"}
                    className="text-[9px] font-bold px-1.5 py-0 shadow-sm"
                  >
                    {isCrypto ? "CRYPTO" : isForex ? "FOREX" : "EQUITY"}
                  </Badge>
                </div>
                <div className="relative z-10">
                  {isLoading ? (
                    <Skeleton className="h-6 w-20 mt-1 rounded bg-secondary/50" />
                  ) : priceInfo?.price != null ? (
                    <p className="text-xl font-bold text-foreground tabular-nums tracking-tight">
                      ${priceInfo.price.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: priceInfo.price < 1 ? 6 : 2,
                      })}
                    </p>
                  ) : (
                    <p className="text-sm text-muted-foreground mt-1 font-mono">—</p>
                  )}
                </div>
              </button>
            );
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
        {/* Chart + Regime */}
        <div className="xl:col-span-2 space-y-6">
          <Card variant="gradient" className="h-[450px] flex flex-col">
            <CardHeader className="pb-4">
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <BarChart3 className="w-4 h-4 text-sky" />
                <span className="text-sky text-lg font-mono tracking-tight font-bold">{selectedSymbol}</span>
                <span className="text-muted-foreground ml-2">Price Action</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="flex-1 min-h-0">
              <div className="h-full w-full relative">
                {loadingOHLCV ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="w-8 h-8 text-sky animate-spin drop-shadow-[0_0_10px_rgba(14,165,233,0.5)]" />
                  </div>
                ) : chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#0ea5e9" stopOpacity={0.4} />
                          <stop offset="95%" stopColor="#0ea5e9" stopOpacity={0.0} />
                        </linearGradient>
                        <filter id="glowSky" x="-20%" y="-20%" width="140%" height="140%">
                          <feGaussianBlur stdDeviation="4" result="blur" />
                          <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(10, 15, 26, 0.95)",
                          backdropFilter: "blur(10px)",
                          border: "1px solid rgba(14, 165, 233, 0.3)",
                          borderRadius: "8px",
                          boxShadow: "0 4px 20px rgba(0,0,0,0.4), 0 0 10px rgba(14,165,233,0.1)",
                          fontSize: "12px",
                          fontWeight: 600,
                        }}
                        itemStyle={{ color: "#0ea5e9" }}
                        cursor={{ stroke: 'rgba(14, 165, 233, 0.5)', strokeWidth: 1, strokeDasharray: '4 4' }}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="#0ea5e9"
                        fill="url(#marketGrad)"
                        strokeWidth={3}
                        activeDot={{ r: 6, fill: "#0ea5e9", stroke: "#030712", strokeWidth: 2, filter: "url(#glowSky)" }}
                      />
                    </AreaChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-medium">
                    No data available for {selectedSymbol}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Market Regime */}
          <Card variant="flat" className="border-l-4 border-l-purple relative overflow-hidden group">
            <div className="absolute right-0 bottom-0 w-32 h-32 bg-purple/5 rounded-tl-full translate-x-16 translate-y-16 group-hover:bg-purple/10 transition-colors pointer-events-none" />
            <CardHeader className="pb-3 relative z-10">
              <CardTitle className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <Gauge className="w-4 h-4 text-purple" />
                  Regime Classifier
                </span>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleDetectRegime}
                  className="cursor-pointer font-bold tracking-wide border-purple/30 text-purple hover:bg-purple/10"
                >
                  <RefreshCw className="w-3.5 h-3.5 mr-1.5" />
                  DETECT REGIME
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="relative z-10">
              {regimeResult ? (
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-fade-in stagger-children">
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 transition-colors">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Dominant State</p>
                    <Badge
                      variant={regimeResult.regime.includes("bull") ? "emerald" : "rose"}
                      className="font-bold shadow-sm"
                    >
                      {regimeResult.regime.toUpperCase()}
                    </Badge>
                  </div>
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 transition-colors">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Volatility</p>
                    <p className="text-sm font-black text-foreground uppercase tracking-tight">
                      {regimeResult.volatility}
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 transition-colors">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Liquidity</p>
                    <p className="text-sm font-black text-foreground uppercase tracking-tight">
                      {regimeResult.liquidity}
                    </p>
                  </div>
                  <div className="p-4 rounded-xl bg-secondary/20 border border-border/40 hover:bg-secondary/40 transition-colors">
                    <p className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground mb-1.5">Permission</p>
                    <p
                      className={cn("text-sm font-black uppercase tracking-tight",
                        regimeResult.trade_allowed ? "text-emerald drop-shadow-[0_0_5px_rgba(16,185,129,0.5)]" : "text-rose drop-shadow-[0_0_5px_rgba(244,63,94,0.5)]"
                      )}
                    >
                      {regimeResult.trade_allowed ? "GRANTED" : "DENIED"}
                    </p>
                  </div>
                </div>
              ) : (
                <div className="text-center py-6 text-muted-foreground text-sm font-medium">
                  Trigger detection to process current OHLCV footprint through regime models.
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel */}
        <div className="space-y-6">
          {/* Pressure Analysis */}
          <Card variant="flat">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber" />
                Microstructure Pressure
              </CardTitle>
            </CardHeader>
            <CardContent>
              {pressureData ? (
                <div className="space-y-6 animate-fade-in">
                  <div className="space-y-4">
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-emerald">Buy Pressure</span>
                        <span className="text-xs font-bold text-emerald tabular-nums">
                          <AnimatedNumber value={pressureData.buy_pressure * 100} formatter={(v) => v.toFixed(1)} />%
                        </span>
                      </div>
                      <div className="h-3 rounded-full bg-secondary/50 border border-border/50 overflow-hidden relative">
                        <div
                          className="absolute left-0 top-0 bottom-0 bg-emerald transition-all duration-700 ease-out"
                          style={{ width: `${pressureData.buy_pressure * 100}%` }}
                        >
                           <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)] bg-[length:200%_100%] animate-shimmer" />
                        </div>
                      </div>
                    </div>
                    <div>
                      <div className="flex items-center justify-between mb-1.5">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-rose">Sell Pressure</span>
                        <span className="text-xs font-bold text-rose tabular-nums">
                          <AnimatedNumber value={pressureData.sell_pressure * 100} formatter={(v) => v.toFixed(1)} />%
                        </span>
                      </div>
                      <div className="h-3 rounded-full bg-secondary/50 border border-border/50 overflow-hidden relative">
                        <div
                          className="absolute left-0 top-0 bottom-0 bg-rose transition-all duration-700 ease-out"
                          style={{ width: `${pressureData.sell_pressure * 100}%` }}
                        >
                          <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.3),transparent)] bg-[length:200%_100%] animate-shimmer" />
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div className="bg-secondary/10 p-4 rounded-xl border border-border/30 space-y-3">
                    <div className="flex justify-between items-center pb-2 border-b border-border/30">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Spread</span>
                      <span className="text-sm font-mono font-bold text-foreground">
                        {pressureData.spread?.toFixed(4) ?? "—"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center pb-2 border-b border-border/30">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">Mid Price</span>
                      <span className="text-sm font-mono font-bold text-foreground">
                        {pressureData.mid_price?.toFixed(2) ?? "—"}
                      </span>
                    </div>
                    <div className="flex justify-between items-center">
                      <span className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground">ML Verdict</span>
                      <Badge
                        variant={
                          pressureData.verdict.includes("BUY")
                            ? "emerald"
                            : pressureData.verdict.includes("SELL")
                            ? "rose"
                            : "outline"
                        }
                        className="text-[10px] font-bold shadow-sm"
                      >
                        {pressureData.verdict.replace('_', ' ')}
                      </Badge>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="flex flex-col items-center justify-center py-10 text-muted-foreground">
                  {loadingPressure ? (
                    <RefreshCw className="w-6 h-6 animate-spin text-amber mb-3" />
                  ) : (
                    <Activity className="w-6 h-6 mb-3 opacity-50" />
                  )}
                  <p className="text-sm font-medium">{loadingPressure ? "Analyzing tape..." : "No orderbook data"}</p>
                </div>
              )}
            </CardContent>
          </Card>

          {/* Market Sentiment */}
          <Card variant="flat">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Newspaper className="w-4 h-4 text-cyan" />
                Macro Sentiment
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                <div className="p-4 rounded-xl bg-gradient-to-r from-rose/10 via-amber/10 to-emerald/10 border border-border/30 relative overflow-hidden">
                  <div className="flex items-center justify-between mb-3 relative z-10">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-foreground">Fear / Greed</span>
                    <span className="text-sm font-black text-amber uppercase tracking-tight">Neutral 50</span>
                  </div>
                  <div className="h-3 rounded-full bg-background border border-border/50 overflow-hidden relative z-10">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{
                        width: "50%",
                        background: "linear-gradient(90deg, #f43f5e 0%, #f59e0b 50%, #10b981 100%)",
                        boxShadow: "0 0 10px rgba(245,158,11,0.5)"
                      }}
                    />
                  </div>
                  <div className="flex justify-between text-[9px] font-bold uppercase tracking-widest text-muted-foreground mt-2 relative z-10">
                    <span>Fear</span>
                    <span>Greed</span>
                  </div>
                </div>

                <div className="space-y-2 stagger-children">
                  {[
                    { label: "S&P 500", trend: "bullish", confidence: 68 },
                    { label: "NASDAQ", trend: "bullish", confidence: 72 },
                    { label: "BTC", trend: "neutral", confidence: 50 },
                    { label: "EUR/USD", trend: "bearish", confidence: 55 },
                  ].map((item) => (
                    <div
                      key={item.label}
                      className="flex items-center justify-between p-3 rounded-xl bg-secondary/10 border border-border/30 hover:bg-secondary/20 transition-colors"
                    >
                      <span className="text-sm font-bold text-foreground font-mono">{item.label}</span>
                      <div className="flex items-center gap-3">
                        <Badge
                          variant={
                            item.trend === "bullish"
                              ? "emerald"
                              : item.trend === "bearish"
                              ? "rose"
                              : "outline"
                          }
                          className="text-[9px] font-bold uppercase tracking-widest shadow-sm"
                        >
                          {item.trend}
                        </Badge>
                        <span className="text-xs font-mono text-muted-foreground w-8 text-right">
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
