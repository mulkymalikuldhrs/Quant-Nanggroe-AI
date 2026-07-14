"use client";

import { cn, formatCurrency, formatPercent, formatCompact } from "@/lib/utils";
import { Card } from "@/components/ui/card";
import { ArrowUp, ArrowDown, Minus } from "lucide-react";

interface StatusCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
  variant?: "default" | "success" | "danger" | "warning" | "info";
  trend?: "up" | "down" | "neutral";
  loading?: boolean;
  subtitle?: string;
  format?: "currency" | "percent" | "number" | "text";
  compact?: boolean;
}

export function StatusCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  className,
  variant = "default",
  trend,
  loading = false,
  subtitle,
  format = "currency",
  compact = false,
}: StatusCardProps) {
  const variantGlow: Record<string, string> = {
    default: "",
    success: "shadow-[0_0_20px_rgba(16,185,129,0.06)]",
    danger: "shadow-[0_0_20px_rgba(239,68,68,0.06)]",
    warning: "shadow-[0_0_20px_rgba(245,158,11,0.06)]",
    info: "shadow-[0_0_20px_rgba(6,182,212,0.06)]",
  };

  const variantBorder: Record<string, string> = {
    default: "border-white/[0.06]",
    success: "border-emerald-500/15",
    danger: "border-red-500/15",
    warning: "border-amber-500/15",
    info: "border-cyan-500/15",
  };

  const formattedValue = () => {
    if (loading) return "—";
    if (typeof value === "number") {
      if (format === "currency") return formatCurrency(value);
      if (format === "percent") return formatPercent(value, 2, false);
      if (format === "number") return formatCompact(value);
    }
    return value;
  };

  const changeIcon = change !== undefined ? (
    change > 0 ? <ArrowUp className="w-3 h-3" /> :
    change < 0 ? <ArrowDown className="w-3 h-3" /> :
    <Minus className="w-3 h-3" />
  ) : null;

  const changeColor = change !== undefined ? (
    change > 0 ? "text-profit" : change < 0 ? "text-loss" : "text-neutral"
  ) : "";

  return (
    <Card
      className={cn(
        "relative overflow-hidden group transition-all duration-300",
        variantGlow[variant],
        variantBorder[variant],
        compact ? "p-3" : "p-4",
        className,
      )}
    >
      {/* Hover glow effect */}
      <div className={cn(
        "absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none",
        variant === "success" ? "bg-gradient-to-br from-emerald-500/[0.02] to-transparent" :
        variant === "danger" ? "bg-gradient-to-br from-red-500/[0.02] to-transparent" :
        "bg-gradient-to-br from-white/[0.02] to-transparent",
      )} />

      <div className="relative z-10">
        {/* Loading shimmer */}
        {loading && (
          <div className="absolute inset-0 animate-shimmer rounded-[inherit] pointer-events-none" />
        )}

        {/* Header */}
        <div className="flex items-start justify-between mb-2">
          <p className={cn(
            "text-[11px] font-medium uppercase tracking-[0.1em]",
            loading ? "text-white/10" : "text-white/30",
          )}>
            {title}
          </p>
          {icon && (
            <div className={cn(
              "p-1.5 rounded-lg transition-colors duration-200",
              loading ? "bg-white/[0.02] text-white/10" : "bg-white/[0.04] text-white/30 group-hover:text-white/50",
            )}>
              {icon}
            </div>
          )}
        </div>

        {/* Value */}
        <p className={cn(
          "font-mono font-bold tracking-tight transition-colors",
          loading ? "text-white/10" : "text-white",
          compact ? "text-lg" : "text-2xl",
        )}>
          {loading ? "—" : formattedValue()}
        </p>

        {/* Change / Subtitle */}
        {subtitle && !loading && (
          <p className="text-[10px] text-white/20 mt-0.5">{subtitle}</p>
        )}

        {change !== undefined && !loading && (
          <div className="flex items-center gap-1 mt-1">
            {changeIcon}
            <span className={cn("text-xs font-mono font-medium", changeColor)}>
              {formatPercent(Math.abs(change))}
            </span>
            {changeLabel && (
              <span className="text-[10px] text-white/20 ml-1">{changeLabel}</span>
            )}
          </div>
        )}

        {trend !== undefined && !loading && change === undefined && (
          <div className="flex items-center gap-1 mt-1">
            {trend === "up" ? (
              <ArrowUp className="w-3 h-3 text-emerald-400" />
            ) : trend === "down" ? (
              <ArrowDown className="w-3 h-3 text-red-400" />
            ) : (
              <Minus className="w-3 h-3 text-white/30" />
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
