"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Dialog } from "@/components/ui/dialog";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { Tooltip } from "@/components/ui/tooltip";
import { useRealtimeData } from "@/lib/websocket";
import { useAppStore } from "@/lib/store";
import { cn, formatCurrency, formatPercent, formatPrice, pnlColor } from "@/lib/utils";
import { brokersApi, marketApi } from "@/lib/api-client";
import type { MT5AccountInfo, BrokerPositionsResponse, OrderType } from "@/lib/api-client";
import {
  ArrowLeftRight, Send, RefreshCw, Wallet, TrendingUp, Activity,
  Plug, Unplug, Settings, BarChart3, Globe, X,
  BookOpen, ListOrdered, Star, Clock, ChevronDown, ChevronRight,
  Keyboard, Percent, DollarSign, SlidersHorizontal,
} from "lucide-react";

const WATCHLIST_DEFAULT = ["BTC/USDT", "ETH/USDT", "XAU/USD", "NVDA", "AAPL"];
const KEYBOARD_SHORTCUTS = [
  { key: "Ctrl+Enter", action: "Submit order" },
  { key: "F1", action: "Toggle Buy/Sell" },
  { key: "Esc", action: "Close modal" },
  { key: "↑/↓", action: "Adjust qty by 0.1" },
  { key: "Ctrl+C", action: "Close selected position" },
];

interface BrokerAccountUI {
  id: string; name: string; broker: string;
  type: "mt5" | "crypto" | "ibkr" | "simulated";
  status: "connected" | "disconnected" | "error";
  balance: number; equity: number; margin: number;
  marginLevel: number; leverage: number; currency: string;
  server: string; login: string;
}

interface PositionUI {
  id: string; symbol: string; side: "long" | "short";
  quantity: number; entryPrice: number; currentPrice: number;
  pnl: number; pnlPercent: number; stopLoss: number; takeProfit: number;
  broker: string; account: string; timestamp: string;
  trailingStop: boolean; ticket?: number | null;
}

interface OrderBookLevel {
  price: number; size: number; total: number;
}

interface TradeTick {
  price: number; size: number; side: "buy" | "sell"; time: string;
}

function computeEstimatedCost(side: string, qty: number, price: number): number {
  return qty * price;
}

function computeRiskPercent(entry: number, stop: number, qty: number, balance: number, side: string): number {
  if (!stop || !balance) return 0;
  const riskPerUnit = side === "buy" ? entry - stop : stop - entry;
  return (riskPerUnit * qty / balance) * 100;
}

