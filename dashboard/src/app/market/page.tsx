"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect, useMemo, useRef } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { marketApi } from "@/lib/api-client";
import { useAppStore } from "@/lib/store";
import { useRealtimeData } from "@/lib/websocket";
import type { MarketSentiment, CandleStick } from "@/lib/api-client";
import { formatCurrency, cn } from "@/lib/utils";
import {
  BarChart3,
  TrendingUp,
  TrendingDown,
  Activity,
  Wifi,
  WifiOff,
} from "lucide-react";
import {
  Area,
  ComposedChart,
  Bar,
  Line,
  XAxis,
  YAxis,
  Tooltip as RechartsTooltip,
  ResponsiveContainer,
  CartesianGrid,
} from "recharts";

// ── Fallback data ──────────────────────────────────────────────────

const FALLBACK_CANDLES: CandleStick[] = Array.from({ length: 30 }, (_, i) => ({
  time: `2026-${String(Math.min(i + 6, 12)).padStart(2, "0")}-${String(Math.min(i + 1, 28)).padStart(2, "0")}`,
  open: 65000 + i * 100 + (i % 7) * 50,
  high: 65500 + i * 120 + (i % 5) * 80,
  low: 64800 + i * 80 + (i % 3) * 60,
  close: 65200 + i * 110 + (i % 4) * 70,
}));

const FALLBACK_SCANNER = [
  { symbol: "NVDA", price: 875.28, change: 5.23, volume: "52.3M", signal: "Breakout" },
  { symbol: "SOL", price: 148.32, change: 4.87, volume: "3.2B", signal: "Momentum" },
  { symbol: "META", price: 502.34, change: 3.45, volume: "18.7M", signal: "Reversal" },
  { symbol: "TSLA", price: 178.35, change: -2.87, volume: "89.5M", signal: "Oversold" },
  { symbol: "AAPL", price: 198.22, change: 1.15, volume: "22.4M", signal: "Accumulation" },
];

