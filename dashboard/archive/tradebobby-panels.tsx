// TradeBobby-style panels for Quant-Nanggroe-AI Dashboard
// Macro Pulse, COT, Crypto Pulse, Setup Tracker, Agent Brief

"use client";

import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import {
  Activity, TrendingUp, TrendingDown, Globe, BarChart3,
  Shield, Zap, Radio, ArrowUp, ArrowDown, RefreshCw,
  Target, Bot,
} from "lucide-react";

/* ─── Macro Pulse Panel ─── */
interface MacroData {
  vix: number; dxy: number; gold: number; oil: number;
  us10y: number; spx: number; nasdaq: number;
  regime: string; riskIndex: number;
}

export function MacroPulsePanel() {
  const [data, setData] = useState<MacroData | null>(null);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const resp = await fetch("/api/macro-pulse");
      if (!resp.ok) throw new Error("Failed to fetch");
      const json = await resp.json();
      const m = json.macro || {};
      const r = json.regime || {};
      setData({
        vix: m.VIX?.price ?? 14.2,
        dxy: m.DXY?.price ?? 104.5,
        gold: m.GOLD?.price ?? 2420,
        oil: m.WTI?.price ?? 78.5,
        us10y: m.US10Y?.price ?? 4.25,
        spx: m.SPX?.price ?? 5520,
        nasdaq: m.NAS?.price ?? 18200,
        regime: r.regime ?? "MIXED",
        riskIndex: r.risk_index ?? 50,
      });
      setLastUpdate(json.updated_at ? new Date(json.updated_at).toLocaleTimeString() : "");
    } catch { /* keep previous data */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading || !data) {
    return (
      <Card className="p-4">
        <CardHeader><CardTitle className="text-sm">📊 Macro Pulse</CardTitle></CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[1, 2, 3].map(i => <div key={i} className="h-6 bg-white/5 rounded" />)}
          </div>
        </CardContent>
      </Card>
    );
  }

  const regimeColor = data.regime === "RISK-ON" ? "success" : data.regime === "RISK-OFF" ? "danger" : "warning";
  const riskColor = data.riskIndex < 40 ? "text-emerald-400" : data.riskIndex < 70 ? "text-yellow-400" : "text-red-400";

  const items = [
    { label: "VIX", value: data.vix.toFixed(2), color: data.vix > 20 ? "text-red-400" : "text-emerald-400" },
    { label: "DXY", value: data.dxy.toFixed(2), color: "text-blue-400" },
    { label: "GOLD", value: `$${data.gold.toFixed(0)}`, color: "text-yellow-400" },
    { label: "WTI", value: `$${data.oil.toFixed(1)}`, color: "text-orange-400" },
    { label: "10Y", value: `${data.us10y.toFixed(2)}%`, color: "text-cyan-400" },
    { label: "SPX", value: data.spx.toFixed(0), color: "text-emerald-400" },
    { label: "NAS", value: data.nasdaq.toFixed(0), color: "text-violet-400" },
  ];

  return (
    <Card className="p-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Globe className="w-4 h-4 text-blue-400" /> Macro Pulse
          </CardTitle>
          <Badge variant={regimeColor} size="sm">{data.regime}</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="mb-3 p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
          <div className="flex items-center justify-between mb-1">
            <span className="text-[10px] text-white/40 uppercase tracking-wider">Composite Risk Index</span>
            <span className={`text-lg font-mono font-bold ${riskColor}`}>{data.riskIndex}</span>
          </div>
          <div className="w-full h-1.5 bg-gray-800 rounded-full overflow-hidden">
            <div
              className={cn("h-full rounded-full transition-all duration-500",
                data.riskIndex < 40 ? "bg-emerald-500" : data.riskIndex < 70 ? "bg-yellow-500" : "bg-red-500"
              )}
              style={{ width: `${data.riskIndex}%` }}
            />
          </div>
        </div>
        <div className="grid grid-cols-4 gap-1.5">
          {items.map(item => (
            <div key={item.label} className="p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04] text-center">
              <div className="text-[9px] text-white/30 uppercase">{item.label}</div>
              <div className={cn("text-xs font-mono font-bold", item.color)}>{item.value}</div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── COT Panel ─── */
interface COTData {
  market: string; smartLong: number; retailLong: number; signal: string;
}

export function COTPanel() {
  const [markets, setMarkets] = useState<COTData[]>([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdate, setLastUpdate] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const resp = await fetch("/api/cot-data");
      if (!resp.ok) throw new Error("Failed");
      const json = await resp.json();
      const items = (json.markets || []).slice(0, 8).map((m: any) => ({
        market: m.market,
        smartLong: m.smart_long_pct,
        retailLong: m.retail_long_pct,
        signal: m.signal,
      }));
      setMarkets(items);
      setLastUpdate(json.updated_at ? new Date(json.updated_at).toLocaleTimeString() : "");
    } catch { /* keep previous data */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 300_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <Card className="p-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <BarChart3 className="w-4 h-4 text-violet-400" /> COT Positioning
          </CardTitle>
          <Badge variant="warning" size="sm">CFTC Weekly</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          {loading && markets.length === 0 ? (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3].map(i => <div key={i} className="h-6 bg-white/5 rounded" />)}
            </div>
          ) : markets.map(d => (
            <div key={d.market} className="flex items-center justify-between p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-white/70 w-16">{d.market}</span>
                <Badge variant={d.signal === "Bullish" ? "success" : d.signal === "Bearish" ? "danger" : "warning"} size="sm" className="text-[9px]">
                  {d.signal}
                </Badge>
              </div>
              <div className="flex items-center gap-3 text-[10px]">
                <span className="text-emerald-400/70">Smart {d.smartLong}%</span>
                <span className="text-white/20">vs</span>
                <span className="text-red-400/70">Retail {d.retailLong}%</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── Crypto Pulse Panel ─── */
interface CryptoData {
  symbol: string; price: number; change24h: number;
  fundingRate: number; openInterest: number;
}

export function CryptoPulsePanel() {
  const [data, setData] = useState<CryptoData[]>([]);
  const [loading, setLoading] = useState(true);
  const [fng, setFng] = useState<{ value: number; classification: string }>({ value: 50, classification: "Neutral" });
  const [lastUpdate, setLastUpdate] = useState("");

  const fetchData = useCallback(async () => {
    try {
      const resp = await fetch("/api/crypto-pulse");
      if (!resp.ok) throw new Error("Failed");
      const json = await resp.json();
      const prices = (json.prices || []).slice(0, 6).map((c: any) => {
        const fr = json.funding_rates?.[c.symbol] || {};
        return {
          symbol: c.symbol,
          price: c.price,
          change24h: c.change_24h ?? 0,
          fundingRate: fr.funding_rate ?? 0,
          openInterest: c.market_cap ? +(c.market_cap / 1e9).toFixed(1) : 0,
        };
      });
      setData(prices);
      if (json.fear_greed) setFng(json.fear_greed);
      setLastUpdate(json.updated_at ? new Date(json.updated_at).toLocaleTimeString() : "");
    } catch { /* keep previous data */ }
    setLoading(false);
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 60_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  if (loading) {
    return (
      <Card className="p-4">
        <CardHeader><CardTitle className="text-sm">🪙 Crypto Pulse</CardTitle></CardHeader>
        <CardContent>
          <div className="animate-pulse space-y-2">
            {[1, 2, 3, 4].map(i => <div key={i} className="h-8 bg-white/5 rounded" />)}
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Zap className="w-4 h-4 text-yellow-400" /> Crypto Pulse
          </CardTitle>
          <Badge variant="success" size="sm" pulse>
            <Radio className="w-3 h-3 mr-1" /> LIVE
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          {data.map(d => (
            <div key={d.symbol} className="flex items-center justify-between p-1.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold text-white w-8">{d.symbol}</span>
                <span className="text-xs font-mono text-white/70">${d.price.toLocaleString(undefined, { maximumFractionDigits: 0 })}</span>
                <span className={cn("text-[10px] font-mono flex items-center gap-0.5",
                  d.change24h >= 0 ? "text-emerald-400" : "text-red-400"
                )}>
                  {d.change24h >= 0 ? <ArrowUp className="w-2.5 h-2.5" /> : <ArrowDown className="w-2.5 h-2.5" />}
                  {Math.abs(d.change24h).toFixed(2)}%
                </span>
              </div>
              <div className="flex items-center gap-3 text-[10px] text-white/40">
                <span>Fund: {(d.fundingRate * 100).toFixed(3)}%</span>
                <span>OI: ${d.openInterest}B</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── Setup Tracker Panel ─── */
interface Setup {
  symbol: string; direction: string; score: number;
  entry: number; sl: number; tp: number; status: string; time: string;
}

export function SetupTrackerPanel() {
  const setups: Setup[] = [
    { symbol: "BTC-USD", direction: "LONG", score: 9, entry: 67200, sl: 65800, tp: 71500, status: "ACTIVE", time: "14:32" },
    { symbol: "XAUUSD", direction: "LONG", score: 8, entry: 2415, sl: 2390, tp: 2480, status: "ACTIVE", time: "13:15" },
    { symbol: "EURUSD", direction: "SHORT", score: 7, entry: 1.0875, sl: 1.0920, tp: 1.0780, status: "WATCHING", time: "12:00" },
    { symbol: "ETH-USD", direction: "LONG", score: 8, entry: 3420, sl: 3320, tp: 3650, status: "ACTIVE", time: "11:45" },
    { symbol: "SOL-USD", direction: "LONG", score: 6, entry: 172, sl: 165, tp: 195, status: "WATCHING", time: "10:20" },
  ];

  return (
    <Card className="p-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Target className="w-4 h-4 text-emerald-400" /> Setup Tracker
          </CardTitle>
          <Badge variant="success" size="sm">{setups.filter(s => s.status === "ACTIVE").length} Active</Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="space-y-1.5">
          {setups.map((s, i) => (
            <div key={i} className="p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
              <div className="flex items-center justify-between mb-1">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-bold text-white">{s.symbol}</span>
                  <Badge variant={s.direction === "LONG" ? "success" : "danger"} size="sm" className="text-[9px]">
                    {s.direction}
                  </Badge>
                </div>
                <div className="flex items-center gap-2">
                  <span className="text-[10px] font-mono text-white/40">{s.time}</span>
                  <Badge variant={s.status === "ACTIVE" ? "success" : "warning"} size="sm" className="text-[9px]">
                    {s.status}
                  </Badge>
                </div>
              </div>
              <div className="flex items-center gap-2 mb-1">
                <div className="flex-1 bg-gray-800 rounded-full h-1">
                  <div className={cn("h-1 rounded-full",
                    s.score >= 8 ? "bg-emerald-500" : s.score >= 6 ? "bg-yellow-500" : "bg-gray-600"
                  )} style={{ width: `${s.score * 10}%` }} />
                </div>
                <span className="text-[10px] text-white/40 w-4 text-right">{s.score}</span>
              </div>
              <div className="flex gap-3 text-[10px] text-white/40">
                <span>E: {s.entry.toLocaleString()}</span>
                <span className="text-red-400/60">SL: {s.sl.toLocaleString()}</span>
                <span className="text-emerald-400/60">TP: {s.tp.toLocaleString()}</span>
              </div>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

/* ─── Agent Brief Panel ─── */
export function AgentBriefPanel() {
  const [brief, setBrief] = useState<string>("");

  const fetchData = useCallback(async () => {
    try {
      const resp = await fetch("/api/news-scan");
      if (!resp.ok) throw new Error("Failed");
      const json = await resp.json();
      const sents = json.sentiments || {};
      const totalCount = json.total_count || 0;

      // Build brief from real news sentiment
      const lines: string[] = [];
      for (const [cat, info] of Object.entries(sents) as [string, any][]) {
        const emoji = info.label === "bullish" ? "🟢" : info.label === "bearish" ? "🔴" : "🟡";
        lines.push(`${emoji} ${cat.toUpperCase()}: ${info.label} (${info.avg_score}/100, ${info.count} articles)`);
      }

      // Add top headlines
      const news = json.news || {};
      const topHeadlines: string[] = [];
      for (const [cat, items] of Object.entries(news) as [string, any[]][]) {
        const top = items.slice(0, 2);
        for (const item of top) {
          const sent = item.sentiment?.score > 60 ? "🟢" : item.sentiment?.score < 40 ? "🔴" : "🟡";
          topHeadlines.push(`${sent} ${item.title}`);
        }
      }

      const briefText = lines.length > 0
        ? `Market News Scan (${totalCount} articles)\n\nSentiment by Category:\n${lines.join("\n")}\n\nTop Headlines:\n${topHeadlines.slice(0, 5).map(h => `• ${h}`).join("\n")}`
        : "No news data available. Run the news_scanner daemon to populate.";

      setBrief(briefText);
    } catch {
      setBrief("Failed to load news data. Ensure news_scanner daemon is running.");
    }
  }, []);

  useEffect(() => {
    fetchData();
    const interval = setInterval(fetchData, 300_000);
    return () => clearInterval(interval);
  }, [fetchData]);

  return (
    <Card className="p-4">
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm flex items-center gap-2">
            <Bot className="w-4 h-4 text-cyan-400" /> Agent Brief
          </CardTitle>
          <Badge variant="success" size="sm" pulse>
            <RefreshCw className="w-3 h-3 mr-1" /> Auto
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <div className="text-xs text-white/70 leading-relaxed whitespace-pre-wrap font-mono">
          {brief || (
            <div className="animate-pulse space-y-2">
              {[1, 2, 3, 4].map(i => <div key={i} className="h-3 bg-white/5 rounded" />)}
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
