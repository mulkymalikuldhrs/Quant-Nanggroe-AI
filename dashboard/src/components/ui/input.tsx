"use client";

import { cn } from "@/lib/utils";
import React from "react";

interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  icon?: React.ReactNode;
  label?: string;
  error?: string;
}

export const Input = React.forwardRef<HTMLInputElement, InputProps>(
  ({ className, icon, label, error, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="block text-[11px] font-medium text-white/40 uppercase tracking-[0.08em]">
            {label}
          </label>
        )}
        <div className="relative">
          {icon && (
            <div className="absolute left-3 top-1/2 -translate-y-1/2 text-white/20 pointer-events-none">
              {icon}
            </div>
          )}
          <input
            ref={ref}
            className={cn(
              "w-full h-9 rounded-xl bg-white/[0.04] border border-white/[0.08]",
              "text-xs text-white/80 placeholder:text-white/20",
              "focus:outline-none focus:border-emerald-500/30 focus:bg-white/[0.06]",
              "transition-all duration-200",
              icon && "pl-9",
              "px-3",
              error && "border-red-500/30",
              className,
            )}
            {...props}
          />
        </div>
        {error && (
          <p className="text-[10px] text-red-400">{error}</p>
        )}
      </div>
    );
  },
);

Input.displayName = "Input";
