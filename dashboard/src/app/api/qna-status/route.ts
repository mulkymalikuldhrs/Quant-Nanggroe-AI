import { NextResponse } from "next/server";
import { readFileSync } from "node:fs";

// ponytail: minimal status endpoint. Reads local state files; no deps beyond next.
const WORKTREE = process.cwd();
const KILL_STATE_FILE =
  process.env.QNA_KILL_SWITCH_STATE_FILE || `${WORKTREE}/data/kill_switch_state.json`;
const GRAPH_HTML =
  process.env.QNA_GRAPH_HTML_PATH || `${WORKTREE}/docs/graph.html`;
const LEDGER_MD =
  process.env.QNA_LEDGER_MD_PATH || `${WORKTREE}/docs/DECISION_LEDGER.md`;

function read(path: string): string | null {
  try {
    return readFileSync(path, "utf8");
  } catch {
    return null;
  }
}

function killSwitch() {
  const raw = read(KILL_STATE_FILE);
  if (!raw) return { active: false, file_path: KILL_STATE_FILE };
  try {
    const s = JSON.parse(raw);
    return { active: s.status === "active", file_path: KILL_STATE_FILE };
  } catch {
    return { active: false, file_path: KILL_STATE_FILE };
  }
}

function guardConfig() {
  const env = process.env;
  // ponytail: unset/empty env -> sane defaults; explicit non-empty value wins
  const list = (key: string, def: string[]) => {
    const v = env[key];
    if (!v || !v.trim()) return def;
    return v.split(",").map((x) => x.trim()).filter(Boolean);
  };
  return {
    allowed_symbols: list("QNA_GUARD_ALLOWED_SYMBOLS", ["BTCUSDT", "ETHUSDT"]),
    blocked_symbols: list("QNA_GUARD_BLOCKED_SYMBOLS", []),
    cooldown: Number(env.QNA_GUARD_COOLDOWN ?? 60),
    max_position_pct: Number(env.QNA_GUARD_MAX_POSITION_PCT ?? 2.0),
    max_notional: Number(env.QNA_GUARD_MAX_NOTIONAL ?? 0),
  };
}

function graphQueue() {
  const html = read(GRAPH_HTML);
  if (!html) return [];
  const m = html.match(/queue:\s*(\[[\s\S]*?\])/);
  if (!m) return [];
  // ponytail: graph.html uses JS object literals (unquoted keys), not strict JSON.
  // DATA block is orchestrator-authored local file (no external input) -> new Function safe.
  try {
    return new Function(`return ${m[1]}`)() as unknown[];
  } catch {
    return [];
  }
}

function lastLedger() {
  const md = read(LEDGER_MD);
  if (!md) return "";
  const lines = md.split(/\r?\n/);
  let last = -1;
  lines.forEach((l, i) => {
    if (l.startsWith("## ")) last = i;
  });
  if (last < 0) return "";
  return lines.slice(last, last + 4).join("\n").trim();
}

export const dynamic = "force-dynamic";

export async function GET() {
  return NextResponse.json({
    kill_switch: killSwitch(),
    guard_config: guardConfig(),
    graph_queue: graphQueue(),
    last_ledger: lastLedger(),
  });
}
