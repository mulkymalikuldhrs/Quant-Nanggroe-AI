"use client";
export const dynamic = "force-dynamic";

import { useState, useEffect, useCallback } from "react";
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { useRealtimeData } from "@/lib/websocket";
import { useAppStore } from "@/lib/store";
import { cn, formatCurrency, formatPercent, formatPrice, formatTimestamp } from "@/lib/utils";
import { brokersApi, tradingApi } from "@/lib/api-client";
import type { MT5AccountInfo, BrokerPositionsResponse, OrderType } from "@/lib/api-client";
import {
  ArrowLeftRight, Send, Route, RefreshCw, Wallet, TrendingUp, Activity,
  Plug, Unplug, Settings, BarChart3, Split, SwitchCamera, Globe,
} from "lucide-react";

// ── UI Model Types (populated from API) ────────────────────────────

interface BrokerAccountUI {
  id: string;
  name: string;
  broker: string;
  type: "mt5" | "crypto" | "ibkr" | "simulated";
  status: "connected" | "disconnected" | "error";
  balance: number;
  equity: number;
  margin: number;
  marginLevel: number;
  leverage: number;
  currency: string;
  server: string;
  login: string;
}

interface PositionUI {
  id: string;
  symbol: string;
  side: "long" | "short";
  quantity: number;
  entryPrice: number;
  currentPrice: number;
  pnl: number;
  pnlPercent: number;
  stopLoss: number;
  takeProfit: number;
  broker: string;
  account: string;
  timestamp: string;
}

// ── Mock accounts (will be replaced with real API data) ────────────



