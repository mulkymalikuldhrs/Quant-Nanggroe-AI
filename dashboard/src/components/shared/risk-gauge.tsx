"use client";

import { cn } from "@/lib/utils";

interface RiskGaugeProps {
  value: number; // 0 to 1 (or absolute value for maxValue mode)
  label?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  showValue?: boolean;
  sublabel?: string;
  maxValue?: number;
  variant?: string;
}

const sizeMap = {
  sm: { width: 80, height: 44, stroke: 4, fontSize: "text-xs" },
  md: { width: 120, height: 64, stroke: 6, fontSize: "text-sm" },
  lg: { width: 160, height: 84, stroke: 8, fontSize: "text-lg" },
};

export function RiskGauge({
  value,
  label,
  size = "md",
  className,
  showValue = true,
  sublabel,
  maxValue,
  variant,
}: RiskGaugeProps) {
  const config = sizeMap[size];
  // If maxValue is provided, normalize value to 0-1 range
  const normalizedValue = maxValue ? Math.max(0, Math.min(1, value / maxValue)) : value;
  const clampedValue = Math.max(0, Math.min(1, normalizedValue));
  const cx = config.width / 2;
  const cy = config.height * 0.85;
  const radius = Math.min(cx, cy) - config.stroke;
  const arcLength = Math.PI * radius;
  const offset = arcLength * (1 - clampedValue);

  // Color based on value
  const color =
    clampedValue < 0.3 ? "#34d399" :
    clampedValue < 0.6 ? "#fbbf24" :
    "#f87171";

  const label_text =
    clampedValue < 0.3 ? "Low Risk" :
    clampedValue < 0.6 ? "Medium Risk" :
    "High Risk";

  return (
    <div className={cn("flex flex-col items-center", className)}>
      <svg width={config.width} height={config.height} viewBox={`0 0 ${config.width} ${config.height}`}>
        {/* Background arc */}
        <path
          d={`M ${config.stroke},${cy} A ${cx - config.stroke},${cy - config.stroke} 0 0,1 ${config.width - config.stroke},${cy}`}
          fill="none"
          stroke="rgba(255,255,255,0.06)"
          strokeWidth={config.stroke}
          strokeLinecap="round"
        />
        {/* Value arc */}
        <path
          d={`M ${config.stroke},${cy} A ${cx - config.stroke},${cy - config.stroke} 0 0,1 ${config.width - config.stroke},${cy}`}
          fill="none"
          stroke={color}
          strokeWidth={config.stroke}
          strokeLinecap="round"
          strokeDasharray={arcLength}
          strokeDashoffset={offset}
          style={{ transition: "stroke-dashoffset 1s cubic-bezier(0.16, 1, 0.3, 1)" }}
        />
        {/* Glow dot */}
        <circle
          cx={cx + (radius * Math.cos(Math.PI * (1 - clampedValue)))}
          cy={cy + (-radius * Math.sin(Math.PI * (1 - clampedValue)))}
          r={config.stroke * 0.6}
          fill={color}
          filter={`drop-shadow(0 0 6px ${color}80)`}
        />
      </svg>

      {showValue && (
        <div className="text-center -mt-1">
          <span className={cn(
            "font-mono font-bold",
            config.fontSize,
          )}
          style={{ color }}
          >
            {maxValue ? value.toLocaleString() : `${(clampedValue * 100).toFixed(0)}%`}
          </span>
          {label && (
            <p className="text-[10px] text-white/30 mt-0.5">{label}</p>
          )}
          {sublabel && !maxValue && (
            <p className="text-[9px] text-white/20 mt-0.5">{sublabel}</p>
          )}
        </div>
      )}
    </div>
  );
}
