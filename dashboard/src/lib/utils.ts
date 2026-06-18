import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  }).format(value);
}

export function formatPercent(value: number): string {
  return `${value >= 0 ? "+" : ""}${value.toFixed(2)}%`;
}

export function formatNumber(value: number, decimals = 2): string {
  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatLargeNumber(value: number): string {
  if (value >= 1e9) return `${(value / 1e9).toFixed(2)}B`;
  if (value >= 1e6) return `${(value / 1e6).toFixed(2)}M`;
  if (value >= 1e3) return `${(value / 1e3).toFixed(2)}K`;
  return value.toFixed(2);
}

export function getStatusColor(status: string): string {
  switch (status.toLowerCase()) {
    case "active":
    case "online":
    case "profit":
    case "long":
    case "filled":
      return "text-emerald-400";
    case "warning":
    case "pending":
    case "neutral":
      return "text-amber-400";
    case "error":
    case "offline":
    case "loss":
    case "short":
    case "rejected":
    case "cancelled":
      return "text-red-400";
    default:
      return "text-blue-400";
  }
}

export function getStatusBg(status: string): string {
  switch (status.toLowerCase()) {
    case "active":
    case "online":
    case "profit":
    case "long":
    case "filled":
      return "bg-emerald-500/10 border-emerald-500/20";
    case "warning":
    case "pending":
    case "neutral":
      return "bg-amber-500/10 border-amber-500/20";
    case "error":
    case "offline":
    case "loss":
    case "short":
    case "rejected":
    case "cancelled":
      return "bg-red-500/10 border-red-500/20";
    default:
      return "bg-blue-500/10 border-blue-500/20";
  }
}
