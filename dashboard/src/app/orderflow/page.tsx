"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect, useRef } from "react";
import dynamicImport from "next/dynamic";
import Link from "next/link";
import { apiRequest } from "@/lib/api-client";
import { cn } from "@/lib/utils";
import { RefreshCw, Wifi, AlertCircle, ArrowUp, ArrowDown } from "lucide-react";

/* ─── dynamic import canvas-heavy map ───────────────────────────── */
const OrderFlowMap = dynamicImport(() => import("@/components/OrderFlowMap"), {
  ssr: false,
  loading: () => (
    <div className="h-full flex items-center justify-center bg-[#080b10] text-gray-500">
      <div className="text-center">
        <div className="animate-pulse text-2xl mb-2">🔥</div>
        <div className="text-xs">Loading OrderFlowMap…</div>
      </div>
    </div>
  ),
});

const DerivativesRibbon = dynamicImport(
  () => import("@/components/terminal/derivatives-ribbon").then(m => ({ default: m.DerivativesRibbon })),
  { ssr: false, loading: () => <div className="bbg-cell h-10 animate-pulse" /> }
);

/* ─── instruments ──────────────────────────────────────────────── */
const INSTRUMENTS = [
  // Crypto
  { sym: "BTC-USD", name: "Bitcoin", tick: 0.01, mid: 67500, cat: "Crypto" },
  { sym: "ETH-USD", name: "Ethereum", tick: 0.01, mid: 3450, cat: "Crypto" },
  { sym: "SOL-USD", name: "Solana", tick: 0.01, mid: 175, cat: "Crypto" },
  { sym: "BNB-USD", name: "BNB", tick: 0.01, mid: 590, cat: "Crypto" },
  { sym: "XRP-USD", name: "XRP", tick: 0.0001, mid: 0.62, cat: "Crypto" },
  { sym: "DOGE-USD", name: "Dogecoin", tick: 0.00001, mid: 0.145, cat: "Crypto" },
  { sym: "ADA-USD", name: "Cardano", tick: 0.0001, mid: 0.45, cat: "Crypto" },
  { sym: "AVAX-USD", name: "Avalanche", tick: 0.01, mid: 35, cat: "Crypto" },
  // Exchange
  { sym: "BTCUSDT", name: "BTC/USDT", tick: 0.01, mid: 67500, cat: "Exchange" },
  { sym: "ETHUSDT", name: "ETH/USDT", tick: 0.01, mid: 3450, cat: "Exchange" },
  { sym: "SOLUSDT", name: "SOL/USDT", tick: 0.01, mid: 175, cat: "Exchange" },
  // Forex
  { sym: "EURUSD", name: "EUR/USD", tick: 0.00001, mid: 1.0875, cat: "Forex" },
  { sym: "GBPUSD", name: "GBP/USD", tick: 0.00001, mid: 1.2750, cat: "Forex" },
  { sym: "USDJPY", name: "USD/JPY", tick: 0.001, mid: 157.5, cat: "Forex" },
  { sym: "AUDUSD", name: "AUD/USD", tick: 0.00001, mid: 0.6575, cat: "Forex" },
  // Commodities
  { sym: "XAUUSD", name: "Gold", tick: 0.01, mid: 2420, cat: "Commodities" },
  { sym: "XAGUSD", name: "Silver", tick: 0.01, mid: 28.5, cat: "Commodities" },
  { sym: "WTIUSD", name: "Crude Oil", tick: 0.01, mid: 78.5, cat: "Commodities" },
];

const CATEGORIES = ["All", "Crypto", "Exchange", "Forex", "Commodities"];

/* ─── helpers (mirror terminal page) ───────────────────────────── */
const REFRESH_MS = 15000;
const API = (ep: string) => `/api/terminal/${ep}`;

function clsPct(v: number | null | undefined) {
  if (v == null) return "text-white/30";
  if (v > 0) return "text-profit";
  if (v < 0) return "text-loss";
  return "text-white/70";
}
function fmtPct(v: number | null | undefined) {
  if (v == null) return "—";
  return `${v >= 0 ? "+" : ""}${v.toFixed(2)}%`;
}
function fmtNum(n: number | null | undefined, d = 2) {
  if (n == null) return "—";
  return n.toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d });
}

