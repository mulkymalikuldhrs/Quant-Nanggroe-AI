"use client";

import React, { useState, useEffect, useMemo } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { formatCurrency, cn } from "@/lib/utils";
import { useAppStore } from "@/lib/store";
import apiRequest, { tradingApi } from "@/lib/api-client";
import { ArrowLeftRight, Send, Route, Loader2 } from "lucide-react";

interface Exchange {
  id: string; name: string; type: string; status: string;
}

interface Order {
  id: string; symbol: string; side: string; type: string;
  quantity: number; price: number; status: string;
  time: string; exchange: string;
}

export default function TradingPage() {
  const { selectedSymbol, setSelectedSymbol, selectedExchange, setSelectedExchange, portfolioData, fetchPortfolio } = useAppStore();
  const [orderSymbol, setOrderSymbol] = useState(selectedSymbol);
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState("market");
  const [orderQty, setOrderQty] = useState("10");
  const [orderPrice, setOrderPrice] = useState("");
  const [exchanges, setExchanges] = useState<Exchange[]>([]);
  const [orders, setOrders] = useState<Order[]>([]);
  const [loading, setLoading] = useState(true);
  const [placing, setPlacing] = useState(false);

  useEffect(() => {
    const load = async () => {
      try {
        const [exch, ords] = await Promise.all([
          apiRequest<Exchange[]>("/api/v1/trading/exchanges").catch(() => []),
          apiRequest<Order[]>("/api/v1/trading/orders").catch(() => []),
        ]);
        setExchanges(exch);
        setOrders(ords);
      } finally {
        setLoading(false);
      }
    };
    load();
    fetchPortfolio();
  }, [fetchPortfolio]);

  const handlePlaceOrder = async () => {
    setPlacing(true);
    try {
      await tradingApi.placeOrder({ symbol: orderSymbol, side: orderSide, type: orderType, quantity: parseFloat(orderQty), price: orderPrice ? parseFloat(orderPrice) : undefined, exchange: selectedExchange });
      const ords = await apiRequest<Order[]>("/api/v1/trading/orders");
      setOrders(ords);
    } finally {
      setPlacing(false);
    }
  };

  const orderColumns = [
    { key: "symbol", header: "Symbol", render: (row: Record<string, unknown>) => (<span className="font-medium text-white">{row.symbol as string}</span>) },
    { key: "side", header: "Side", render: (row: Record<string, unknown>) => (<Badge variant={(row.side as string) === "buy" ? "success" : "danger"} className="text-[10px]">{(row.side as string).toUpperCase()}</Badge>) },
    { key: "type", header: "Type", render: (row: Record<string, unknown>) => (<span className="text-white/60 uppercase text-xs">{row.type as string}</span>) },
    { key: "quantity", header: "Qty", render: (row: Record<string, unknown>) => (<span className="font-mono text-white/70">{(row.quantity as number).toLocaleString()}</span>) },
    { key: "price", header: "Price", render: (row: Record<string, unknown>) => (<span className="font-mono text-white">{formatCurrency(row.price as number)}</span>) },
    { key: "status", header: "Status", render: (row: Record<string, unknown>) => { const s = row.status as string; return (<Badge variant={s === "filled" ? "success" : s === "active" ? "info" : s === "rejected" ? "danger" : "warning"} className="text-[10px]">{s.toUpperCase()}</Badge>); } },
    { key: "exchange", header: "Exchange", render: (row: Record<string, unknown>) => (<span className="text-xs text-white/40">{row.exchange as string}</span>) },
    { key: "time", header: "Time", render: (row: Record<string, unknown>) => (<span className="text-xs text-white/30">{row.time as string}</span>) },
  ];

  const [orderBook, setOrderBook] = useState<{ asks: { price: number; size: string; total: string }[]; bids: { price: number; size: string; total: string }[] }>({ asks: [], bids: [] });
  const [orderBookLoading, setOrderBookLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const book = await apiRequest<{ asks: { price: number; size: string; total: string }[]; bids: { price: number; size: string; total: string }[] }>("/api/v1/trading/orderbook?symbol=BTC");
        setOrderBook(book);
      } catch {
        setOrderBook({ asks: [], bids: [] });
      } finally {
        setOrderBookLoading(false);
      }
    };
    load();
  }, []);

  const openOrdersCount = orders.filter(o => o.status !== "filled").length;
  const filledCount = orders.filter(o => o.status === "filled").length;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <Loader2 className="w-8 h-8 text-blue-400 animate-spin" />
      </div>
    );
  }

  return (
    <div className="space-y-4 animate-slide-up">
      <div><h1 className="text-xl font-bold text-white flex items-center gap-2"><ArrowLeftRight className="w-5 h-5 text-blue-400" />Live Trading</h1><p className="text-sm text-white/40 mt-0.5">Smart order routing • {exchanges.length} exchanges</p></div>
      <Tabs defaultValue="order">
        <TabsList><TabsTrigger value="order">Order Entry</TabsTrigger><TabsTrigger value="book">Order Book</TabsTrigger><TabsTrigger value="orders">Open Orders</TabsTrigger><TabsTrigger value="history">Trade History</TabsTrigger></TabsList>
        <TabsContent value="order">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            <ChartCard title="Place Order" subtitle="Market, Limit & Stop orders" glow="blue">
              <div className="space-y-3">
                <div className="flex gap-2">
                  <button className={cn("flex-1 py-2 rounded-lg text-sm font-medium transition-all", orderSide === "buy" ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30" : "bg-white/[0.03] text-white/40 border border-white/[0.06]")} onClick={() => setOrderSide("buy")}>Buy</button>
                  <button className={cn("flex-1 py-2 rounded-lg text-sm font-medium transition-all", orderSide === "sell" ? "bg-red-500/20 text-red-400 border border-red-500/30" : "bg-white/[0.03] text-white/40 border border-white/[0.06]")} onClick={() => setOrderSide("sell")}>Sell</button>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-xs text-white/40 mb-1 block">Symbol</label><Input value={orderSymbol} onChange={(e) => setOrderSymbol(e.target.value)} /></div>
                  <div><label className="text-xs text-white/40 mb-1 block">Exchange</label><Select value={selectedExchange} onChange={(e) => setSelectedExchange(e.target.value)} options={exchanges.filter(e => e.status === "connected").map(e => ({ value: e.id, label: e.name }))} /></div>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div><label className="text-xs text-white/40 mb-1 block">Order Type</label><Select value={orderType} onChange={(e) => setOrderType(e.target.value)} options={[{ value: "market", label: "Market" }, { value: "limit", label: "Limit" }, { value: "stop", label: "Stop" }, { value: "stop_limit", label: "Stop Limit" }]} /></div>
                  <div><label className="text-xs text-white/40 mb-1 block">Quantity</label><Input type="number" value={orderQty} onChange={(e) => setOrderQty(e.target.value)} /></div>
                </div>
                {(orderType === "limit" || orderType === "stop_limit") && <div><label className="text-xs text-white/40 mb-1 block">Limit Price</label><Input type="number" value={orderPrice} onChange={(e) => setOrderPrice(e.target.value)} placeholder="0.00" /></div>}
                <Button className={cn("w-full", orderSide === "buy" ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30" : "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30")} onClick={handlePlaceOrder} disabled={placing}><Send className="w-3.5 h-3.5 mr-1.5" />{placing ? "Placing..." : `${orderSide === "buy" ? "Buy" : "Sell"} ${orderSymbol}`}</Button>
              </div>
            </ChartCard>
            <div className="space-y-4">
              <ChartCard title="Smart Order Routing" subtitle="Best execution across exchanges">
                <div className="space-y-2">
                  {exchanges.filter(e => e.status === "connected").map((exchange) => (
                    <div key={exchange.id} className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                      <div className="flex items-center gap-2.5"><Route className="w-3.5 h-3.5 text-white/30" /><div><p className="text-xs font-medium text-white/70">{exchange.name}</p><p className="text-[10px] text-white/30">{exchange.type}</p></div></div>
                      <div className="flex items-center gap-2"><Badge variant={exchange.status === "connected" ? "success" : "danger"} className="text-[10px]">{exchange.status}</Badge></div>
                    </div>
                  ))}
                </div>
              </ChartCard>
              <div className="grid grid-cols-2 gap-3"><StatusCard title="Open Orders" value={String(openOrdersCount)} variant="warning" /><StatusCard title="Filled Today" value={String(filledCount)} variant="success" /></div>
            </div>
          </div>
        </TabsContent>
        <TabsContent value="book">
          <ChartCard title="Order Book" subtitle="BTC/USDT depth" className="mt-3" glow="blue">
            {orderBookLoading ? (
              <div className="flex items-center justify-center h-32"><Loader2 className="w-6 h-6 text-blue-400 animate-spin" /></div>
            ) : orderBook.asks.length > 0 || orderBook.bids.length > 0 ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div><div className="flex items-center justify-between mb-2 px-2"><span className="text-[10px] text-white/30 uppercase">Price</span><span className="text-[10px] text-white/30 uppercase">Size</span></div>{orderBook.asks.map((ask, i) => (<div key={i} className="relative flex items-center justify-between py-1 px-2 rounded"><div className="absolute right-0 top-0 bottom-0 bg-red-500/5 rounded" style={{ width: `${(parseFloat(ask.total) / 25) * 100}%` }} /><span className="text-xs font-mono text-red-400 relative z-10">{formatCurrency(ask.price)}</span><span className="text-xs font-mono text-white/50 relative z-10">{ask.size}</span></div>))}</div>
                <div><div className="flex items-center justify-between mb-2 px-2"><span className="text-[10px] text-white/30 uppercase">Price</span><span className="text-[10px] text-white/30 uppercase">Size</span></div>{orderBook.bids.map((bid, i) => (<div key={i} className="relative flex items-center justify-between py-1 px-2 rounded"><div className="absolute left-0 top-0 bottom-0 bg-emerald-500/5 rounded" style={{ width: `${(parseFloat(bid.total) / 25) * 100}%` }} /><span className="text-xs font-mono text-emerald-400 relative z-10">{formatCurrency(bid.price)}</span><span className="text-xs font-mono text-white/50 relative z-10">{bid.size}</span></div>))}</div>
              </div>
            ) : <p className="text-sm text-white/30 text-center py-8">No order book data available</p>}
          </ChartCard>
        </TabsContent>
        <TabsContent value="orders"><ChartCard title="Open Orders" subtitle="Active and pending orders" className="mt-3"><DataTable columns={orderColumns} data={orders.filter(o => o.status !== "filled") as unknown as Record<string, unknown>[]} /></ChartCard></TabsContent>
        <TabsContent value="history"><ChartCard title="Trade History" subtitle="Completed trades" className="mt-3"><DataTable columns={orderColumns} data={orders as unknown as Record<string, unknown>[]} /></ChartCard></TabsContent>
      </Tabs>
    </div>
  );
}