function TradingDashboardContent() {
  useRealtimeData();
  const { realtimePrices, refreshAll } = useAppStore();

  const [activeAccount, setActiveAccount] = useState("");
  const [orderSymbol, setOrderSymbol] = useState("BTC/USDT");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState("market");
  const [orderQty, setOrderQty] = useState("0.01");
  const [orderPrice, setOrderPrice] = useState("");
  const [orderSL, setOrderSL] = useState("");
  const [orderTP, setOrderTP] = useState("");
  const [ocoPrice, setOcoPrice] = useState("");
  const [ocoSL, setOcoSL] = useState("");
  const [ocoTP, setOcoTP] = useState("");
  const [loading, setLoading] = useState(true);
  const [orderMsg, setOrderMsg] = useState("");
  const [accounts, setAccounts] = useState<BrokerAccountUI[]>([]);
  const [positions, setPositions] = useState<PositionUI[]>([]);
  const [restPrices, setRestPrices] = useState<Record<string, { price: number; change: number }>>({});
  const [previewOpen, setPreviewOpen] = useState(false);
  const [closePosId, setClosePosId] = useState<string | null>(null);
  const [closePercent, setClosePercent] = useState("100");
  const [modifyPosId, setModifyPosId] = useState<string | null>(null);
  const [newSL, setNewSL] = useState("");
  const [newTP, setNewTP] = useState("");
  const [showShortcuts, setShowShortcuts] = useState(false);
  const [orderBookOpen, setOrderBookOpen] = useState(true);
  const [watchlist, setWatchlist] = useState<string[]>(() => {
    if (typeof window === "undefined") return WATCHLIST_DEFAULT;
    try { const stored = localStorage.getItem("qna-watchlist"); return stored ? JSON.parse(stored) : WATCHLIST_DEFAULT; }
    catch { return WATCHLIST_DEFAULT; }
  });
  const [newWatchSymbol, setNewWatchSymbol] = useState("");
  const [orderBook, setOrderBook] = useState<{ bids: OrderBookLevel[]; asks: OrderBookLevel[] } | null>(null);
  // REAL-ONLY: time&sales show empty until backend provides real tick data
  const [trades, setTrades] = useState<TradeTick[]>([]);

  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      setLoading(true);
      try {
        const list = await brokersApi.list();
        if (cancelled || !list.accounts?.length) { setLoading(false); return; }
        const infoResults = await Promise.allSettled(list.accounts.map(b => brokersApi.account(b.name)));
        const posResults = await Promise.allSettled(list.accounts.map(b => brokersApi.positions(b.name)));
        if (cancelled) return;

        const uiAccounts: BrokerAccountUI[] = list.accounts.map((b, i) => {
          const info = infoResults[i].status === "fulfilled" ? (infoResults[i] as PromiseFulfilledResult<MT5AccountInfo>).value : null;
          return {
            id: b.name, name: b.name, broker: b.role || b.name, type: "mt5" as const,
            status: b.connected ? "connected" as const : "disconnected" as const,
            balance: info?.balance ?? 0, equity: info?.equity ?? 0,
            margin: info?.margin ?? 0, marginLevel: info?.margin_level ?? 0,
            leverage: info?.leverage ?? 0, currency: info?.currency ?? "USD",
            server: info?.server ?? "", login: info?.login?.toString() ?? "",
          };
        });
        setAccounts(uiAccounts);
        if (!activeAccount && uiAccounts.length) setActiveAccount(uiAccounts[0].id);

        const allPositions: PositionUI[] = [];
        posResults.forEach((res, i) => {
          if (res.status === "fulfilled") {
            const brokerName = list.accounts[i].name;
            for (const p of res.value.positions || []) {
              allPositions.push({
                id: `${brokerName}-${p.symbol}`, symbol: p.symbol,
                side: (p.side === "short" ? "short" : "long") as "long" | "short",
                quantity: p.quantity, entryPrice: p.entry_price,
                currentPrice: p.current_price, pnl: p.unrealized_pnl,
                pnlPercent: p.entry_price > 0
                  ? ((p.current_price - p.entry_price) / p.entry_price) * 100 * (p.side === "short" ? -1 : 1)
                  : 0,
                stopLoss: (p as { stop_loss?: number | null }).stop_loss ?? 0,
                takeProfit: (p as { take_profit?: number | null }).take_profit ?? 0,
                broker: brokerName, account: brokerName,
                timestamp: new Date().toISOString(), trailingStop: false,
                ticket: (p as { ticket?: number | null }).ticket ?? null,
              });
            }
          }
        });
        setPositions(allPositions);
      } catch { /* empty state */ }
      if (!cancelled) setLoading(false);
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (Object.keys(realtimePrices).length > 0) return;
    let cancelled = false;
    const load = async () => {
      const res = await Promise.allSettled(watchlist.map(s => marketApi.getPrice(s)));
      if (cancelled) return;
      const next: Record<string, { price: number; change: number }> = {};
      res.forEach((r, i) => {
        if (r.status === "fulfilled" && r.value.price != null) {
          next[watchlist[i]] = { price: r.value.price, change: r.value.change ?? 0 };
        }
      });
      setRestPrices(next);
    };
    load();
    const id = setInterval(load, 15000);
    return () => { cancelled = true; clearInterval(id); };
  }, [realtimePrices, watchlist]);

  // REAL-ONLY no-data guard: order book and time&sales render only from WS/REST feed.
  // REAL-ONLY: order book and time&sales show NO DATA when backend doesn't provide them.
  // Previously these were Math.random() fabricated — hedge-fund integrity violation.
  // Data comes from WebSocket or REST when available.

  const activeAcct = accounts.find(a => a.id === activeAccount);
  const accountPositions = positions.filter(p => p.account === activeAccount);

  const totalEquity = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.equity, 0);
  const totalBalance = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.balance, 0);
  const totalPnl = positions.reduce((s, p) => s + p.pnl, 0);
  const totalMargin = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.margin, 0);
  const winningPos = positions.filter(p => p.pnl > 0).length;
  const winRate = positions.length > 0 ? (winningPos / positions.length * 100) : 0;
  const avgRR = positions.length > 0
    ? positions.reduce((s, p) => s + Math.abs(p.pnlPercent), 0) / positions.length
    : 0;
  const openPnl = totalPnl;

  const qtyNum = parseFloat(orderQty) || 0;
  const priceNum = parseFloat(orderPrice) || (restPrices[orderSymbol]?.price || 0);
  const slNum = parseFloat(orderSL) || 0;
  const tpNum = parseFloat(orderTP) || 0;
  const estimatedCost = computeEstimatedCost(orderSide, qtyNum, priceNum);
  const riskPercent = computeRiskPercent(priceNum, slNum, qtyNum, activeAcct?.balance || 1, orderSide);

  const addToWatchlist = () => {
    if (!newWatchSymbol || watchlist.includes(newWatchSymbol)) return;
    const next = [...watchlist, newWatchSymbol.toUpperCase()];
    setWatchlist(next);
    localStorage.setItem("qna-watchlist", JSON.stringify(next));
    setNewWatchSymbol("");
  };

  const removeFromWatchlist = (sym: string) => {
    const next = watchlist.filter(s => s !== sym);
    setWatchlist(next);
    localStorage.setItem("qna-watchlist", JSON.stringify(next));
  };

  const submitOrder = async () => {
    if (!activeAcct) return;
    setOrderMsg("Placing order...");
    try {
      const body: Record<string, unknown> = {
        symbol: orderSymbol, side: orderSide, type: orderType as OrderType,
        quantity: qtyNum, price: orderType === "limit" || orderType === "stop_limit" || orderType === "stop" ? priceNum : undefined,
        stopLoss: slNum || undefined, takeProfit: tpNum || undefined,
      };
      if (orderType === "oco") {
        body.oco = { price: parseFloat(ocoPrice) || 0, stopLoss: parseFloat(ocoSL) || 0, takeProfit: parseFloat(ocoTP) || 0 };
      }
      await brokersApi.placeOrder(activeAcct.name, body);
      setOrderMsg(`✓ Order placed on ${activeAcct.name}`);
      setPreviewOpen(false);
    } catch (e) {
      setOrderMsg(`✗ ${e instanceof Error ? e.message : "Order failed"}`);
    }
    setTimeout(() => setOrderMsg(""), 5000);
  };

  const closePosition = async (pos: PositionUI, pct: number) => {
    if (!activeAcct) return;
    try {
      if (pos.ticket == null) {
        throw new Error("No ticket for position — cannot close via broker");
      }
      const volume = pct < 100 ? pos.quantity * (pct / 100) : undefined;
      await brokersApi.closePosition(activeAcct.name, pos.ticket, volume);
      setOrderMsg(`✓ Closed ${pct}% of ${pos.symbol}`);
      setClosePosId(null);
    } catch (e) {
      setOrderMsg(`✗ Close failed: ${e instanceof Error ? e.message : "error"}`);
    }
    setTimeout(() => setOrderMsg(""), 5000);
  };

  const openModify = (pos: PositionUI) => {
    setModifyPosId(pos.id);
    setNewSL(pos.stopLoss ? String(pos.stopLoss) : "");
    setNewTP(pos.takeProfit ? String(pos.takeProfit) : "");
  };

  const modifySLTP = async (pos: PositionUI) => {
    if (!activeAcct) return;
    try {
      if (pos.ticket == null) {
        throw new Error("No ticket for position — cannot modify via broker");
      }
      const sl = newSL.trim() === "" ? null : parseFloat(newSL);
      const tp = newTP.trim() === "" ? null : parseFloat(newTP);
      if (sl !== null && (isNaN(sl) || sl <= 0)) throw new Error("Invalid SL");
      if (tp !== null && (isNaN(tp) || tp <= 0)) throw new Error("Invalid TP");
      await brokersApi.modifyPosition(activeAcct.name, pos.ticket, sl, tp);
      setOrderMsg(`✓ SL/TP updated for ${pos.symbol}`);
      setModifyPosId(null);
    } catch (e) {
      setOrderMsg(`✗ Modify failed: ${e instanceof Error ? e.message : "error"}`);
    }
    setTimeout(() => setOrderMsg(""), 5000);
  };

  const toggleTrailingStop = (posId: string) => {
    setPositions(prev => prev.map(p => p.id === posId ? { ...p, trailingStop: !p.trailingStop } : p));
  };

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === "F1") { e.preventDefault(); setOrderSide(s => s === "buy" ? "sell" : "buy"); }
      if (e.key === "ArrowUp" && e.target instanceof HTMLInputElement) {
        const inp = e.target as HTMLInputElement;
        if (inp.type === "number") { inp.stepUp(); inp.dispatchEvent(new Event("input", { bubbles: true })); }
      }
      if (e.key === "ArrowDown" && e.target instanceof HTMLInputElement) {
        const inp = e.target as HTMLInputElement;
        if (inp.type === "number") { inp.stepDown(); inp.dispatchEvent(new Event("input", { bubbles: true })); }
      }
    };
    document.addEventListener("keydown", handler);
    return () => document.removeEventListener("keydown", handler);
  }, []);

  const positionColumns = [
    { key: "symbol", label: "Symbol", render: (r: PositionUI) => <span className="font-medium text-white">{r.symbol}</span>, width: "90px" },
    { key: "side", label: "Side", sortable: true, render: (r: PositionUI) => (
      <Badge variant={r.side === "long" ? "success" : "danger"} size="sm">{r.side.toUpperCase()}</Badge>
    ), width: "55px" },
    { key: "quantity", label: "Qty", align: "right" as const, render: (r: PositionUI) => <span className="font-mono">{r.quantity}</span>, width: "65px" },
    { key: "entryPrice", label: "Entry", align: "right" as const, render: (r: PositionUI) => <span className="font-mono text-white/60">{formatPrice(r.entryPrice, "$")}</span>, width: "85px" },
    { key: "currentPrice", label: "Current", align: "right" as const, render: (r: PositionUI) => <span className="font-mono">{formatPrice(r.currentPrice, "$")}</span>, width: "85px" },
    { key: "pnl", label: "P&L", align: "right" as const, sortable: true, render: (r: PositionUI) => (
      <span className={cn("font-mono font-medium transition-colors duration-300", pnlColor(r.pnl))}>{formatCurrency(r.pnl)}</span>
    ), width: "100px" },
    { key: "pnlPercent", label: "P&L %", align: "right" as const, render: (r: PositionUI) => (
      <span className={cn("font-mono text-xs", pnlColor(r.pnlPercent))}>{formatPercent(r.pnlPercent)}</span>
    ), width: "70px" },
    { key: "trailing", label: "Trail", render: (r: PositionUI) => (
      <button
        onClick={() => toggleTrailingStop(r.id)}
        className={cn("px-1.5 py-0.5 rounded text-[10px] font-mono border transition-colors",
          r.trailingStop
            ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
            : "bg-white/[0.03] text-white/30 border-white/[0.06] hover:border-white/[0.12]",
        )}
      >
        {r.trailingStop ? "ON" : "OFF"}
      </button>
    ), width: "55px" },
    { key: "actions", label: "", render: (r: PositionUI) => (
      <div className="flex items-center gap-1">
        <Tooltip content="Modify SL/TP">
          <button onClick={() => openModify(r)}
            className="p-1 rounded hover:bg-cyan-500/10 text-white/30 hover:text-cyan-400 transition-colors">
            <SlidersHorizontal className="w-3.5 h-3.5" />
          </button>
        </Tooltip>
        <Tooltip content="Close position">
          <button onClick={() => { setClosePosId(r.id); setClosePercent("100"); }}
            className="p-1 rounded hover:bg-loss/10 text-white/30 hover:text-loss transition-colors">
            <X className="w-3.5 h-3.5" />
          </button>
        </Tooltip>
      </div>
    ), width: "40px" },
  ];

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-xl font-bold text-white flex items-center gap-2">
            <ArrowLeftRight className="w-5 h-5 text-emerald-400" />
            Live Trading
          </h1>
          <p className="text-sm text-white/40">Multi-broker execution • Cross-broker routing • Real-time monitoring</p>
        </div>
        <div className="flex items-center gap-2">
          <div className="relative" onMouseEnter={() => setShowShortcuts(true)} onMouseLeave={() => setShowShortcuts(false)}>
            <Button variant="ghost" size="sm" className="h-8 w-8 p-0">
              <Keyboard className="w-3.5 h-3.5" />
            </Button>
            {showShortcuts && (
              <div className="absolute right-0 top-full mt-2 z-50 w-56 p-3 rounded-xl glass-strong animate-slide-down">
                <p className="text-[10px] text-white/40 uppercase tracking-wider mb-2">Shortcuts</p>
                {KEYBOARD_SHORTCUTS.map(s => (
                  <div key={s.key} className="flex items-center justify-between py-1">
                    <kbd className="text-[10px] px-1.5 py-0.5 rounded bg-white/[0.06] text-white/60 font-mono">{s.key}</kbd>
                    <span className="text-[10px] text-white/40">{s.action}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
          <Button variant="ghost" size="sm" icon={<Settings className="w-3.5 h-3.5" />} iconPosition="left">
            Broker Config
          </Button>
          <Button variant="secondary" size="sm" onClick={() => refreshAll()}>
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Account Selector — Enhanced */}
      <Card className="p-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          {accounts.map(acc => (
            <button
              key={acc.id}
              onClick={() => setActiveAccount(acc.id)}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-all duration-200 whitespace-nowrap flex-1 min-w-[160px]",
                activeAccount === acc.id
                  ? "bg-white/[0.08] border border-white/[0.12] text-white"
                  : "text-white/40 hover:text-white/60 hover:bg-white/[0.03] border border-transparent",
              )}
            >
              <div className={cn(
                "w-2 h-2 rounded-full shrink-0",
                acc.status === "connected" ? "bg-profit shadow-[0_0_6px_rgba(52,211,153,0.5)]" :
                acc.status === "error" ? "bg-loss" : "bg-white/20",
              )} />
              <div className="text-left min-w-0">
                <div className="flex items-center gap-1.5">
                  <p className="font-medium text-xs">{acc.name}</p>
                  <span className="text-[9px] text-white/30 font-mono">{acc.login}</span>
                </div>
                <p className="text-[9px] text-white/30 truncate">{acc.server} · {acc.currency}</p>
              </div>
              {acc.status === "connected" && (
                <div className="ml-auto text-right">
                  <span className="font-mono text-[11px] text-emerald-400 block">{formatCurrency(acc.equity)}</span>
                  <span className="text-[9px] text-white/20">M: {formatCurrency(acc.margin)}</span>
                </div>
              )}
            </button>
          ))}
        </div>
      </Card>

      {/* Aggregated Stats Bar */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard title="Total P&L" value={totalPnl} change={totalPnl} changeLabel="unrealized"
          variant={totalPnl >= 0 ? "success" : "danger"} format="currency" icon={<Wallet className="w-4 h-4" />} loading={loading} />
        <StatusCard title="Win Rate" value={winRate.toFixed(1)} format="percent" variant="info"
          icon={<TrendingUp className="w-4 h-4" />} subtitle={`${winningPos}/${positions.length} positions`} loading={loading} />
        <StatusCard title="Avg R:R" value={avgRR.toFixed(2)} format="text" variant="default"
          icon={<BarChart3 className="w-4 h-4" />} subtitle="per position" loading={loading} />
        <StatusCard title="Open P&L" value={openPnl} change={openPnl}
          variant={openPnl >= 0 ? "success" : "danger"} format="currency"
          icon={<Activity className="w-4 h-4" />} loading={loading} />
      </div>

      {/* Main Trading Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Left Column — Order Entry */}
        <div className="space-y-4">
          {activeAcct && (
            <Card>
              <CardHeader>
                <CardTitle>{activeAcct.name}</CardTitle>
                <Badge variant={activeAcct.status === "connected" ? "success" : "danger"} size="sm">
                  {activeAcct.status === "connected" ? <><Plug className="w-3 h-3 mr-1" /> Connected</> : <><Unplug className="w-3 h-3 mr-1" /> Disconnected</>}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-2">
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Balance</p>
                    <p className="text-sm font-mono font-bold text-white">{formatCurrency(activeAcct.balance)}</p>
                  </div>
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Equity</p>
                    <p className="text-sm font-mono font-bold text-white">{formatCurrency(activeAcct.equity)}</p>
                  </div>
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Margin</p>
                    <p className="text-sm font-mono text-white">{formatCurrency(activeAcct.margin)}</p>
                  </div>
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Margin Lvl</p>
                    <p className={cn("text-sm font-mono font-bold", activeAcct.marginLevel > 300 ? "text-profit" : activeAcct.marginLevel > 100 ? "text-warning" : "text-loss")}>
                      {activeAcct.marginLevel.toFixed(1)}%
                    </p>
                  </div>
                </div>
                <div className="mt-2 flex items-center gap-2 text-[10px] text-white/20 font-mono">
                  <Globe className="w-3 h-3" /> {activeAcct.login}@{activeAcct.server} · 1:{activeAcct.leverage}
                </div>
              </CardContent>
            </Card>
          )}

          {/* Order Entry */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Order</CardTitle>
              <Badge variant="info" size="sm">Smart Routing</Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {/* Side Toggle */}
                <div className="flex gap-2">
                  <button
                    className={cn("flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200",
                      orderSide === "buy"
                        ? "bg-profit text-white border border-profit shadow-[0_0_12px_rgba(52,211,153,0.15)]"
                        : "bg-white/[0.03] text-white/30 border border-white/[0.06] hover:border-white/[0.12]",
                    )}
                    onClick={() => setOrderSide("buy")}
                  >
                    BUY
                  </button>
                  <button
                    className={cn("flex-1 py-2.5 rounded-xl text-sm font-bold transition-all duration-200",
                      orderSide === "sell"
                        ? "bg-loss text-white border border-loss shadow-[0_0_12px_rgba(248,113,113,0.15)]"
                        : "bg-white/[0.03] text-white/30 border border-white/[0.06] hover:border-white/[0.12]",
                    )}
                    onClick={() => setOrderSide("sell")}
                  >
                    SELL
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Input label="Symbol" value={orderSymbol} onChange={e => setOrderSymbol(e.target.value.toUpperCase())} />
                  <Select label="Type" value={orderType} onChange={e => setOrderType(e.target.value)}
                    options={[
                      { value: "market", label: "Market" },
                      { value: "limit", label: "Limit" },
                      { value: "stop", label: "Stop" },
                      { value: "stop_limit", label: "Stop Limit" },
                      { value: "oco", label: "OCO" },
                      { value: "oto", label: "OTO" },
                    ]}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Input label="Quantity" type="number" step="0.01" min="0" value={orderQty} onChange={e => setOrderQty(e.target.value)} />
                  {(orderType === "limit" || orderType === "stop" || orderType === "stop_limit") && (
                    <Input label="Price" type="number" step="0.01" value={orderPrice} onChange={e => setOrderPrice(e.target.value)}
                      placeholder={orderType === "limit" ? "Limit price" : "Stop price"} />
                  )}
                </div>

                {/* SL / TP fields — shown for all except OCO which has its own */}
                {orderType !== "oco" && (
                  <div className="grid grid-cols-2 gap-2">
                    <Input label="Stop Loss" type="number" step="0.01" value={orderSL} onChange={e => setOrderSL(e.target.value)}
                      placeholder={orderSide === "buy" ? "Below entry" : "Above entry"} className="text-loss/80" />
                    <Input label="Take Profit" type="number" step="0.01" value={orderTP} onChange={e => setOrderTP(e.target.value)}
                      placeholder={orderSide === "buy" ? "Above entry" : "Below entry"} className="text-profit/80" />
                  </div>
                )}

                {/* OCO: two rows of price/sl/tp */}
                {orderType === "oco" && (
                  <div className="space-y-2 p-2 rounded-lg bg-white/[0.02] border border-white/[0.06]">
                    <p className="text-[10px] text-white/30 uppercase tracking-wider">OCO Leg 1</p>
                    <div className="grid grid-cols-3 gap-1">
                      <Input label="Price" type="number" step="0.01" value={orderPrice} onChange={e => setOrderPrice(e.target.value)} placeholder="Entry" />
                      <Input label="SL" type="number" step="0.01" value={orderSL} onChange={e => setOrderSL(e.target.value)} placeholder="Stop" className="text-loss/80" />
                      <Input label="TP" type="number" step="0.01" value={orderTP} onChange={e => setOrderTP(e.target.value)} placeholder="Target" className="text-profit/80" />
                    </div>
                    <p className="text-[10px] text-white/30 uppercase tracking-wider mt-2">OCO Leg 2</p>
                    <div className="grid grid-cols-3 gap-1">
                      <Input label="Price" type="number" step="0.01" value={ocoPrice} onChange={e => setOcoPrice(e.target.value)} placeholder="Entry" />
                      <Input label="SL" type="number" step="0.01" value={ocoSL} onChange={e => setOcoSL(e.target.value)} placeholder="Stop" className="text-loss/80" />
                      <Input label="TP" type="number" step="0.01" value={ocoTP} onChange={e => setOcoTP(e.target.value)} placeholder="Target" className="text-profit/80" />
                    </div>
                  </div>
                )}

                {/* Estimated Cost & Risk */}
                <div className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04] text-[11px]">
                  <div className="flex items-center gap-1.5 text-white/40">
                    <DollarSign className="w-3 h-3" />
                    <span>Est. Cost:</span>
                    <span className="font-mono text-white/70">{formatCurrency(estimatedCost)}</span>
                  </div>
                  <div className="flex items-center gap-1.5 text-white/40">
                    <Percent className="w-3 h-3" />
                    <span>Risk:</span>
                    <span className={cn("font-mono", riskPercent > 2 ? "text-loss" : riskPercent > 0.5 ? "text-warning" : "text-white/70")}>
                      {riskPercent.toFixed(2)}%
                    </span>
                  </div>
                </div>

                {/* Submit + Preview */}
                <div className="flex gap-2">
                  <Button
                    className={cn("flex-1 h-11 text-sm font-bold",
                      orderSide === "buy" ? "bg-profit text-black hover:brightness-110" : "bg-loss text-white hover:brightness-110",
                    )}
                    icon={<Send className="w-4 h-4" />}
                    iconPosition="left"
                    onClick={() => setPreviewOpen(true)}
                  >
                    Preview {orderSide === "buy" ? "BUY" : "SELL"}
                  </Button>
                </div>
                {orderMsg && (
                  <p className="text-[11px] text-center text-white/50 mt-1">{orderMsg}</p>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Watchlist */}
          <Card>
            <CardHeader>
              <CardTitle>Watchlist</CardTitle>
              <Badge variant="info" size="sm"><Star className="w-3 h-3 mr-1" />{watchlist.length}</Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-1">
                {watchlist.map(symbol => {
                  const wsPrice = realtimePrices[symbol];
                  const restItem = restPrices[symbol];
                  const price = wsPrice?.price ?? restItem?.price;
                  const change = wsPrice?.change_24h ?? restItem?.change ?? 0;
                  return (
                    <div key={symbol} className="flex items-center justify-between p-1.5 rounded-lg hover:bg-white/[0.02] group">
                      <div className="flex items-center gap-2">
                        <button onClick={() => removeFromWatchlist(symbol)}
                          className="opacity-0 group-hover:opacity-100 transition-opacity text-white/20 hover:text-loss">
                          <X className="w-3 h-3" />
                        </button>
                        <span className="text-xs font-mono text-white/70">{symbol}</span>
                      </div>
                      <div className="flex items-center gap-2">
                        {price ? <span className="text-xs font-mono text-white">{formatPrice(price, "$")}</span> : <span className="text-xs text-white/20">—</span>}
                        {price && (
                          <span className={cn("text-[10px] font-mono w-14 text-right", change >= 0 ? "text-profit" : "text-loss")}>
                            {change >= 0 ? "+" : ""}{change.toFixed(2)}%
                          </span>
                        )}
                      </div>
                    </div>
                  );
                })}
                <div className="flex gap-1 pt-1">
                  <Input placeholder="Add symbol..." value={newWatchSymbol} onChange={e => setNewWatchSymbol(e.target.value.toUpperCase())}
                    onKeyDown={e => { if (e.key === "Enter") addToWatchlist(); }} className="h-7 text-[10px]" />
                  <Button variant="ghost" size="sm" className="h-7 w-7 p-0 shrink-0" onClick={addToWatchlist}>
                    <TrendingUp className="w-3 h-3" />
                  </Button>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Right Column — Positions & Market Data */}
        <div className="xl:col-span-2 space-y-4">
          {/* Positions Table */}
          <Card>
            <CardHeader>
              <CardTitle>Open Positions</CardTitle>
              <div className="flex items-center gap-2">
                <span className="text-[11px] text-white/30">{accountPositions.length} positions</span>
                <Badge variant={totalPnl >= 0 ? "success" : "danger"} size="sm">
                  {totalPnl >= 0 ? "+" : ""}{formatCurrency(totalPnl)}
                </Badge>
              </div>
            </CardHeader>
            <CardContent>
              <DataTable columns={positionColumns} data={accountPositions}
                keyExtractor={p => p.id} loading={loading} emptyMessage="No open positions" />
            </CardContent>
          </Card>

          {/* Close Position Dialog */}
          <Dialog open={!!closePosId} onClose={() => setClosePosId(null)} title="Close Position">
            {(() => {
              const pos = positions.find(p => p.id === closePosId);
              if (!pos) return null;
              return (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-white/60">
                    <span>{pos.symbol} ({pos.side.toUpperCase()})</span>
                    <span className="font-mono">{formatCurrency(pos.pnl)}</span>
                  </div>
                  <Input label="Close %" type="number" min="1" max="100" value={closePercent}
                    onChange={e => setClosePercent(e.target.value)} />
                  <div className="flex gap-2">
                    {[25, 50, 75, 100].map(pct => (
                      <Button key={pct} variant={closePercent === String(pct) ? "primary" : "secondary"} size="sm"
                        onClick={() => setClosePercent(String(pct))}>{pct}%</Button>
                    ))}
                  </div>
                  <div className="flex gap-2 pt-2">
                    <Button variant="ghost" className="flex-1" onClick={() => setClosePosId(null)}>Cancel</Button>
                    <Button variant="danger" className="flex-1" onClick={() => closePosition(pos, parseFloat(closePercent) || 100)}>
                      Close {closePercent}%
                    </Button>
                  </div>
                </div>
              );
            })()}
          </Dialog>

          {/* Modify SL/TP Dialog — real broker modify via brokersApi.modifyPosition */}
          <Dialog open={!!modifyPosId} onClose={() => setModifyPosId(null)} title="Modify SL / TP">
            {(() => {
              const pos = positions.find(p => p.id === modifyPosId);
              if (!pos) return null;
              return (
                <div className="space-y-3">
                  <div className="flex items-center justify-between text-xs text-white/60">
                    <span>{pos.symbol} ({pos.side.toUpperCase()})</span>
                    <span className="font-mono">{formatCurrency(pos.entryPrice)} entry</span>
                  </div>
                  <Input label="Stop Loss (price)" type="number" step="0.00001" value={newSL}
                    onChange={e => setNewSL(e.target.value)} placeholder="leave empty to keep" />
                  <Input label="Take Profit (price)" type="number" step="0.00001" value={newTP}
                    onChange={e => setNewTP(e.target.value)} placeholder="leave empty to keep" />
                  <div className="flex gap-2 pt-2">
                    <Button variant="ghost" className="flex-1" onClick={() => setModifyPosId(null)}>Cancel</Button>
                    <Button variant="primary" className="flex-1" onClick={() => modifySLTP(pos)}>
                      Save SL/TP
                    </Button>
                  </div>
                </div>
              );
            })()}
          </Dialog>

          {/* Order Preview Dialog */}
          <Dialog open={previewOpen} onClose={() => setPreviewOpen(false)} title="Order Preview">
            <div className="space-y-3">
              <div className="grid grid-cols-2 gap-2 text-xs">
                <div className="p-2 rounded bg-white/[0.03]">
                  <span className="text-white/30 block">Symbol</span>
                  <span className="font-mono text-white/80">{orderSymbol}</span>
                </div>
                <div className="p-2 rounded bg-white/[0.03]">
                  <span className="text-white/30 block">Side</span>
                  <Badge variant={orderSide === "buy" ? "success" : "danger"} size="sm" className="mt-0.5">{orderSide.toUpperCase()}</Badge>
                </div>
                <div className="p-2 rounded bg-white/[0.03]">
                  <span className="text-white/30 block">Type</span>
                  <span className="font-mono text-white/80 capitalize">{orderType.replace("_", " ")}</span>
                </div>
                <div className="p-2 rounded bg-white/[0.03]">
                  <span className="text-white/30 block">Quantity</span>
                  <span className="font-mono text-white/80">{qtyNum}</span>
                </div>
                {(orderType !== "market" || orderPrice) && (
                  <div className="p-2 rounded bg-white/[0.03]">
                    <span className="text-white/30 block">Price</span>
                    <span className="font-mono text-white/80">{formatPrice(priceNum, "$")}</span>
                  </div>
                )}
                <div className="p-2 rounded bg-white/[0.03]">
                  <span className="text-white/30 block">Est. Cost</span>
                  <span className="font-mono text-white/80">{formatCurrency(estimatedCost)}</span>
                </div>
                {slNum > 0 && (
                  <div className="p-2 rounded bg-white/[0.03]">
                    <span className="text-white/30 block">Stop Loss</span>
                    <span className="font-mono text-loss">{formatPrice(slNum, "$")}</span>
                  </div>
                )}
                {tpNum > 0 && (
                  <div className="p-2 rounded bg-white/[0.03]">
                    <span className="text-white/30 block">Take Profit</span>
                    <span className="font-mono text-profit">{formatPrice(tpNum, "$")}</span>
                  </div>
                )}
              </div>
              {slNum > 0 && (
                <div className="flex items-center justify-between text-xs p-2 rounded bg-white/[0.03]">
                  <span className="text-white/40">Risk % of Account</span>
                  <span className={cn("font-mono font-bold", riskPercent > 2 ? "text-loss" : riskPercent > 0.5 ? "text-warning" : "text-profit")}>
                    {riskPercent.toFixed(2)}%
                  </span>
                </div>
              )}
              <div className="flex gap-2 pt-2">
                <Button variant="ghost" className="flex-1" onClick={() => setPreviewOpen(false)}>Cancel</Button>
                <Button variant={orderSide === "buy" ? "primary" : "danger"} className="flex-1" onClick={submitOrder}>
                  Confirm {orderSide.toUpperCase()}
                </Button>
              </div>
            </div>
          </Dialog>

          {/* Market Data Tabs */}
          <Tabs defaultValue="orderbook">
            <TabsList>
              <TabsTrigger value="orderbook"><BookOpen className="w-3.5 h-3.5 mr-1.5" />Order Book</TabsTrigger>
              <TabsTrigger value="trades"><ListOrdered className="w-3.5 h-3.5 mr-1.5" />Time & Sales</TabsTrigger>
              <TabsTrigger value="prices"><BarChart3 className="w-3.5 h-3.5 mr-1.5" />Prices</TabsTrigger>
            </TabsList>

            {/* Order Book / DOM */}
            <TabsContent value="orderbook">
              <Card>
                <CardHeader>
                  <CardTitle>Depth of Market</CardTitle>
                  <button onClick={() => setOrderBookOpen(!orderBookOpen)}
                    className="text-white/30 hover:text-white/50 transition-colors">
                    {orderBookOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                  </button>
                </CardHeader>
                {orderBookOpen && (
                  <CardContent>
                    <div className="grid grid-cols-2 gap-4">
                      {/* Bids */}
                      <div>
                        <div className="flex items-center justify-between text-[10px] text-white/30 uppercase tracking-wider pb-1 border-b border-white/[0.06] mb-1">
                          <span>Bids</span>
                          <span className="text-profit">Size</span>
                          <span>Total</span>
                        </div>
                        <div className="space-y-[1px] max-h-[180px] overflow-y-auto">
                          {(orderBook?.bids ?? []).map((level, i) => (
                            <div key={i} className="flex items-center justify-between text-[11px] font-mono relative">
                              <div className="absolute right-0 top-0 bottom-0 bg-profit/5"
                                style={{ width: `${(level.total / (orderBook?.bids[orderBook.bids.length - 1]?.total || 1)) * 100}%` }} />
                              <span className="text-profit/90 z-10 relative">{level.price.toFixed(2)}</span>
                              <span className="text-white/60 z-10 relative">{level.size.toFixed(3)}</span>
                              <span className="text-white/30 z-10 relative">{level.total.toFixed(3)}</span>
                            </div>
                          ))}
                          {!orderBook?.bids?.length && (
                            <p className="text-[10px] text-white/20 py-4 text-center">No order book data</p>
                          )}
                        </div>
                      </div>
                      {/* Asks */}
                      <div>
                        <div className="flex items-center justify-between text-[10px] text-white/30 uppercase tracking-wider pb-1 border-b border-white/[0.06] mb-1">
                          <span>Asks</span>
                          <span className="text-loss">Size</span>
                          <span>Total</span>
                        </div>
                        <div className="space-y-[1px] max-h-[180px] overflow-y-auto">
                          {(orderBook?.asks ?? []).map((level, i) => (
                            <div key={i} className="flex items-center justify-between text-[11px] font-mono relative">
                              <div className="absolute right-0 top-0 bottom-0 bg-loss/5"
                                style={{ width: `${(level.total / (orderBook?.asks[orderBook.asks.length - 1]?.total || 1)) * 100}%` }} />
                              <span className="text-loss/90 z-10 relative">{level.price.toFixed(2)}</span>
                              <span className="text-white/60 z-10 relative">{level.size.toFixed(3)}</span>
                              <span className="text-white/30 z-10 relative">{level.total.toFixed(3)}</span>
                            </div>
                          ))}
                          {!orderBook?.asks?.length && (
                            <p className="text-[10px] text-white/20 py-4 text-center">No order book data</p>
                          )}
                        </div>
                      </div>
                    </div>
                  </CardContent>
                )}
              </Card>
            </TabsContent>

            {/* Time & Sales */}
            <TabsContent value="trades">
              <Card>
                <CardHeader>
                  <CardTitle>Time & Sales</CardTitle>
                  <Badge variant="info" size="sm"><Clock className="w-3 h-3 mr-1" />Live</Badge>
                </CardHeader>
                <CardContent>
                  <div className="max-h-[240px] overflow-y-auto">
                    <div className="flex items-center justify-between text-[10px] text-white/30 uppercase tracking-wider pb-1 border-b border-white/[0.06] mb-1 px-1">
                      <span>Time</span><span>Price</span><span>Size</span><span>Side</span>
                    </div>
                    <div className="space-y-[1px]">
                      {trades.map((t, i) => (
                        <div key={i} className="flex items-center justify-between text-[11px] font-mono px-1 py-[1px] hover:bg-white/[0.02]">
                          <span className="text-white/30 w-16">{t.time}</span>
                          <span className={cn("w-20 text-right", t.side === "buy" ? "text-profit" : "text-loss")}>
                            {t.price.toFixed(2)}
                          </span>
                          <span className="text-white/50 w-12 text-right">{t.size.toFixed(3)}</span>
                          <Badge variant={t.side === "buy" ? "success" : "danger"} size="sm" className="w-10 text-center">
                            {t.side === "buy" ? "B" : "S"}
                          </Badge>
                        </div>
                      ))}
                    </div>
                  </div>
                </CardContent>
              </Card>
            </TabsContent>

            {/* Live Prices (existing) */}
            <TabsContent value="prices">
              <Card>
                <CardHeader>
                  <CardTitle>Live Prices</CardTitle>
                  <Badge variant="success" size="sm" pulse>
                    {Object.keys(realtimePrices).length > 0 ? "WS LIVE" : "REST"}
                  </Badge>
                </CardHeader>
                <CardContent>
                  {Object.keys(realtimePrices).length > 0 ? (
                    <div className="space-y-1.5">
                      {Object.entries(realtimePrices).map(([symbol, data]: [string, { price: number; change_24h: number }]) => (
                        <div key={symbol} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                          <span className="text-xs font-mono text-white/70">{symbol}</span>
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-mono text-white">${data.price.toLocaleString()}</span>
                            <span className={cn("text-[10px] font-mono", data.change_24h >= 0 ? "text-profit" : "text-loss")}>
                              {data.change_24h >= 0 ? "+" : ""}{data.change_24h.toFixed(2)}%
                            </span>
                          </div>
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="space-y-1.5">
                      {watchlist.map(symbol => {
                        const item = restPrices[symbol];
                        if (!item) return null;
                        return (
                          <div key={symbol} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                            <span className="text-xs font-mono text-white/70">{symbol}</span>
                            <div className="flex items-center gap-2">
                              <span className="text-xs font-mono text-white">${item.price.toLocaleString()}</span>
                              <span className={cn("text-[10px] font-mono", item.change >= 0 ? "text-profit" : "text-loss")}>
                                {item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%
                              </span>
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </CardContent>
              </Card>
            </TabsContent>
          </Tabs>

          {/* Cross-Broker Status */}
          <Card>
            <CardHeader>
              <CardTitle>Cross-Broker Status</CardTitle>
              <Badge variant="success" size="sm"><Globe className="w-3 h-3 mr-1" /> Multi-Broker</Badge>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {accounts.map(acc => (
                  <div key={acc.id} className="flex items-center justify-between p-2.5 rounded-xl bg-white/[0.02] border border-white/[0.04]">
                    <div className="flex items-center gap-2.5">
                      <div className={cn("w-2 h-2 rounded-full",
                        acc.status === "connected" ? "bg-profit" : acc.status === "error" ? "bg-loss" : "bg-white/20",
                      )} />
                      <div>
                        <p className="text-xs font-medium text-white/70">{acc.name}</p>
                        <p className="text-[10px] text-white/30">{acc.broker} · {acc.login}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className="text-xs font-mono text-white/50">{formatCurrency(acc.equity)}</span>
                      <Badge variant={acc.status === "connected" ? "success" : "warning"} size="sm" className="text-[9px]">
                        {acc.status}
                      </Badge>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}

export default function TradingPage() {
  return (
    <ErrorBoundary>
      <TradingDashboardContent />
    </ErrorBoundary>
  );
}