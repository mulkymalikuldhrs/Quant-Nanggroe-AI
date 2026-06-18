"use client";

import { cn } from "@/lib/utils";

interface RiskGaugeProps {
  value: number;
  maxValue?: number;
  label: string;
  sublabel?: string;
  className?: string;
  size?: "sm" | "md" | "lg";
  variant?: "default" | "danger" | "warning" | "safe";
}

export function RiskGauge({
  value,
  maxValue = 100,
  label,
  sublabel,
  className,
  size = "md",
  variant = "default",
}: RiskGaugeProps) {
  const percentage = Math.min(100, Math.max(0, (value / maxValue) * 100));
  const radius = size === "sm" ? 40 : size === "md" ? 56 : 72;
  const strokeWidth = size === "sm" ? 6 : size === "md" ? 8 : 10;
  const circumference = 2 * Math.PI * radius;
  const strokeDashoffset = circumference - (percentage / 100) * circumference;

  const getGaugeColor = () => {
    if (variant === "danger" || percentage > 75) return "#ef4444";
    if (variant === "warning" || percentage > 50) return "#f59e0b";
    if (variant === "safe" || percentage <= 25) return "#10b981";
    return "#3b82f6";
  };

  const color = getGaugeColor();
  const fontSize = size === "sm" ? "text-lg" : size === "md" ? "text-2xl" : "text-3xl";

  return (
    <div className={cn("flex flex-col items-center gap-2", className)}>
      <div className="relative">
        <svg
          width={(radius + strokeWidth) * 2}
          height={(radius + strokeWidth) * 2}
          className="-rotate-90"
        >
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke="rgba(255,255,255,0.06)"
            strokeWidth={strokeWidth}
          />
          <circle
            cx={radius + strokeWidth}
            cy={radius + strokeWidth}
            r={radius}
            fill="none"
            stroke={color}
            strokeWidth={strokeWidth}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={strokeDashoffset}
            className="transition-all duration-1000 ease-out"
            style={{ filter: `drop-shadow(0 0 6px ${color}40)` }}
          />
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <span className={cn("font-mono font-bold text-white", fontSize)}>
            {typeof value === "number" ? value.toFixed(1) : value}
          </span>
          {sublabel && (
            <span className="text-[10px] text-white/40">{sublabel}</span>
          )}
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs font-medium text-white/60">{label}</p>
      </div>
    </div>
  );
}
