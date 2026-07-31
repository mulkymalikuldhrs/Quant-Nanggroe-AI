// Econ Calendar — upcoming macro events with severity, affected symbols, countdown.

"use client";

import { useTerminalData, Card, cn } from "./terminal-shared";

interface EconEvent {
  time?: string;
  time_utc?: string;
  event?: string;
  name?: string;
  impact?: string;
  severity?: string;
  affects?: string[];
  symbols?: string[];
  currency?: string;
  forecast?: string;
  previous?: string;
  actual?: string;
  t_minus?: string;
  countdown?: string;
}

interface EconCalendarData {
  events?: EconEvent[];
}

function severityColor(sev: string | undefined) {
  if (!sev) return "text-white/30 bg-white/5";
  const s = sev.toLowerCase();
  if (s === "high" || s === "critical" || s === "3" || s === "!!!")
    return "text-loss bg-loss/10 border-loss/20";
  if (s === "medium" || s === "moderate" || s === "2" || s === "!!")
    return "text-amber-400 bg-amber-400/10 border-amber-400/20";
  return "text-white/50 bg-white/5 border-white/10";
}

function severityLabel(sev: string | undefined) {
  if (!sev) return "LOW";
  const s = sev.toLowerCase();
  if (s === "high" || s === "critical" || s === "3" || s === "!!!") return "HIGH";
  if (s === "medium" || s === "moderate" || s === "2" || s === "!!") return "MED";
  return "LOW";
}

export function EconCalendar() {
  const { data, loading, error } = useTerminalData<EconCalendarData>("econ-calendar", {});
  const d = data as any;
  const events: EconEvent[] = d?.events || [];

  return (
    <Card
      title="Econ Calendar"
      col="col-span-6 lg:col-span-4"
      loading={loading}
      error={error}
    >
      {events.length === 0 ? (
        <div className="text-[10px] text-white/20 text-center py-4">
          No upcoming events
        </div>
      ) : (
        <div className="space-y-1">
          {events.slice(0, 12).map((e, i) => {
            const name = e.event || e.name || "—";
            const time = e.time || e.time_utc || "—";
            const sev = e.severity || e.impact || "low";
            const syms = e.affects || e.symbols || [];
            const countdown = e.t_minus || e.countdown || "";
            const forecast = e.forecast;
            const previous = e.previous;
            const actual = e.actual;

            return (
              <div
                key={i}
                className="flex items-start gap-2 p-1.5 rounded border border-white/[0.04] bg-black/20 hover:bg-white/[0.02]"
              >
                {/* time + countdown */}
                <div className="shrink-0 w-[52px] text-[8px] leading-tight">
                  <div className="text-white/50 font-medium">{time}</div>
                  {countdown && (
                    <div className="text-amber-400/70 mt-0.5">{countdown}</div>
                  )}
                </div>

                {/* severity badge */}
                <span
                  className={cn(
                    "shrink-0 inline-block px-1 py-0.5 rounded text-[7px] font-bold border leading-none mt-0.5",
                    severityColor(sev)
                  )}
                >
                  {severityLabel(sev)}
                </span>

                {/* event detail */}
                <div className="flex-1 min-w-0">
                  <div className="text-[9px] text-white/70 truncate">{name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5 flex-wrap">
                    {syms.slice(0, 4).map((s: string) => (
                      <span
                        key={s}
                        className="text-[7px] px-1 py-0.5 rounded bg-white/[0.04] text-white/40"
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                  {(forecast || previous || actual) && (
                    <div className="flex gap-2 text-[7px] text-white/30 mt-0.5">
                      {actual && (
                        <span>
                          Act: <span className="text-white/60">{actual}</span>
                        </span>
                      )}
                      {forecast && (
                        <span>
                          Fcst: <span className="text-white/50">{forecast}</span>
                        </span>
                      )}
                      {previous && (
                        <span>
                          Prev: <span className="text-white/40">{previous}</span>
                        </span>
                      )}
                    </div>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      )}
    </Card>
  );
}
