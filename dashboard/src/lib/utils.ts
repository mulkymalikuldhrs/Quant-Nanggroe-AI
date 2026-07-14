import { type ClassValue, clsx } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

// ── Number Formatting ─────────────────────────────────────────────

export function formatCurrency(
  value: number,
  decimals = 2,
  prefix = "$",
): string {
  if (!Number.isFinite(value)) return `${prefix}0.00`;

  const abs = Math.abs(value);
  const sign = value < 0 ? "-" : "";

  if (abs >= 1_000_000_000) {
    return `${sign}${prefix}${(abs / 1_000_000_000).toFixed(2)}B`;
  }
  if (abs >= 1_000_000) {
    return `${sign}${prefix}${(abs / 1_000_000).toFixed(2)}M`;
  }
  if (abs >= 1_000) {
    return `${sign}${prefix}${(abs / 1_000).toFixed(1)}K`;
  }

  return `${sign}${prefix}${abs.toFixed(decimals)}`;
}

export function formatPercent(
  value: number,
  decimals = 2,
  includeSign = true,
): string {
  if (!Number.isFinite(value)) return "0.00%";

  const prefix = includeSign && value > 0 ? "+" : "";
  return `${prefix}${value.toFixed(decimals)}%`;
}

export function formatChange(value: number): { text: string; className: string } {
  if (value === 0 || !Number.isFinite(value)) {
    return { text: "0.00", className: "text-neutral" };
  }
  const positive = value > 0;
  return {
    text: `${positive ? "+" : ""}${value.toFixed(2)}`,
    className: positive ? "text-profit" : "text-loss",
  };
}

export function formatPrice(
  price: number,
  symbol = "$",
): string {
  if (!Number.isFinite(price)) return `${symbol}—`;
  if (price >= 1000) return `${symbol}${price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (price >= 1) return `${symbol}${price.toFixed(2)}`;
  return `${symbol}${price.toFixed(4)}`;
}

export function formatVolume(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

export function formatCompact(value: number): string {
  if (!Number.isFinite(value)) return "—";
  if (value >= 1_000_000_000) return `${(value / 1_000_000_000).toFixed(2)}B`;
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(2)}M`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K`;
  return value.toFixed(0);
}

// ── Date Formatting ───────────────────────────────────────────────

export function formatTimestamp(ts: number | string): string {
  const date = typeof ts === "string" ? new Date(ts) : new Date(ts);
  if (isNaN(date.getTime())) return "—";

  return date.toLocaleTimeString("en-US", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  });
}

export function formatDate(ts: number | string): string {
  const date = typeof ts === "string" ? new Date(ts) : new Date(ts);
  if (isNaN(date.getTime())) return "—";

  return date.toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}

export function formatDateTime(ts: number | string): string {
  return `${formatDate(ts)} ${formatTimestamp(ts)}`;
}

export function timeAgo(ts: number | string): string {
  const date = typeof ts === "string" ? new Date(ts) : new Date(ts);
  const now = Date.now();
  const diff = now - date.getTime();

  const seconds = Math.floor(diff / 1000);
  const minutes = Math.floor(seconds / 60);
  const hours = Math.floor(minutes / 60);
  const days = Math.floor(hours / 24);

  if (seconds < 10) return "just now";
  if (seconds < 60) return `${seconds}s ago`;
  if (minutes < 60) return `${minutes}m ago`;
  if (hours < 24) return `${hours}h ago`;
  if (days < 7) return `${days}d ago`;
  return formatDate(ts);
}

// ── Color Helpers ─────────────────────────────────────────────────

export function pnlColor(value: number): string {
  if (value > 0) return "text-profit";
  if (value < 0) return "text-loss";
  return "text-neutral";
}

export function pnlBg(value: number): string {
  if (value > 0) return "bg-profit";
  if (value < 0) return "bg-loss";
  return "bg-white/5";
}

export function pnlBadge(value: number): "success" | "danger" | "default" {
  if (value > 0) return "success";
  if (value < 0) return "danger";
  return "default";
}

// ── Status Helpers ─────────────────────────────────────────────────

export function getStatusColor(status: string): string {
  const colors: Record<string, string> = {
    active: "text-emerald-400",
    online: "text-emerald-400",
    running: "text-emerald-400",
    connected: "text-emerald-400",
    success: "text-emerald-400",
    warning: "text-amber-400",
    idle: "text-amber-400",
    degraded: "text-amber-400",
    error: "text-red-400",
    danger: "text-red-400",
    offline: "text-red-400",
    disconnected: "text-white/30",
    paused: "text-white/30",
    info: "text-cyan-400",
    default: "text-white/40",
  };
  return colors[status] || colors.default;
}

// ── Risk Helpers ──────────────────────────────────────────────────

export function riskColor(score: number): string {
  if (score < 0.3) return "text-profit";
  if (score < 0.6) return "text-warning";
  return "text-loss";
}

export function riskBadge(score: number): "success" | "warning" | "danger" {
  if (score < 0.3) return "success";
  if (score < 0.6) return "warning";
  return "danger";
}

// ── Strategy / Performance ────────────────────────────────────────

export function sharpeRating(sharpe: number): string {
  if (sharpe > 2) return "Excellent";
  if (sharpe > 1.5) return "Good";
  if (sharpe > 1) return "Decent";
  if (sharpe > 0.5) return "Mediocre";
  return "Poor";
}

export function winRateColor(rate: number): string {
  if (rate >= 0.6) return "text-profit";
  if (rate >= 0.4) return "text-warning";
  return "text-loss";
}
