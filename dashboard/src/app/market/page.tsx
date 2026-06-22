"use client";

import React, { useState, useEffect, useMemo } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { formatCurrency, cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import apiRequest from "@/lib/api-client";
import { BarChart3, TrendingUp, TrendingDown, Activity, Search, Wifi, WifiOff, Loader2 } from "lucide-react";
import { Area, ComposedChart, Bar, Line, XAxis, YAxis, Tooltip as RechartsTooltip, ResponsiveContainer, CartesianGrid } from "recharts";

interface MarketSymbol {
  symbol: string; price: number; change: number; volume: string;
}

interface SentimentItem {
  name: string; sentiment: number;
}

interface ProviderItem {
  name: string; status: string; type: string; latency: string;
}

interface CandleItem {
  time: string; open: number; high: number; low: number; close: number;
}

interface ScannerItem {
  symbol: string; price: number; change: number; volume: string; signal: string;
}

export default function MarketPage() {
  const { selectedSymbol, setSelectedSymbol } = useAppStore();
  const [chartType, setChartType] = useState<"area" | "candle">("area");
  const [symbols, setSymbols] = useState<MarketSymbol[]>([]);
  const [sectorSentiment, setSectorSentiment] = useState<SentimentItem[]>([]);
  const [dataProviders, setDataProviders] = useState<ProviderItem[]>([]);
  const [candleData, setCandleData] = useState<CandleItem[]>([]);
  const [scannerData, setScannerData] = useState<ScannerItem[]>([]);
  const [livePrice, setLivePrice] = useState(0);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [sym, sent, prov, candles, scan] = await Promise.all([
          apiRequest<MarketSymbol[]>("/api/v1/market/symbols").catch(() => []),
          apiRequest<SentimentItem[]>("/api/v1/market/sentiment").catch(() => []),
          apiRequest<ProviderItem[]>("/api/v1/market/providers").catch(() => []),
          apiRequest<CandleItem[]>("/api/v1/market/candles?symbol=BTC&days=100").catch(() => []),
          apiRequest<ScannerItem[]>("/api/v1/market/scanner").catch(() => []),
        ]);
        setSymbols(sym);
        setSectorSentiment(sent);
        setDataProviders(prov);
        setCandleData(candles);
        setScannerData(scan);
        if (sym.length > 0) setLivePrice(sym[0].price);
      } finally {
        setLoading(false);
      }
    };
    load();
  }, []);

  useEffect(() => {
    if (candleData.length === 0) return;
    const interval = setInterval(async () => {
      try {
        const price = await apiRequest<{ price: number }>(`/api/v1/market/price?symbol=${selectedSymbol}`);
        setLivePrice(price.price);
      } catch {
        // keep current price
      }
    }, 5000);
    return () => clearInterval(interval);
  }, [selectedSymbol, candleData.length]);

  const chartData = useMemo(() => candleData.map((c, idx) => ({
    date: c.time.slice(5), open: c.open, high: c.high, low: c.low, close: c.close,
    volume: Math.round(400 + idx * 7.3),
  })), [candleData]);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div><h1 className="text-xl font-bold text-white flex items-center gap-2"><BarChart3 className="w-5 h-5 text-blue-400" />Market Data</h1><p className="text-sm text-white/40 mt-0.5">Real-time prices, charts & research</p></div>
        <div className="flex items-center gap-2"><Select value={selectedSymbol} onChange={(e) => setSelectedSymbol(e.target.value)} options={[{ value: "BTC", label: "BTC/USDT" }, { value: "ETH", label: "ETH/USDT" }, { value: "AAPL", label: "AAPL" }, { value: "NVDA", label: "NVDA" }, { value: "SPY", label: "SPY" }, { value: "EUR/USD", label: "EUR/USD" }]} /><Input placeholder="Search symbol..." icon={<Search className="w-3.5 h-3.5" />} className="w-40" /></div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
        {symbols.map((item) => (
          <div key={item.symbol} onClick={() => setSelectedSymbol(item.symbol)}
            className={cn("p-4 rounded-xl border cursor-pointer transition-all hover:scale-[1.02]", selectedSymbol === item.symbol ? "bg-white/[0.06] border-blue-500/30 shadow-[0_0_20px_rgba(59,130,246,0.1)]" : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.04]")}>
            <div className="flex items-center justify-between mb-2"><span className="text-sm font-medium text-white">{item.symbol}</span>{item.change >= 0 ? <TrendingUp className="w-3.5 h-3.5 text-emerald-400" /> : <TrendingDown className="w-3.5 h-3.5 text-red-400" />}</div>
            <p className="text-xl font-mono font-bold text-white">{item.symbol.includes("/") ? item.price.toFixed(4) : formatCurrency(item.price)}</p>
            <p className={cn("text-xs font-mono mt-1", item.change >= 0 ? "text-emerald-400" : "text-red-400")}>{item.change >= 0 ? "+" : ""}{item.change}%</p>
          </div>
        ))}
      </div>

      <Tabs defaultValue="chart">
        <TabsList><TabsTrigger value="chart">Charts</TabsTrigger><TabsTrigger value="sentiment">Sentiment</TabsTrigger><TabsTrigger value="scanner">Scanner</TabsTrigger><TabsTrigger value="providers">Data Providers</TabsTrigger></TabsList>
        <TabsContent value="chart">
          <ChartCard title={`${selectedSymbol} Chart`} subtitle="Price action with volume" className="mt-3" glow="blue" action={<div className="flex items-center gap-2"><Button variant={chartType === "area" ? "default" : "ghost"} size="sm" onClick={() => setChartType("area")}>Area</Button><Button variant={chartType === "candle" ? "default" : "ghost"} size="sm" onClick={() => setChartType("candle")}>OHLC</Button></div>}>
            <div className="flex items-center gap-3 mb-4 p-3 rounded-lg bg-white/[0.03] border border-white/[0.04]">
              <span className="text-2xl font-mono font-bold text-white">{formatCurrency(livePrice)}</span>
              <Badge variant="success" className="text-xs"><Activity className="w-3 h-3 mr-1" />LIVE</Badge>
              <div className="ml-auto flex items-center gap-4 text-xs text-white/40"><span>H: {formatCurrency(livePrice + 300)}</span><span>L: {formatCurrency(livePrice - 200)}</span><span>Vol: 28.5B</span></div>
            </div>
            <div className="h-80">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData.filter((_, i) => i % 2 === 0)}>
                  <defs><linearGradient id="marketGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor="#3b82f6" stopOpacity={0.3} /><stop offset="95%" stopColor="#3b82f6" stopOpacity={0} /></linearGradient></defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                  <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} />
                  <YAxis yAxisId="price" axisLine={false} tickLine={false} tick={{ fill: "rgba(255,255,255,0.3)", fontSize: 10 }} tickFormatter={(v) => `$${(v / 1000).toFixed(1)}K`} />
                  <YAxis yAxisId="vol" axisLine={false} tickLine={false} tick={false} orientation="right" />
                  <RechartsTooltip contentStyle={{ backgroundColor: "rgba(10,10,26,0.95)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: "8px", fontSize: "12px" }} />
                  <Bar yAxisId="vol" dataKey="volume" fill="rgba(59,130,246,0.15)" radius={[2, 2, 0, 0]} />
                  {chartType === "area" ? <Area yAxisId="price" type="monotone" dataKey="close" stroke="#3b82f6" fill="url(#marketGrad)" strokeWidth={2} /> : <Line yAxisId="price" type="monotone" dataKey="close" stroke="#3b82f6" strokeWidth={2} dot={false} />}
                  {chartType === "area" && <Line yAxisId="price" type="monotone" dataKey="high" stroke="rgba(16,185,129,0.3)" strokeWidth={0.5} dot={false} strokeDasharray="3,3" />}
                  {chartType === "area" && <Line yAxisId="price" type="monotone" dataKey="low" stroke="rgba(239,68,68,0.3)" strokeWidth={0.5} dot={false} strokeDasharray="3,3" />}
                  {chartType === "candle" && <Line yAxisId="price" type="monotone" dataKey="high" stroke="rgba(16,185,129,0.4)" strokeWidth={1} dot={false} />}
                  {chartType === "candle" && <Line yAxisId="price" type="monotone" dataKey="low" stroke="rgba(239,68,68,0.4)" strokeWidth={1} dot={false} />}
                </ComposedChart>
              </ResponsiveContainer>
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
                    <path d="M 20 90 A 80 80 0 0 1 180 90" fill="none" stroke="url(#fearGreedGrad)" strokeWidth={12} strokeLinecap="round" strokeDasharray={`${(72 / 100) * 251.2} 251.2`} />
                    <defs><linearGradient id="fearGreedGrad" x1="0" y1="0" x2="1" y2="0"><stop offset="0%" stopColor="#ef4444" /><stop offset="50%" stopColor="#f59e0b" /><stop offset="100%" stopColor="#10b981" /></linearGradient></defs>
                  </svg>
                  <div className="absolute inset-0 flex flex-col items-center justify-end pb-2"><span className="text-3xl font-mono font-bold text-emerald-400">72</span><span className="text-xs text-white/40">Greed</span></div>
                </div>
              </div>
            </ChartCard>
            <ChartCard title="Sector Sentiment" subtitle="By sector analysis">
              <div className="space-y-3">{sectorSentiment.length > 0 ? sectorSentiment.map((sector) => (
                <div key={sector.name}><div className="flex items-center justify-between mb-1"><span className="text-xs text-white/50">{sector.name}</span><span className={cn("text-xs font-mono", sector.sentiment > 0.6 ? "text-emerald-400" : sector.sentiment > 0.4 ? "text-amber-400" : "text-red-400")}>{(sector.sentiment * 100).toFixed(0)}%</span></div><div className="h-2 bg-white/5 rounded-full overflow-hidden"><div className={cn("h-full rounded-full transition-all duration-500", sector.sentiment > 0.6 ? "bg-emerald-400" : sector.sentiment > 0.4 ? "bg-amber-400" : "bg-red-400")} style={{ width: `${sector.sentiment * 100}%` }} /></div></div>
              )) : <p className="text-sm text-white/30 text-center py-4">No sentiment data available</p>}</div>
            </ChartCard>
          </div>
        </TabsContent>
        <TabsContent value="scanner">
          <ChartCard title="Market Scanner" subtitle="Top movers and signals" className="mt-3">
            <div className="space-y-2">
              {scannerData.length > 0 ? scannerData.map((item) => (
                <div key={item.symbol} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04] hover:bg-white/[0.04] transition-colors cursor-pointer">
                  <div className="flex items-center gap-3"><div className="w-10 h-10 rounded-lg bg-white/5 flex items-center justify-center text-xs font-bold text-white/60">{item.symbol.slice(0, 2)}</div><div><p className="text-sm font-medium text-white">{item.symbol}</p><p className="text-xs text-white/30">Vol: {item.volume}</p></div></div>
                  <div className="text-right"><p className="text-sm font-mono text-white">{item.price > 100 ? formatCurrency(item.price) : item.price.toFixed(4)}</p><div className="flex items-center justify-end gap-2"><span className={cn("text-xs font-mono", item.change >= 0 ? "text-emerald-400" : "text-red-400")}>{item.change >= 0 ? "+" : ""}{item.change}%</span><Badge variant={item.signal === "Breakout" || item.signal === "Momentum" ? "success" : item.signal === "Oversold" ? "danger" : "info"} className="text-[10px]">{item.signal}</Badge></div></div>
                </div>
              )) : <p className="text-sm text-white/30 text-center py-4">No scanner data available</p>}
            </div>
          </ChartCard>
        </TabsContent>
        <TabsContent value="providers">
          <ChartCard title="Data Providers" subtitle="Connection status" className="mt-3">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">{dataProviders.length > 0 ? dataProviders.map((provider) => (
              <div key={provider.name} className="flex items-center justify-between p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <div className="flex items-center gap-3">{provider.status === "connected" ? <Wifi className="w-4 h-4 text-emerald-400" /> : provider.status === "degraded" ? <Activity className="w-4 h-4 text-amber-400" /> : <WifiOff className="w-4 h-4 text-red-400" />}<div><p className="text-sm font-medium text-white/70">{provider.name}</p><p className="text-xs text-white/30">{provider.type}</p></div></div>
                <div className="text-right"><Badge variant={provider.status === "connected" ? "success" : provider.status === "degraded" ? "warning" : "danger"} className="text-[10px]">{provider.status}</Badge><p className="text-xs text-white/30 mt-0.5">{provider.latency}</p></div>
              </div>
            )) : <p className="text-sm text-white/30 text-center py-4 col-span-2">No provider data available</p>}</div>
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
