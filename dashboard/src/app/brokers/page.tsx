"use client";

import React, { useEffect, useState, useCallback } from "react";
import { brokersApi } from "@/lib/api-client";
import type { BrokerAccount, BrokerPositionsResponse, MT5AccountInfo } from "@/lib/api-client";

// ponytail: single page, no extra components. Lists MT5 accounts (Exness /
// Valutrades / etc), shows balance + positions per account, and lets you
// fire a market order directly through the connected terminal.

export default function BrokersPage() {
  const [accounts, setAccounts] = useState<BrokerAccount[]>([]);
  const [selected, setSelected] = useState<string>("");
  const [info, setInfo] = useState<MT5AccountInfo | null>(null);
  const [positions, setPositions] = useState<BrokerPositionsResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState({ symbol: "EURUSD", side: "buy", quantity: 0.01, type: "market" });
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

  useEffect(() => { refresh(); }, [refresh]);

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
    <div className="p-6 space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">Brokers — Multi-Account MT5</h1>
        <button onClick={refresh} className="px-3 py-1 bg-blue-600 rounded text-sm">
          {loading ? "Loading…" : "Refresh"}
        </button>
      </div>

      {msg && <div className="text-sm text-yellow-400 bg-yellow-900/20 p-2 rounded">{msg}</div>}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {accounts.map((a) => (
          <button
            key={a.name}
            onClick={() => loadAccount(a.name)}
            className={`text-left p-4 rounded-lg border ${
              selected === a.name ? "border-blue-500 bg-blue-900/20" : "border-gray-700 bg-gray-900/40"
            }`}
          >
            <div className="font-semibold">{a.name}</div>
            <div className="text-xs text-gray-400">{a.role} · {a.state}</div>
            <div className={`text-xs ${a.connected ? "text-green-400" : "text-red-400"}`}>
              {a.connected ? "● connected" : "○ offline"}
            </div>
          </button>
        ))}
        {!accounts.length && <div className="text-gray-500 text-sm">No MT5 accounts registered. Add to config/mt5_accounts.yaml.</div>}
      </div>

      {selected && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="space-y-4">
            <h2 className="text-lg font-semibold">Account: {selected}</h2>
            {info ? (
              <div className="grid grid-cols-2 gap-2 text-sm">
                <Stat label="Login" value={info.login} />
                <Stat label="Server" value={info.server} />
                <Stat label="Balance" value={info.balance.toFixed(2)} />
                <Stat label="Equity" value={info.equity.toFixed(2)} />
                <Stat label="Margin" value={info.margin.toFixed(2)} />
                <Stat label="Free Margin" value={info.margin_free.toFixed(2)} />
                <Stat label="Margin Level" value={info.margin_level.toFixed(1) + "%"} />
                <Stat label="Leverage" value={"1:" + info.leverage} />
              </div>
            ) : <div className="text-gray-500 text-sm">No data (terminal offline?)</div>}

            <h3 className="text-md font-semibold mt-4">Open Positions</h3>
            {positions?.positions?.length ? (
              <table className="w-full text-sm">
                <thead><tr className="text-left text-gray-400"><th>Symbol</th><th>Side</th><th>Vol</th><th>Entry</th><th>Curr</th><th>PNL</th></tr></thead>
                <tbody>
                  {positions.positions.map((p, i) => (
                    <tr key={i} className="border-t border-gray-800">
                      <td>{p.symbol}</td><td>{p.side}</td><td>{p.quantity}</td>
                      <td>{p.entry_price}</td><td>{p.current_price}</td>
                      <td className={p.unrealized_pnl >= 0 ? "text-green-400" : "text-red-400"}>{p.unrealized_pnl.toFixed(2)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : <div className="text-gray-500 text-sm">No open positions.</div>}
          </div>

          <div className="space-y-3">
            <h3 className="text-md font-semibold">Execute Order</h3>
            <input className="w-full bg-gray-800 rounded p-2 text-sm" placeholder="Symbol (e.g. EURUSD)"
              value={order.symbol} onChange={(e) => setOrder({ ...order, symbol: e.target.value })} />
            <div className="flex gap-2">
              <select className="bg-gray-800 rounded p-2 text-sm flex-1" value={order.side}
                onChange={(e) => setOrder({ ...order, side: e.target.value })}>
                <option value="buy">BUY</option><option value="sell">SELL</option>
              </select>
              <select className="bg-gray-800 rounded p-2 text-sm flex-1" value={order.type}
                onChange={(e) => setOrder({ ...order, type: e.target.value })}>
                <option value="market">MARKET</option><option value="limit">LIMIT</option><option value="stop">STOP</option>
              </select>
            </div>
            <input type="number" step="0.01" className="w-full bg-gray-800 rounded p-2 text-sm" placeholder="Volume (lots)"
              value={order.quantity} onChange={(e) => setOrder({ ...order, quantity: parseFloat(e.target.value) || 0 })} />
            <button onClick={submitOrder} className="w-full py-2 bg-green-600 rounded font-semibold">
              SEND ORDER → {selected}
            </button>
            <p className="text-xs text-gray-500">Routes through MT5 terminal → kill-switch + risk manager guards apply.</p>
          </div>
        </div>
      )}
    </div>
  );
}

function Stat({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="bg-gray-900/40 rounded p-2">
      <div className="text-xs text-gray-400">{label}</div>
      <div className="font-mono">{value}</div>
    </div>
  );
}
