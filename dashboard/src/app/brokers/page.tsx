"use client";

import React, { useEffect, useState, useCallback } from "react";
import { brokersApi } from "@/lib/api-client";
import type {
  BrokerAccount, BrokerPositionsResponse, MT5AccountInfo,
  LedgerAccount,
} from "@/lib/api-client";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { RefreshCw } from "lucide-react";

// GATE-6 final: dark-tech rewrite (restored) + all-ever-connected ledger +
// live-discovered terminals. Single page, no extra components.

function BrokersContent() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [ledger, setLedger] = useState<LedgerAccount[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [info, setInfo] = useState<MT5AccountInfo | null>(null);
  const [positions, setPositions] = useState<BrokerPositionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState({ symbol: "EURUSD.vx", side: "buy", quantity: 0.01, type: "market" });
  const [msg, setMsg] = useState("");

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const list = await brokersApi.list();
      setAccounts(list.accounts);
      if (!selected && list.accounts.length) setSelected(list.accounts[0].name);
    } catch (e) {
      setMsg(`List error: ${(e as Error).message}`);
    } finally {
      setLoading(false);
    }
  }, [selected]);

  const loadLedger = useCallback(async () => {
    try {
      const l = await brokersApi.ledger();
      setLedger(l.accounts ?? []);
    } catch { /* ledger optional */ }
  }, []);

  const loadAccount = useCallback(async (name: string) => {
    setSelected(name);
    setInfo(null);
    setPositions(null);
    try {
      const [acc, pos] = await Promise.all([
        brokersApi.account(name),
        brokersApi.positions(name),
      ]);
      setInfo(acc);
      setPositions(pos);
    } catch (e) {
      setMsg(`Account error: ${(e as Error).message}`);
    }
  }, []);

  useEffect(() => { refresh(); loadLedger(); }, [refresh, loadLedger]);

  const submitOrder = async () => {
    setMsg("");
    try {
      const r = await brokersApi.placeOrder(selected, { ...order });
      setMsg(`Order sent: ${JSON.stringify(r).slice(0, 120)}`);
      loadAccount(selected);
    } catch (e) {
      setMsg(`Order error: ${(e as Error).message}`);
    }
  };

  return (
    <div className="p-6 space-y-4 animate-slide-up">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-bold text-white flex items-center gap-2">
          Brokers — Multi-Account MT5
        </h1>
        <Button variant="ghost" size="sm" onClick={() => { refresh(); loadLedger(); }} disabled={loading}>
          <RefreshCw className={`w-3.5 h-3.5 mr-1 ${loading ? "animate-spin" : ""}`} /> Refresh
        </Button>
      </div>

      {msg && <div className="text-sm text-amber-400 bg-amber-500/10 border border-amber-500/20 p-2 rounded">{msg}</div>}

      {/* Registered execution accounts */}
      <Card>
        <h2 className="text-sm font-semibold text-white/70 mb-1">Registered Accounts</h2>
        <p className="text-[10px] text-white/30 mb-3">Execution targets from config</p>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-4">
          {accounts.map((a) => (
            <button key={a.name} onClick={() => loadAccount(a.name)}
              className={`text-left p-3 rounded-lg border transition-colors ${
                selected === a.name
                  ? "border-cyan-500/40 bg-white/[0.06]"
                  : "border-white/[0.06] bg-white/[0.02] hover:bg-white/[0.04]"
              }`}>
              <div className="font-semibold text-sm text-white/85">{a.name}</div>
              <div className="text-[10px] text-white/35">{a.role} · {a.state}</div>
              <div className="mt-1">
                <Badge variant={a.connected ? "success" : "danger"} className="text-[10px]">
                  {a.connected ? "● connected" : "○ offline"}
                </Badge>
              </div>
            </button>
          ))}
          {!accounts.length && (
            <div className="text-white/35 text-sm col-span-3">No MT5 accounts registered. Add to config/mt5_accounts.yaml (editable via /config).</div>
          )}
        </div>
      </Card>

      {/* GATE-6: every account EVER connected */}
      <Card>
        <h2 className="text-sm font-semibold text-white/70 mb-1">Account Ledger</h2>
        <p className="text-[10px] text-white/30 mb-3">{ledger.length} account(s) ever connected — auto-detected from MT5 terminals</p>
        {ledger.length === 0 ? (
          <p className="text-sm text-white/30 py-4 text-center">
            Ledger empty — connect a terminal and QNA records it automatically.
          </p>
        ) : (
          <div className="overflow-x-auto rounded-xl border border-white/[0.06]">
            <table className="w-full text-xs">
              <thead className="sticky top-0 bg-[#0A0A0E]">
                <tr className="text-left text-[10px] uppercase tracking-wider text-white/30">
                  <th className="px-3 py-2">Login</th>
                  <th className="px-3 py-2">Name</th>
                  <th className="px-3 py-2">Server</th>
                  <th className="px-3 py-2">Trades</th>
                  <th className="px-3 py-2">Total PnL</th>
                  <th className="px-3 py-2">Last Seen</th>
                </tr>
              </thead>
              <tbody>
                {ledger.map((l) => (
                  <tr key={l.login} className="border-t border-white/[0.04] hover:bg-white/[0.02]">
                    <td className="px-3 py-2 font-mono text-white/70">{l.login}</td>
                    <td className="px-3 py-2 text-white/60">{l.name || "—"}</td>
                    <td className="px-3 py-2 text-white/60">{l.server}</td>
                    <td className="px-3 py-2 font-mono tabular-nums text-white/60">{l.total_trades}</td>
                    <td className={`px-3 py-2 font-mono tabular-nums ${(l.total_pnl ?? 0) >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                      {(l.total_pnl ?? 0).toFixed(2)}
                    </td>
                    <td className="px-3 py-2 text-white/40 font-mono text-[10px]">{String(l.last_seen).slice(0, 16)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {selected && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          <Card>
            <h2 className="text-sm font-semibold text-white/70 mb-1">Account: {selected}</h2>
            <p className="text-[10px] text-white/30 mb-3">Live terminal data</p>
            {info ? (
              <div className="grid grid-cols-2 gap-2 text-sm bbg-cell">
                <Stat label="Login" value={info.login} />
                <Stat label="Server" value={info.server} />
                <Stat label="Balance" value={info.balance.toFixed(2)} />
                <Stat label="Equity" value={info.equity.toFixed(2)} />
                <Stat label="Margin" value={info.margin.toFixed(2)} />
                <Stat label="Free Margin" value={info.margin_free.toFixed(2)} />
                <Stat label="Margin Level" value={info.margin_level.toFixed(1) + "%"} />
                <Stat label="Leverage" value={"1:" + info.leverage} />
              </div>
            ) : <div className="text-white/35 text-sm">No data (terminal offline?)</div>}

            <h3 className="text-sm font-semibold mt-4 mb-2 text-white/60">Open Positions</h3>
            {positions?.positions?.length ? (
              <table className="w-full text-xs">
                <thead><tr className="text-left text-white/30 uppercase text-[10px] tracking-wider">
                  <th className="pb-1">Symbol</th><th>Side</th><th>Vol</th><th>Entry</th><th>Curr</th><th>PNL</th></tr></thead>
                <tbody>
                  {positions.positions.map((p, i) => (
                    <tr key={i} className="border-t border-white/[0.04]">
                      <td className="py-1.5 font-mono">{p.symbol}</td><td>{p.side}</td>
                      <td className="font-mono tabular-nums">{p.quantity}</td>
                      <td className="font-mono tabular-nums">{p.entry_price}</td>
                      <td className="font-mono tabular-nums">{p.current_price}</td>
                      <td className={`font-mono tabular-nums ${p.unrealized_pnl >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                        {p.unrealized_pnl.toFixed(2)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <div className="text-white/35 text-sm">No open positions.</div>}
          </Card>

          <Card>
            <h2 className="text-sm font-semibold text-white/70 mb-1">Execute Order</h2>
            <p className="text-[10px] text-white/30 mb-3">Kill-switch + risk guards apply</p>
            <div className="space-y-3">
              <Input placeholder="Symbol (e.g. EURUSD.vx)" value={order.symbol}
                onChange={(e) => setOrder({ ...order, symbol: e.target.value })} />
              <div className="flex gap-2">
                <Select value={order.side} onChange={(e) => setOrder({ ...order, side: e.target.value })}
                  options={[{ value: "buy", label: "BUY" }, { value: "sell", label: "SELL" }]} />
                <Select value={order.type} onChange={(e) => setOrder({ ...order, type: e.target.value })}
                  options={[{ value: "market", label: "MARKET" }, { value: "limit", label: "LIMIT" }, { value: "stop", label: "STOP" }]} />
              </div>
              <Input type="number" step="0.01" placeholder="Volume (lots)"
                value={order.quantity}
                onChange={(e) => setOrder({ ...order, quantity: parseFloat(e.target.value) || 0 })} />
              <Button variant="primary" className="w-full" onClick={submitOrder}>
                SEND ORDER → {selected}
              </Button>
              <p className="text-[10px] text-white/25">
                Symbol auto-resolved against the terminal&apos;s real catalog (any broker suffix).
              </p>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-white/[0.03] border border-white/[0.05] rounded p-2">
      <div className="text-[10px] uppercase tracking-wider text-white/30">{label}</div>
      <div className="font-mono tabular-nums text-white/80 text-sm">{value}</div>
    </div>
  );
}

export default function BrokersPage() {
  return (
    <ErrorBoundary>
      <BrokersContent />
    </ErrorBoundary>
  );
}
