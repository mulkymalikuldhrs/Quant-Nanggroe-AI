import { NextResponse } from "next/server";
import { readFileSync, existsSync } from "node:fs";

export const dynamic = "force-dynamic";

const WORKTREE = process.cwd();

function read(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

interface CandleEvent {
  symbol: string;
  timeframe: string;
  timestamp: string;
  signal: string;
  confidence: number;
  traded: boolean;
  notified: boolean;
  error: string | null;
  duration_ms: number;
}

function getCandleEvents(): CandleEvent[] {
  // Try reading from the candle scheduler state file
  const stateFile = `${WORKTREE}/data/candle_scheduler_state.json`;
  const raw = read(stateFile);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : parsed.events || [];
    } catch {
      return [];
    }
  }
  return [];
}

function getSchedulerStatus() {
  const stateFile = `${WORKTREE}/data/candle_scheduler_state.json`;
  const raw = read(stateFile);
  if (raw) {
    try {
      const parsed = JSON.parse(raw);
      return {
        running: parsed.running ?? false,
        symbols: parsed.symbols ?? [],
        timeframes: parsed.timeframes ?? ["M15", "H1", "H4", "D1"],
        total_events: parsed.total_events ?? 0,
        last_event: parsed.last_event ?? null,
        uptime_seconds: parsed.uptime_seconds ?? 0,
      };
    } catch {
      return { running: false, symbols: [], timeframes: [], total_events: 0, last_event: null, uptime_seconds: 0 };
    }
  }
  return { running: false, symbols: [], timeframes: [], total_events: 0, last_event: null, uptime_seconds: 0 };
}

function getTfPerformance() {
  const events = getCandleEvents();
  const perf: Record<string, { total: number; traded: number; avg_confidence: number; signals: Record<string, number> }> = {};

  for (const ev of events) {
    const tf = ev.timeframe;
    if (!perf[tf]) {
      perf[tf] = { total: 0, traded: 0, avg_confidence: 0, signals: { buy: 0, sell: 0, hold: 0 } };
    }
    perf[tf].total++;
    if (ev.traded) perf[tf].traded++;
    perf[tf].avg_confidence += ev.confidence;
    if (ev.signal in perf[tf].signals) {
      const sig = ev.signal as "buy" | "sell" | "hold";
      perf[tf].signals[sig]++;
    }
  }

  // Average confidence
  for (const tf of Object.keys(perf)) {
    if (perf[tf].total > 0) {
      perf[tf].avg_confidence = perf[tf].avg_confidence / perf[tf].total;
    }
  }

  return perf;
}

export async function GET() {
  return NextResponse.json({
    status: getSchedulerStatus(),
    events: getCandleEvents(),
    tf_performance: getTfPerformance(),
  });
}
