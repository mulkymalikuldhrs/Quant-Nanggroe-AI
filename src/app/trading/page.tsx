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
  CandlestickChart,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Separator } from "@/components/ui/separator";
import { MetricCard, SectionHeader, Skeleton, AnimatedNumber } from "@/components/dashboard/shared";
import { useAppStore } from "@/lib/store";
import { apiClient } from "@/lib/api-client";
import { cn } from "@/lib/utils";

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
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 animate-slide-up">
        <div className="space-y-1">
          <h1 className="text-3xl font-black gradient-text flex items-center gap-3 tracking-tight">
            <CandlestickChart className="w-8 h-8 text-emerald animate-pulse-glow" />
            Trading Terminal
          </h1>
          <p className="text-sm font-medium text-muted-foreground uppercase tracking-widest pl-11">
            Execute & Monitor Market Positions
          </p>
        </div>
        <div className="flex items-center gap-3 bg-secondary/20 p-1.5 rounded-xl border border-border/50 backdrop-blur-sm shadow-[0_0_15px_rgba(0,0,0,0.1)]">
          <div className="relative">
            <SearchIcon className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-muted-foreground" />
            <Input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value.toUpperCase())}
              className="w-28 font-mono pl-9 h-9 border-none bg-secondary/30 focus-visible:ring-1 focus-visible:ring-emerald/50"
              placeholder="Symbol"
            />
          </div>
          <Select value={timeframe} onValueChange={setTimeframe}>
            <SelectTrigger className="w-24 h-9 border-none bg-secondary/30 focus:ring-1 focus:ring-emerald/50">
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
          <Button
            variant="ghost"
            size="icon"
            onClick={() => {
              fetchOHLCV(symbol, timeframe, 100);
              fetchPressure(symbol);
              fetchPositions();
            }}
            className="cursor-pointer h-9 w-9 scale-tap hover:bg-emerald/10 hover:text-emerald transition-colors"
          >
            <RefreshCw className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 animate-slide-up stagger-children" style={{ animationDelay: '100ms' }}>
        <MetricCard
          title="Total P&L"
          value={`${totalPnl >= 0 ? "+" : ""}$${totalPnl.toFixed(2)}`}
          subtitle="Unrealized returns"
          icon={<TrendingUp className="w-5 h-5" />}
          color={totalPnl >= 0 ? "emerald" : "rose"}
          loading={loadingPositions}
        />
        <MetricCard
          title="Open Positions"
          value={positions.length}
          subtitle="Active trades"
          icon={<Activity className="w-5 h-5" />}
          color="cyan"
          loading={loadingPositions}
        />
        <MetricCard
          title="Total Exposure"
          value={`$${totalExposure.toLocaleString(undefined, { maximumFractionDigits: 0 })}`}
          subtitle="Current market value"
          icon={<ShoppingCart className="w-5 h-5" />}
          color="purple"
          loading={loadingPositions}
        />
        <MetricCard
          title="Trades Today"
          value={trades.length}
          subtitle="Recent executions"
          icon={<BarChart className="w-5 h-5" />}
          color="amber"
          loading={loadingTrades}
        />
      </div>

      {/* Main Content Grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-6 animate-slide-up" style={{ animationDelay: '200ms' }}>
        {/* Chart + Open Positions (2 cols) */}
        <div className="xl:col-span-2 space-y-6">
          {/* Price Chart */}
          <Card variant="gradient" className="h-full">
            <CardHeader className="pb-4">
              <CardTitle className="flex items-center justify-between">
                <span className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                  <LineChart className="w-4 h-4 text-emerald" />
                  <span className="text-emerald text-lg font-mono tracking-tight font-bold">{symbol}</span>
                  <span className="text-muted-foreground ml-2">{timeframe}</span>
                </span>
                {pressureData && (
                  <div className="flex items-center gap-4 bg-background/50 px-3 py-1.5 rounded-lg border border-border/50">
                    <div className="flex items-center gap-1.5 text-xs font-medium">
                      <span className="text-emerald">Buy</span>
                      <span className="text-emerald font-mono">{(pressureData.buy_pressure * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-px h-3 bg-border/50" />
                    <div className="flex items-center gap-1.5 text-xs font-medium">
                      <span className="text-rose">Sell</span>
                      <span className="text-rose font-mono">{(pressureData.sell_pressure * 100).toFixed(1)}%</span>
                    </div>
                    <div className="w-px h-3 bg-border/50" />
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
                      className="text-[9px] font-bold shadow-[0_0_10px_rgba(0,0,0,0.1)]"
                    >
                      {pressureData.verdict.replace('_', ' ')}
                    </Badge>
                  </div>
                )}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="h-[400px] w-full relative">
                {loadingOHLCV ? (
                  <div className="flex items-center justify-center h-full">
                    <RefreshCw className="w-8 h-8 text-emerald animate-spin drop-shadow-[0_0_10px_rgba(16,185,129,0.5)]" />
                  </div>
                ) : chartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="priceGrad" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#10b981" stopOpacity={0.3} />
                          <stop offset="95%" stopColor="#10b981" stopOpacity={0.0} />
                        </linearGradient>
                        <filter id="glowGreen" x="-20%" y="-20%" width="140%" height="140%">
                          <feGaussianBlur stdDeviation="3" result="blur" />
                          <feComposite in="SourceGraphic" in2="blur" operator="over" />
                        </filter>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="rgba(30,41,59,0.5)" vertical={false} />
                      <XAxis dataKey="time" stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} />
                      <YAxis stroke="#64748b" fontSize={10} tickMargin={10} axisLine={false} tickLine={false} domain={["auto", "auto"]} />
                      <Tooltip
                        contentStyle={{
                          background: "rgba(10, 15, 26, 0.95)",
                          backdropFilter: "blur(10px)",
                          border: "1px solid rgba(16, 185, 129, 0.3)",
                          borderRadius: "8px",
                          boxShadow: "0 4px 20px rgba(0,0,0,0.4), 0 0 10px rgba(16,185,129,0.1)",
                          fontSize: "12px",
                          fontWeight: 600,
                        }}
                        itemStyle={{ color: "#10b981" }}
                        cursor={{ stroke: 'rgba(16, 185, 129, 0.5)', strokeWidth: 1, strokeDasharray: '4 4' }}
                      />
                      <Area
                        type="monotone"
                        dataKey="close"
                        stroke="#10b981"
                        fill="url(#priceGrad)"
                        strokeWidth={2}
                        activeDot={{ r: 6, fill: "#10b981", stroke: "#030712", strokeWidth: 2, filter: "url(#glowGreen)" }}
                      />
                      <Line
                        type="monotone"
                        dataKey="high"
                        stroke="rgba(139, 92, 246, 0.3)"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="2 2"
                      />
                      <Line
                        type="monotone"
                        dataKey="low"
                        stroke="rgba(139, 92, 246, 0.3)"
                        strokeWidth={1}
                        dot={false}
                        strokeDasharray="2 2"
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-medium">
                    No chart data available for {symbol}
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Open Positions */}
          <Card variant="flat">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-cyan" />
                Active Positions Tracker
              </CardTitle>
            </CardHeader>
            <CardContent>
              {positions.length > 0 ? (
                <div className="overflow-x-auto custom-scroll">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[10px] uppercase tracking-widest text-muted-foreground border-b border-border/30">
                        <th className="text-left py-3 px-3 font-semibold">Symbol</th>
                        <th className="text-right py-3 px-3 font-semibold">Qty</th>
                        <th className="text-right py-3 px-3 font-semibold">Avg Price</th>
                        <th className="text-right py-3 px-3 font-semibold">Current</th>
                        <th className="text-right py-3 px-3 font-semibold">Unrealized P&L</th>
                      </tr>
                    </thead>
                    <tbody>
                      {positions.map((pos, idx) => (
                        <tr
                          key={idx}
                          className="border-b border-border/10 hover:bg-secondary/30 transition-colors group cursor-default"
                        >
                          <td className="py-3 px-3 font-mono font-bold text-foreground">
                            <span className="flex items-center gap-2">
                              <span className="w-1.5 h-1.5 rounded-full bg-cyan group-hover:shadow-[0_0_8px_rgba(6,182,212,0.8)] transition-shadow" />
                              {pos.ticker}
                            </span>
                          </td>
                          <td className="py-3 px-3 text-right text-foreground font-mono">
                            {pos.amount}
                          </td>
                          <td className="py-3 px-3 text-right text-muted-foreground font-mono">
                            ${pos.avg_price.toFixed(2)}
                          </td>
                          <td className="py-3 px-3 text-right text-foreground font-mono">
                            ${pos.current_price.toFixed(2)}
                          </td>
                          <td className="py-3 px-3 text-right">
                            <Badge
                              variant={pos.pnl >= 0 ? "emerald" : "rose"}
                              className="font-mono text-xs shadow-[0_0_10px_rgba(0,0,0,0.1)]"
                            >
                              {pos.pnl >= 0 ? "+" : ""}
                              <AnimatedNumber value={pos.pnl} formatter={(v) => v.toFixed(2)} />
                            </Badge>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              ) : (
                <div className="text-center py-12 text-muted-foreground text-sm font-medium">
                  <Activity className="w-8 h-8 mx-auto mb-3 text-border" />
                  No active market exposure
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Right Panel - Order Form + Trade History */}
        <div className="space-y-6">
          {/* Order Form */}
          <Card variant="flat" className="border-t-4 border-t-cyan relative overflow-hidden group">
            <div className="absolute right-0 top-0 w-32 h-32 bg-cyan/5 rounded-bl-full translate-x-16 -translate-y-16 group-hover:bg-cyan/10 transition-colors pointer-events-none" />
            <CardHeader className="relative z-10">
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <ShoppingCart className="w-4 h-4 text-cyan" />
                Execution Panel
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-5 relative z-10">
              {/* Direction Toggle */}
              <div className="grid grid-cols-2 gap-3 bg-secondary/20 p-1 rounded-xl border border-border/50">
                <button
                  onClick={() => setOrderDirection("BUY")}
                  className={cn(
                    "py-2.5 rounded-lg text-sm font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm",
                    orderDirection === "BUY"
                      ? "bg-emerald text-primary-foreground shadow-[0_0_15px_rgba(16,185,129,0.3)]"
                      : "bg-transparent text-muted-foreground hover:bg-secondary/50"
                  )}
                >
                  <ArrowUpRight className="w-4 h-4" />
                  BUY LONG
                </button>
                <button
                  onClick={() => setOrderDirection("SELL")}
                  className={cn(
                    "py-2.5 rounded-lg text-sm font-bold transition-all cursor-pointer flex items-center justify-center gap-1.5 shadow-sm",
                    orderDirection === "SELL"
                      ? "bg-rose text-primary-foreground shadow-[0_0_15px_rgba(244,63,94,0.3)]"
                      : "bg-transparent text-muted-foreground hover:bg-secondary/50"
                  )}
                >
                  <ArrowDownRight className="w-4 h-4" />
                  SELL SHORT
                </button>
              </div>

              {/* Order Type */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">
                  Order Type
                </label>
                <Select value={orderType} onValueChange={setOrderType}>
                  <SelectTrigger className="bg-secondary/20 focus:ring-cyan/50 h-10">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="MARKET" className="font-bold">Market Execution</SelectItem>
                    <SelectItem value="LIMIT" className="font-bold">Limit Order</SelectItem>
                    <SelectItem value="STOP" className="font-bold">Stop Order</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              {/* Quantity */}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">
                  Amount / Shares
                </label>
                <Input
                  type="number"
                  value={quantity}
                  onChange={(e) => setQuantity(e.target.value)}
                  className="tabular-nums font-mono text-lg h-12 bg-secondary/20 focus-visible:ring-cyan/50"
                  min="0.01"
                  step="0.01"
                />
              </div>

              {/* Price (for limit/stop) */}
              {orderType !== "MARKET" && (
                <div className="space-y-1.5 animate-in slide-in-from-top-2">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">
                    Target Price
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">$</span>
                    <Input
                      type="number"
                      value={price}
                      onChange={(e) => setPrice(e.target.value)}
                      className="tabular-nums font-mono pl-7 bg-secondary/20 focus-visible:ring-cyan/50"
                      placeholder="0.00"
                      step="0.01"
                    />
                  </div>
                </div>
              )}

              {/* Stop Loss / Take Profit */}
              <div className="grid grid-cols-2 gap-3 pt-2 border-t border-border/30">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">
                    Stop Loss
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">$</span>
                    <Input
                      type="number"
                      value={stopLoss}
                      onChange={(e) => setStopLoss(e.target.value)}
                      className="tabular-nums font-mono pl-6 bg-secondary/20 focus-visible:ring-rose/50"
                      placeholder="—"
                      step="0.01"
                    />
                  </div>
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold uppercase tracking-widest text-muted-foreground block">
                    Take Profit
                  </label>
                  <div className="relative">
                    <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground text-xs">$</span>
                    <Input
                      type="number"
                      value={takeProfit}
                      onChange={(e) => setTakeProfit(e.target.value)}
                      className="tabular-nums font-mono pl-6 bg-secondary/20 focus-visible:ring-emerald/50"
                      placeholder="—"
                      step="0.01"
                    />
                  </div>
                </div>
              </div>

              {/* Order Result */}
              {orderResult && (
                <div
                  className={cn("p-3 rounded-xl text-sm font-medium animate-fade-in border shadow-sm",
                    orderResult.includes("FILLED")
                      ? "bg-emerald/10 text-emerald border-emerald/30 shadow-[0_0_10px_rgba(16,185,129,0.1)]"
                      : "bg-rose/10 text-rose border-rose/30 shadow-[0_0_10px_rgba(244,63,94,0.1)]"
                  )}
                >
                  <div className="flex items-center gap-2">
                    {orderResult.includes("FILLED") ? <TrendingUp className="w-4 h-4" /> : <X className="w-4 h-4" />}
                    {orderResult}
                  </div>
                </div>
              )}

              {/* Submit */}
              <Button
                className={cn("w-full cursor-pointer h-12 font-bold text-base tracking-wide shadow-lg hover-lift",
                  orderDirection === "BUY"
                    ? "bg-emerald hover:bg-emerald/90 text-primary-foreground shadow-[0_4px_20px_rgba(16,185,129,0.3)]"
                    : "bg-rose hover:bg-rose/90 text-primary-foreground shadow-[0_4px_20px_rgba(244,63,94,0.3)]"
                )}
                onClick={handlePlaceOrder}
                disabled={isPlacing || !quantity || parseFloat(quantity) <= 0}
              >
                {isPlacing ? (
                  <>
                    <RefreshCw className="w-5 h-5 animate-spin mr-2" />
                    TRANSMITTING...
                  </>
                ) : (
                  <>
                    {orderDirection === "BUY" ? (
                      <ArrowUpRight className="w-5 h-5 mr-2" />
                    ) : (
                      <ArrowDownRight className="w-5 h-5 mr-2" />
                    )}
                    SUBMIT {orderDirection} ORDER
                  </>
                )}
              </Button>
            </CardContent>
          </Card>

          {/* Trade History */}
          <Card variant="flat">
            <CardHeader>
              <CardTitle className="text-sm font-semibold text-foreground uppercase tracking-wider flex items-center gap-2">
                <Activity className="w-4 h-4 text-amber" />
                Execution Log
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ScrollArea className="h-[280px] pr-3">
                {trades.length > 0 ? (
                  <div className="space-y-3 stagger-children">
                    {trades.slice(0, 15).map((trade) => (
                      <div
                        key={trade.id}
                        className="p-3 rounded-xl bg-secondary/10 border border-border/30 text-sm hover:bg-secondary/20 transition-colors"
                      >
                        <div className="flex items-center justify-between mb-1.5">
                          <div className="flex items-center gap-2.5">
                            <span className="font-mono font-bold text-foreground">
                              {trade.ticker}
                            </span>
                            <Badge
                              variant={trade.action === "BUY" ? "emerald" : "rose"}
                              className="text-[9px] font-bold px-1.5 py-0 shadow-sm"
                            >
                              {trade.action}
                            </Badge>
                          </div>
                          <span className="text-xs font-mono text-muted-foreground">
                            {new Date(trade.timestamp).toLocaleTimeString([], {
                              hour: "2-digit",
                              minute: "2-digit",
                              second: "2-digit"
                            })}
                          </span>
                        </div>
                        <div className="flex items-center justify-between text-muted-foreground text-xs font-medium">
                          <span className="font-mono bg-background/50 px-1.5 py-0.5 rounded border border-border/40">{trade.amount} @ ${trade.price.toFixed(2)}</span>
                          <span className="tabular-nums font-bold text-foreground">
                            ${trade.total_value.toFixed(2)}
                          </span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="flex items-center justify-center h-full text-muted-foreground text-sm font-medium">
                    <div className="text-center">
                      <BarChart className="w-8 h-8 mx-auto mb-3 text-border" />
                      No recent executions
                    </div>
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

function SearchIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}
