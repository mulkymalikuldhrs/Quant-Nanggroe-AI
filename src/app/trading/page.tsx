"use client";

import React, { useEffect, useState, useCallback } from "react";
import {
  LineChart,
  BarChart,
  Bar,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ComposedChart,
} from "recharts";
import {
  TrendingUp,
  TrendingDown,
  ShoppingCart,
  Activity,
  RefreshCw,
  ArrowUpRight,
  ArrowDownRight,
  X,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { MetricCard, SectionHeader, Skeleton } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";

export default function TradingPage() {
  const {
    positions,
    trades,
    ohlcvData,
    pressureData,
    loadingPositions,
    loadingTrades,
    loadingOHLCV,
    fetchPositions,
    fetchTrades,
    fetchOHLCV,
    fetchPressure,
    placeOrder,
  } = useAppStore();

  const [symbol, setSymbol] = useState("AAPL");
  const [timeframe, setTimeframe] = useState("1d");
  const [orderDirection, setOrderDirection] = useState("BUY");
  const [orderType, setOrderType] = useState("MARKET");
  const [quantity, setQuantity] = useState("1");
  const [price, setPrice] = useState("");
  const [stopLoss, setStopLoss] = useState("");
  const [takeProfit, setTakeProfit] = useState("");
  const [isPlacing, setIsPlacing] = useState(false);
  const [orderResult, setOrderResult] = useState<string | null>(null);

  useEffect(() => {
    fetchPositions();
    fetchTrades(20);
    fetchOHLCV(symbol, timeframe, 100);
    fetchPressure(symbol);
  }, [fetchPositions, fetchTrades, fetchOHLCV, fetchPressure, symbol, timeframe]);

  const handlePlaceOrder = async () => {
    setIsPlacing(true);
    setOrderResult(null);
    try {
      const result = await placeOrder({
        symbol,
        direction: orderDirection,
        quantity: parseFloat(quantity),
        order_type: orderType,
        price: price ? parseFloat(price) : undefined,
        stop_loss: stopLoss ? parseFloat(stopLoss) : undefined,
        take_profit: takeProfit ? parseFloat(takeProfit) : undefined,
      });
      if (result) {
        setOrderResult(`Order ${result.status}: ${result.order_id}`);
        setQuantity("1");
        setPrice("");
        setStopLoss("");
        setTakeProfit("");
      } else {
        setOrderResult("Order failed");
      }
    } finally {
      setIsPlacing(false);
    }
  };

  // Transform OHLCV data for chart
  const chartData = ohlcvData.map((candle) => ({
    time: new Date(candle.timestamp).toLocaleDateString([], {
      month: "short",
      day: "numeric",
    }),
    open: candle.open,
    high: candle.high,
    low: candle.low,
    close: candle.close,
    volume: candle.volume,
  }));

  const totalPnl = positions.reduce((acc, p) => acc + p.pnl, 0);
  const totalExposure = positions.reduce(
    (acc, p) => acc + p.current_price * p.amount,
    0
  );

  return (
    <div className="space-y-6 animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-foreground flex items-center gap-2">
            <LineChart className="w-6 h-6 text-emerald" />
            Trading Terminal
          </h1>
          <p className="text-sm text-muted-foreground mt-1">
            Execute trades, manage positions, and monitor the market
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-2">
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-28 font-mono"
              placeholder="Symbol"
            />
            <Select value={timeframe} onValueChange={setTimeframe}>
              <SelectTrigger className="w-24">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="1m">1m</SelectItem>
                <SelectItem value="5m">5m</SelectItem>
                <SelectItem value="15m">15m</SelectItem>
                <SelectItem value="1h">1H</SelectItem>
                <SelectItem value="4h">4H</SelectItem>
                <SelectItem value="1d">1D</SelectItem>
                <SelectItem value="1w">1W</SelectItem>
              </SelectContent>
            </Select>
          </div>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              fetchOHLCV(symbol, timeframe, 100);
              fetchPressure(symbol);
              fetchPositions();
            }}
            className="cursor-pointer"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard
          title="Total P&L"
          value={`${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}`}
          subtitle="Unrealized"
          icon={<TrendingUp className="w-4 h-4" />}
          color={totalPnl >= 0 ? "emerald" : "rose"}
          loading={loadingPositions}
        />
        <MetricCard
          title="Open Positions"
          value={positions.length}
          subtitle="Active trades"
          icon={<Activity className="w-4 h-4" />}
          color="cyan"
          loading={loadingPositions}
        />
        <MetricCard
          title="Total Exposure"
          value={`$${totalExposure.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          subtitle="Current market value"
          icon={<ShoppingCart className="w-4 h-4" />}
          color="purple"
          loading={loadingPositions}
        />
        <MetricCard
          title="Trades Today"
          value={trades.length}
          subtitle="Recent executions"
          icon={<BarChart className="w-4 h-4" />}
          color="amber"
          loading={loadingTrades}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Chart - 2 cols */}
        <div className="lg:col-span-2 space-y-6">
          {/* Price Chart */}
          <Card className="glass-card">
            <CardHeader className="pb-2">
              <CardTitle className="flex items-center justify-between">
                <span className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                  <LineChart className="w-4 h-4 text-cyan" />
                  {symbol} — {timeframe}
                </span>
                {pressureData && (
                  <div className="flex items-center gap-3 text-xs">
                    <span className="text-emerald">
                      Buy: {(pressureData.buy_pressure * 100).toFixed(1)}%
                    </span>
                    <span className="text-rose">
                      Sell: {(pressureData.sell_pressure * 100).toFixed(1)}%
                    </span>
                    <Badge
                      variant={
                        pressureData.verdict === "STRONG_BUY"
                          ? "emerald"
                          : pressureData.verdict === "BUY"
                          ? "emerald"
                          : pressureData.verdict === "STRONG_SELL"
                          ? "rose"
                          : pressureData.verdict === "SELL"
                          ? "rose"
                          : "outline"
                      }
                      className="text-[10px]"
                    >
                      {pressureData.verdict}
                    </Badge>
                  </div>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-80">
                {loadingOHLCV ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="w-6 h-6 text-muted-foreground animate-spin" />
                  </div>
                ) : chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData}>
                      <defs>
                        <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#06b6d4" stopOpacity={0.15} />
                          <stop offset="95%" stopColor="#06b6d4" stopOpacity={0} />
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} />
                      <YAxis stroke="#64748b" fontSize={10} domain={["auto", "auto"]} />
                      <Tooltip
                        contentStyle={{
                          background: "#0d1117",
                          border: "1px solid #1e293b",
                          borderRadius: "8px",
                          fontSize: "11px",
                        }}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="#06b6d4"
                        fill="url(#priceGrad)"
                        strokeWidth={2}
                      />
                      <Line
                        type="monotone"
                        dataKey="high"
                        stroke="#8b5cf640"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="2 2"
                      />
                      <Line
                        type="monotone"
                        dataKey="low"
                        stroke="#8b5cf640"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="2 2"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm">
                    No chart data available for {symbol}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Open Positions */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-emerald" />
                Open Positions
              </CardTitle>
            </CardHeader>
            <CardContent>
              {positions.length > 0 ? (
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-xs text-muted-foreground border-b border-border/30">
                        <th className="text-left py-2 px-2">Symbol</th>
                        <th className="text-right py-2 px-2">Qty</th>
                        <th className="text-right py-2 px-2">Avg Price</th>
                        <th className="text-right py-2 px-2">Current</th>
                        <th className="text-right py-2 px-2">P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-border/10 hover:bg-secondary/20 transition-colors"
                        >
                          <td className="py-2 px-2 font-mono font-medium text-foreground">
                            {pos.ticker}
                          </td>
                          <td className="py-2 px-2 text-right text-foreground tabular-nums">
                            {pos.amount}
                          </td>
                          <td className="py-2 px-2 text-right text-muted-foreground tabular-nums">
                            {pos.avg_price.toFixed(2)}
                          </td>
                          <td className="py-2 px-2 text-right text-foreground tabular-nums">
                            {pos.current_price.toFixed(2)}
                          </td>
                          <td
                            className={`py-2 px-2 text-right font-medium tabular-nums ${
                              pos.pnl >= 0 ? "profit-text" : "loss-text"
                            }`}
                          >
                            {pos.pnl >= 0 ? "+" : ""}
                            {pos.pnl.toFixed(2)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-8 text-muted-foreground text-sm">
                  No open positions
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Order + Trade History */}
        <div className="space-y-6">
          {/* Order Form */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-cyan" />
                Place Order
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Direction Toggle */}
              <div className="grid grid-cols-2 gap-2">
                <button
                  onClick={() => setOrderDirection("BUY")}
                  className={`py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                    orderDirection === "BUY"
                      ? "bg-emerald/20 text-emerald border border-emerald/30"
                      : "bg-secondary/30 text-muted-foreground border border-transparent hover:bg-secondary/50"
                  }`}
                >
                  <ArrowUpRight className="w-4 h-4 inline mr-1" />
                  Buy
                </button>
                <button
                  onClick={() => setOrderDirection("SELL")}
                  className={`py-2 rounded-lg text-sm font-medium transition-all cursor-pointer ${
                    orderDirection === "SELL"
                      ? "bg-rose/20 text-rose border border-rose/30"
                      : "bg-secondary/30 text-muted-foreground border border-transparent hover:bg-secondary/50"
                  }`}
                >
                  <ArrowDownRight className="w-4 h-4 inline mr-1" />
                  Sell
                </button>
              </div>

              {/* Order Type */}
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">
                  Order Type
                </label>
                <Select value={orderType} onValueChange={setOrderType}>
                  <SelectTrigger>
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MARKET">Market</SelectItem>
                    <SelectItem value="LIMIT">Limit</SelectItem>
                    <SelectItem value="STOP">Stop</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Quantity */}
              <div>
                <label className="text-xs text-muted-foreground mb-1.5 block">
                  Quantity
                </label>
                <Input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="tabular-nums"
                  min="0.01"
                  step="0.01"
                />
              </div>

              {/* Price (for limit/stop) */}
              {orderType !== "MARKET" && (
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">
                    Price
                  </label>
                  <Input
                    type="number"
                    value={price}
                    onChange={(e) => setPrice(e.target.value)}
                    className="tabular-nums"
                    placeholder="0.00"
                    step="0.01"
                  />
                </div>
              )}

              {/* Stop Loss / Take Profit */}
              <div className="grid grid-cols-2 gap-2">
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">
                    Stop Loss
                  </label>
                  <Input
                    type="number"
                    value={stopLoss}
                    onChange={(e) => setStopLoss(e.target.value)}
                    className="tabular-nums"
                    placeholder="—"
                    step="0.01"
                  />
                </div>
                <div>
                  <label className="text-xs text-muted-foreground mb-1.5 block">
                    Take Profit
                  </label>
                  <Input
                    type="number"
                    value={takeProfit}
                    onChange={(e) => setTakeProfit(e.target.value)}
                    className="tabular-nums"
                    placeholder="—"
                    step="0.01"
                  />
                </div>
              </div>

              {/* Order Result */}
              {orderResult && (
                <div
                  className={`p-2 rounded-lg text-xs ${
                    orderResult.includes("FILLED")
                      ? "bg-emerald/10 text-emerald border border-emerald/20"
                      : "bg-rose/10 text-rose border border-rose/20"
                  }`}
                >
                  {orderResult}
                </div>
              )}

              {/* Submit */}
              <Button
                className={`w-full cursor-pointer ${
                  orderDirection === "BUY"
                    ? "bg-emerald hover:bg-emerald/90 text-white"
                    : "bg-rose hover:bg-rose/90 text-white"
                }`}
                onClick={handlePlaceOrder}
                disabled={isPlacing || !quantity || parseFloat(quantity) <= 0}
              >
                {isPlacing ? (
                  <RefreshCw className="w-4 h-4 animate-spin mr-2" />
                ) : orderDirection === "BUY" ? (
                  <ArrowUpRight className="w-4 h-4 mr-2" />
                ) : (
                  <ArrowDownRight className="w-4 h-4 mr-2" />
                )}
                {orderDirection} {symbol}
              </Button>
            </CardContent>
          </Card>

          {/* Trade History */}
          <Card className="glass-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-muted-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber" />
                Recent Trades
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="max-h-72">
                {trades.length > 0 ? (
                  <div className="space-y-2">
                    {trades.slice(0, 15).map((trade) => (
                      <div
                        key={trade.id}
                        className="p-2 rounded-lg bg-secondary/20 border border-border/30 text-xs"
                      >
                        <div className="flex items-center justify-between mb-1">
                          <div className="flex items-center gap-2">
                            <span className="font-mono font-medium text-foreground">
                              {trade.ticker}
                            </span>
                            <Badge
                              variant={
                                trade.action === "BUY" ? "emerald" : "rose"
                              }
                              className="text-[9px] px-1.5 py-0"
                            >
                              {trade.action}
                            </Badge>
                          </div>
                          <span className="text-muted-foreground">
                            {new Date(trade.timestamp).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                            })}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-muted-foreground">
                          <span>{trade.amount} @ ${trade.price.toFixed(2)}</span>
                          <span className="tabular-nums">
                            ${trade.total_value.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-center py-8 text-muted-foreground text-sm">
                    No recent trades
                  </div>
                )}
              </ScrollArea>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
