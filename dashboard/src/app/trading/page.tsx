"use client";

import React, { useState, useMemo } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { StatusCard } from "@/components/shared/status-card";
import { DataTable } from "@/components/shared/data-table";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { mockOrders, mockExchanges } from "@/lib/mock-data";
import { formatCurrency, cn } from "@/lib/utils";
import {
  ArrowLeftRight,
  Send,
  Route,
} from "lucide-react";

export default function TradingPage() {
  const [orderSymbol, setOrderSymbol] = useState("AAPL");
  const [orderSide, setOrderSide] = useState<"buy" | "sell">("buy");
  const [orderType, setOrderType] = useState("market");
  const [orderQty, setOrderQty] = useState("10");
  const [orderPrice, setOrderPrice] = useState("");
  const [selectedExchange, setSelectedExchange] = useState("alpaca");

  const orderColumns = [
    {
      key: "symbol",
      header: "Symbol",
      render: (row: Record<string, unknown>) => (
        <span className="font-medium text-white">{row.symbol as string}</span>
      ),
    },
    {
      key: "side",
      header: "Side",
      render: (row: Record<string, unknown>) => (
        <Badge variant={(row.side as string) === "buy" ? "success" : "danger"} className="text-[10px]">
          {(row.side as string).toUpperCase()}
        </Badge>
      ),
    },
    { key: "type", header: "Type", render: (row: Record<string, unknown>) => (
      <span className="text-white/60 uppercase text-xs">{row.type as string}</span>
    )},
    { key: "quantity", header: "Qty", render: (row: Record<string, unknown>) => (
      <span className="font-mono text-white/70">{(row.quantity as number).toLocaleString()}</span>
    )},
    { key: "price", header: "Price", render: (row: Record<string, unknown>) => (
      <span className="font-mono text-white">{formatCurrency(row.price as number)}</span>
    )},
    {
      key: "status",
      header: "Status",
      render: (row: Record<string, unknown>) => {
        const status = row.status as string;
        return (
          <Badge
            variant={
              status === "filled" ? "success" : status === "active" ? "info" : status === "rejected" ? "danger" : "warning"
            }
            className="text-[10px]"
          >
            {status.toUpperCase()}
          </Badge>
        );
      },
    },
    { key: "exchange", header: "Exchange", render: (row: Record<string, unknown>) => (
      <span className="text-xs text-white/40">{row.exchange as string}</span>
    )},
    { key: "time", header: "Time", render: (row: Record<string, unknown>) => (
      <span className="text-xs text-white/30">{row.time as string}</span>
    )},
  ];

  const handlePlaceOrder = () => {
    console.log("Placing order:", { orderSymbol, orderSide, orderType, orderQty, orderPrice, selectedExchange });
  };

  // Mock order book data (deterministic for SSR)
  const asks = useMemo(() =>
    Array.from({ length: 8 }, (_, i) => ({
      price: 67250 + (8 - i) * 10,
      size: (2.5 + i * 0.3).toFixed(4),
      total: (12 + i * 1.5).toFixed(4),
    })).reverse(), []);

  const bids = useMemo(() =>
    Array.from({ length: 8 }, (_, i) => ({
      price: 67250 - i * 10,
      size: (1.8 + i * 0.4).toFixed(4),
      total: (8 + i * 2).toFixed(4),
    })), []);

  return (
    <div className="space-y-4 animate-slide-up">
      {/* Header */}
      <div>
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          <ArrowLeftRight className="w-5 h-5 text-blue-400" />
          Live Trading
        </h1>
        <p className="text-sm text-white/40 mt-0.5">
          Smart order routing • 10 exchanges • Real-time execution
        </p>
      </div>

      <Tabs defaultValue="order">
        <TabsList>
          <TabsTrigger value="order">Order Entry</TabsTrigger>
          <TabsTrigger value="book">Order Book</TabsTrigger>
          <TabsTrigger value="orders">Open Orders</TabsTrigger>
          <TabsTrigger value="history">Trade History</TabsTrigger>
        </TabsList>

        <TabsContent value="order">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mt-3">
            {/* Order Entry Form */}
            <ChartCard title="Place Order" subtitle="Market, Limit & Stop orders" glow="blue">
              <div className="space-y-3">
                {/* Side Toggle */}
                <div className="flex gap-2">
                  <button
                    className={cn(
                      "flex-1 py-2 rounded-lg text-sm font-medium transition-all",
                      orderSide === "buy"
                        ? "bg-emerald-500/20 text-emerald-400 border border-emerald-500/30"
                        : "bg-white/[0.03] text-white/40 border border-white/[0.06]",
                    )}
                    onClick={() => setOrderSide("buy")}
                  >
                    Buy
                  </button>
                  <button
                    className={cn(
                      "flex-1 py-2 rounded-lg text-sm font-medium transition-all",
                      orderSide === "sell"
                        ? "bg-red-500/20 text-red-400 border border-red-500/30"
                        : "bg-white/[0.03] text-white/40 border border-white/[0.06]",
                    )}
                    onClick={() => setOrderSide("sell")}
                  >
                    Sell
                  </button>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-white/40 mb-1 block">Symbol</label>
                    <Input value={orderSymbol} onChange={(e) => setOrderSymbol(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-xs text-white/40 mb-1 block">Exchange</label>
                    <Select
                      value={selectedExchange}
                      onChange={(e) => setSelectedExchange(e.target.value)}
                      options={mockExchanges.filter(e => e.status === "connected").map(e => ({ value: e.id, label: e.name }))}
                    />
                  </div>
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs text-white/40 mb-1 block">Order Type</label>
                    <Select
                      value={orderType}
                      onChange={(e) => setOrderType(e.target.value)}
                      options={[
                        { value: "market", label: "Market" },
                        { value: "limit", label: "Limit" },
                        { value: "stop", label: "Stop" },
                        { value: "stop_limit", label: "Stop Limit" },
                        { value: "twap", label: "TWAP" },
                        { value: "vwap", label: "VWAP" },
                      ]}
                    />
                  </div>
                  <div>
                    <label className="text-xs text-white/40 mb-1 block">Quantity</label>
                    <Input
                      type="number"
                      value={orderQty}
                      onChange={(e) => setOrderQty(e.target.value)}
                    />
                  </div>
                </div>

                {(orderType === "limit" || orderType === "stop_limit") && (
                  <div>
                    <label className="text-xs text-white/40 mb-1 block">Limit Price</label>
                    <Input
                      type="number"
                      value={orderPrice}
                      onChange={(e) => setOrderPrice(e.target.value)}
                      placeholder="0.00"
                    />
                  </div>
                )}

                <Button
                  className={cn(
                    "w-full",
                    orderSide === "buy"
                      ? "bg-emerald-500/20 text-emerald-400 hover:bg-emerald-500/30 border border-emerald-500/30"
                      : "bg-red-500/20 text-red-400 hover:bg-red-500/30 border border-red-500/30",
                  )}
                  onClick={handlePlaceOrder}
                >
                  <Send className="w-3.5 h-3.5 mr-1.5" />
                  {orderSide === "buy" ? "Buy" : "Sell"} {orderSymbol}
                </Button>
              </div>
            </ChartCard>

            {/* Smart Order Routing */}
            <div className="space-y-4">
              <ChartCard title="Smart Order Routing" subtitle="Best execution across exchanges">
                <div className="space-y-2">
                  {mockExchanges.filter(e => e.status === "connected").map((exchange) => (
                    <div
                      key={exchange.id}
                      className="flex items-center justify-between p-2.5 rounded-lg bg-white/[0.02] border border-white/[0.04]"
                    >
                      <div className="flex items-center gap-2.5">
                        <Route className="w-3.5 h-3.5 text-white/30" />
                        <div>
                          <p className="text-xs font-medium text-white/70">{exchange.name}</p>
                          <p className="text-[10px] text-white/30">{exchange.type}</p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={exchange.status === "connected" ? "success" : "danger"} className="text-[10px]">
                          {exchange.status}
                        </Badge>
                        {exchange.id === selectedExchange && (
                          <div className="w-2 h-2 rounded-full bg-blue-400 shadow-[0_0_6px_rgba(59,130,246,0.5)]" />
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </ChartCard>

              {/* Quick Stats */}
              <div className="grid grid-cols-2 gap-3">
                <StatusCard title="Open Orders" value="3" variant="warning" />
                <StatusCard title="Filled Today" value="7" variant="success" />
              </div>
            </div>
          </div>
        </TabsContent>

        <TabsContent value="book">
          <ChartCard title="Order Book" subtitle="BTC/USDT depth" className="mt-3" glow="blue">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {/* Asks */}
              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-[10px] text-white/30 uppercase">Price</span>
                  <span className="text-[10px] text-white/30 uppercase">Size</span>
                </div>
                {asks.map((ask, i) => (
                  <div key={i} className="relative flex items-center justify-between py-1 px-2 rounded">
                    <div
                      className="absolute right-0 top-0 bottom-0 bg-red-500/5 rounded"
                      style={{ width: `${(parseFloat(ask.total) / 25) * 100}%` }}
                    />
                    <span className="text-xs font-mono text-red-400 relative z-10">
                      {formatCurrency(ask.price)}
                    </span>
                    <span className="text-xs font-mono text-white/50 relative z-10">{ask.size}</span>
                  </div>
                ))}
              </div>
              {/* Bids */}
              <div>
                <div className="flex items-center justify-between mb-2 px-2">
                  <span className="text-[10px] text-white/30 uppercase">Price</span>
                  <span className="text-[10px] text-white/30 uppercase">Size</span>
                </div>
                {bids.map((bid, i) => (
                  <div key={i} className="relative flex items-center justify-between py-1 px-2 rounded">
                    <div
                      className="absolute left-0 top-0 bottom-0 bg-emerald-500/5 rounded"
                      style={{ width: `${(parseFloat(bid.total) / 25) * 100}%` }}
                    />
                    <span className="text-xs font-mono text-emerald-400 relative z-10">
                      {formatCurrency(bid.price)}
                    </span>
                    <span className="text-xs font-mono text-white/50 relative z-10">{bid.size}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="mt-3 p-2 rounded-lg bg-white/[0.03] border border-white/[0.04] text-center">
              <span className="text-sm font-mono font-bold text-white">
                Spread: {formatCurrency(asks[asks.length - 1].price - bids[0].price)}
              </span>
            </div>
          </ChartCard>
        </TabsContent>

        <TabsContent value="orders">
          <ChartCard title="Open Orders" subtitle="Active and pending orders" className="mt-3">
            <DataTable columns={orderColumns} data={mockOrders.filter(o => o.status !== "filled") as unknown as Record<string, unknown>[]} />
          </ChartCard>
        </TabsContent>

        <TabsContent value="history">
          <ChartCard title="Trade History" subtitle="Completed trades" className="mt-3">
            <DataTable columns={orderColumns} data={mockOrders as unknown as Record<string, unknown>[]} />
          </ChartCard>
        </TabsContent>
      </Tabs>
    </div>
  );
}