function TradingDashboardContent() {
  useRealtimeData(); // Subscribe to real-time WebSocket channels
  const { realtimePrices, refreshAll } = useAppStore();

  // State
  const [activeAccount, setActiveAccount] = useState("");
  const [orderSymbol, setOrderSymbol] = useState("BTC/USDT");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState("market");
  const [orderQty, setOrderQty] = useState("1.0");
  const [orderPrice, setOrderPrice] = useState("");
  const [loading, setLoading] = useState(true);
  const [orderMsg, setOrderMsg] = useState("");
  const [accounts, setAccounts] = useState<BrokerAccountUI[]>([]);
  const [positions, setPositions] = useState<PositionUI[]>([]);

  // Fetch real data from backend
  useEffect(() => {
    let cancelled = false;
    async function fetchData() {
      setLoading(true);
      try {
        const list = await brokersApi.list();
        if (cancelled || !list.accounts?.length) { setLoading(false); return; }

        // Fetch account info and positions for each broker
        const infoResults = await Promise.allSettled(
          list.accounts.map(b => brokersApi.account(b.name))
        );
        const posResults = await Promise.allSettled(
          list.accounts.map(b => brokersApi.positions(b.name))
        );
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
                stopLoss: 0, takeProfit: 0, broker: brokerName, account: brokerName,
                timestamp: new Date().toISOString(),
              });
            }
          }
        });
        setPositions(allPositions);
      } catch (e) { console.error("Failed to load trading data:", e); }
      if (!cancelled) setLoading(false);
    }
    fetchData();
    return () => { cancelled = true; };
  }, []);

  // Active account data
  const activeAcct = accounts.find(a => a.id === activeAccount);
  const accountPositions = positions.filter(p => p.account === activeAccount);

  // Aggregate totals
  const totalEquity = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.equity, 0);
  const totalBalance = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.balance, 0);
  const totalPnl = positions.reduce((s, p) => s + p.pnl, 0);
  const totalMargin = accounts.filter(a => a.status === "connected").reduce((s, a) => s + a.margin, 0);

  // Position columns
  const positionColumns = [
    { key: "symbol", label: "Symbol", render: (r: PositionUI) => <span className="font-medium text-white">{r.symbol}</span>, width: "100px" },
    { key: "side", label: "Side", sortable: true, render: (r: PositionUI) => (
      <Badge variant={r.side === "long" ? "success" : "danger"} size="sm">{r.side.toUpperCase()}</Badge>
    ), width: "60px" },
    { key: "quantity", label: "Qty", align: "right" as const, render: (r: PositionUI) => <span className="font-mono">{r.quantity}</span>, width: "80px" },
    { key: "entryPrice", label: "Entry", align: "right" as const, render: (r: PositionUI) => <span className="font-mono text-white/60">{formatPrice(r.entryPrice, "$")}</span>, width: "100px" },
    { key: "currentPrice", label: "Current", align: "right" as const, render: (r: PositionUI) => <span className="font-mono">{formatPrice(r.currentPrice, "$")}</span>, width: "100px" },
    { key: "pnl", label: "P&L", align: "right" as const, sortable: true, render: (r: PositionUI) => (
      <span className={cn("font-mono font-medium", r.pnl >= 0 ? "text-profit" : "text-loss")}>{formatCurrency(r.pnl)}</span>
    ), width: "120px" },
    { key: "pnlPercent", label: "P&L %", align: "right" as const, render: (r: PositionUI) => (
      <span className={cn("font-mono", r.pnlPercent >= 0 ? "text-profit" : "text-loss")}>{formatPercent(r.pnlPercent)}</span>
    ), width: "80px" },
    { key: "broker", label: "Broker", render: (r: PositionUI) => <span className="text-xs text-white/40">{r.broker}</span>, width: "100px" },
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
          <Button variant="secondary" size="sm" icon={<Settings className="w-3.5 h-3.5" />} iconPosition="left">
            Broker Config
          </Button>
          <Button variant="primary" size="sm" onClick={() => refreshAll()}>
            <RefreshCw className="w-3.5 h-3.5" />
          </Button>
        </div>
      </div>

      {/* Account Selector Bar */}
      <Card className="p-2">
        <div className="flex items-center gap-2 overflow-x-auto">
          {accounts.map(acc => (
            <button
              key={acc.id}
              onClick={() => setActiveAccount(acc.id)}
              className={cn(
                "flex items-center gap-2.5 px-3 py-2 rounded-xl text-xs transition-all duration-200 whitespace-nowrap",
                activeAccount === acc.id
                  ? "bg-white/[0.08] border border-white/[0.12] text-white"
                  : "text-white/40 hover:text-white/60 hover:bg-white/[0.03] border border-transparent",
              )}
            >
              <div className={cn(
                "w-2 h-2 rounded-full",
                acc.status === "connected" ? "bg-profit shadow-[0_0_6px_rgba(52,211,153,0.5)]" :
                acc.status === "error" ? "bg-loss" : "bg-white/20",
              )} />
              <div className="text-left">
                <p className="font-medium">{acc.name}</p>
                <p className="text-[10px] text-white/30">{acc.broker} · {acc.type.toUpperCase()}</p>
              </div>
              {acc.status === "connected" && (
                <span className="font-mono text-[11px] text-emerald-400">{formatCurrency(acc.equity)}</span>
              )}
            </button>
          ))}
        </div>
      </Card>

      {/* Aggregate Portfolio Summary */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <StatusCard
          title="Total Equity"
          value={totalEquity}
          change={totalPnl}
          changeLabel="unrealized"
          variant={totalPnl >= 0 ? "success" : "danger"}
          format="currency"
          icon={<Wallet className="w-4 h-4" />}
          loading={loading}
        />
        <StatusCard
          title="Total Balance"
          value={totalBalance}
          format="currency"
          icon={<Activity className="w-4 h-4" />}
          loading={loading}
        />
        <StatusCard
          title="Used Margin"
          value={totalMargin}
          format="currency"
          subtitle={`${((totalMargin / totalEquity) * 100).toFixed(1)}% utilization`}
          icon={<BarChart3 className="w-4 h-4" />}
          loading={loading}
        />
        <StatusCard
          title="Open Positions"
          value={positions.length}
          format="number"
          subtitle={`${accounts.filter(a => a.status === "connected").length} brokers active`}
          icon={<TrendingUp className="w-4 h-4" />}
          loading={loading}
        />
      </div>

      {/* Main Trading Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        {/* Account Detail & Order Entry */}
        <div className="space-y-4">
          {/* Active Account Detail */}
          {activeAcct && (
            <Card>
              <CardHeader>
                <CardTitle>{activeAcct.name}</CardTitle>
                <Badge variant={activeAcct.status === "connected" ? "success" : "danger"} size="sm">
                  {activeAcct.status === "connected" ? <><Plug className="w-3 h-3 mr-1" /> Connected</> : <><Unplug className="w-3 h-3 mr-1" /> Disconnected</>}
                </Badge>
              </CardHeader>
              <CardContent>
                <div className="grid grid-cols-2 gap-3">
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
                    <p className="text-[10px] text-white/30 mb-0.5">Margin Level</p>
                    <p className={cn("text-sm font-mono font-bold", activeAcct.marginLevel > 300 ? "text-profit" : activeAcct.marginLevel > 100 ? "text-warning" : "text-loss")}>
                      {activeAcct.marginLevel.toFixed(1)}%
                    </p>
                  </div>
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Leverage</p>
                    <p className="text-sm font-mono text-white">1:{activeAcct.leverage || "—"}</p>
                  </div>
                  <div className="bbg-cell">
                    <p className="text-[10px] text-white/30 mb-0.5">Server</p>
                    <p className="text-xs font-mono text-white/60 truncate">{activeAcct.server}</p>
                  </div>
                </div>
                <div className="mt-3 flex items-center gap-2 text-[10px] text-white/20 font-mono">
                  <Globe className="w-3 h-3" /> Login: {activeAcct.login} · {activeAcct.currency}
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
                  <Input label="Symbol" value={orderSymbol} onChange={e => setOrderSymbol(e.target.value)} />
                  <Select label="Type" value={orderType} onChange={e => setOrderType(e.target.value)}
                    options={[
                      { value: "market", label: "Market" }, { value: "limit", label: "Limit" },
                      { value: "stop", label: "Stop" }, { value: "stop_limit", label: "Stop Limit" },
                      { value: "twap", label: "TWAP" },
                    ]}
                  />
                </div>

                <div className="grid grid-cols-2 gap-2">
                  <Input label="Quantity" type="number" value={orderQty} onChange={e => setOrderQty(e.target.value)} />
                  {(orderType === "limit" || orderType === "stop_limit") && (
                    <Input label="Price" type="number" value={orderPrice} onChange={e => setOrderPrice(e.target.value)} />
                  )}
                  {orderType === "market" && (
                    <Input label="Account" value={activeAcct?.name || ""} disabled />
                  )}
                </div>

                <Button
                  className={cn("w-full h-11 text-sm font-bold",
                    orderSide === "buy" ? "bg-profit text-black hover:brightness-110" : "bg-loss text-white hover:brightness-110",
                  )}
                  icon={<Send className="w-4 h-4" />}
                  iconPosition="left"
                  onClick={async () => {
                    if (!activeAcct) return;
                    setOrderMsg("Placing order...");
                    try {
                      await brokersApi.placeOrder(activeAcct.name, {
                        symbol: orderSymbol,
                        side: orderSide,
                        type: orderType as OrderType,
                        quantity: parseFloat(orderQty) || 0,
                        price: orderPrice ? parseFloat(orderPrice) : undefined,
                      });
                      setOrderMsg(`✓ Order placed on ${activeAcct.name}`);
                    } catch (e: any) {
                      setOrderMsg(`✗ ${e?.message || "Order failed"}`);
                    }
                    setTimeout(() => setOrderMsg(""), 5000);
                  }}
                >
                  {orderSide === "buy" ? "BUY" : "SELL"} {orderSymbol}
                </Button>
                {orderMsg && (
                  <p className="text-[11px] text-center text-white/50 mt-1">{orderMsg}</p>
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Positions & Order Book */}
        <div className="xl:col-span-2 space-y-4">
          {/* Active Positions */}
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
              <DataTable
                columns={positionColumns}
                data={accountPositions}
                keyExtractor={p => p.id}
                loading={loading}
                emptyMessage="No open positions"
              />
            </CardContent>
          </Card>

          {/* Cross-Broker Overview */}
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Broker Status */}
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
                          <p className="text-[10px] text-white/30">{acc.broker}</p>
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

            {/* Live Prices */}
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
                    {[
                      { symbol: "BTC/USDT", price: 67340, change: 2.93 },
                      { symbol: "ETH/USDT", price: 3620, change: 4.93 },
                      { symbol: "XAU/USD", price: 2355, change: -1.05 },
                      { symbol: "NVDA", price: 132.30, change: 2.96 },
                      { symbol: "AAPL", price: 196.80, change: -0.71 },
                    ].map(item => (
                      <div key={item.symbol} className="flex items-center justify-between p-2 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                        <span className="text-xs font-mono text-white/70">{item.symbol}</span>
                        <div className="flex items-center gap-2">
                          <span className="text-xs font-mono text-white">${item.price.toLocaleString()}</span>
                          <span className={cn("text-[10px] font-mono", item.change >= 0 ? "text-profit" : "text-loss")}>
                            {item.change >= 0 ? "+" : ""}{item.change.toFixed(2)}%
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>
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
