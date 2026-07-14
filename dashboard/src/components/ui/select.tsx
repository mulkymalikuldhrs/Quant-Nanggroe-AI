"use client";

import { cn } from "@/lib/utils";
import React from "react";
import { ChevronDown } from "lucide-react";

interface SelectProps extends React.SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  options: { value: string; label: string }[];
  error?: string;
}

export const Select = React.forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, options, error, ...props }, ref) => {
    return (
      <div className="space-y-1.5">
        {label && (
          <label className="block text-[11px] font-medium text-white/40 uppercase tracking-[0.08em]">
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            className={cn(
              "w-full h-9 rounded-xl bg-white/[0.04] border border-white/[0.08]",
              "text-xs text-white/80 placeholder:text-white/20",
              "focus:outline-none focus:border-emerald-500/30 focus:bg-white/[0.06]",
              "transition-all duration-200 appearance-none cursor-pointer",
              "px-3 pr-9",
              error && "border-red-500/30",
              className,
            )}
            {...props}
          >
            {options.map((opt) => (
              <option key={opt.value} value={opt.value} className="bg-[#0a0a1a] text-white/80">
                {opt.label}
              </option>
            ))}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-white/20 pointer-events-none" />
        </div>
        {error && (
          <p className="text-[10px] text-red-400">{error}</p>
        )}
      </div>
    );
  },
);

Select.displayName = "Select";
