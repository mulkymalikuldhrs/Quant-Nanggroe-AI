"use client";

import { cn } from "@/lib/utils";
import React from "react";

interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "glass" | "glow" | "default" | "outline";
  size?: "sm" | "md" | "lg" | "icon";
  icon?: React.ReactNode;
  iconPosition?: "left" | "right";
  loading?: boolean;
  children?: React.ReactNode;
}

const variantStyles = {
  primary:
    "bg-gradient-to-br from-emerald-500 to-emerald-600 text-white border-emerald-500/30 hover:from-emerald-400 hover:to-emerald-500 active:from-emerald-600 active:to-emerald-700 shadow-[0_0_20px_rgba(16,185,129,0.15)] hover:shadow-[0_0_30px_rgba(16,185,129,0.25)]",
  secondary:
    "bg-white/[0.06] text-white/70 border-white/[0.08] hover:bg-white/[0.10] hover:text-white active:bg-white/[0.04]",
  ghost:
    "text-white/40 hover:text-white/60 hover:bg-white/[0.04] active:bg-white/[0.02] border-transparent",
  danger:
    "bg-red-500/10 text-red-400 border-red-500/20 hover:bg-red-500/20 hover:text-red-300 active:bg-red-500/5",
  glass:
    "glass text-white/80 hover:text-white border-white/[0.10] hover:border-white/[0.16] active:scale-[0.98]",
  glow:
    "bg-gradient-to-br from-purple-500/20 to-cyan-500/20 text-white border-white/[0.12] hover:border-white/[0.20] hover:from-purple-500/30 hover:to-cyan-500/30 shadow-[0_0_20px_rgba(168,85,247,0.08)] hover:shadow-[0_0_30px_rgba(168,85,247,0.15)] active:scale-[0.98]",
  default:
    "bg-white/[0.08] text-white/80 border-white/[0.10] hover:bg-white/[0.12] hover:text-white active:bg-white/[0.06]",
  outline:
    "bg-transparent text-white/60 border-white/[0.12] hover:text-white/80 hover:border-white/[0.20] active:bg-white/[0.02]",
};

const sizeStyles = {
  sm: "h-8 px-3 text-xs rounded-xl gap-1.5",
  md: "h-10 px-4 text-sm rounded-xl gap-2",
  lg: "h-12 px-6 text-base rounded-2xl gap-2.5",
  icon: "h-8 w-8 p-0 rounded-lg",
};

export function Button({
  variant = "primary",
  size = "md",
  icon,
  iconPosition = "right",
  loading = false,
  className,
  children,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(
        "inline-flex items-center justify-center font-medium transition-all duration-200 border",
        "hover:-translate-y-[0.5px] active:translate-y-0 active:scale-[0.98]",
        "disabled:opacity-40 disabled:cursor-not-allowed disabled:hover:translate-y-0 disabled:active:scale-100",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      disabled={disabled || loading}
      {...props}
    >
      {loading && (
        <svg className="animate-spin -ml-1 h-3.5 w-3.5" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}

      {icon && iconPosition === "left" && (
        <span className="w-5 h-5 flex items-center justify-center opacity-70">{icon}</span>
      )}
      {children}
      {icon && iconPosition === "right" && (
        <span className="w-6 h-6 rounded-full bg-white/[0.12] flex items-center justify-center group-hover:bg-white/[0.18] transition-colors flex-shrink-0">
          {icon}
        </span>
      )}
    </button>
  );
}
