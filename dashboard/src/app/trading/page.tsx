"use client";

import { useEffect, useState } from "react";
import { ChartCard } from "@/components/shared/chart-card";
import { Badge } from "@/components/ui/badge";
import { ScrollArea } from "@/components/ui/scroll-area";
import { ArrowLeftRight, ShieldAlert, ShieldCheck } from "lucide-react";
import { tradingApi, agentsApi, type OrderSide, type OrderType, type PlaceOrderResponse, type KillSwitchStatusResponse } from "@/lib/api-client";

export default function TradingPage() {
  const [positions, setPositions] = useState<any>(null);
  const [ksActive, setKsActive] = useState<boolean>(false);
  const [ksStatus, setKsStatus] = useState<KillSwitchStatusResponse | null>(null);

  // order form state
  const [symbol, setSymbol] = useState("BTC/USDT");
  const [side, setSide] = useState<OrderSide>("buy");
  const [type, setType] = useState<OrderType>("market");
  const [quantity, setQuantity] = useState<number>(0.01);
  const [price, setPrice] = useState<string>("");
  const [orderMsg, setOrderMsg] = useState<string>("");
  const [orderBusy, setOrderBusy] = useState<boolean>(false);

  async function refresh() {
    try {
      const pos = await tradingApi.getPositions();
      setPositions(pos);
    } catch {
      setPositions(null);
    }
    try {
      const st = await agentsApi.getStatus();
      setKsActive(st.kill_switch_active);
    } catch {
      /* ignore */
    }
  }

  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 5000);
    return () => clearInterval(t);
  }, []);

  async function submitOrder(e: React.FormEvent) {
    e.preventDefault();
    setOrderBusy(true);
    setOrderMsg("");
    try {
      const res: PlaceOrderResponse = await tradingApi.placeOrder({
        symbol,
        side,
        type,
        quantity,
        price: price ? Number(price) : undefined,
      });
      setOrderMsg(`✓ ${res.status.toUpperCase()}: ${res.message} (${res.orderId})`);
      refresh();
    } catch (err: any) {
      setOrderMsg(`✗ ${err?.message || "order failed"}`);
    } finally {
      setOrderBusy(false);
    }
  }

  async function toggleKillSwitch() {
    try {
      const res = ksActive
        ? await agentsApi.resetKillSwitch()
        : await agentsApi.activateKillSwitch("manual trigger from dashboard");
      setKsStatus(res);
      setKsActive(res.active);
    } catch (err: any) {
      setOrderMsg(`✗ kill-switch error: ${err?.message || "unknown"}`);
    }
  }

  return (
    <div className="space-y-4">
      <h1 className="text-xl font-bold text-white flex items-center gap-2">
        <ArrowLeftRight className="w-5 h-5 text-cyan-400" />
        Trading
      </h1>

      {/* Kill switch — war-grade emergency halt */}
      <ChartCard title="Kill Switch" subtitle="Halt / resume all live trading">
        <div className="flex items-center gap-3 p-2">
          <button
            onClick={toggleKillSwitch}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg font-semibold text-sm transition ${
              ksActive
                ? "bg-red-600/80 hover:bg-red-600 text-white"
                : "bg-emerald-600/80 hover:bg-emerald-600 text-white"
            }`}
          >
            {ksActive ? <ShieldAlert className="w-4 h-4" /> : <ShieldCheck className="w-4 h-4" />}
            {ksActive ? "TRADING HALTED — RESUME" : "HALT ALL TRADING"}
          </button>
          <Badge variant={ksActive ? "danger" : "success"} className="text-[11px]">
            {ksActive ? "KILL SWITCH ACTIVE" : "SYSTEM NOMINAL"}
          </Badge>
          {ksStatus?.reason && <span className="text-xs text-white/50">reason: {ksStatus.reason}</span>}
        </div>
      </ChartCard>

      {/* Execution panel */}
      <ChartCard title="Place Order" subtitle="Live execution via /api/trading/order">
        <form onSubmit={submitOrder} className="grid grid-cols-2 md:grid-cols-5 gap-2 p-2 items-end">
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Symbol
            <input
              value={symbol}
              onChange={(e) => setSymbol(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm"
            />
          </label>
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Side
            <select
              value={side}
              onChange={(e) => setSide(e.target.value as OrderSide)}
              className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm"
            >
              <option value="buy">BUY</option>
              <option value="sell">SELL</option>
            </select>
          </label>
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Type
            <select
              value={type}
              onChange={(e) => setType(e.target.value as OrderType)}
              className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm"
            >
              <option value="market">MARKET</option>
              <option value="limit">LIMIT</option>
              <option value="stop">STOP</option>
              <option value="stop_limit">STOP-LIMIT</option>
            </select>
          </label>
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Qty
            <input
              type="number"
              step="0.0001"
              value={quantity}
              onChange={(e) => setQuantity(Number(e.target.value))}
              className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm"
            />
          </label>
          <label className="text-xs text-white/60 flex flex-col gap-1">
            Price (limit)
            <input
              value={price}
              placeholder="mkt"
              onChange={(e) => setPrice(e.target.value)}
              className="bg-white/[0.04] border border-white/[0.08] rounded px-2 py-1 text-white text-sm"
            />
          </label>
          <button
            type="submit"
            disabled={orderBusy}
            className="col-span-2 md:col-span-5 mt-1 px-4 py-2 rounded-lg bg-cyan-600 hover:bg-cyan-500 disabled:opacity-50 text-white font-semibold text-sm"
          >
            {orderBusy ? "Submitting…" : "SUBMIT ORDER"}
          </button>
        </form>
        {orderMsg && (
          <p className="text-xs px-2 pb-2 text-white/70 font-mono">{orderMsg}</p>
        )}
      </ChartCard>

      {/* Positions monitor */}
      <ChartCard title="Positions" subtitle="Live from /api/trading/positions">
        <ScrollArea className="max-h-96">
          <div className="space-y-2">
            {positions?.positions?.map((p: any) => (
              <div key={p.ticker} className="p-3 rounded-lg bg-white/[0.02] border border-white/[0.04]">
                <span className="text-sm font-mono text-white/80">{p.ticker}</span>
                <span className="text-xs text-white/50 ml-2">Qty: {p.amount}</span>
                <Badge variant={p.pnl >= 0 ? "success" : "danger"} className="ml-2 text-[10px]">
                  PnL: {p.pnl}
                </Badge>
              </div>
            ))}
            {(!positions?.positions || positions.positions.length === 0) && (
              <p className="text-white/40 text-sm p-4">No positions or API unavailable</p>
            )}
          </div>
        </ScrollArea>
      </ChartCard>
    </div>
  );
}
