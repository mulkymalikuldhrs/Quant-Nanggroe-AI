"use client";

import React, { useState, useEffect } from "react";
import { cn } from "@/lib/utils";
import { RefreshCw } from "lucide-react";

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
  | "HALT"
  | "processing";

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
  processing: { color: "text-cyan", label: "Processing", dotClass: "status-dot-processing" },
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
        "inline-flex items-center gap-1.5 font-medium px-2 py-0.5 rounded-full border border-transparent transition-all duration-300",
        size === "sm" ? "text-xs" : "text-sm",
        config.color,
        status === "active" || status === "OK" || status === "connected" ? "bg-emerald/10 border-emerald/20" : "",
        status === "error" || status === "HALT" ? "bg-rose/10 border-rose/20" : "",
        status === "processing" ? "bg-cyan/10 border-cyan/20 animate-pulse" : "",
        className
      )}
    >
      {showDot && (
        status === "processing" ? (
          <RefreshCw className="w-3 h-3 animate-spin text-cyan" />
        ) : (
          <span className={cn("status-dot", config.dotClass)} />
        )
      )}
      {config.label}
    </span>
  );
}

// Custom AnimatedNumber component
export function AnimatedNumber({ value, formatter = (v: number) => v.toString() }: { value: number; formatter?: (v: number) => string }) {
  const [displayValue, setDisplayValue] = useState(value);

  useEffect(() => {
    let startTimestamp: number | null = null;
    const duration = 500;
    const startValue = displayValue;
    const endValue = value;

    const step = (timestamp: number) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      // ease-out cubic
      const easeOut = 1 - Math.pow(1 - progress, 3);
      setDisplayValue(startValue + (endValue - startValue) * easeOut);
      
      if (progress < 1) {
        window.requestAnimationFrame(step);
      } else {
        setDisplayValue(endValue);
      }
    };

    if (startValue !== endValue) {
      window.requestAnimationFrame(step);
    }
  }, [value, displayValue]);

  return <span className="tabular-nums">{formatter(displayValue)}</span>;
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
    cyan: "border-cyan/20 hover:border-cyan/40 shadow-[0_0_15px_rgba(6,182,212,0.05)]",
    purple: "border-purple/20 hover:border-purple/40 shadow-[0_0_15px_rgba(139,92,246,0.05)]",
    emerald: "border-emerald/20 hover:border-emerald/40 shadow-[0_0_15px_rgba(16,185,129,0.05)]",
    amber: "border-amber/20 hover:border-amber/40 shadow-[0_0_15px_rgba(245,158,11,0.05)]",
    rose: "border-rose/20 hover:border-rose/40 shadow-[0_0_15px_rgba(244,63,94,0.05)]",
    sky: "border-sky/20 hover:border-sky/40 shadow-[0_0_15px_rgba(14,165,233,0.05)]",
  };
  const textColorMap = {
    cyan: "text-cyan neon-text-cyan",
    purple: "text-purple neon-text-purple",
    emerald: "text-emerald neon-text-emerald",
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

  const isNumeric = typeof value === "number";

  return (
    <div
      className={cn(
        "glass-card p-5 bg-gradient-to-br hover-lift group relative overflow-hidden",
        bgGradientMap[color],
        colorMap[color],
        className
      )}
    >
      <div className={cn("absolute -top-10 -right-10 w-24 h-24 bg-current opacity-[0.02] rounded-full blur-xl group-hover:opacity-[0.05] transition-opacity", textColorMap[color].split(' ')[0])} />
      
      {loading ? (
        <div className="space-y-3">
          <div className="h-3 w-20 rounded bg-secondary/50 animate-pulse" />
          <div className="h-8 w-24 rounded bg-secondary/50 animate-pulse" />
          <div className="h-3 w-32 rounded bg-secondary/50 animate-pulse" />
        </div>
      ) : (
        <>
          <div className="flex items-start justify-between relative z-10">
            <div className="space-y-1.5">
              <p className="text-[11px] font-semibold text-muted-foreground uppercase tracking-widest">
                {title}
              </p>
              <div className={cn("text-3xl font-bold font-mono tracking-tight", textColorMap[color])}>
                {isNumeric ? <AnimatedNumber value={value as number} formatter={(v) => Number.isInteger(value) ? Math.round(v).toString() : v.toFixed(2)} /> : value}
              </div>
              {subtitle && <p className="text-xs text-muted-foreground font-medium">{subtitle}</p>}
            </div>
            {icon && (
              <div className={cn("p-2.5 rounded-xl bg-secondary/40 border border-border/50 group-hover:bg-secondary/60 transition-colors", textColorMap[color].split(' ')[0])}>
                {icon}
              </div>
            )}
          </div>
          {trend && (
            <div className="mt-4 flex items-center gap-1.5 bg-background/50 px-2 py-1 rounded-md w-fit border border-border/30 relative z-10">
              <span
                className={cn(
                  "text-xs font-bold",
                  trend.positive ? "text-emerald" : "text-rose"
                )}
              >
                {trend.positive ? "↑" : "↓"} {Math.abs(trend.value)}%
              </span>
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider">vs last</span>
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
    <div className={cn("flex items-end justify-between border-b border-border/30 pb-4 relative", className)}>
      <div className="space-y-1">
        <h2 className="text-xl font-bold text-foreground flex items-center gap-2">
          {title}
        </h2>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="relative z-10">{action}</div>
      {/* Decorative gradient underline */}
      <div className="absolute bottom-[-1px] left-0 w-32 h-[2px] bg-gradient-to-r from-cyan via-purple to-transparent" />
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
    pct < 33 ? "bg-emerald shadow-[0_0_10px_rgba(16,185,129,0.5)]" : pct < 66 ? "bg-amber shadow-[0_0_10px_rgba(245,158,11,0.5)]" : "bg-rose shadow-[0_0_10px_rgba(244,63,94,0.5)]";

  return (
    <div className={cn("space-y-2", className)}>
      <div className="flex items-center justify-between text-xs">
        <span className="text-muted-foreground font-medium uppercase tracking-wider text-[10px]">{label}</span>
        <span className={cn("font-bold font-mono", color)}><AnimatedNumber value={value} formatter={(v) => v.toFixed(2)} />%</span>
      </div>
      <div className="h-2.5 rounded-full bg-secondary/50 border border-border/50 relative overflow-hidden">
        {/* Threshold markers */}
        <div className="absolute top-0 bottom-0 left-[33%] w-px bg-border/80 z-10" />
        <div className="absolute top-0 bottom-0 left-[66%] w-px bg-border/80 z-10" />
        
        <div
          className={cn("h-full rounded-full transition-all duration-700 ease-out relative", bgColor)}
          style={{ width: `${pct}%` }}
        >
          <div className="absolute inset-0 bg-[linear-gradient(90deg,transparent,rgba(255,255,255,0.2),transparent)] bg-[length:200%_100%] animate-shimmer rounded-full" />
        </div>
      </div>
    </div>
  );
}

export function Skeleton({ className }: { className?: string }) {
  return <div className={cn("shimmer rounded bg-secondary/30", className)} />;
}

export function LoadingCards({ count = 4 }: { count?: number }) {
  return (
    <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
      {Array.from({ length: count }).map((_, i) => (
        <div key={i} className="glass-card p-5 space-y-4">
          <Skeleton className="h-3 w-20" />
          <Skeleton className="h-8 w-24" />
          <Skeleton className="h-3 w-32" />
        </div>
      ))}
    </div>
  );
}