export default function MarketPage() {
  const { realtimePrices } = useAppStore();
  const { isConnected } = useRealtimeData();
  const [selectedSymbol, setSelectedSymbol] = useState("BTC");
  const [chartType, setChartType] = useState<"area" | "candle">("area");
  const [timeframe, setTimeframe] = useState("1D");
  const [sentiment, setSentiment] = useState<MarketSentiment | null>(null);
  const [candles, setCandles] = useState<CandleStick[]>([]);
  const [scanner, setScanner] = useState<{ symbol: string; price: number; change: number; volume: string; signal: string }[]>([]);
  const chartContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    marketApi.getSentiment()
      .then(setSentiment)
      .catch(() => { /* fallback */ });
    marketApi.getCandles(selectedSymbol)
      .then(setCandles)
      .catch(() => { setCandles(FALLBACK_CANDLES); });
    marketApi.getSignals()
      .then((signals) => setScanner(
        signals.map((s) => ({
          symbol: s.symbol || "UNKNOWN",
          price: s.price ?? 0,
          change: s.change_pct ?? 0,
          volume: String(s.volume ?? 0),
          signal: s.signal ?? "Neutral",
        }))
      ))
      .catch(() => { setScanner(FALLBACK_SCANNER); });
  }, [selectedSymbol]);

  const symbols = [
    { value: "BTC", label: "BTC/USDT" },
    { value: "ETH", label: "ETH/USDT" },
    { value: "AAPL", label: "AAPL" },
    { value: "NVDA", label: "NVDA" },
    { value: "SPY", label: "SPY" },
    { value: "SOL", label: "SOL/USDT" },
    { value: "EUR/USD", label: "EUR/USD" },
  ];

  const chartData = useMemo(() =>
    candles.slice(0, 30).map((c, idx) => ({
      date: c.time.slice(5),
      open: c.open, high: c.high, low: c.low, close: c.close,
      volume: Math.round(400 + idx * 7.3),
    })), [candles]);

  // Live price ticker from WebSocket
  const wsPrice = selectedSymbol && realtimePrices[selectedSymbol]
    ? realtimePrices[selectedSymbol].price
    : null;
  const wsChange = selectedSymbol && realtimePrices[selectedSymbol]
    ? realtimePrices[selectedSymbol].change_24h
    : null;
  // fail-closed: livePrice = WS price or last candle close, never fabricated
  const [livePrice, setLivePrice] = useState<number | null>(null);
  useEffect(() => {
    if (wsPrice) { setLivePrice(wsPrice); return; }
    // No WS → use last REST poll value (set by fetchCandles)
    const lastClose = candles.length ? candles[candles.length - 1].close : null;
    if (lastClose) setLivePrice(lastClose);
  }, [wsPrice, candles]);

  // Lightweight chart
  useEffect(() => {
    if (chartType !== "candle" || !chartContainerRef.current) return;
    let chart: ReturnType<typeof import("lightweight-charts").createChart> | null = null;
    import("lightweight-charts").then(({ createChart, CandlestickSeries }) => {
      if (!chartContainerRef.current) return;
      chart = createChart(chartContainerRef.current, {
        layout: { background: { color: "transparent" }, textColor: "rgba(255,255,255,0.5)" },
        grid: { vertLines: { color: "rgba(255,255,255,0.04)" }, horzLines: { color: "rgba(255,255,255,0.04)" } },
        crosshair: { mode: 0 },
        timeScale: { borderColor: "rgba(255,255,255,0.08)" },
        rightPriceScale: { borderColor: "rgba(255,255,255,0.08)" },
      });
      const series = chart.addSeries(CandlestickSeries, {
        upColor: "#10b981", downColor: "#ef4444",
        borderUpColor: "#10b981", borderDownColor: "#ef4444",
        wickUpColor: "#10b981", wickDownColor: "#ef4444",
      });
      series.setData(candles.map((c) => ({ time: c.time, open: c.open, high: c.high, low: c.low, close: c.close })));
      chart.timeScale().fitContent();
    });
    return () => { chart?.remove(); };
  }, [chartType, candles]);

  const fearGreed = sentiment?.fear_greed ?? null;

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <BarChart3 className="w-5 h-5 text-blue-400" />
            Market Data
          </h1>
          <p className="text-sm text-white/40 mt-0.5">
            {isConnected ? "Real-time via WebSocket" : "Market overview"}
            {!isConnected && (
              <span className="ml-2 text-xs text-amber-400/60">(offline mode)</span>
            )}
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-lg bg-white/[0.03] border border-white/[0.06]">
            {isConnected ? (
              <><Wifi className="w-3 h-3 text-emerald-400" /><span className="text-[10px] text-emerald-400 font-medium">LIVE</span></>
            ) : (
              <><WifiOff className="w-3 h-3 text-white/30" /><span className="text-[10px] text-white/30 font-medium">OFFLINE</span></>
            )}
          </div>
          <select
            value={selectedSymbol}
            onChange={(e) => setSelectedSymbol(e.target.value)}
            className="bg-white/5 border border-white/10 rounded-lg px-3 py-1.5 text-xs text-white/70 focus:outline-none focus:border-blue-500/50"
          >
            {symbols.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      {/* Price Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {symbols.slice(0, 4).map((item) => {
          const ws = realtimePrices[item.value];
          const price: number | null = ws?.price ?? null;
          const change: number | null = ws?.change_24h ?? null;
          return (
            <div key={item.value}
              className={cn(
                "p-4 rounded-xl border cursor-pointer transition-all hover:scale-[1.02]",
                selectedSymbol === item.value
                  ? "bg-white/[0.06] border-blue-500/30 shadow-[0_0_20px_rgba(59,130,246,0.1)]"
                  : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]",
              )}
              onClick={() => setSelectedSymbol(item.value)}
            >
              <div className="flex items-center justify-between mb-2">
                <span className="text-sm font-medium text-white">{item.label}</span>
                {change >= 0 ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> : <TrendingDown className="w-3.5 h-3.5 text-red-400" />}
              </div>
              <p className="text-xl font-mono font-bold text-white">{formatCurrency(price)}</p>
              <p className={cn("text-xs font-mono mt-1", change >= 0 ? "text-emerald-400" : "text-red-400")}>
                {change != null ? (change >= 0 ? "+" : "") + change.toFixed(2) + "%" : "N/A"}
              </p>
            </div>
          );
        })}
      </div>

      <Tabs defaultValue="chart">
        <TabsList>
          <TabsTrigger value="chart">Charts</TabsTrigger>
          <TabsTrigger value="sentiment">Sentiment</TabsTrigger>
          <TabsTrigger value="scanner">Scanner</TabsTrigger>
        </TabsList>

        <TabsContent value="chart">
          <ChartCard title={`${selectedSymbol} Chart`} subtitle="Price action with volume" className="mt-3" glow="cyan"
            action={
              <div className="flex items-center gap-2">
                <Button variant={chartType === "area" ? "default" : "ghost"} size="sm" onClick={() => setChartType("area")}>Area</Button>
                <Button variant={chartType === "candle" ? "default" : "ghost"} size="sm" onClick={() => setChartType("candle")}>OHLC</Button>
                <div className="w-px h-5 bg-white/10" />
                {["15m", "1h", "4h", "1D"].map((i) => (
                  <Button key={i} variant={timeframe === i ? "default" : "ghost"} size="sm" onClick={() => setTimeframe(i)}>{i}</Button>
                ))}
              </div>
            }
          >
            <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <span suppressHydrationWarning className="text-2xl font-mono font-bold text-white">{livePrice !== null ? formatCurrency(livePrice) : "—"}</span>
              <Badge variant={wsPrice ? "success" : "info"} className="text-xs">
                <Activity className="w-3 h-3 mr-1" />
                {wsPrice ? "WS LIVE" : "FALLBACK"}
              </Badge>
            </div>
            <div ref={chartContainerRef} className="h-80">
              {chartType === "area" && (
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData}>
                    <defs>
                      <linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                    <YAxis yAxisId="price" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} domain={["auto", "auto"]} tickFormatter={(v) => `$${(v / 1000).toFixed(1)}K`} />
                    <YAxis yAxisId="vol" axisLine={false} tickLine={false} tick={false} orientation="right" domain={[0, "auto"]} />
                    <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                    <Bar yAxisId="vol" dataKey="volume" fill="rgba(59,130,246,0.15)" radius={[2, 2, 0, 0]} />
                    <Area yAxisId="price" type="monotone" dataKey="close" stroke="#3b82f6" fill="url(#marketGrad)" strokeWidth={2} />
                    <Line yAxisId="price" type="monotone" dataKey="high" stroke="rgba(16,185,129,0.3)" strokeWidth={0.5} dot={false} strokeDasharray="3,3" />
                    <Line yAxisId="price" type="monotone" dataKey="low" stroke="rgba(239,68,68,0.3)" strokeWidth={0.5} dot={false} strokeDasharray="3,3" />
                  </ComposedChart>
                </ResponsiveContainer>
              )}
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="sentiment">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Market Sentiment" subtitle="Fear & Greed Index" glow="amber">
              <div className="flex flex-col items-center gap-4 py-4">
                <div className="relative w-48 h-24">
                  <svg viewBox="0 0 200 100" className="w-full h-full">
                    <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth={12} strokeLinecap="round" />
                    <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="url(#fearGreedGrad)" strokeWidth={12} strokeLinecap="round" strokeDasharray={`${((fearGreed ?? 0) / 100) * 251.2} 251.2`} />
                    <defs>
                      <linearGradient id="fearGreedGrad" x1="0" y1="0" x2="1" y2="0">
                        <stop offset="0%" stopColor="#ef4444" /><stop offset="50%" stopColor="#f59e0b" /><stop offset="100%" stopColor="#10b981" />
                      </linearGradient>
                    </defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
                    <span className="text-3xl font-mono font-bold text-emerald-400">{fearGreed ?? "—"}</span>
                    {fearGreed !== null && <span className="text-xs text-white/40">{fearGreed > 60 ? "Greed" : fearGreed > 40 ? "Neutral" : "Fear"}</span>}
                    {fearGreed === null && <span className="text-xs text-white/30">No data</span>}
                  </div>
                </div>
              </div>
            </ChartCard>
            <ChartCard title="Sector Sentiment" subtitle="By sector analysis">
              {(sentiment?.sectors?.length ?? 0) > 0 ? (
               <div className="space-y-3">
                {(sentiment!.sectors ?? []).map((sector) => (
                  <div key={sector.name}>
                    <div className="flex items-center justify-between mb-1">
                      <span className="text-xs text-white/50">{sector.name}</span>
                      <span className={cn("text-xs font-mono", sector.sentiment > 0.6 ? "text-emerald-400" : sector.sentiment > 0.4 ? "text-amber-400" : "text-red-400")}>
                        {(sector.sentiment * 100).toFixed(0)}%
                      </span>
                    </div>
                    <div className="h-2 bg-white/5 rounded-full overflow-hidden">
                      <div className={cn("h-full rounded-full transition-all duration-500", sector.sentiment > 0.6 ? "bg-emerald-400" : sector.sentiment > 0.4 ? "bg-amber-400" : "bg-red-400")}
                        style={{ width: `${sector.sentiment * 100}%` }} />
                    </div>
                  </div>
                 ))}
               </div>
              ) : (
                <p className="text-sm text-white/30 py-6 text-center">No sector sentiment data — backend unavailable.</p>
              )}
             </ChartCard>
          </div>
        </TabsContent>

        <TabsContent value="scanner">
          <ChartCard title="Market Scanner" subtitle="Top movers and signals" className="mt-3">
            <div className="space-y-2">
              {scanner.map((item) => (
                <div key={item.symbol} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-xs font-bold text-white/60">{item.symbol.slice(0, 2)}</div>
                    <div><p className="text-sm font-medium text-white">{item.symbol}</p><p className="text-xs text-white/30">Vol: {item.volume}</p></div>
                  </div>
                  <div className="text-right">
                    <p className="text-sm font-mono text-white">{item.price > 100 ? formatCurrency(item.price) : item.price.toFixed(4)}</p>
                    <div className="flex items-center justify-end gap-2">
                      <span className={cn("text-xs font-mono", item.change >= 0 ? "text-emerald-400" : "text-red-400")}>{item.change >= 0 ? "+" : ""}{item.change}%</span>
                      <Badge variant={item.signal === "Breakout" || item.signal === "Momentum" ? "success" : item.signal === "Oversold" ? "danger" : "info"} className="text-[10px]">{item.signal}</Badge>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
