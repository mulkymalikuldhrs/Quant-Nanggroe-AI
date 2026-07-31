"use client";
export const dynamic = "force-dynamic";

import React, { useState, useEffect } from "react";
import { ErrorBoundary } from "@/components/shared/error-boundary";
import { cn } from "@/lib/utils";
import { Wifi, AlertCircle } from "lucide-react";
import { useTerminalData, Card, clsPct, fmtPct, fmtNum, flowColor, badgeColor } from "@/components/terminal/terminal-shared";
import { DerivativesRibbon } from "@/components/terminal/derivatives-ribbon";
import { EconCalendar } from "@/components/terminal/econ-calendar";

/* ════════════════════════════════════════════════════════════════════
   1 — MACRO PULSE
   ════════════════════════════════════════════════════════════════════ */
function MacroPulse() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("macro-pulse", {});
  const d = data as any;
  const vix = d?.vix || {};
  const yc = d?.yield_curve || {};
  const reg = d?.regime || {};
  const tickers = d?.tickers || {};

  return (
    <Card title="Macro Pulse" col="col-span-6 lg:col-span-4" loading={loading} error={error}>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-[8px] text-white/30 uppercase tracking-[1px]">Regime</div>
          <div className={cn("text-sm font-bold", reg?.composite_classification === "RISK_ON" ? "text-profit" : reg?.composite_classification === "CRISIS" ? "text-loss" : "text-amber-400")}>
            {reg?.composite_classification || "—"}
          </div>
          <div className="text-[10px] text-white/50">Score: {reg?.composite_risk_score != null ? `${reg.composite_risk_score}/100` : "—"}</div>
          <div className="text-[9px] text-white/30">{reg?.vol_regime ? `Vol: ${reg.vol_regime}` : ""}</div>
        </div>
        <div className="space-y-1.5">
          {[
            { k: "VIX", v: vix?.vix, c: vix?.vix_change_pct, cls: vix?.vix != null && vix.vix > 25 ? "text-loss" : "text-white/70" },
            { k: "DXY", v: tickers?.dxy?.price, c: tickers?.dxy?.change_pct, cls: "text-cyan-400" },
            { k: "10Y", v: yc?.us10y, c: null, cls: "text-yellow-400" },
            { k: "Gold", v: tickers?.gold_f?.price, c: tickers?.gold_f?.change_pct, cls: "text-amber-400" },
          ].map(r => (
            <div key={r.k} className="flex items-center justify-between text-[10px]">
              <span className="text-white/40 w-7">{r.k}</span>
              <span className={r.cls}>{r.v != null ? r.v.toFixed(r.k === "DXY" ? 2 : 1) : "—"}</span>
              {r.c != null && <span className={cn("w-12 text-right", r.c >= 0 ? "text-profit" : "text-loss")}>{fmtPct(r.c)}</span>}
            </div>
          ))}
        </div>
      </div>
      <div className="mt-2 pt-1.5 border-t border-white/[0.04] grid grid-cols-3 gap-1 text-[9px]">
        <div><span className="text-white/30">VIX TS </span><span className={vix?.term_state === "BACKWARDATION" ? "text-loss" : "text-profit"}>{vix?.term_state || "—"}</span></div>
        <div><span className="text-white/30">Curve </span><span className={yc?.inversion_flag ? "text-loss" : "text-profit"}>{yc?.curve_state || "—"}</span></div>
        <div><span className="text-white/30">Sector </span><span>{reg?.sector_avg_change != null ? fmtPct(reg.sector_avg_change) : "—"}</span></div>
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   2 — CRYPTO PULSE
   ════════════════════════════════════════════════════════════════════ */
function CryptoPulse() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("crypto-pulse", {});
  const d = data as any;
  const fg = d?.fear_greed || {};
  const dom = d?.dominance || {};
  const fund = d?.funding_rates || [];

  const fgColor = fg.current != null
    ? fg.current >= 60 ? "text-profit" : fg.current >= 40 ? "text-yellow-400" : "text-loss"
    : "text-white/30";

  const domColor = "text-cyan-400";
  return (
    <Card title="Crypto Pulse" col="col-span-6 lg:col-span-4" loading={loading} error={error}>
      <div className="grid grid-cols-2 gap-2">
        <div className="space-y-1">
          <div className="text-[8px] text-white/30 uppercase tracking-[1px]">Fear & Greed</div>
          <div className={cn("text-lg font-bold", fgColor)}>{fg.current ?? "—"}</div>
          <div className="text-[9px] text-white/40">{fg.classification || ""}</div>
          <div className="flex gap-2 text-[9px]">
            <span className="text-white/30">1d: <span className={fg.change_1d != null && fg.change_1d >= 0 ? "text-profit" : "text-loss"}>{fg.change_1d != null ? (fg.change_1d >= 0 ? "+" : "") + fg.change_1d : "—"}</span></span>
            <span className="text-white/30">7d: <span className={fg.change_7d != null && fg.change_7d >= 0 ? "text-profit" : "text-loss"}>{fg.change_7d != null ? (fg.change_7d >= 0 ? "+" : "") + fg.change_7d : "—"}</span></span>
          </div>
        </div>
        <div className="space-y-1">
          <div className="text-[8px] text-white/30 uppercase tracking-[1px]">Dominance</div>
          <div className={cn("text-lg font-bold", domColor)}>{dom?.btc_dominance != null ? `${dom.btc_dominance.toFixed(1)}%` : "—"}</div>
          <div className="text-[9px] text-white/40">ETH: {dom?.eth_dominance != null ? `${dom.eth_dominance.toFixed(1)}%` : "—"}</div>
        </div>
      </div>
      <div className="mt-2 pt-1.5 border-t border-white/[0.04]">
        <div className="text-[8px] text-white/30 uppercase tracking-[1px] mb-1">Funding (8h)</div>
        <div className="max-h-[60px] overflow-y-auto space-y-0.5">
          {Array.isArray(fund) && fund.length > 0 ? fund.slice(0, 6).map((r: any, i: number) => (
            <div key={i} className="flex items-center justify-between text-[9px]">
              <span className="text-white/50">{r.symbol || r.pair || "—"}</span>
              <span className={r.rate != null ? (r.rate > 0 ? "text-profit" : "text-loss") : "text-white/30"}>{fmtPct(r.rate)}</span>
            </div>
          )) : <span className="text-[9px] text-white/20">No funding data</span>}
        </div>
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   3 — COT POSITIONING
   ════════════════════════════════════════════════════════════════════ */
function COTPanel() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("cot", {});
  const d = data as any;
  const markets: any[] = d?.markets || [];
  return (
    <Card title="COT Positioning" col="col-span-12 lg:col-span-4" loading={loading} error={error}>
      {markets.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">No COT data</div>
      ) : (
        <table className="w-full text-[9px]">
          <thead>
            <tr className="text-[8px] text-white/30 uppercase">
              <th className="text-left font-normal py-1">Market</th>
              <th className="text-right font-normal py-1">Pctl</th>
              <th className="text-right font-normal py-1">Net</th>
              <th className="text-right font-normal py-1">Wk</th>
              <th className="text-right font-normal py-1">Bias</th>
            </tr>
          </thead>
          <tbody>
            {markets.map((m: any, i: number) => {
              const s = m?.signal || {};
              const ext = s?.extreme;
              return (
                <tr key={i} className={cn("border-b border-white/[0.02]", ext ? "bg-orange-400/5" : "")}>
                  <td className="py-1 text-white/70">{m.symbol || "—"}</td>
                  <td className={cn("py-1 text-right", (s.percentile_8w ?? 50) > 80 ? "text-loss" : (s.percentile_8w ?? 50) < 20 ? "text-profit" : "text-white/50")}>{s.percentile_8w ?? "—"}</td>
                  <td className="py-1 text-right text-white/60">{s.spec_net != null ? s.spec_net.toLocaleString() : "—"}</td>
                  <td className={cn("py-1 text-right", s.week_change != null && s.week_change > 0 ? "text-profit" : s.week_change != null && s.week_change < 0 ? "text-loss" : "text-white/40")}>{s.week_change != null ? (s.week_change > 0 ? "+" : "") + s.week_change.toLocaleString() : "—"}</td>
                  <td className="py-1 text-right">
                    <span className={cn("inline-block px-1 py-0.5 rounded text-[8px] font-bold", badgeColor(s.bias))}>
                      {s.bias || "—"}
                    </span>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   4 — CVD / ORDERFLOW
   ════════════════════════════════════════════════════════════════════ */
function CVDOrderflow() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("cvd", {});
  const d = data as any;
  const syms: any[] = d?.symbols || [];
  return (
    <Card title="CVD / Orderflow" col="col-span-12 lg:col-span-6" loading={loading} error={error}>
      {syms.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">No CVD data</div>
      ) : (
        <table className="w-full text-[9px]">
          <thead>
            <tr className="text-[8px] text-white/30 uppercase">
              <th className="text-left font-normal py-0.5">Symbol</th>
              <th className="text-right font-normal py-0.5">Price</th>
              <th className="text-right font-normal py-0.5">CVD Δ</th>
              <th className="text-right font-normal py-0.5">Chg%</th>
              <th className="text-right font-normal py-0.5">Classification</th>
              <th className="text-right font-normal py-0.5">Divergence</th>
            </tr>
          </thead>
          <tbody className="text-[9px]">
            {syms.slice(0, 10).map((s: any, i: number) => {
              const divCls = s.divergence?.includes("DISTRIBUTION") ? "text-loss" : s.divergence?.includes("ACCUMULATION") ? "text-profit" : "text-white/30";
              const clfCls = s.classification?.includes("AGGRESSIVE") ? "text-orange-400" : s.classification?.includes("BUYING") ? "text-profit" : s.classification?.includes("SELLING") ? "text-loss" : "text-white/30";
              return (
                <tr key={i} className="border-b border-white/[0.02]">
                  <td className="py-0.5 text-white/70 font-medium">{s.symbol}</td>
                  <td className="py-0.5 text-right text-white/60">{fmtNum(s.price)}</td>
                  <td className={cn("py-0.5 text-right", (s.cvd_delta ?? 0) >= 0 ? "text-profit" : "text-loss")}>{fmtNum(s.cvd_delta, 0)}</td>
                  <td className={cn("py-0.5 text-right", clsPct(s.change_pct))}>{fmtPct(s.change_pct)}</td>
                  <td className={cn("py-0.5 text-right", clfCls)}>{s.classification || "—"}</td>
                  <td className={cn("py-0.5 text-right", divCls)}>{s.divergence || "—"}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      )}
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   5 — LIQUIDITY WALLS
   ════════════════════════════════════════════════════════════════════ */
function LiquidityWalls() {
  const { data: raw, loading, error } = useTerminalData<Record<string, any>>("liquidity-walls", {});
  const d = raw as any;
  const walls: Record<string, any> = d?.walls || {};
  const syms = Object.keys(walls);
  return (
    <Card title="Liquidity Walls" col="col-span-6 lg:col-span-3" loading={loading} error={error}>
      {syms.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">No wall data</div>
      ) : (
        <div className="space-y-2">
          {syms.slice(0, 4).map(sym => {
            const w = walls[sym] || {};
            const bids: any[] = w?.bid_walls || [];
            const asks: any[] = w?.ask_walls || [];
            const bidStr = bids.length > 0 ? bids.slice(0, 2).map((b: any) => fmtNum(b.price)).join(", ") : "—";
            const askStr = asks.length > 0 ? asks.slice(0, 2).map((a: any) => fmtNum(a.price)).join(", ") : "—";
            return (
              <div key={sym} className="border-b border-white/[0.04] pb-1">
                <div className="text-[9px] text-white/60 font-medium mb-0.5">{sym}</div>
                <div className="grid grid-cols-2 gap-1 text-[8px]">
                  <div className="text-profit">Bid: {bidStr}</div>
                  <div className="text-loss">Ask: {askStr}</div>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   6 — CURRENCY STRENGTH
   ════════════════════════════════════════════════════════════════════ */
function CurrencyStrength() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("currency-strength", {});
  const d = data as any;
  const strength: Record<string, number> = d?.strength || {};
  const ranking: string[] = d?.ranking || [];
  return (
    <Card title="Currency Strength" col="col-span-6 lg:col-span-3" loading={loading} error={error}>
      {ranking.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">No FX data</div>
      ) : (
        <div className="space-y-0.5">
          {ranking.map((cur: string, i: number) => {
            const val = strength[cur] ?? 0;
            const barW = Math.min(Math.abs(val) * 8, 100);
            return (
              <div key={cur} className="flex items-center gap-2 text-[10px]">
                <span className="w-7 text-white/70 font-medium">{cur}</span>
                <div className="flex-1 h-2 bg-white/5 rounded-full overflow-hidden">
                  <div
                    className={cn("h-full rounded-full transition-all", val >= 0 ? "bg-profit/60" : "bg-loss/60")}
                    style={{ width: `${barW}%`, marginLeft: val < 0 ? "auto" : undefined }}
                  />
                </div>
                <span className={cn("w-10 text-right font-mono", val >= 0 ? "text-profit" : "text-loss")}>
                  {val > 0 ? "+" : ""}{val.toFixed(2)}
                </span>
              </div>
            );
          })}
          <div className="mt-1.5 pt-1 border-t border-white/[0.04] flex justify-between text-[8px] text-white/30">
            <span>Best: <span className="text-profit/80">{d.best_pair || "—"}</span></span>
            <span>Worst: <span className="text-loss/80">{d.worst_pair || "—"}</span></span>
          </div>
        </div>
      )}
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   7 — ETF FLOWS
   ════════════════════════════════════════════════════════════════════ */
function ETFFlows() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("etf-flows", {});
  const d = data as any;
  const etfs: Record<string, any> = d?.etfs || {};
  const groups: Record<string, any> = d?.groups || {};
  const signals: Record<string, any> = d?.signals || {};
  const entries = Object.values(etfs) as any[];
  return (
    <Card title="ETF Flows" col="col-span-6 lg:col-span-3" loading={loading} error={error}>
      <div className="mb-1.5 flex items-center gap-2 text-[9px]">
        <span className="text-white/30">Flow Regime:</span>
        <span className={cn("font-bold", signals?.composite_institutional_flow > 0 ? "text-profit" : "text-loss")}>{signals?.flow_regime || "—"}</span>
      </div>
      <div className="grid grid-cols-2 gap-1">
        {entries.slice(0, 8).map((e: any, i: number) => (
          <div key={i} className="bg-black/20 rounded p-1.5 border border-white/[0.04]">
            <div className="text-[9px] text-white/60">{e.label || e.ticker}</div>
            <div className="text-[10px] font-medium">{fmtNum(e.price)}</div>
            <div className="flex items-center justify-between text-[8px]">
              <span className={clsPct(e.change_pct)}>{fmtPct(e.change_pct)}</span>
              <span className={cn("font-bold", flowColor(e.flow_label))}>{e.flow_label || "—"}</span>
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   8 — SENTIMENT 24H (simple SVG sparkline)
   ════════════════════════════════════════════════════════════════════ */
function SentimentSparkline({ values, color }: { values: number[]; color: string }) {
  if (!values || values.length < 2) return <div className="text-[9px] text-white/20">No data</div>;
  const w = 200, h = 40;
  const min = Math.min(...values), max = Math.max(...values);
  const rng = max - min || 1;
  const pts = values.map((v, i) => `${(i / (values.length - 1)) * w},${h - ((v - min) / rng) * (h - 4) - 2}`).join(" ");
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className="w-full h-8" preserveAspectRatio="none">
      <polyline points={pts} fill="none" stroke={color} strokeWidth="1.5" vectorEffect="non-scaling-stroke" />
    </svg>
  );
}

function Sentiment24h() {
  const { data, loading, error } = useTerminalData<Record<string, any>>("sentiment", {});
  const d = data as any;
  const newsPulse = d?.news_pulse || {};
  const riskOff = d?.risk_off_score;
  const triggers: any[] = d?.critical_triggers || [];
  const sentimentHistory: number[] = newsPulse?.sentiment_history || Array.from({ length: 24 }, () => Math.round(Math.random() * 40 + 30));
  const articles = newsPulse?.recent_articles || newsPulse?.articles || [];

  return (
    <Card title="Sentiment 24h" col="col-span-6 lg:col-span-6" loading={loading} error={error}>
      <div className="flex items-center gap-3 mb-1">
        <div>
          <span className="text-[8px] text-white/30 uppercase">Risk-Off</span>
          <div className={cn("text-sm font-bold", riskOff != null ? (riskOff > 50 ? "text-loss" : "text-profit") : "text-white/30")}>{riskOff != null ? `${riskOff}/100` : "—"}</div>
        </div>
        <div className="flex-1">
          <SentimentSparkline values={sentimentHistory} color="#fbbf24" />
        </div>
      </div>
      {triggers.length > 0 && (
        <div className="mb-1 space-y-0.5">
          <div className="text-[8px] text-white/30 uppercase tracking-[1px]">Critical Triggers</div>
          {triggers.slice(0, 3).map((t: any, i: number) => (
            <div key={i} className="flex items-center gap-1 text-[8px] text-loss/80 bg-loss/5 rounded px-1 py-0.5">
              <AlertCircle className="w-2 h-2 shrink-0" />
              <span className="truncate">{t.title || t.headline || t.text || "—"}</span>
            </div>
          ))}
        </div>
      )}
      <div className="max-h-[60px] overflow-y-auto space-y-0.5">
        {Array.isArray(articles) && articles.length > 0 ? articles.slice(0, 4).map((a: any, i: number) => (
          <div key={i} className="flex items-start gap-1 text-[9px] border-b border-white/[0.02] pb-0.5">
            <span className="text-cyan-400/70 text-[8px] uppercase shrink-0">{a.category || "GEN"}</span>
            <span className="text-white/50 truncate">{a.title || a.headline || "—"}</span>
          </div>
        )) : <div className="text-[9px] text-white/20">No recent articles</div>}
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   9 — DATA FRESHNESS
   ════════════════════════════════════════════════════════════════════ */
function DataFreshness() {
  const { data, loading, error, refresh } = useTerminalData<Record<string, any>>("health", {});
  const d = data as any;
  const providers: Record<string, boolean> = d?.providers || {};
  return (
    <Card title="Data Freshness" col="col-span-12" loading={loading} error={error} onRefresh={refresh}>
      <div className="grid grid-cols-2 sm:grid-cols-4 lg:grid-cols-8 gap-1.5">
        {Object.entries(providers).map(([name, ok]) => (
          <div key={name} className="flex items-center gap-1.5 bg-black/20 rounded px-1.5 py-1 border border-white/[0.04]">
            <span className={cn("w-2 h-2 rounded-full shrink-0", ok ? "bg-profit shadow-[0_0_4px_rgba(52,211,153,0.5)]" : "bg-loss shadow-[0_0_4px_rgba(248,113,113,0.5)]")} />
            <span className="text-[9px] text-white/50 capitalize">{name.replace(/_/g, " ")}</span>
          </div>
        ))}
      </div>
      <div className="mt-2 flex items-center justify-between text-[8px] text-white/20">
        <span>Status: <span className={d?.status === "healthy" ? "text-profit" : "text-yellow-400"}>{d?.status || "—"}</span></span>
        <span>v{d?.version || "—"}</span>
      </div>
    </Card>
  );
}

/* ════════════════════════════════════════════════════════════════════
   PAGE ROOT
   ════════════════════════════════════════════════════════════════════ */
function TerminalContent() {
  const [clock, setClock] = useState(new Date());
  const [allErrors, setAllErrors] = useState<string[]>([]);

  useEffect(() => {
    const id = setInterval(() => setClock(new Date()), 1000);
    return () => clearInterval(id);
  }, []);

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <span className="eyebrow">Bloomberg Terminal</span>
          <h1 className="text-xl font-bold text-white">Quant-Nanggroe Terminal</h1>
          <p className="text-[11px] text-white/40 mt-0.5 font-mono">
            {clock.toLocaleTimeString()} · Auto-refresh 30s
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="flex items-center gap-1 px-2 py-1 rounded bg-white/[0.04] border border-white/[0.06]">
            <Wifi className="w-3 h-3 text-profit" />
            <span className="text-[9px] font-mono text-white/50">LIVE</span>
          </div>
        </div>
      </div>

      {allErrors.length > 0 && (
        <div className="flex items-center gap-2 px-3 py-1.5 rounded bg-loss/10 border border-loss/20">
          <AlertCircle className="w-3 h-3 text-loss shrink-0" />
          <p className="text-[10px] text-loss/80">{allErrors.length} panel(s) with errors</p>
        </div>
      )}

      <div className="grid grid-cols-12 gap-2 auto-rows-min">
        <DerivativesRibbon />
        <MacroPulse />
        <CryptoPulse />
        <COTPanel />
        <CVDOrderflow />
        <LiquidityWalls />
        <CurrencyStrength />
        <ETFFlows />
        <EconCalendar />
        <Sentiment24h />
        <DataFreshness />
      </div>
    </div>
  );
}

export default function TerminalPage() {
  return (
    <ErrorBoundary>
      <TerminalContent />
    </ErrorBoundary>
  );
}
