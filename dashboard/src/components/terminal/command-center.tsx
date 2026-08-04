"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";
import { tradingApi } from "@/lib/api-client";
import { Activity, Bot, Shield, Wifi, ArrowUp, ArrowDown } from "lucide-react";

/* ════════════════════════════════════════════════════════════════════
   POSITIONS + PnL (70% hero panel) — blueprint: command center
   ════════════════════════════════════════════════════════════════════ */
interface Pos {
  id?: string; ticket?: string; symbol: string; side?: string;
  volume?: number; price_open?: number; current?: number;
  profit?: number; sl?: number; tp?: number;
}

export function PositionsPanel({ col = "col-span-12 lg:col-span-8" }: { col?: string }) {
  const [pos, setPos] = useState<Pos[]>([]);
  const [err, setErr] = useState<string | null>(null);
  const [ts, setTs] = useState<string>("");

  const load = async () => {
    try {
      const r = await tradingApi.getPositions();
      const raw = (r as any)?.positions ?? [];
      setPos(raw);
      setTs(new Date().toLocaleTimeString());
      setErr(null);
    } catch (e: any) {
      setErr(e.message || "positions unavailable");
    }
  };
  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id); }, []);

  const totalPnl = pos.reduce((s, p) => s + (p.profit ?? 0), 0);

  return (
    <div className={cn("double-bezel p-2", col)}>
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-1.5">
          <Activity className="w-3 h-3 text-white/40" />
          <span className="text-[10px] font-mono uppercase tracking-[1px] text-white/50">Positions &amp; PnL</span>
        </div>
        <div className="flex items-center gap-2">
          <span className={cn("text-[11px] font-mono font-bold", totalPnl >= 0 ? "text-profit" : "text-loss")}>
            {totalPnl >= 0 ? "+" : ""}{totalPnl.toFixed(2)}
          </span>
          <span className="text-[8px] text-white/25 font-mono">{ts}</span>
        </div>
      </div>
      {err && <div className="text-[9px] text-loss/80 px-1 py-2">{err}</div>}
      {!err && pos.length === 0 && (
        <div className="text-[10px] text-white/25 text-center py-6 font-mono">NO OPEN POSITIONS</div>
      )}
      {pos.length > 0 && (
        <table className="w-full text-[9px] font-mono">
          <thead>
            <tr className="text-[8px] text-white/30 uppercase">
              <th className="text-left font-normal py-1">Symbol</th>
              <th className="text-right font-normal">Side</th>
              <th className="text-right font-normal">Vol</th>
              <th className="text-right font-normal">Open</th>
              <th className="text-right font-normal">Now</th>
              <th className="text-right font-normal">SL</th>
              <th className="text-right font-normal">TP</th>
              <th className="text-right font-normal">PnL</th>
            </tr>
          </thead>
          <tbody>
            {pos.map((p, i) => {
              const side = String(p.side ?? (p as any).type ?? "").toLowerCase();
              const isBuy = side.startsWith("buy") || side === "0";
              const isSell = side.startsWith("sell") || side === "1";
              return (
                <tr key={i} className="border-b border-white/[0.03]">
                  <td className="py-1 text-white/80 font-medium">{p.symbol}</td>
                  <td className={cn("py-1 text-right font-bold", isBuy ? "text-profit" : isSell ? "text-loss" : "text-white/40")}>
                    {isBuy ? "LONG" : isSell ? "SHORT" : side || "—"}
                  </td>
                  <td className="py-1 text-right text-white/50">{p.volume ?? "—"}</td>
                  <td className="py-1 text-right text-white/60">{p.price_open != null ? p.price_open.toFixed(5) : "—"}</td>
                  <td className="py-1 text-right text-white/60">{p.current != null ? p.current.toFixed(5) : "—"}</td>
                  <td className="py-1 text-right text-loss/70">{p.sl ?? "—"}</td>
                  <td className="py-1 text-right text-profit/70">{p.tp ?? "—"}</td>
                  <td className={cn("py-1 text-right font-bold", (p.profit ?? 0) >= 0 ? "text-profit" : "text-loss")}>
                    {(p.profit ?? 0) >= 0 ? "+" : ""}{(p.profit ?? 0).toFixed(2)}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   AI REASONING (30% panel) — blueprint: scoring + bias + uncertainty
   ════════════════════════════════════════════════════════════════════ */
export function AIReasoningPanel({ col = "col-span-12 lg:col-span-4" }: { col?: string }) {
  const [st, setSt] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);

  const load = async () => {
    try {
      const r = await fetch("/api/autonomous/status", { cache: "no-store" });
      setSt(await r.json());
      setErr(null);
    } catch (e: any) { setErr(e.message || "unavailable"); }
  };
  useEffect(() => { load(); const id = setInterval(load, 15000); return () => clearInterval(id); }, []);

  const isRunning = st?.is_running === true;
  const sharpe = st?.sharpe_ratio ?? 0;
  const dd = st?.drawdown ?? 0;
  const eq = st?.current_equity ?? 0;

  return (
    <div className={cn("double-bezel p-2", col)}>
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-1.5">
          <Bot className="w-3 h-3 text-white/40" />
          <span className="text-[10px] font-mono uppercase tracking-[1px] text-white/50">AI Reasoning</span>
        </div>
        <span className={cn("flex items-center gap-1 text-[8px] font-mono", isRunning ? "text-profit" : "text-white/25")}>
          <span className={cn("w-1.5 h-1.5 rounded-full", isRunning ? "bg-profit animate-pulse" : "bg-white/20")} />
          {isRunning ? "SELF-LOOP ACTIVE" : "SELF-LOOP OFF"}
        </span>
      </div>
      {err && <div className="text-[9px] text-loss/80 px-1 py-2">{err}</div>}
      <div className="grid grid-cols-2 gap-2 text-[10px] font-mono">
        <div className="bg-black/20 rounded p-2 border border-white/[0.04]">
          <div className="text-[8px] text-white/30 uppercase mb-0.5">Equity</div>
          <div className={cn("text-sm font-bold", eq >= 0 ? "text-white" : "text-loss")}>
            {eq != null ? `$${eq.toFixed(2)}` : "—"}
          </div>
        </div>
        <div className="bg-black/20 rounded p-2 border border-white/[0.04]">
          <div className="text-[8px] text-white/30 uppercase mb-0.5">Sharpe</div>
          <div className={cn("text-sm font-bold", sharpe >= 1 ? "text-profit" : sharpe < 0 ? "text-loss" : "text-amber-400")}>
            {sharpe != null ? sharpe.toFixed(2) : "—"}
          </div>
        </div>
        <div className="bg-black/20 rounded p-2 border border-white/[0.04]">
          <div className="text-[8px] text-white/30 uppercase mb-0.5">Drawdown</div>
          <div className={cn("text-sm font-bold", dd > 10 ? "text-loss" : "text-white")}>
            {dd != null ? `${dd.toFixed(1)}%` : "—"}
          </div>
        </div>
        <div className="bg-black/20 rounded p-2 border border-white/[0.04]">
          <div className="text-[8px] text-white/30 uppercase mb-0.5">Evolved</div>
          <div className="text-sm font-bold text-cyan-400">{st?.strategies_evolved ?? 0}</div>
        </div>
      </div>
      <div className="mt-2 pt-1.5 border-t border-white/[0.04] text-[8px] text-white/25 font-mono">
        eval: {st?.last_evaluation ? new Date(st.last_evaluation).toLocaleTimeString() : "—"}
        {" · "}evolve: {st?.last_evolution ? new Date(st.last_evolution).toLocaleTimeString() : "—"}
        {" · "}cycles: {st?.cycle_count ?? 0}
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   SIGNAL BAR — blueprint: BUY 55% | SELL 32% | HOLD 23%
   ════════════════════════════════════════════════════════════════════ */
export function SignalBar({ col = "col-span-12" }: { col?: string }) {
  const [sig, setSig] = useState<any>(null);
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/market/signals", { cache: "no-store" });
        const j = await r.json();
        setSig(Array.isArray(j) ? j : j?.signals ?? []);
      } catch { setSig([]); }
    };
    load(); const id = setInterval(load, 15000); return () => clearInterval(id);
  }, []);

  const list = Array.isArray(sig) ? sig : [];
  const buy = list.filter((s: any) => String(s.side ?? s.direction ?? "").toLowerCase().startsWith("buy")).length;
  const sell = list.filter((s: any) => String(s.side ?? s.direction ?? "").toLowerCase().startsWith("sell")).length;
  const hold = Math.max(0, list.length - buy - sell);
  const total = Math.max(list.length, 1);
  const pBuy = (buy / total) * 100, pSell = (sell / total) * 100, pHold = (hold / total) * 100;

  return (
    <div className={cn("double-bezel p-2", col)}>
      <div className="flex items-center gap-1.5 mb-1">
        <span className="text-[10px] font-mono uppercase tracking-[1px] text-white/50">Signal</span>
        <span className="text-[8px] text-white/25 font-mono">({list.length} raw)</span>
      </div>
      <div className="flex h-3 w-full overflow-hidden rounded-full bg-white/5">
        <div className="bg-profit/70 transition-all" style={{ width: `${pBuy}%` }} title={`BUY ${pBuy.toFixed(0)}%`} />
        <div className="bg-loss/70 transition-all" style={{ width: `${pSell}%` }} title={`SELL ${pSell.toFixed(0)}%`} />
        <div className="bg-white/15 transition-all" style={{ width: `${pHold}%` }} title={`HOLD ${pHold.toFixed(0)}%`} />
      </div>
      <div className="flex justify-between mt-1 text-[9px] font-mono">
        <span className="text-profit">▲ BUY {pBuy.toFixed(0)}%</span>
        <span className="text-loss">▼ SELL {pSell.toFixed(0)}%</span>
        <span className="text-white/40">— HOLD {pHold.toFixed(0)}%</span>
      </div>
    </div>
  );
}

/* ════════════════════════════════════════════════════════════════════
   STATUS BAR (24px) — blueprint: MT5: OK · LAT: 23ms · EQ
   ════════════════════════════════════════════════════════════════════ */
export function StatusBar({ col = "col-span-12" }: { col?: string }) {
  const [h, setH] = useState<any>(null);
  useEffect(() => {
    const load = async () => {
      try {
        const r = await fetch("/api/qna-status", { cache: "no-store" });
        setH(await r.json());
      } catch { setH(null); }
    };
    load(); const id = setInterval(load, 10000); return () => clearInterval(id);
  }, []);

  const backend = (h as any)?.execution_backend ?? (h as any)?.backend ?? "unknown";
  const ks = (h as any)?.kill_switch?.active ?? (h as any)?.kill_switch_active;
  const mt5Ok = String(backend).toLowerCase() === "mt5";

  return (
    <div className={cn("flex items-center gap-4 px-2 py-1 bg-black/30 rounded border border-white/[0.05] font-mono text-[9px]", col)}>
      <span className="flex items-center gap-1">
        <span className={cn("w-1.5 h-1.5 rounded-full", mt5Ok ? "bg-profit" : "bg-loss")} />
        MT5: {mt5Ok ? "OK" : String(backend)}
      </span>
      <span className="flex items-center gap-1">
        <Shield className={cn("w-2.5 h-2.5", ks ? "text-loss" : "text-profit")} />
        KS: {ks ? "HALT" : "ARMED"}
      </span>
      <span className="text-white/30 ml-auto hidden sm:flex">
        <Wifi className="w-2.5 h-2.5 mr-1" /> {new Date().toLocaleTimeString()}
      </span>
    </div>
  );
}