/* ─── fetch hook ───────────────────────────────────────────────── */
function useFlowData<T>(endpoint: string, fallback: T) {
  const [data, setData] = useState<T>(fallback);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const mounted = useRef(true);

  const refresh = React.useCallback(async () => {
    try {
      const res = await apiRequest<T>(API(endpoint), { deduplicate: false });
      if (mounted.current) { setData(res); setError(null); }
    } catch (e: any) {
      if (mounted.current) setError(e?.message || "fetch failed");
    } finally {
      if (mounted.current) setLoading(false);
    }
  }, [endpoint]);

  useEffect(() => {
    mounted.current = true;
    refresh();
    const id = setInterval(refresh, REFRESH_MS);
    return () => { mounted.current = false; clearInterval(id); };
  }, [refresh]);

  return { data, loading, error, refresh };
}

/* ─── Panel wrapper (same as terminal bbg-cell) ────────────────── */
function Panel({ title, loading, error, children, onRefresh }: {
  title: string; loading?: boolean; error?: string | null;
  children: React.ReactNode; onRefresh?: () => void;
}) {
  return (
    <div className="bbg-cell p-0 flex flex-col" style={{ minHeight: 180 }}>
      <div className="flex items-center justify-between px-2.5 py-1.5 border-b border-white/[0.04] bg-black/20">
        <span className="text-[9px] font-bold uppercase tracking-[1.2px] text-amber-400/90 flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 bg-amber-400/70 inline-block rounded-sm" />
          {title}
        </span>
        <div className="flex items-center gap-1">
          {loading && <span className="w-2 h-2 rounded-full bg-amber-400/50 animate-pulse" />}
          {onRefresh && (
            <button onClick={onRefresh} className="p-0.5 hover:bg-white/5 rounded">
              <RefreshCw className="w-2.5 h-2.5 text-white/30" />
            </button>
          )}
        </div>
      </div>
      <div className="flex-1 p-2.5 text-[11px] font-mono overflow-auto">
        {error ? (
          <div className="flex items-center gap-1.5 text-loss/80 text-[10px] h-full">
            <AlertCircle className="w-3 h-3 shrink-0" />
            <span>{error}</span>
          </div>
        ) : children}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   CVD SUMMARY PANEL
   ════════════════════════════════════════════════════════════════════ */
function CVDSummary({ symbol }: { symbol: string }) {
  const { data, loading, error, refresh } = useFlowData<Record<string, any>>("cvd", {});
  const d = data as any;
  const syms: any[] = d?.symbols || [];
  const match = syms.find((s: any) => s.symbol === symbol) || syms[0];

  return (
    <Panel title="CVD Summary" loading={loading} error={error} onRefresh={refresh}>
      {!match ? (
        <div className="text-[10px] text-white/20 text-center py-4">No CVD data for {symbol}</div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-baseline justify-between">
            <span className="text-[9px] text-white/40 uppercase">{match.symbol}</span>
            <span className="text-[10px] text-white/60">{fmtNum(match.price)}</span>
          </div>

          <div className="grid grid-cols-2 gap-1.5">
            <div className="bg-black/20 rounded p-1.5 border border-white/[0.04]">
              <div className="text-[8px] text-white/30 uppercase">CVD Delta</div>
              <div className={cn("text-sm font-bold", (match.cvd_delta ?? 0) >= 0 ? "text-profit" : "text-loss")}>
                {fmtNum(match.cvd_delta, 0)}
              </div>
            </div>
            <div className="bg-black/20 rounded p-1.5 border border-white/[0.04]">
              <div className="text-[8px] text-white/30 uppercase">Change</div>
              <div className={cn("text-sm font-bold", clsPct(match.change_pct))}>
                {fmtPct(match.change_pct)}
              </div>
            </div>
          </div>

          <div className="space-y-1">
            <div className="flex justify-between text-[9px]">
              <span className="text-white/40">Classification</span>
              <span className={cn(
                match.classification?.includes("AGGRESSIVE") ? "text-orange-400" :
                match.classification?.includes("BUYING") ? "text-profit" :
                match.classification?.includes("SELLING") ? "text-loss" : "text-white/30"
              )}>{match.classification || "—"}</span>
            </div>
            <div className="flex justify-between text-[9px]">
              <span className="text-white/40">Divergence</span>
              <span className={cn(
                match.divergence?.includes("DISTRIBUTION") ? "text-loss" :
                match.divergence?.includes("ACCUMULATION") ? "text-profit" : "text-white/30"
              )}>{match.divergence || "—"}</span>
            </div>
            {match.buy_vol != null && (
              <div className="flex justify-between text-[9px]">
                <span className="text-white/40">Buy Vol</span>
                <span className="text-profit">{fmtNum(match.buy_vol, 0)}</span>
              </div>
            )}
            {match.sell_vol != null && (
              <div className="flex justify-between text-[9px]">
                <span className="text-white/40">Sell Vol</span>
                <span className="text-loss">{fmtNum(match.sell_vol, 0)}</span>
              </div>
            )}
          </div>

          {/* mini CVD bar */}
          {match.buy_vol != null && match.sell_vol != null && (
            <div className="h-2 rounded-full overflow-hidden flex bg-white/5">
              <div className="bg-profit/60 h-full" style={{ width: `${Math.min((match.buy_vol / (match.buy_vol + match.sell_vol)) * 100, 100)}%` }} />
              <div className="bg-loss/60 h-full flex-1" />
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}

/* ════════════════════════════════════════════════════════════════════
   LIQUIDITY WALLS PANEL (filtered to selected symbol)
   ════════════════════════════════════════════════════════════════════ */
function LiquidityWallsPanel({ symbol }: { symbol: string }) {
  const { data: raw, loading, error, refresh } = useFlowData<Record<string, any>>("liquidity-walls", {});
  const d = raw as any;
  const walls: Record<string, any> = d?.walls || {};

  // Try exact match first, then fuzzy
  const matchKey = Object.keys(walls).find(k => k === symbol)
    || Object.keys(walls).find(k => symbol.includes(k) || k.includes(symbol.split("-")[0]))
    || Object.keys(walls)[0];
  const w = matchKey ? walls[matchKey] : null;
  const bids: any[] = w?.bid_walls || [];
  const asks: any[] = w?.ask_walls || [];

  return (
    <Panel title="Liquidity Walls" loading={loading} error={error} onRefresh={refresh}>
      {!w ? (
        <div className="text-[10px] text-white/20 text-center py-4">No wall data for {symbol}</div>
      ) : (
        <div className="space-y-2">
          <div className="text-[9px] text-white/40 uppercase">{matchKey}</div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <div className="text-[8px] text-profit/70 uppercase tracking-wider mb-1">Bids (Support)</div>
              {bids.length === 0 ? (
                <div className="text-[9px] text-white/20">—</div>
              ) : bids.slice(0, 5).map((b: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-[9px] py-0.5 border-b border-white/[0.02]">
                  <span className="text-profit/80">{fmtNum(b.price)}</span>
                  <span className="text-white/40">{fmtNum(b.size ?? b.volume, 0)}</span>
                </div>
              ))}
            </div>
            <div>
              <div className="text-[8px] text-loss/70 uppercase tracking-wider mb-1">Asks (Resistance)</div>
              {asks.length === 0 ? (
                <div className="text-[9px] text-white/20">—</div>
              ) : asks.slice(0, 5).map((a: any, i: number) => (
                <div key={i} className="flex items-center justify-between text-[9px] py-0.5 border-b border-white/[0.02]">
                  <span className="text-loss/80">{fmtNum(a.price)}</span>
                  <span className="text-white/40">{fmtNum(a.size ?? a.volume, 0)}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </Panel>
  );
}

/* ════════════════════════════════════════════════════════════════════
   TRADE TAPE (recent trades with buy/sell coloring)
   ════════════════════════════════════════════════════════════════════ */
interface Trade {
  price: number;
  size: number;
  side: "buy" | "sell" | string;
  time: string;
}

function TradeTape({ symbol }: { symbol: string }) {
  const { data, loading, error, refresh } = useFlowData<Record<string, any>>("trade-tape", {});
  const d = data as any;
  const allTrades: Trade[] = d?.trades || d?.recent_trades || [];
  // Filter by symbol if available, otherwise show all
  const trades = allTrades.filter((t: any) => !t.symbol || t.symbol === symbol).slice(0, 30);

  return (
    <Panel title="Trade Tape" loading={loading} error={error} onRefresh={refresh}>
      {trades.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">No recent trades</div>
      ) : (
        <div className="space-y-0 max-h-[200px] overflow-y-auto">
          {/* header */}
          <div className="flex items-center text-[8px] text-white/30 uppercase pb-1 border-b border-white/[0.04] sticky top-0 bg-[#0b0e15]">
            <span className="w-12">Time</span>
            <span className="flex-1 text-right">Price</span>
            <span className="w-16 text-right">Size</span>
            <span className="w-10 text-right">Side</span>
          </div>
          {trades.map((t: Trade, i: number) => {
            const isBuy = t.side?.toLowerCase() === "buy";
            const isSell = t.side?.toLowerCase() === "sell";
            return (
              <div
                key={i}
                className={cn(
                  "flex items-center text-[9px] py-0.5 border-b border-white/[0.02] transition-colors",
                  isBuy && "bg-profit/[0.03]",
                  isSell && "bg-loss/[0.03]",
                )}
              >
                <span className="w-12 text-white/30">{t.time || "—"}</span>
                <span className={cn("flex-1 text-right font-medium", isBuy ? "text-profit" : isSell ? "text-loss" : "text-white/50")}>
                  {fmtNum(t.price)}
                </span>
                <span className="w-16 text-right text-white/50">{fmtNum(t.size, 0)}</span>
                <span className={cn("w-10 text-right flex items-center justify-end gap-0.5", isBuy ? "text-profit" : "text-loss")}>
                  {isBuy ? <ArrowUp className="w-2 h-2" /> : isSell ? <ArrowDown className="w-2 h-2" /> : null}
                  {t.side?.slice(0, 3)?.toUpperCase() || "—"}
                </span>
              </div>
            );
          })}
        </div>
      )}
    </Panel>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PAGE ROOT
   ════════════════════════════════════════════════════════════════════ */
export default function OrderFlowPage() {
  const [selected, setSelected] = useState(INSTRUMENTS[0]);
  const [showPicker, setShowPicker] = useState(false);
  const [category, setCategory] = useState("All");
  const [search, setSearch] = useState("");
  const pickerRef = useRef<HTMLDivElement>(null);
  const searchRef = useRef<HTMLInputElement>(null);

  const filtered = INSTRUMENTS.filter(s => {
    if (category !== "All" && s.cat !== category) return false;
    if (search && !s.sym.toLowerCase().includes(search.toLowerCase()) && !s.name.toLowerCase().includes(search.toLowerCase())) return false;
    return true;
  });

  // Close picker on outside click
  useEffect(() => {
    if (!showPicker) return;
    const handler = (e: MouseEvent) => {
      if (pickerRef.current && !pickerRef.current.contains(e.target as Node)) setShowPicker(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [showPicker]);

  // Close picker on Escape
  useEffect(() => {
    if (!showPicker) return;
    const handler = (e: KeyboardEvent) => { if (e.key === "Escape") setShowPicker(false); };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, [showPicker]);

  // Focus search on open
  useEffect(() => {
    if (showPicker && searchRef.current) searchRef.current.focus();
  }, [showPicker]);

  return (
    <div className="h-screen flex flex-col">
      {/* ─── top bar ──────────────────────────────────────────────── */}
      <div className="h-8 border-b border-white/[0.06] flex items-center px-3 gap-3 text-xs bg-white/[0.02]">
        <Link href="/" className="text-white/40 hover:text-white transition-colors">← Dashboard</Link>
        <span className="text-white/20">|</span>
        <Link href="/terminal" className="text-white/40 hover:text-white transition-colors">Terminal</Link>
        <span className="text-white/20">|</span>
        <span className="text-white/60 font-medium">🔥 Order Flow</span>
        <div className="ml-auto flex items-center gap-2">
          <div className="flex items-center gap-1 px-2 py-0.5 rounded bg-white/[0.04] border border-white/[0.06]">
            <Wifi className="w-3 h-3 text-profit" />
            <span className="text-[9px] font-mono text-white/50">LIVE</span>
          </div>
          {/* instrument picker */}
          <div className="relative" ref={pickerRef}>
            <button
              onClick={() => { setShowPicker(!showPicker); setSearch(""); }}
              className="px-2 py-0.5 bg-white/[0.04] border border-white/[0.06] rounded text-xs text-white font-bold hover:bg-white/[0.08] transition-colors flex items-center gap-1.5"
            >
              <span className="text-amber-400/80">{selected.sym}</span>
              <span className="text-white/30 text-[10px]">{selected.name}</span>
              <span className="text-white/20">▾</span>
            </button>
            {showPicker && (
              <div className="absolute top-full right-0 mt-1 w-72 bg-[#0e131b] border border-white/[0.08] rounded-md shadow-xl z-50 overflow-hidden">
                {/* search */}
                <div className="p-1.5 border-b border-white/[0.06]">
                  <input
                    ref={searchRef}
                    value={search}
                    onChange={e => setSearch(e.target.value)}
                    placeholder="Search symbol..."
                    className="w-full bg-black/30 border border-white/[0.06] rounded px-2 py-1 text-[11px] text-white placeholder:text-white/20 outline-none focus:border-amber-400/30"
                  />
                </div>
                {/* category tabs */}
                <div className="flex gap-0.5 px-1.5 pt-1.5 pb-1 border-b border-white/[0.06]">
                  {CATEGORIES.map(c => (
                    <button
                      key={c}
                      onClick={() => setCategory(c)}
                      className={cn(
                        "px-1.5 py-0.5 rounded text-[9px] font-medium transition-colors",
                        category === c ? "bg-amber-400/10 text-amber-400" : "text-white/40 hover:text-white/60"
                      )}
                    >
                      {c}
                    </button>
                  ))}
                </div>
                {/* list */}
                <div className="max-h-60 overflow-y-auto">
                  {filtered.length === 0 ? (
                    <div className="px-3 py-3 text-[10px] text-white/30 text-center">No matches</div>
                  ) : filtered.map((s, i) => (
                    <button
                      key={`${s.sym}-${i}`}
                      onClick={() => { setSelected(s); setShowPicker(false); }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs hover:bg-white/[0.05] flex justify-between items-center",
                        selected.sym === s.sym ? "bg-white/[0.05] text-white" : "text-white/70"
                      )}
                    >
                      <div className="flex items-center gap-2">
                        <span className="font-bold">{s.sym}</span>
                        <span className="text-white/30 text-[10px]">{s.name}</span>
                      </div>
                      <span className="text-[9px] text-white/20 bg-white/[0.04] px-1 rounded">{s.cat}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ─── derivatives ribbon (full width) ─────────────────────── */}
      <div className="px-2 pt-2">
        <DerivativesRibbon />
      </div>

      {/* ─── main area: 70% chart + 30% side panels ─────────────── */}
      <div className="flex-1 min-h-0 flex gap-2 p-2 pt-1">
        {/* chart 70% */}
        <div className="w-[70%] min-w-0">
          <OrderFlowMap
            symbol={selected.sym}
            tick={selected.tick}
            initialMid={selected.mid}
          />
        </div>

        {/* side panels 30% */}
        <div className="w-[30%] flex flex-col gap-2 overflow-y-auto">
          <CVDSummary symbol={selected.sym} />
          <LiquidityWallsPanel symbol={selected.sym} />
          <TradeTape symbol={selected.sym} />
        </div>
      </div>
    </div>
  );
}
