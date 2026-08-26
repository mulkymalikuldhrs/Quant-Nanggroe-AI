"use client";

import { useState, useEffect, useCallback } from "react";

interface OrderFlowMapProps {
  symbol?: string;
  tick?: number;
  initialMid?: number;
}

interface OrderBookLevel {
  price: number;
  quantity: number;
  total: number;
}

interface OrderBookData {
  bids: OrderBookLevel[];
  asks: OrderBookLevel[];
  bid_depth: number;
  ask_depth: number;
  spread: number;
  mid_price: number;
  source: string;
  timestamp: string;
}

function formatPrice(price: number, symbol: string): string {
  if (symbol.includes("JPY")) return price.toFixed(3);
  if (symbol.includes("USD") && !symbol.includes("BTC") && !symbol.includes("ETH") && !symbol.includes("SOL") && !symbol.includes("BNB"))
    return price.toFixed(5);
  if (price > 1000) return price.toFixed(2);
  if (price > 1) return price.toFixed(4);
  return price.toFixed(6);
}

function formatQty(q: number): string {
  if (q >= 1000) return q.toFixed(0);
  if (q >= 1) return q.toFixed(2);
  return q.toFixed(4);
}

export default function OrderFlowMap({ symbol = "BTC-USD", tick = 0.01, initialMid = 0 }: OrderFlowMapProps) {
  const [data, setData] = useState<OrderBookData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOrderBook = useCallback(async () => {
    try {
      // Convert symbol format: BTC-USD -> BTC/USDT for Binance
      const apiSymbol = symbol
        .replace("-USD", "/USDT")
        .replace("USD", "/USD")
        .replace("XAUUSD", "XAU/USD")
        .replace("EURUSD", "EUR/USD")
        .replace("GBPUSD", "GBP/USD")
        .replace("USDJPY", "USD/JPY");

      const res = await fetch(`/api/orderbook/orderbook/${encodeURIComponent(apiSymbol)}?limit=25`);
      if (!res.ok) throw new Error(`${res.status}`);
      const json = await res.json();
      setData(json);
      setError(null);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : "fetch failed");
    } finally {
      setLoading(false);
    }
  }, [symbol]);

  useEffect(() => {
    setLoading(true);
    fetchOrderBook();
    const iv = setInterval(fetchOrderBook, 3000);
    return () => clearInterval(iv);
  }, [fetchOrderBook]);

  if (loading && !data) {
    return (
      <div className="h-full flex items-center justify-center bg-[#080b10]">
        <div className="text-center">
          <div className="animate-pulse text-2xl mb-2">📡</div>
          <div className="text-xs text-white/40">Loading order book…</div>
        </div>
      </div>
    );
  }

  if (error && !data) {
    return (
      <div className="h-full flex items-center justify-center bg-[#080b10]">
        <div className="text-center">
          <div className="text-red-400 text-sm mb-1">Order book unavailable</div>
          <div className="text-xs text-white/30">{error}</div>
          <button onClick={fetchOrderBook} className="mt-3 px-3 py-1 text-xs bg-white/5 border border-white/10 rounded hover:bg-white/10 text-white/60">
            Retry
          </button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const maxQty = Math.max(
    ...data.bids.map((l) => l.quantity),
    ...data.asks.map((l) => l.quantity),
    0.01
  );

  const bidPct = data.bid_depth / (data.bid_depth + data.ask_depth || 1) * 100;
  const askPct = 100 - bidPct;

  return (
    <div className="h-full flex flex-col bg-[#080b10] text-white overflow-hidden">
      {/* Header bar */}
      <div className="h-10 border-b border-white/[0.06] flex items-center px-4 gap-4 text-xs bg-white/[0.02] shrink-0">
        <span className="font-bold text-white">{symbol}</span>
        <span className="text-white/30">|</span>
        <span className="text-white/50">Mid: <span className="text-white font-mono">{formatPrice(data.mid_price, symbol)}</span></span>
        <span className="text-white/50">Spread: <span className="text-amber-400 font-mono">{formatPrice(data.spread, symbol)}</span></span>
        <span className="ml-auto text-white/30">{data.source} · {new Date(data.timestamp).toLocaleTimeString()}</span>
      </div>

      {/* Depth bar */}
      <div className="h-6 mx-4 mt-2 flex rounded overflow-hidden text-[10px] font-mono">
        <div className="bg-emerald-600/70 flex items-center justify-center text-white transition-all" style={{ width: `${bidPct}%` }}>
          BID {bidPct.toFixed(0)}%
        </div>
        <div className="bg-rose-600/70 flex items-center justify-center text-white transition-all" style={{ width: `${askPct}%` }}>
          ASK {askPct.toFixed(0)}%
        </div>
      </div>

      {/* Order book table */}
      <div className="flex-1 min-h-0 flex flex-col mx-4 mt-2 mb-2 overflow-hidden">
        {/* Column headers */}
        <div className="grid grid-cols-3 text-[10px] text-white/30 uppercase tracking-wider px-2 py-1 border-b border-white/[0.04]">
          <span>Price</span>
          <span className="text-right">Size</span>
          <span className="text-right">Depth</span>
        </div>

        {/* Asks (reversed — highest at top) */}
        <div className="flex-1 overflow-y-auto flex flex-col-reverse">
          {data.asks.slice(0, 15).map((level, i) => {
            const pct = (level.quantity / maxQty) * 100;
            return (
              <div key={`ask-${i}`} className="relative grid grid-cols-3 px-2 py-[3px] text-xs hover:bg-white/[0.03]">
                <div className="absolute inset-0 bg-rose-500/[0.08] transition-all" style={{ width: `${pct}%`, left: "auto", right: 0 }} />
                <span className="relative font-mono text-rose-400">{formatPrice(level.price, symbol)}</span>
                <span className="relative text-right font-mono text-white/60">{formatQty(level.quantity)}</span>
                <span className="relative text-right font-mono text-white/30">{formatQty(level.total)}</span>
              </div>
            );
          })}
        </div>

        {/* Spread separator */}
        <div className="border-y border-white/[0.08] bg-white/[0.02] px-2 py-1 text-center text-[10px] text-amber-400/80 font-mono">
          ← SPREAD {formatPrice(data.spread, symbol)} →
        </div>

        {/* Bids */}
        <div className="flex-1 overflow-y-auto">
          {data.bids.slice(0, 15).map((level, i) => {
            const pct = (level.quantity / maxQty) * 100;
            return (
              <div key={`bid-${i}`} className="relative grid grid-cols-3 px-2 py-[3px] text-xs hover:bg-white/[0.03]">
                <div className="absolute inset-0 bg-emerald-500/[0.08] transition-all" style={{ width: `${pct}%` }} />
                <span className="relative font-mono text-emerald-400">{formatPrice(level.price, symbol)}</span>
                <span className="relative text-right font-mono text-white/60">{formatQty(level.quantity)}</span>
                <span className="relative text-right font-mono text-white/30">{formatQty(level.total)}</span>
              </div>
            );
          })}
        </div>
      </div>

      {/* Footer depth totals */}
      <div className="h-8 border-t border-white/[0.06] flex items-center px-4 gap-6 text-[10px] text-white/40 bg-white/[0.02] shrink-0">
        <span>Bid depth: <span className="text-emerald-400 font-mono">{formatQty(data.bid_depth)}</span></span>
        <span>Ask depth: <span className="text-rose-400 font-mono">{formatQty(data.ask_depth)}</span></span>
        <span>Imbalance: <span className={`font-mono ${bidPct > 55 ? "text-emerald-400" : bidPct < 45 ? "text-rose-400" : "text-white/50"}`}>
          {bidPct.toFixed(1)}%
        </span></span>
      </div>
    </div>
  );
}

export type { OrderFlowMapProps };
