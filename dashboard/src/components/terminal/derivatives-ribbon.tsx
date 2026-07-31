// Derivatives Ribbon — horizontal stat row for crypto derivatives.
// Funding/8h + annualized, OI + 24h change, L-S ratio, taker buy%, venue gap, net bias.

"use client";

import { useTerminalData, Card, fmtPct, fmtNum, clsPct, badgeColor } from "./terminal-shared";
import { cn } from "@/lib/utils";

interface DerivativesData {
  symbols?: {
    symbol: string;
    funding_rate?: number | null;
    funding_annualized?: number | null;
    funding_next_in?: string | null;
    open_interest?: number | null;
    oi_change_24h?: number | null;
    long_short_ratio?: number | null;
    taker_buy_pct?: number | null;
    venue_gap?: number | null;
    net_bias?: string | null;
  }[];
}

export function DerivativesRibbon() {
  const { data, loading, error } = useTerminalData<DerivativesData>("derivatives", {});
  const d = data as any;
  const syms: any[] = d?.symbols || [];

  return (
    <Card
      title="Derivatives Ribbon"
      col="col-span-12"
      loading={loading}
      error={error}
    >
      {syms.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">
          No derivatives data
        </div>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-[9px] min-w-[700px]">
            <thead>
              <tr className="text-[8px] text-white/30 uppercase">
                <th className="text-left font-normal py-1 px-1">Symbol</th>
                <th className="text-right font-normal py-1 px-1">Fund/8h</th>
                <th className="text-right font-normal py-1 px-1">Annual</th>
                <th className="text-right font-normal py-1 px-1">Next</th>
                <th className="text-right font-normal py-1 px-1">OI</th>
                <th className="text-right font-normal py-1 px-1">OI Δ24h</th>
                <th className="text-right font-normal py-1 px-1">L/S</th>
                <th className="text-right font-normal py-1 px-1">Taker Buy%</th>
                <th className="text-right font-normal py-1 px-1">Venue Gap</th>
                <th className="text-right font-normal py-1 px-1">Net Bias</th>
              </tr>
            </thead>
            <tbody>
              {syms.slice(0, 10).map((s: any, i: number) => {
                const fr = s.funding_rate;
                const ann = s.funding_annualized;
                const oi = s.open_interest;
                const oiChg = s.oi_change_24h;
                const ls = s.long_short_ratio;
                const taker = s.taker_buy_pct;
                const gap = s.venue_gap;
                const bias = s.net_bias || "—";

                return (
                  <tr
                    key={i}
                    className="border-b border-white/[0.02] hover:bg-white/[0.02]"
                  >
                    <td className="py-1 px-1 text-white/70 font-medium">
                      {s.symbol}
                    </td>
                    <td className={cn("py-1 px-1 text-right", clsPct(fr))}>
                      {fmtPct(fr != null ? fr * 100 : null)}
                    </td>
                    <td className={cn("py-1 px-1 text-right", clsPct(ann))}>
                      {ann != null ? `${ann >= 0 ? "+" : ""}${ann.toFixed(1)}%` : "—"}
                    </td>
                    <td className="py-1 px-1 text-right text-white/40">
                      {s.funding_next_in || "—"}
                    </td>
                    <td className="py-1 px-1 text-right text-white/60">
                      {fmtNum(oi, 0)}
                    </td>
                    <td className={cn("py-1 px-1 text-right", clsPct(oiChg))}>
                      {fmtPct(oiChg)}
                    </td>
                    <td className={cn("py-1 px-1 text-right font-medium",
                      ls != null && ls > 1 ? "text-profit" : ls != null && ls < 1 ? "text-loss" : "text-white/40"
                    )}>
                      {ls != null ? ls.toFixed(2) : "—"}
                    </td>
                    <td className={cn("py-1 px-1 text-right",
                      taker != null && taker > 55 ? "text-profit" : taker != null && taker < 45 ? "text-loss" : "text-white/50"
                    )}>
                      {taker != null ? `${taker.toFixed(1)}%` : "—"}
                    </td>
                    <td className={cn("py-1 px-1 text-right", clsPct(gap))}>
                      {gap != null ? `${gap >= 0 ? "+" : ""}${gap.toFixed(3)}%` : "—"}
                    </td>
                    <td className="py-1 px-1 text-right">
                      <span className={cn("inline-block px-1 py-0.5 rounded text-[8px] font-bold", badgeColor(bias))}>
                        {bias}
                      </span>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
}
