"use client";

import { Card, CardContent } from "@/components/ui/card";
import { cn, formatCurrency, formatPercent } from "@/lib/utils";

interface StatusCardProps {
  title: string;
  value: string | number;
  change?: number;
  changeLabel?: string;
  icon?: React.ReactNode;
  className?: string;
  variant?: "default" | "success" | "danger" | "warning";
}

export function StatusCard({
  title,
  value,
  change,
  changeLabel,
  icon,
  className,
  variant = "default",
}: StatusCardProps) {
  const variantStyles = {
    default: "",
    success: "border-emerald-500/20 shadow-[0_0_20px_rgba(16,185,129,0.06)]",
    danger: "border-red-500/20 shadow-[0_0_20px_rgba(239,68,68,0.06)]",
    warning: "border-amber-500/20 shadow-[0_0_20px_rgba(245,158,11,0.06)]",
  };

  const changeColor = change !== undefined ? (change >= 0 ? "text-emerald-400" : "text-red-400") : "";

  return (
    <Card className={cn(variantStyles[variant], className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between">
          <div className="space-y-1">
            <p className="text-xs font-medium text-white/50 uppercase tracking-wider">{title}</p>
            <p className="text-2xl font-bold text-white font-mono tracking-tight">
              {typeof value === "number" ? formatCurrency(value) : value}
            </p>
            {change !== undefined && (
              <div className="flex items-center gap-1.5">
                <span className={cn("text-xs font-mono font-medium", changeColor)}>
                  {formatPercent(change)}
                </span>
                {changeLabel && (
                  <span className="text-xs text-white/30">{changeLabel}</span>
                )}
              </div>
            )}
          </div>
          {icon && (
            <div className="p-2 rounded-lg bg-white/5 text-white/40">{icon}</div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
