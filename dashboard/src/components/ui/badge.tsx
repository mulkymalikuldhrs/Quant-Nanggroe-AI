"use client";

import { cn } from "@/lib/utils";

interface BadgeProps {
  children: React.ReactNode;
  className?: string;
  variant?: "default" | "secondary" | "outline" | "success" | "danger" | "warning" | "info";
  size?: "sm" | "md" | "lg";
  pulse?: boolean;
}

const variantStyles = {
  default: "bg-white/[0.06] text-white/50 border-white/[0.08]",
  secondary: "bg-slate-500/10 text-slate-400 border-slate-500/20",
  outline: "bg-transparent text-white/30 border-white/[0.08]",
  success: "bg-emerald-500/10 text-emerald-400 border-emerald-500/20",
  danger: "bg-red-500/10 text-red-400 border-red-500/20",
  warning: "bg-amber-500/10 text-amber-400 border-amber-500/20",
  info: "bg-blue-500/10 text-blue-400 border-blue-500/20",
};

const sizeStyles = {
  sm: "text-[10px] px-1.5 py-0.5",
  md: "text-[11px] px-2.5 py-1",
  lg: "text-xs px-3 py-1.5",
};

export function Badge({
  children,
  className,
  variant = "default",
  size = "sm",
  pulse = false,
}: BadgeProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-full font-medium border transition-all duration-200",
        variantStyles[variant],
        sizeStyles[size],
        pulse && "animate-pulse",
        className,
      )}
    >
      {children}
    </span>
  );
}
