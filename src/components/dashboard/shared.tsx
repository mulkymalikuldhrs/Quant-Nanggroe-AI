"use client";

import React from "react";
import { cn } from "@/lib/utils";

type StatusType =
  | "active"
  | "idle"
  | "error"
  | "offline"
  | "connected"
  | "disconnected"
  | "available"
  | "busy"
  | "disabled"
  | "scaling"
  | "OK"
  | "HALT";

const statusConfig: Record<string, { color: string; label: string; dotClass: string }> = {
  active: { color: "text-emerald", label: "Active", dotClass: "status-dot-active" },
  idle: { color: "text-amber", label: "Idle", dotClass: "status-dot-idle" },
  error: { color: "text-rose", label: "Error", dotClass: "status-dot-error" },
  offline: { color: "text-muted-foreground", label: "Offline", dotClass: "status-dot-offline" },
  connected: { color: "text-emerald", label: "Connected", dotClass: "status-dot-active" },
  disconnected: { color: "text-muted-foreground", label: "Disconnected", dotClass: "status-dot-offline" },
  available: { color: "text-emerald", label: "Available", dotClass: "status-dot-active" },
  busy: { color: "text-amber", label: "Busy", dotClass: "status-dot-idle" },
  disabled: { color: "text-muted-foreground", label: "Disabled", dotClass: "status-dot-offline" },
  scaling: { color: "text-cyan", label: "Scaling", dotClass: "status-dot-idle" },
  OK: { color: "text-emerald", label: "OK", dotClass: "status-dot-active" },
  HALT: { color: "text-rose", label: "HALT", dotClass: "status-dot-error" },
};

interface StatusBadgeProps {
  status: string;
  size?: "sm" | "md";
  showDot?: boolean;
  className?: string;
}

export function StatusBadge({ status, size = "sm", showDot = true, className }: StatusBadgeProps) {
  const config = statusConfig[status] || statusConfig.offline;
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 font-medium",
        size === "sm" ? "text-xs" : "text-sm",
        config.color,
        className
      )}
    >
      {showDot && <span className={cn("status-dot", config.dotClass)} />}
      {config.label}
    </span>
  );
}

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  trend?: { value: number; positive: boolean };
  color?: "cyan" | "purple" | "emerald" | "amber" | "rose" | "sky";
  className?: string;
  loading?: boolean;
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon,
  trend,
  color = "cyan",
  className,
  loading = false,
}: MetricCardProps) {
  const colorMap = {
    cyan: "border-cyan/20 hover:border-cyan/40",
    purple: "border-purple/20 hover:border-purple/40",
    emerald: "border-emerald/20 hover:border-emerald/40",
    amber: "border-amber/20 hover:border-amber/40",
    rose: "border-rose/20 hover:border-rose/40",
    sky: "border-sky/20 hover:border-sky/40",
  };
  const textColorMap = {
    cyan: "text-cyan",
    purple: "text-purple",
    emerald: "text-emerald",
    amber: "text-amber",
    rose: "text-rose",
    sky: "text-sky",
  };
  const bgGradientMap = {
    cyan: "from-cyan/5 to-transparent",
    purple: "from-purple/5 to-transparent",
    emerald: "from-emerald/5 to-transparent",
    amber: "from-amber/5 to-transparent",
    rose: "from-rose/5 to-transparent",
    sky: "from-sky/5 to-transparent",
  };

  return (
    <div
      className={cn(
        "glass-card p-4 bg-gradient-to-br",
        bgGradientMap[color],
        colorMap[color],
        className
      )}
    >
      {loading ? (
        <div className="space-y-2">
          <div className="h-3 w-20 rounded bg-secondary/50 animate-pulse" />
          <div className="h-7 w-16 rounded bg-secondary/50 animate-pulse" />
          <div className="h-3 w-24 rounded bg-secondary/50 animate-pulse" />
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between">
            <div className="space-y-1">
              <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {title}
              </p>
              <p className={cn("text-2xl font-bold", textColorMap[color])}>{value}</p>
              {subtitle && <p className="text-xs text-muted-foreground">{subtitle}</p>}
            </div>
            {icon && (
              <div className={cn("p-2 rounded-lg bg-secondary/50", textColorMap[color])}>
                {icon}
              </div>
            )}
          </div>
          {trend && (
            <div className="mt-2 flex items-center gap-1">
              <span
                className={cn(
                  "text-xs font-medium",
                  trend.positive ? "text-emerald" : "text-rose"
                )}
              >
                {trend.positive ? "↑" : "↓"} {Math.abs(trend.value)}%
              </span>
              <span className="text-xs text-muted-foreground">vs last period</span>
            </div>
          )}
        </>
      )}
    </div>
  );
}

interface SectionHeaderProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
  className?: string;
}

export function SectionHeader({ title, description, action, className }: SectionHeaderProps) {
  return (
    <div className={cn("flex items-center justify-between", className)}>
      <div>
        <h2 className="text-lg font-semibold text-foreground">{title}</h2>
        {description && <p className="text-sm text-muted-foreground mt-0.5">{description}</p>}
      </div>
      {action}
    </div>
  );
}

interface RiskGaugeProps {
  value: number;
  max: number;
  label: string;
  className?: string;
}

export function RiskGauge({ value, max, label, className }: RiskGaugeProps) {
  const pct = Math.min((value / max) * 100, 100);
  const color =
    pct < 33 ? "text-emerald" : pct < 66 ? "text-amber" : "text-rose";
  const bgColor =
    pct < 33 ? "bg-emerald" : pct < 66 ? "bg-amber" : "bg-rose";

  return (
    <div className={cn("space-y-1", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground">{label}</span>
        <span className={cn("font-medium", color)}>{value.toFixed(2)}%</span>
      </div>
      <div className="h-2 rounded-full bg-secondary/50">
        <div
          className={cn("h-full rounded-full transition-all duration-500", bgColor)}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("animate-pulse rounded bg-secondary/50", className)} />;
}

export function LoadingCards({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass-card p-4 space-y-3">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-7 w-16" />
          <Skeleton className="h-3 w-24" />
        </div>
      ))}
    </div>
  );
}
